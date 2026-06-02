"""Sanity-check that every public module imports cleanly (no syntax errors,
no missing names) on a machine with zero API keys."""

import importlib

MODULES = [
    "app",
    "app.cli",
    "app.config",
    "app.db",
    "app.notifier",
    "app.publisher",
    "app.analytics",
    "app.dashboard",
    "app.news_fetcher",
    "app.news_summarizer",
    "app.news_pipeline",
    "app.sources",
    "app.tone_loader",
    "app.viral_memory",
    "app.utils",
    "app.schema",
    "agents.writer",
    "agents.title_generator",
    "agents.title_ranker",
    "agents.critic",
    "agents.analyst",
    "agents.orchestrator",
]


def test_all_modules_import():
    for m in MODULES:
        importlib.import_module(m)
