from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .config import ensure_dirs, load_config
from .default_config import DEFAULT_CONFIG
from .exporter import build_outputs
from .media import patch_media_crawler, run_media_crawler
from .ocr import PaddleOcrEngine
from .wechat import crawl_wechat


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crawl admission cases from Weibo, Xiaohongshu and WeChat articles.")
    parser.add_argument("--config", default="config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")

    crawl_parser = subparsers.add_parser("crawl")
    crawl_parser.add_argument("--platform", choices=["xhs", "weibo", "wechat"], required=True)

    subparsers.add_parser("build")
    subparsers.add_parser("patch")
    subparsers.add_parser("start-wechat")
    subparsers.add_parser("ocr-check")

    args = parser.parse_args(argv)
    config_path = Path(args.config).resolve()

    if args.command == "init":
        if not config_path.exists():
            config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
        cfg = load_config(config_path)
        ensure_dirs(cfg)
        print(f"initialized: {config_path}")
        return 0

    cfg = load_config(config_path)
    ensure_dirs(cfg)

    if args.command == "patch":
        patched = patch_media_crawler(cfg)
        print(f"MediaCrawler CDP proxy patch: {'ok' if patched else 'not-applied'}")
    elif args.command == "crawl":
        if args.platform == "wechat":
            output = crawl_wechat(cfg)
            print(f"wechat raw saved: {output}")
        else:
            run_media_crawler(cfg, args.platform)
    elif args.command == "build":
        records = build_outputs(cfg)
        print(f"built {len(records)} records")
        print(f"excel: {cfg.output_dir / 'excel' / '微博小红书公众号录取案例汇总_无False.xlsx'}")
    elif args.command == "start-wechat":
        start_wechat(cfg.wechat_exporter_dir)
    elif args.command == "ocr-check":
        PaddleOcrEngine(lang=cfg.ocr_lang)
        print("OCR engine: ok")
    return 0


def start_wechat(exporter_dir: Path) -> None:
    if not exporter_dir.exists():
        raise FileNotFoundError(f"WeChat exporter not found: {exporter_dir}")
    command = ["corepack", "yarn", "dev", "--host", "0.0.0.0"]
    subprocess.run(command, cwd=exporter_dir, check=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
