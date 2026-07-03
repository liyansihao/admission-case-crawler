from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .config import AppConfig


COLUMNS = [
    "platform",
    "source_account",
    "publish_time",
    "url",
    "content_type",
    "raw_text",
    "comments_text",
    "undergraduate_school",
    "undergraduate_major",
    "gpa",
    "gpa_scale",
    "toefl_ielts",
    "gre_gmat",
    "application_region",
    "application_school",
    "application_program",
    "admission_result",
    "admission_year",
    "is_repost",
    "from_image",
    "confidence",
    "needs_review",
    "is_new",
    "notes",
    "source_id",
    "crawl_time",
    "title",
]

REGION_TERMS = {
    "香港": ["香港", "港硕", "港校", "HKU", "CUHK", "HKUST", "CityU", "PolyU"],
    "英国": ["英国", "英硕", "G5", "KCL", "UCL", "Manchester", "Edinburgh"],
    "美国": ["美国", "美研", "US", "USA"],
    "新加坡": ["新加坡", "NUS", "NTU"],
    "澳洲": ["澳洲", "澳大利亚", "Melbourne", "Sydney"],
}

SCHOOL_TERMS = {
    "香港大学": ["香港大学", "港大", "HKU"],
    "香港中文大学": ["香港中文大学", "港中文", "CUHK"],
    "香港科技大学": ["香港科技大学", "港科", "HKUST"],
    "香港城市大学": ["香港城市大学", "港城", "CityU"],
    "新加坡国立大学": ["新加坡国立大学", "NUS"],
    "南洋理工大学": ["南洋理工", "NTU"],
    "伦敦大学学院": ["伦敦大学学院", "UCL"],
    "伦敦国王学院": ["伦敦国王学院", "KCL", "King's College London"],
}


def build_outputs(cfg: AppConfig) -> list[dict[str, Any]]:
    comments = load_comments(cfg.raw_dir)
    records = []
    for platform, raw in load_content_records(cfg.raw_dir):
        note_id = text(raw.get("note_id") or raw.get("id") or "")
        records.append(normalize_record(platform, raw, comments.get(f"{platform}:{note_id}", [])))
    records = dedupe(records)
    mark_incremental(records, cfg.state_file)
    write_outputs(records, cfg.output_dir)
    return records


def load_content_records(raw_dir: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    if not raw_dir.exists():
        return
    for platform_dir in sorted(raw_dir.iterdir()):
        jsonl_dir = platform_dir / "jsonl"
        if not jsonl_dir.exists():
            continue
        for jsonl in sorted(jsonl_dir.glob("*_contents_*.jsonl")):
            for item in read_jsonl(jsonl):
                yield platform_dir.name, item


def load_comments(raw_dir: Path) -> dict[str, list[dict[str, Any]]]:
    by_note: dict[str, list[dict[str, Any]]] = {}
    if not raw_dir.exists():
        return by_note
    for platform_dir in sorted(raw_dir.iterdir()):
        jsonl_dir = platform_dir / "jsonl"
        if not jsonl_dir.exists():
            continue
        for jsonl in sorted(jsonl_dir.glob("*_comments_*.jsonl")):
            for item in read_jsonl(jsonl):
                note_id = text(item.get("note_id"))
                if note_id:
                    by_note.setdefault(f"{platform_dir.name}:{note_id}", []).append(item)
    return by_note


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield value


def normalize_record(platform: str, raw: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]:
    note_id = text(raw.get("note_id") or raw.get("id") or "")
    title = text(raw.get("title") or "")
    body = text(raw.get("desc") or raw.get("content") or raw.get("raw_text") or "")
    raw_text = combine(title, body)
    comments_text = "\n".join(text(item.get("content")) for item in comments if item.get("content"))
    full_text = "\n".join(part for part in [raw_text, comments_text] if part)
    extracted = extract_fields(full_text)
    source_id = f"{platform}:{note_id}" if note_id else f"{platform}:{stable_hash(raw_text)}"
    content_type = classify(full_text)
    needs_review = not bool(raw_text and (raw.get("note_url") or raw.get("url"))) or content_type == "other"
    return {
        "platform": "weibo" if platform == "wb" else platform,
        "source_account": text(raw.get("nickname") or raw.get("source_account") or raw.get("author_name") or ""),
        "publish_time": normalize_time(raw.get("time") or raw.get("create_time") or raw.get("create_date_time")),
        "url": text(raw.get("note_url") or raw.get("url") or ""),
        "content_type": content_type,
        "raw_text": raw_text,
        "comments_text": comments_text,
        "undergraduate_school": extracted["undergraduate_school"],
        "undergraduate_major": extracted["undergraduate_major"],
        "gpa": extracted["gpa"],
        "gpa_scale": extracted["gpa_scale"],
        "toefl_ielts": extracted["toefl_ielts"],
        "gre_gmat": extracted["gre_gmat"],
        "application_region": extracted["application_region"],
        "application_school": extracted["application_school"],
        "application_program": extracted["application_program"],
        "admission_result": extracted["admission_result"],
        "admission_year": extracted["admission_year"],
        "is_repost": bool(raw.get("retweeted_status") or "//@" in full_text or "转发" in full_text),
        "from_image": False,
        "confidence": confidence(extracted, content_type),
        "needs_review": needs_review,
        "is_new": True,
        "notes": "",
        "source_id": source_id,
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": title or first_line(raw_text) or note_id,
    }


def extract_fields(value: str) -> dict[str, str]:
    return {
        "undergraduate_school": first_match(value, [r"(?:本科|本科学校|院校)[:： ]{0,3}([^,，。；;\n]{2,30})"]),
        "undergraduate_major": first_match(value, [r"(?:专业|本科专业)[:： ]{0,3}([^,，。；;\n]{2,30})"]),
        "gpa": first_match(value, [r"GPA[:： ]?([0-9.]{1,4})", r"均分[:： ]?([0-9.]{2,5})"]),
        "gpa_scale": first_match(value, [r"GPA[:： ]?[0-9.]{1,4}\s*/\s*([0-9.]{1,4})"]),
        "toefl_ielts": first_match(value, [r"(?:雅思|IELTS)[:： ]?([0-9.]{1,4})", r"(?:托福|TOEFL)[:： ]?([0-9]{2,3})"]),
        "gre_gmat": first_match(value, [r"(?:GRE|GMAT)[:： ]?([0-9]{2,3})"]),
        "application_region": alias_lookup(value, REGION_TERMS),
        "application_school": alias_lookup(value, SCHOOL_TERMS),
        "application_program": first_match(value, [r"(?:项目|专业|programme|program)[:： ]{0,3}([^,，。；;\n]{2,50})"]),
        "admission_result": result(value),
        "admission_year": first_match(value, [r"(20[0-9]{2})(?:fall|Fall|秋|申请|录取)?"]),
    }


def classify(value: str) -> str:
    if re.search(r"offer|录取|admit|admitted", value, re.I):
        return "admission_case"
    if re.search(r"面经|面试", value):
        return "interview"
    if re.search(r"申请经验|申请复盘|时间线|文书", value):
        return "application_experience"
    return "other"


def result(value: str) -> str:
    if re.search(r"waitlist|wl|候补", value, re.I):
        return "waitlist"
    if re.search(r"拒信|被拒|reject|rejection", value, re.I):
        return "reject"
    if re.search(r"offer|录取|admit|admitted", value, re.I):
        return "offer"
    return ""


def confidence(extracted: dict[str, str], content_type: str) -> str:
    score = sum(bool(extracted.get(key)) for key in ["gpa", "application_school", "admission_result"])
    if content_type == "other":
        return "low"
    return "high" if score >= 2 else "medium"


def dedupe(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in records:
        key = text(record.get("source_id")) or stable_hash(record.get("raw_text", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def mark_incremental(records: list[dict[str, Any]], state_file: Path) -> None:
    previous: set[str] = set()
    if state_file.exists():
        try:
            previous = set(json.loads(state_file.read_text(encoding="utf-8")).get("seen_source_ids", []))
        except json.JSONDecodeError:
            previous = set()
    current = set(previous)
    for record in records:
        source_id = text(record.get("source_id"))
        record["is_new"] = source_id not in previous
        if source_id:
            current.add(source_id)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"seen_source_ids": sorted(current)}, ensure_ascii=False, indent=2), encoding="utf-8")


def write_outputs(records: list[dict[str, Any]], output_dir: Path) -> None:
    excel_dir = output_dir / "excel"
    markdown_dir = output_dir / "markdown"
    excel_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    rows = [{column: excel_value(record.get(column, "")) for column in COLUMNS} for record in records]
    main_xlsx = excel_dir / "admission_cases.xlsx"
    cn_xlsx = excel_dir / "微博小红书公众号录取案例汇总_无False.xlsx"
    pd.DataFrame(rows, columns=COLUMNS).to_excel(main_xlsx, index=False)
    pd.DataFrame(rows, columns=COLUMNS).to_excel(cn_xlsx, index=False)

    for record in records:
        filename = f"{safe_filename(record.get('publish_time') or 'unknown')}_{safe_filename(record.get('source_id'))}.md"
        (markdown_dir / filename).write_text(render_markdown(record), encoding="utf-8")

    summary = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "record_count": len(records),
        "new_count": sum(1 for item in records if item.get("is_new")),
        "needs_review_count": sum(1 for item in records if item.get("needs_review")),
    }
    (output_dir / "update_log.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def render_markdown(record: dict[str, Any]) -> str:
    lines = [
        f"# {record.get('title') or record.get('source_id')}",
        "",
        f"- platform: {record.get('platform', '')}",
        f"- account: {record.get('source_account', '')}",
        f"- publish_time: {record.get('publish_time', '')}",
        f"- url: {record.get('url', '')}",
        f"- result: {record.get('admission_result', '')}",
        f"- school: {record.get('application_school', '')}",
        "",
        "## Raw Text",
        "",
        str(record.get("raw_text", "")),
    ]
    return "\n".join(lines).strip() + "\n"


def combine(title: Any, body: Any) -> str:
    parts = [text(title), text(body)]
    parts = [part for part in parts if part]
    if len(parts) == 2 and parts[0] == parts[1]:
        return parts[0]
    return "\n\n".join(parts)


def normalize_time(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str) and not value.isdigit():
        return text(value)
    try:
        number = int(value)
    except (TypeError, ValueError):
        return text(value)
    if number > 10_000_000_000:
        number //= 1000
    return datetime.fromtimestamp(number).strftime("%Y-%m-%d %H:%M:%S")


def first_match(value: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, value, re.I)
        if match:
            return text(match.group(1))
    return ""


def alias_lookup(value: str, aliases: dict[str, list[str]]) -> str:
    lower = value.lower()
    for label, terms in aliases.items():
        if any(term.lower() in lower for term in terms):
            return label
    return ""


def excel_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "是" if value else ""
    return value


def text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def first_line(value: str) -> str:
    return value.splitlines()[0].strip() if value else ""


def stable_hash(value: Any) -> str:
    return hashlib.sha1(text(value).encode("utf-8")).hexdigest()[:16]


def safe_filename(value: Any) -> str:
    value = text(value).replace(":", "-")
    value = re.sub(r'[<>"/\\|?*\s]+', "_", value)
    return value[:120] or "untitled"
