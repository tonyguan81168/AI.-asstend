---
name: social-auto-upload
description: 多平台社交媒体自动发布工具。当用户需要向抖音、B站、小红书、快手上传视频或图文时使用。项目路径：social-auto-upload/，CLI 入口：sau。支持登录、cookie 校验、视频上传、图文发布和定时发布。
---

# social-auto-upload Skill

GitHub 项目：https://github.com/dreammis/social-auto-upload（11.3k stars）

支持平台：抖音、Bilibili、小红书、快手、视频号、百家号、TikTok

## 快速开始

项目已安装在 `social-auto-upload/` 目录，使用 Python 3.12 虚拟环境。

### 激活环境

```bash
cd social-auto-upload
source .venv/bin/activate
```

或直接用 uv 运行：

```bash
cd social-auto-upload && uv run sau --help
```

### 验证安装

```bash
sau --help
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
```

## 已接入平台 CLI

| 平台 | 登录 | 视频上传 | 图文上传 | 定时发布 |
|------|------|----------|----------|----------|
| 抖音 | `sau douyin login` | ✅ | ✅ | ✅ |
| Bilibili | `sau bilibili login` | ✅ | ❌ | ✅ |
| 小红书 | `sau xiaohongshu login` | ✅ | ✅ | ✅ |
| 快手 | `sau kuaishou login` | ✅ | ✅ | ✅ |

## 通用工作流

1. 激活虚拟环境（或用 `uv run`）
2. 登录目标平台账号：`sau <platform> login --account <name>`
3. 校验 cookie：`sau <platform> check --account <name>`
4. 上传内容：`sau <platform> upload-video ...` 或 `upload-note ...`

## 平台专属 Skill

每个平台有独立 skill，包含详细命令契约和故障排查：

- `.claude/skills/douyin-upload/` - 抖音
- `.claude/skills/bilibili-upload/` - B站
- `.claude/skills/xiaohongshu-upload/` - 小红书
- `.claude/skills/kuaishou-upload/` - 快手

## 环境要求

- Python 3.12（3.11 有语法不兼容问题）
- uv 包管理器
- patchright + Chromium（浏览器自动化）
- conf.py（已从 conf.example.py 复制）

## 安装/重新安装

```bash
cd social-auto-upload
uv venv --python python3.12
source .venv/bin/activate
uv pip install -e .
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium
```

## 注意事项

- 登录时如果生成二维码图片，直接展示图片给用户扫码，不要只返回路径
- Bilibili 登录需要用户在本地真实终端交互执行
- 定时发布使用 `--schedule "YYYY-MM-DD HH:MM"` 格式
- 多账号管理通过 `--account <name>` 区分，每个账号名对应独立 cookie 文件
