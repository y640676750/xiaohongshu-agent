"""Unified CLI entry point.

Usage:
    python -m app.cli <command> [args]

Commands:
    news        - 抓取资讯并生成小红书文案推送 (alias: app.news_pipeline)
    batch       - 按主题批量生成 (alias: app.batch_main)
    orchestrate - 多 Agent 协同流水线 (alias: agents.orchestrator)
    publish     - 发布相关操作 (alias: app.publisher)
    report      - 生成数据分析报告 (alias: app.dashboard)
    mcp         - 启动 MCP server
    db-init     - 初始化数据库
"""

from __future__ import annotations

import argparse
import sys

COMMANDS = {
    "news": "app.news_pipeline",
    "batch": "app.batch_main",
    "orchestrate": "agents.orchestrator",
    "publish": "app.publisher",
    "report": "app.dashboard",
    "mcp": "mcp_server.server",
}


def main(argv: list[str] | None = None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return

    cmd = argv[0]
    rest = argv[1:]

    if cmd == "db-init":
        from app.db import init_db

        init_db()
        print("✅ database initialized at", __import__("app.db", fromlist=["DB_PATH"]).DB_PATH)
        return

    if cmd not in COMMANDS:
        print(f"unknown command: {cmd}\n")
        print(__doc__)
        sys.exit(2)

    module_name = COMMANDS[cmd]
    sys.argv = [module_name] + rest
    mod = __import__(module_name, fromlist=["main"])
    mod.main()


if __name__ == "__main__":
    main()
