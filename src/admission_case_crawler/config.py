from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    root: Path
    output_dir: Path
    raw_dir: Path
    state_file: Path
    media_crawler_dir: Path
    wechat_exporter_dir: Path
    keywords: list[str]
    login_type: str
    headless: bool
    get_comments: bool
    max_notes_per_run: int
    max_comments_per_note: int
    wechat_account_search_keywords: list[str]
    wechat_article_keywords: list[str]
    wechat_account_limit: int
    wechat_articles_per_keyword: int
    wechat_max_articles: int
    wechat_full_text_limit: int


def load_config(path: Path) -> AppConfig:
    path = path.resolve()
    root = path.parent
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    project = data.get("project", {})
    third_party = data.get("third_party", {})
    crawl = data.get("crawl", {})
    wechat = data.get("wechat", {})

    def resolve(value: str) -> Path:
        return (root / value).resolve()

    return AppConfig(
        root=root,
        output_dir=resolve(project.get("output_dir", "output")),
        raw_dir=resolve(project.get("raw_dir", "raw")),
        state_file=resolve(project.get("state_file", "output/state.json")),
        media_crawler_dir=resolve(third_party.get("media_crawler_dir", "third_party/MediaCrawler")),
        wechat_exporter_dir=resolve(third_party.get("wechat_exporter_dir", "third_party/wechat-article-exporter")),
        keywords=list(data.get("keywords", [])),
        login_type=str(crawl.get("login_type", "qrcode")),
        headless=bool(crawl.get("headless", False)),
        get_comments=bool(crawl.get("get_comments", True)),
        max_notes_per_run=int(crawl.get("max_notes_per_run", 30)),
        max_comments_per_note=int(crawl.get("max_comments_per_note", 5)),
        wechat_account_search_keywords=list(wechat.get("account_search_keywords", [])),
        wechat_article_keywords=list(wechat.get("article_keywords", [])),
        wechat_account_limit=int(wechat.get("account_limit", 12)),
        wechat_articles_per_keyword=int(wechat.get("articles_per_keyword", 10)),
        wechat_max_articles=int(wechat.get("max_articles", 120)),
        wechat_full_text_limit=int(wechat.get("full_text_limit", 40)),
    )


def ensure_dirs(cfg: AppConfig) -> None:
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    for platform in ("xhs", "weibo", "wechat"):
        (cfg.raw_dir / platform / "jsonl").mkdir(parents=True, exist_ok=True)


def as_bool_text(value: bool) -> str:
    return "yes" if value else "no"


def deep_get(data: dict[str, Any], key: str, default: Any = "") -> Any:
    value = data.get(key)
    return default if value is None else value
