# 微博小红书公众号录取案例采集器

一套本地采集工具：抓取微博、小红书、微信公众号文章里的留学录取案例，合并导出 Excel 和 Markdown。

## 包含项目

- `NanmiCoder/MediaCrawler`：用于小红书、微博抓取。
- `wechat-article/wechat-article-exporter`：用于微信公众号文章搜索和导出。
- 本仓库的 `admission_case_crawler`：统一调度、去重、字段抽取、合并导出。

## 环境要求

- Windows 10/11
- Git
- Python 3.11+
- Node.js 22+
- Chrome

## 第一次安装

```powershell
.\setup.ps1
```

如果需要识别小红书/微博图片上的文字，使用：

```powershell
.\setup.ps1 -InstallOCR
```

然后在 `config.yaml` 打开：

```yaml
ocr:
  enabled: true
```

验证 OCR：

```powershell
.\run.ps1 ocr-check
```

安装脚本会自动：

- 克隆两个开源项目到 `third_party/`
- 安装 Python 依赖
- 安装 MediaCrawler 依赖
- 安装公众号导出器依赖
- 生成 `config.yaml`
- 修复 MediaCrawler 本地 CDP 代理问题
- 可选安装 PaddleOCR，用于识别小红书/微博图片文字

安装为 Codex 技能：

```powershell
.\install_skill.ps1
```

## 使用

编辑 `config.yaml` 里的关键词后运行：

```powershell
.\run.ps1 crawl-xhs
.\run.ps1 crawl-weibo
```

微信公众号需要扫码登录：

```powershell
.\run.ps1 start-wechat
```

打开 [http://127.0.0.1:3000](http://127.0.0.1:3000) 扫码登录后，在另一个 PowerShell 运行：

```powershell
.\run.ps1 crawl-wechat
```

最后合并导出：

```powershell
.\run.ps1 build
```

输出文件：

```text
output/excel/微博小红书公众号录取案例汇总_无False.xlsx
```

开启 OCR 后，图片文字会参与字段抽取，并写入：

- `逐条案例` 工作表的“其他补充”
- `图片页索引` 工作表的“处理状态 / 备注”
- 对应 Markdown 文件的 `OCR Text` 段落

## 数据字段

核心字段包括：

- 平台
- 账号
- 发布时间
- 链接
- 标题
- 原文
- 评论
- 本科院校
- GPA
- 申请地区
- 申请学校
- 申请项目
- 录取结果
- 是否新增
- 是否需要人工复核

## 注意

- 小红书、微博、公众号都可能需要扫码登录。
- 公众号登录态通常有有效期，过期后重新扫码。
- 本工具只导出本地文件，不上传客户数据。
- 请遵守平台规则和内容版权，仅采集授权或合规范围内的数据。
