from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .config import AppConfig


BASE_URL = "http://127.0.0.1:3000"


def latest_auth_key(exporter_dir: Path) -> str:
    cookie_dir = exporter_dir / ".data" / "kv" / "cookie"
    keys = sorted(cookie_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True) if cookie_dir.exists() else []
    if not keys:
        raise RuntimeError("No WeChat auth key found. Open the exporter web page and scan login first.")
    return keys[0].name


def strip_html(value: Any) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", "", str(value))
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def get_json(path: str, auth_key: str, params: dict[str, Any] | None = None, timeout: int = 40) -> dict[str, Any]:
    response = requests.get(BASE_URL + path, params=params or {}, headers={"X-Auth-Key": auth_key}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response from {path}")
    return data


def search_accounts(cfg: AppConfig, auth_key: str) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for keyword in cfg.wechat_account_search_keywords:
        data = get_json("/api/web/mp/searchbiz", auth_key, {"keyword": keyword, "begin": 0, "size": 5})
        if data.get("base_resp", {}).get("ret") != 0:
            continue
        for item in data.get("list", []):
            fakeid = item.get("fakeid")
            if not fakeid or fakeid in seen:
                continue
            seen.add(fakeid)
            accounts.append(
                {
                    "fakeid": fakeid,
                    "nickname": item.get("nickname") or "",
                    "alias": item.get("alias") or "",
                    "signature": item.get("signature") or "",
                    "source_account_keyword": keyword,
                }
            )
            if len(accounts) >= cfg.wechat_account_limit:
                return accounts
    return accounts


def fetch_article_text(url: str) -> str:
    if not url:
        return ""
    try:
        response = requests.get(BASE_URL + "/api/public/v1/download", params={"url": url, "format": "text"}, timeout=20)
        if response.status_code != 200:
            return ""
        return re.sub(r"\s+", " ", response.text).strip()[:5000]
    except requests.RequestException:
        return ""


def crawl_wechat(cfg: AppConfig) -> Path:
    auth_key = latest_auth_key(cfg.wechat_exporter_dir)
    accounts = search_accounts(cfg, auth_key)
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    for account in accounts:
        for keyword in cfg.wechat_article_keywords:
            data = get_json(
                "/api/public/v1/article",
                auth_key,
                {
                    "fakeid": account["fakeid"],
                    "keyword": keyword,
                    "begin": 0,
                    "size": cfg.wechat_articles_per_keyword,
                },
            )
            if data.get("base_resp", {}).get("ret") != 0:
                continue
            for article in data.get("articles") or []:
                aid = str(article.get("aid") or "")
                link = article.get("link") or ""
                key = link or aid
                if not key or key in seen:
                    continue
                seen.add(key)
                timestamp = article.get("update_time") or article.get("create_time") or ""
                records.append(
                    {
                        "note_id": aid or str(article.get("appmsgid") or key),
                        "id": aid or str(article.get("appmsgid") or key),
                        "title": strip_html(article.get("title") or article.get("highlight_title")),
                        "desc": strip_html(article.get("digest") or article.get("highlight_content")),
                        "content": strip_html(article.get("digest") or article.get("highlight_content")),
                        "nickname": account["nickname"] or article.get("author_name") or "",
                        "source_account": account["nickname"] or article.get("author_name") or "",
                        "author_name": article.get("author_name") or account["nickname"] or "",
                        "time": timestamp,
                        "create_time": timestamp,
                        "url": link,
                        "note_url": link,
                        "cover": article.get("cover") or article.get("cover_img") or "",
                        "source_keyword": keyword,
                        "source_account_keyword": account.get("source_account_keyword", ""),
                        "account_fakeid": account["fakeid"],
                        "account_alias": account.get("alias", ""),
                        "platform": "wechat",
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
                if len(records) >= cfg.wechat_max_articles:
                    break
            if len(records) >= cfg.wechat_max_articles:
                break
            time.sleep(0.25)
        if len(records) >= cfg.wechat_max_articles:
            break

    for record in records[: cfg.wechat_full_text_limit]:
        text = fetch_article_text(record.get("url", ""))
        if text:
            record["content"] = "\n\n".join(part for part in [record.get("desc", ""), text] if part)
        time.sleep(0.15)

    jsonl_dir = cfg.raw_dir / "wechat" / "jsonl"
    jsonl_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    out = jsonl_dir / f"search_contents_{date}.jsonl"
    with out.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    meta = jsonl_dir / f"search_accounts_{date}.json"
    meta.write_text(json.dumps({"accounts": accounts, "record_count": len(records)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
