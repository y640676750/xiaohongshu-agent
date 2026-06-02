"""Smoke tests for the SQLite layer.

Designed to run on a clean machine with no API keys. Uses a temp DB path
via the `XHS_DB_PATH` env var.
"""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_xhs.db"
    monkeypatch.setenv("XHS_DB_PATH", str(db_file))
    # Force the module to pick up the new path (it reads env at import time).
    import importlib

    import app.db as db_mod

    importlib.reload(db_mod)
    yield db_mod


def test_init_db_idempotent(isolated_db):
    db = isolated_db
    db.init_db()
    db.init_db()
    assert Path(os.environ["XHS_DB_PATH"]).exists()


def test_upsert_article_and_list(isolated_db):
    db = isolated_db
    aid = db.upsert_article({
        "url": "https://example.com/a",
        "title": "hello",
        "source": "src",
        "category": "AI资讯",
        "snippet": "snippet",
    })
    assert aid > 0
    db.upsert_article({
        "url": "https://example.com/a",
        "title": "hello v2",
        "source": "src",
        "category": "AI资讯",
        "score": 8,
    })
    rows = db.list_recent_articles(limit=5)
    assert len(rows) == 1
    assert rows[0]["title"] == "hello v2"
    assert rows[0]["score"] >= 8


def test_post_lifecycle(isolated_db):
    db = isolated_db
    pid = db.create_post(
        topic="AI资讯",
        body="测试正文",
        title="测试标题",
        hashtags=["AI", "工具"],
        quality_score=8.0,
    )
    assert pid > 0
    post = db.get_post(pid)
    assert post and post["status"] == "draft"
    db.update_post(pid, status="scheduled", scheduled_at="2099-01-01T00:00:00+00:00")
    assert db.get_post(pid)["status"] == "scheduled"


def test_metrics_aggregate(isolated_db):
    db = isolated_db
    pid = db.create_post(topic="AI使用技巧", body="...", title="t1")
    db.add_metrics(pid, impressions=1000, likes=100, comments=20)
    db.add_metrics(pid, impressions=2000, likes=200, comments=40)
    latest = db.latest_metrics_per_post()
    assert len(latest) == 1
    assert latest[0]["impressions"] == 2000


def test_events(isolated_db):
    db = isolated_db
    db.log_event("run1", "writer", "wrote a post", meta={"k": 1})
    evts = db.list_events("run1")
    assert evts and evts[0]["agent"] == "writer"
