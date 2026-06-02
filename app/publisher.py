"""Auto publishing engine.

Responsibilities:
  * persist drafts to the SQLite store
  * schedule drafts for future publishing
  * dispatch due drafts to a publishing backend
  * record synthetic / real metrics in the metrics table

Publishing backend selection
----------------------------
The real Xiaohongshu publish API is not officially public. To keep the
project runnable in CI and on a laptop, we ship two backends and pick by
the env var `XHS_PUBLISHER_BACKEND`:

  * ``mock`` (default) - writes posts to ``outputs/published/`` and emits
    a Telegram notification. Generates synthetic metrics so the analytics
    pipeline has something to chew on.
  * ``webhook`` - POSTs the post to ``XHS_PUBLISH_WEBHOOK`` (any HTTP
    endpoint you control, e.g. a self-hosted browser-automation worker
    that uses xhs-cli / Playwright cookies). Backend returns ``{"id": ..., "url": ...}``.

This lets the project work today and easily plug into a real workflow
later, without changing the orchestrator or the MCP server.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

from app import db
from app.notifier import send_telegram, send_telegram_file

PUBLISHED_DIR = Path("outputs/published")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_first_title(body: str) -> Optional[str]:
    """Heuristic: find the first plausible title in a writer's output."""
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^[\-\*\d\.\)】\s]+", "", line).strip()
        cleaned = re.sub(r"^(标题[\d:：]*\s*)", "", cleaned).strip()
        if 4 <= len(cleaned) <= 40:
            return cleaned
    return None


def _extract_hashtags(body: str) -> list[str]:
    """Pick up #foo or `# foo` hashtags from the writer output."""
    tags = re.findall(r"#([\w\u4e00-\u9fff]+)", body)
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:15]


def save_draft(
    body: str,
    *,
    topic: str | None = None,
    style: str | None = None,
    article_url: str | None = None,
    title: str | None = None,
    titles_candidates: str | None = None,
    titles_ranked: str | None = None,
    quality_score: float = 0.0,
    critic_feedback: str | None = None,
) -> int:
    """Persist a draft post returned by the writer."""
    title = title or _extract_first_title(body)
    hashtags = _extract_hashtags(body)
    return db.create_post(
        topic=topic,
        style=style,
        article_url=article_url,
        title=title,
        body=body,
        titles_candidates=titles_candidates,
        titles_ranked=titles_ranked,
        hashtags=hashtags,
        status="draft",
        quality_score=quality_score,
        critic_feedback=critic_feedback,
    )


def schedule_post(post_id: int, at: datetime | str) -> dict:
    """Move a draft to status='scheduled' with a future publish time."""
    if isinstance(at, datetime):
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        at_iso = at.isoformat()
    else:
        at_iso = at
    db.update_post(post_id, status="scheduled", scheduled_at=at_iso)
    return {"post_id": post_id, "scheduled_at": at_iso, "status": "scheduled"}


def schedule_in(post_id: int, minutes: int) -> dict:
    at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return schedule_post(post_id, at)


# ───────────────────────── publishing backends ─────────────────────────


class MockBackend:
    """Write the post to disk and notify Telegram. Used in CI / local dev."""

    name = "mock"

    def publish(self, post: dict) -> dict:
        PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = PUBLISHED_DIR / f"published_{post['id']}_{ts}.md"
        title = post.get("title") or "(未命名)"
        hashtags = " ".join(f"#{t}" for t in json.loads(post.get("hashtags") or "[]"))
        body = post.get("body") or ""
        path.write_text(
            f"# {title}\n\n来源链接: {post.get('article_url') or '-'}\n\n{body}\n\n{hashtags}\n",
            encoding="utf-8",
        )
        send_telegram(
            "🚀 [模拟发布] 新文案已发布\n"
            f"标题: {title}\n"
            f"主题: {post.get('topic') or '-'}\n"
            f"文件: {path}"
        )
        send_telegram_file(str(path), f"📎 已发布文案 #{post['id']}")
        return {
            "id": f"mock-{post['id']}-{ts}",
            "url": f"file://{path.resolve().as_posix()}",
        }


class WebhookBackend:
    """POST the post payload to a user-defined HTTP endpoint.

    The endpoint should return JSON ``{"id": str, "url": str}``.
    Provide the URL via env ``XHS_PUBLISH_WEBHOOK``. Optional token via
    ``XHS_PUBLISH_TOKEN`` is sent as ``Authorization: Bearer …``.
    """

    name = "webhook"

    def __init__(self, url: str | None = None, token: str | None = None):
        self.url = url or os.getenv("XHS_PUBLISH_WEBHOOK", "")
        self.token = token or os.getenv("XHS_PUBLISH_TOKEN", "")
        if not self.url:
            raise RuntimeError(
                "WebhookBackend requires XHS_PUBLISH_WEBHOOK env var"
            )

    def publish(self, post: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {
            "title": post.get("title"),
            "body": post.get("body"),
            "hashtags": json.loads(post.get("hashtags") or "[]"),
            "topic": post.get("topic"),
            "source_url": post.get("article_url"),
        }
        r = requests.post(self.url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json() if r.content else {}
        return {
            "id": data.get("id") or f"webhook-{post['id']}",
            "url": data.get("url", ""),
        }


def get_backend() -> MockBackend | WebhookBackend:
    name = (os.getenv("XHS_PUBLISHER_BACKEND") or "mock").strip().lower()
    if name == "webhook":
        return WebhookBackend()
    return MockBackend()


# ─────────────────────────── publish workflow ───────────────────────────


def publish_now(post_id: int, *, simulate_metrics: bool = True) -> dict:
    """Publish a specific post immediately."""
    post = db.get_post(post_id)
    if not post:
        raise ValueError(f"post {post_id} not found")
    backend = get_backend()
    try:
        result = backend.publish(post)
        db.update_post(
            post_id,
            status="published",
            published_at=_now(),
            platform_post_id=result.get("id"),
        )
        db.log_event(
            run_id=f"publish-{post_id}",
            agent="publisher",
            message=f"published via {backend.name}",
            meta={"result": result},
        )
        if simulate_metrics and isinstance(backend, MockBackend):
            _seed_mock_metrics(post_id)
        return {"ok": True, "post_id": post_id, "backend": backend.name, **result}
    except Exception as e:
        db.update_post(post_id, status="failed", error=str(e))
        db.log_event(
            run_id=f"publish-{post_id}",
            agent="publisher",
            message=f"publish failed: {e}",
            level="error",
        )
        return {"ok": False, "post_id": post_id, "error": str(e)}


def publish_due(*, limit: int = 10) -> list[dict]:
    """Publish every post that is due now."""
    posts = db.list_due_posts()[:limit]
    return [publish_now(p["id"]) for p in posts]


def _seed_mock_metrics(post_id: int) -> None:
    """Generate plausible-looking metrics for the mock backend.

    This is only there so the analytics report has something to show
    when nobody hooks up real platform metrics. Roughly mimics XHS:
    impressions in the thousands, single-digit % engagement.
    """
    impressions = random.randint(500, 8000)
    likes = int(impressions * random.uniform(0.02, 0.09))
    comments = max(0, int(likes * random.uniform(0.05, 0.20)))
    collects = max(0, int(likes * random.uniform(0.10, 0.40)))
    shares = max(0, int(likes * random.uniform(0.02, 0.10)))
    follows = max(0, int(likes * random.uniform(0.0, 0.05)))
    db.add_metrics(
        post_id,
        impressions=impressions,
        likes=likes,
        comments=comments,
        shares=shares,
        collects=collects,
        follows=follows,
    )


def record_metrics(
    post_id: int,
    *,
    impressions: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    collects: int = 0,
    follows: int = 0,
) -> int:
    """Public helper - external worker (or MCP client) reports real numbers."""
    return db.add_metrics(
        post_id,
        impressions=impressions,
        likes=likes,
        comments=comments,
        shares=shares,
        collects=collects,
        follows=follows,
    )


# ──────────────────────────────── CLI ────────────────────────────────


def main():
    import argparse
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="小红书自动发帖引擎")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出指定状态的文案")
    p_list.add_argument("--status", default=None)
    p_list.add_argument("--limit", type=int, default=20)

    p_pub = sub.add_parser("publish", help="立即发布指定文案")
    p_pub.add_argument("post_id", type=int)

    p_due = sub.add_parser("publish-due", help="发布所有到期定时文案")
    p_due.add_argument("--limit", type=int, default=10)

    p_sch = sub.add_parser("schedule", help="把草稿安排到未来发布")
    p_sch.add_argument("post_id", type=int)
    p_sch.add_argument("--in-minutes", type=int, default=0)
    p_sch.add_argument("--at", type=str, default=None, help="ISO 时间")

    p_met = sub.add_parser("metrics", help="手动写入互动数据")
    p_met.add_argument("post_id", type=int)
    p_met.add_argument("--impressions", type=int, default=0)
    p_met.add_argument("--likes", type=int, default=0)
    p_met.add_argument("--comments", type=int, default=0)
    p_met.add_argument("--shares", type=int, default=0)
    p_met.add_argument("--collects", type=int, default=0)
    p_met.add_argument("--follows", type=int, default=0)

    args = ap.parse_args()

    if args.cmd == "list":
        rows = db.list_posts(status=args.status, limit=args.limit)
        for r in rows:
            print(
                f"[{r['id']:>4}] {r['status']:<10} {r['topic'] or '-':<10} "
                f"{(r['title'] or '')[:40]}"
            )
        return

    if args.cmd == "publish":
        print(json.dumps(publish_now(args.post_id), ensure_ascii=False, indent=2))
        return

    if args.cmd == "publish-due":
        results = publish_due(limit=args.limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if args.cmd == "schedule":
        if args.at:
            r = schedule_post(args.post_id, args.at)
        else:
            r = schedule_in(args.post_id, args.in_minutes)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    if args.cmd == "metrics":
        mid = record_metrics(
            args.post_id,
            impressions=args.impressions,
            likes=args.likes,
            comments=args.comments,
            shares=args.shares,
            collects=args.collects,
            follows=args.follows,
        )
        print(json.dumps({"metrics_id": mid}, ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
