---
description: B站视频上传：登录、校验账号、上传视频。用法：/sau-bilibili [login|check|upload-video] --account <name>
---

参考 `.claude/skills/bilibili-upload/SKILL.md` 执行 Bilibili 操作。

操作步骤：
1. 确认在 `social-auto-upload/` 目录，激活 `.venv` 或通过 `uv run`
2. 根据用户需求选择命令：
   - 登录（需本地真实终端交互）：`sau bilibili login --account <name>`
   - 校验：`sau bilibili check --account <name>`
   - 上传视频：`sau bilibili upload-video --account <name> --file <path> --title "<title>" --desc "<desc>" --tid 249`
3. **注意**：Bilibili 登录不支持在非交互环境里强行自动化，应指导用户在本地终端执行
4. 终端二维码显示不完整时，提醒用户打开 `qrcode.png` 扫码
5. 程序会自动下载 `biliup`，无需手动安装

用户输入的参数：$ARGUMENTS
