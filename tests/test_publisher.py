"""Tests for the publisher engine using the mock backend (no network)."""

import importlib
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("XHS_DB_PATH", str(db_file))
    monkeypatch.setenv("XHS_PUBLISHER_BACKEND", "mock")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")

    cwd = Path.cwd()
    monkeypatch.chdir(tmp_path)

    import app.db as db_mod

    importlib.reload(db_mod)
    import app.publisher as publisher_mod

    importlib.reload(publisher_mod)
    yield publisher_mod, db_mod

    os.chdir(str(cwd))


def test_save_and_publish_flow(isolated):
    publisher, db = isolated
    body = (
        "1) 标题：用 AI 把 PPT 时间砍半 #AI #效率\n"
        "2) 正文：今天分享一个实测效率翻倍的工作流……\n"
        "标签：#AI #ChatGPT #效率工具 #职场\n"
    )
    pid = publisher.save_draft(body=body, topic="AI使用技巧", style="效率提升")
    assert pid > 0

    res = publisher.publish_now(pid, simulate_metrics=True)
    assert res["ok"] is True
    post = db.get_post(pid)
    assert post["status"] == "published"
    assert post["platform_post_id"]

    latest = db.latest_metrics_per_post()
    assert latest and latest[0]["post_id"] == pid


def test_schedule_and_publish_due(isolated):
    publisher, db = isolated
    pid = publisher.save_draft(body="正文 #AI", topic="AI资讯")
    publisher.schedule_post(pid, "2000-01-01T00:00:00+00:00")  # in the past

    results = publisher.publish_due()
    assert results and results[0]["ok"] is True
    post = db.get_post(pid)
    assert post["status"] == "published"


def test_extract_title(isolated):
    publisher, _ = isolated
    body = "标题1: 别再手动写汇报了\n正文：……"
    assert publisher._extract_first_title(body)
