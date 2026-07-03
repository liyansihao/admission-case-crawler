from __future__ import annotations

DEFAULT_CONFIG = """# Admission case crawler config

project:
  output_dir: output
  raw_dir: raw
  state_file: output/state.json

third_party:
  media_crawler_dir: third_party/MediaCrawler
  wechat_exporter_dir: third_party/wechat-article-exporter

crawl:
  login_type: qrcode
  headless: false
  get_comments: true
  max_notes_per_run: 30
  max_comments_per_note: 5

keywords:
  - 港硕录取
  - 香港留学录取
  - 留学录取案例
  - 英国硕士录取
  - 美国硕士录取
  - 新加坡硕士录取
  - offer
  - 上岸

wechat:
  account_search_keywords:
    - 港硕录取
    - 香港留学录取
    - 留学录取案例
    - 英国硕士录取
    - 美国硕士录取
    - 新加坡硕士录取
  article_keywords:
    - offer
    - Offer
    - 录取
    - 录取案例
    - 港硕
    - 香港
    - 申请
    - 上岸
  account_limit: 12
  articles_per_keyword: 10
  max_articles: 120
  full_text_limit: 40
"""
