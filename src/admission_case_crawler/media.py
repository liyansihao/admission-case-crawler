from __future__ import annotations

import subprocess
from pathlib import Path

from .config import AppConfig, as_bool_text


def run_media_crawler(cfg: AppConfig, platform: str) -> None:
    if platform not in {"xhs", "wb", "weibo"}:
        raise ValueError("platform must be xhs or weibo")
    if not cfg.media_crawler_dir.exists():
        raise FileNotFoundError(f"MediaCrawler not found: {cfg.media_crawler_dir}")

    media_platform = "wb" if platform == "weibo" else platform
    save_dir = str(cfg.raw_dir)
    keywords = ",".join(cfg.keywords)
    command = [
        "uv",
        "run",
        "main.py",
        "--platform",
        media_platform,
        "--lt",
        cfg.login_type,
        "--type",
        "search",
        "--save_data_option",
        "jsonl",
        "--save_data_path",
        save_dir,
        "--crawler_max_notes_count",
        str(cfg.max_notes_per_run),
        "--max_comments_count_singlenotes",
        str(cfg.max_comments_per_note),
        "--get_comment",
        as_bool_text(cfg.get_comments),
        "--headless",
        as_bool_text(cfg.headless),
        "--keywords",
        keywords,
    ]
    subprocess.run(command, cwd=cfg.media_crawler_dir, check=True)


def patch_media_crawler(cfg: AppConfig) -> bool:
    """Avoid local CDP requests being sent through system proxies."""
    target = cfg.media_crawler_dir / "tools" / "cdp_browser.py"
    if not target.exists():
        return False
    text = target.read_text(encoding="utf-8")
    old = "httpx.AsyncClient()"
    new = "httpx.AsyncClient(trust_env=False)"
    if new in text:
        return True
    if old not in text:
        return False
    target.write_text(text.replace(old, new), encoding="utf-8")
    return True
