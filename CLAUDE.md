# AI.-asstend

## 项目概览

本仓库集成了 [social-auto-upload](https://github.com/dreammis/social-auto-upload)（11.3k stars）作为多平台社交媒体自动发布 skill，以及 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 作为 A 股行情/财务/资金面等真实数据源 skill。

## 目录结构

```
.
├── social-auto-upload/   # 核心工具（Python 项目）
│   ├── .venv/            # Python 3.12 虚拟环境
│   ├── conf.py           # 配置文件
│   ├── sau_cli.py        # CLI 入口
│   └── skills/           # 原始 skill 文档
├── .claude/
│   ├── skills/           # Claude Code skill 文档
│   │   ├── social-auto-upload/  # 主 skill
│   │   ├── douyin-upload/       # 抖音 skill
│   │   ├── bilibili-upload/     # B站 skill
│   │   ├── xiaohongshu-upload/  # 小红书 skill
│   │   ├── kuaishou-upload/     # 快手 skill
│   │   └── a-stock-data/        # A 股数据源 skill（含独立 .venv）
│   └── commands/         # 自定义斜杠命令
│       ├── sau-douyin.md
│       ├── sau-bilibili.md
│       ├── sau-xiaohongshu.md
│       └── sau-kuaishou.md
└── CLAUDE.md             # 本文件
```

## 支持平台

| 平台 | 登录 | 视频 | 图文 | 定时 |
|------|------|------|------|------|
| 抖音 | ✅ | ✅ | ✅ | ✅ |
| Bilibili | ✅ | ✅ | ❌ | ✅ |
| 小红书 | ✅ | ✅ | ✅ | ✅ |
| 快手 | ✅ | ✅ | ✅ | ✅ |

## 快速开始

### 环境激活

```bash
cd social-auto-upload
source .venv/bin/activate
# 或使用 uv
uv run sau --help
```

### 安装 Chromium（首次/重装）

```bash
cd social-auto-upload
source .venv/bin/activate
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium
```

### 示例：上传视频到抖音

```bash
cd social-auto-upload
source .venv/bin/activate
sau douyin login --account myaccount
sau douyin check --account myaccount
sau douyin upload-video --account myaccount --file video.mp4 --title "我的视频" --desc "视频简介"
```

## 可用斜杠命令

- `/sau-douyin` - 抖音操作
- `/sau-bilibili` - B站操作  
- `/sau-xiaohongshu` - 小红书操作
- `/sau-kuaishou` - 快手操作

## 注意事项

- Python 版本需要 **3.12**（3.11 有 f-string 语法不兼容问题）
- 首次使用需要登录获取 cookie
- Bilibili 登录须在本地终端交互执行（扫码）
- 定时发布格式：`--schedule "2024-12-31 20:00"`
- 多账号通过 `--account <name>` 区分管理

### A 股数据源（a-stock-data skill）

- Skill 文档位于 `.claude/skills/a-stock-data/SKILL.md`，内含可直接运行的 Python 代码片段（腾讯/东财/新浪/通达信/巨潮等多源行情、财务、资金面、公告、打板等数据接口），无需 API Key。
- 依赖安装在独立虚拟环境 `.claude/skills/a-stock-data/.venv/`（与 social-auto-upload 的 3.12 环境互不影响）：
  ```bash
  cd .claude/skills/a-stock-data
  source .venv/bin/activate
  ```
- 已装依赖：`mootdx requests pandas stockstats numpy baostock xlrd openpyxl`
- 主源被官方接口限流/封禁时，按 SKILL.md 中的「备用源速查」降级到备用数据源。
