---
name: admission-case-collector
description: Use this skill to collect overseas admission cases from Xiaohongshu, Weibo, and WeChat official account articles, then merge them into one Excel/Markdown dataset with deduplication and review fields.
---

# Admission Case Collector

Use this skill when the user wants to crawl, update, merge, or analyze admission case data from:

- Xiaohongshu
- Weibo
- WeChat official account articles

## Workflow

1. Confirm the project folder contains this repository.
2. Run `.\setup.ps1` once if `.venv` or `third_party/` is missing.
3. If image text recognition is requested, run `.\setup.ps1 -InstallOCR` and set `ocr.enabled: true` in `config.yaml`.
4. Edit `config.yaml` keywords if the user gives a target region, school, program, or platform.
5. Crawl platforms:
   - Xiaohongshu: `.\run.ps1 crawl-xhs`
   - Weibo: `.\run.ps1 crawl-weibo`
   - WeChat: run `.\run.ps1 start-wechat`, ask the user to scan login at `http://127.0.0.1:3000`, then run `.\run.ps1 crawl-wechat`
6. Build the merged file with `.\run.ps1 build`.
7. Report the Excel path and per-platform row counts.

## Output

The primary output is:

`output/excel/微博小红书公众号录取案例汇总_无False.xlsx`

Do not expose or commit login cookies, raw customer data, `.venv`, `node_modules`, or `output/` unless the user explicitly asks.

## Failure handling

- If GitHub upload fails, check `gh auth status` first.
- If WeChat crawl fails, ensure the exporter server is running and the user has scanned login.
- If Weibo CDP fails with proxy errors, run `.\run.ps1 patch`.
- If OCR fails with missing PaddleOCR dependencies, run `.\setup.ps1 -InstallOCR` with Python 3.11 or 3.12.
- If platform login is required, open the browser and let the user scan rather than trying to bypass login.
