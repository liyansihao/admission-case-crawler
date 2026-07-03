from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .config import AppConfig


class OcrUnavailable(RuntimeError):
    pass


class PaddleOcrEngine:
    def __init__(self, lang: str = "ch") -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OcrUnavailable(
                "PaddleOCR is not installed. Run setup.ps1 -InstallOCR, or set ocr.enabled: false in config.yaml."
            ) from exc
        try:
            self._engine = PaddleOCR(use_angle_cls=True, lang=lang)
        except TypeError:
            self._engine = PaddleOCR(lang=lang)

    def read_text(self, image_path: Path) -> str:
        if hasattr(self._engine, "ocr"):
            try:
                result = self._engine.ocr(str(image_path), cls=True)
            except TypeError:
                result = self._engine.ocr(str(image_path))
        elif hasattr(self._engine, "predict"):
            result = self._engine.predict(str(image_path))
        else:
            raise OcrUnavailable("Unsupported PaddleOCR engine API.")
        return "\n".join(unique_texts(_extract_ocr_texts(result)))


def enrich_raw_with_ocr(
    cfg: AppConfig,
    platform: str,
    note_id: str,
    raw: dict[str, Any],
    engine: PaddleOcrEngine | None = None,
) -> dict[str, Any]:
    if not cfg.ocr_enabled:
        return raw
    normalized_platform = "weibo" if platform == "wb" else platform
    if normalized_platform not in cfg.ocr_platforms:
        return raw

    image_urls = extract_image_urls(raw)
    if not image_urls:
        return raw

    engine = engine or PaddleOcrEngine(lang=cfg.ocr_lang)
    image_dir = cfg.ocr_image_dir / normalized_platform / safe_segment(note_id or stable_hash(json.dumps(raw, ensure_ascii=False)))
    image_dir.mkdir(parents=True, exist_ok=True)

    ocr_texts: list[str] = []
    local_paths: list[str] = []
    for index, url in enumerate(image_urls[: cfg.ocr_max_images_per_record], start=1):
        image_path = download_image(url, image_dir, index)
        if not image_path:
            continue
        local_paths.append(str(image_path))
        text = engine.read_text(image_path)
        if text:
            ocr_texts.append(text)

    if ocr_texts:
        raw = dict(raw)
        existing = clean_text(raw.get("ocr_text"))
        raw["ocr_text"] = "\n\n".join(part for part in [existing, *ocr_texts] if part)
        raw["ocr_image_paths"] = local_paths
    return raw


def extract_image_urls(raw: dict[str, Any]) -> list[str]:
    candidates: list[Any] = [
        raw.get("image_list"),
        raw.get("images"),
        raw.get("pictures"),
        raw.get("pic_urls"),
        raw.get("cover"),
        raw.get("cover_img"),
    ]
    urls: list[str] = []
    for candidate in candidates:
        urls.extend(parse_url_list(candidate))
    return [url for url in unique_texts(urls) if url.startswith(("http://", "https://"))]


def download_image(url: str, image_dir: Path, index: int) -> Path | None:
    suffix = suffix_from_url(url)
    path = image_dir / f"{index:02d}_{stable_hash(url)}{suffix}"
    if path.exists() and path.stat().st_size > 0:
        return path
    try:
        response = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException:
        return None
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/") and not suffix:
        return None
    if suffix == "":
        suffix = suffix_from_content_type(content_type)
        path = path.with_suffix(suffix)
    path.write_bytes(response.content)
    return path if path.exists() and path.stat().st_size > 0 else None


def parse_url_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(parse_url_list(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(parse_url_list(item))
        return out
    raw = clean_text(value)
    try:
        parsed = json.loads(raw)
        return parse_url_list(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    return [part.strip() for part in re.split(r"[,，\n ]+", raw) if part.strip()]


def _extract_ocr_texts(value: Any) -> list[str]:
    texts: list[str] = []
    if value is None:
        return texts
    if isinstance(value, dict):
        for key in ("rec_texts", "texts"):
            item = value.get(key)
            if isinstance(item, list):
                texts.extend(clean_text(text) for text in item if clean_text(text))
        for key in ("text", "transcription"):
            item = value.get(key)
            if isinstance(item, str) and clean_text(item):
                texts.append(clean_text(item))
        for item in value.values():
            if isinstance(item, (dict, list, tuple)):
                texts.extend(_extract_ocr_texts(item))
        return texts
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and isinstance(value[1], (list, tuple)) and value[1] and isinstance(value[1][0], str):
            texts.append(clean_text(value[1][0]))
        for item in value:
            if isinstance(item, (dict, list, tuple)):
                texts.extend(_extract_ocr_texts(item))
        return texts
    return texts


def unique_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        value = clean_text(value)
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def suffix_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        return suffix
    return ""


def suffix_from_content_type(content_type: str) -> str:
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "bmp" in content_type:
        return ".bmp"
    return ".jpg"


def stable_hash(value: Any) -> str:
    return hashlib.sha1(clean_text(value).encode("utf-8")).hexdigest()[:16]


def safe_segment(value: Any) -> str:
    value = clean_text(value)
    value = re.sub(r'[<>"/\\|?*\s:]+', "_", value)
    return value[:80] or "item"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()
