---
name: artifact-publishing-unavailable
description: 本会话的 Artifact 发布不可用——ANTHROPIC_AUTH_TOKEN 优先于 claude.ai 登录
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5a8d92ac-94c6-4a23-856f-0d7a42daf5b8
  modified: 2026-09-15T12:22:38.166Z
---

在本机（Windows，`C:\Users\mycomputer\.claude`）运行 Claude Code 时，**Artifact 工具会失败**，报错：Artifacts need a claude.ai login, and this session is authenticating with ANTHROPIC_AUTH_TOKEN。

**How to apply:** 需要交付可分享的页面时，直接写成本地 HTML 文件并用系统浏览器打开（chrome-devtools MCP 的 `file:///` 可以正常渲染预览），不要尝试发布 Artifact。如果用户想要真正的分享链接，需要先取消 `ANTHROPIC_AUTH_TOKEN` 环境变量并 `/login` 选择订阅账号。

相关：[[grain-solute-acceleration-project]]
