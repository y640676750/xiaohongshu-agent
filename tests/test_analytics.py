"""Tests for analytics aggregation + dashboard rendering."""

import importlib
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_xhs.db"
    monkeypatch.setenv("XHS_DB_PATH", str(db_file))
    import app.db as db_mod

    importlib.reload(db_mod)
    import app.analytics as analytics_mod

    importlib.reload(analytics_mod)
    import app.dashboard as dashboard_mod

    importlib.reload(dashboard_mod)
    yield db_mod


def _seed(db):
    p1 = db.create_post(topic="AI资讯", body="b1", title="资讯1")
    p2 = db.create_post(topic="AI使用技巧", body="b2", title="技巧1")
    db.add_metrics(p1, impressions=1000, likes=50, comments=10, collects=20)
    db.add_metrics(p2, impressions=4000, likes=400, comments=80, collects=60, follows=8)
    return p1, p2


def test_summary_after_seed(isolated_db):
    from app import analytics, db

    _seed(db)
    s = analytics.summary(days=30)
    assert s["total_posts"] == 2
    assert s["total_impressions"] == 5000
    assert s["avg_engagement_rate"] > 0


def test_top_posts_order(isolated_db):
    from app import analytics, db

    _seed(db)
    top = analytics.top_posts(limit=5)
    assert len(top) == 2
    assert top[0]["title"] == "技巧1"  # higher engagement wins


def test_render_markdown_has_table(isolated_db):
    from app import db, dashboard

    _seed(db)
    md = dashboard.render_markdown(14)
    assert "总文案数" in md
    assert "Top 10 文案" in md
    assert "技巧1" in md


def test_render_telegram_short(isolated_db):
    from app import db, dashboard

    _seed(db)
    tg = dashboard.render_telegram(7)
    assert "数据日报" in tg
    assert len(tg) < 1500


def test_export_report_writes_files(isolated_db, tmp_path):
    from app import db, dashboard

    _seed(db)
    out = dashboard.write_report(out_dir=str(tmp_path), days=14)
    assert Path(out["md"]).exists()
    assert Path(out["html"]).exists()
    assert Path(out["json"]).exists()
