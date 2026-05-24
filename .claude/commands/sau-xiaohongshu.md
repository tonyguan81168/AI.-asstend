---
description: 小红书内容上传：登录、校验 cookie、上传视频/图文笔记。用法：/sau-xiaohongshu [login|check|upload-video|upload-note] --account <name>
---

参考 `.claude/skills/xiaohongshu-upload/SKILL.md` 执行小红书操作。

操作步骤：
1. 确认在 `social-auto-upload/` 目录，激活 `.venv` 或通过 `uv run`
2. 根据用户需求选择命令：
   - 登录：`sau xiaohongshu login --account <name>`
   - 校验：`sau xiaohongshu check --account <name>`
   - 上传视频：`sau xiaohongshu upload-video --account <name> --file <path> --title "<title>" --desc "<desc>"`
   - 上传图文：`sau xiaohongshu upload-note --account <name> --images <img1> <img2> --title "<title>" --note "<content>"`
3. 如果生成了二维码图片，直接展示图片给用户扫码
4. 遇到错误参考 `.claude/skills/xiaohongshu-upload/references/troubleshooting.md`

用户输入的参数：$ARGUMENTS
