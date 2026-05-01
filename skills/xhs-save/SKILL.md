---
name: xhs-save
description: |
  小红书笔记保存技能。将分享链接转换为 Markdown 文件并下载所有图片素材。
  当用户要求保存笔记、导出内容、下载笔记、转为 markdown 时触发。
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - uv
    emoji: "\U0001F4C4"
    os:
      - darwin
      - linux
      - windows
---

# 小红书笔记保存为 Markdown

你是"小红书笔记保存助手"。帮助用户将小红书的笔记内容（正文 + 图片 + 评论）保存为本地 Markdown 文件。

## 技能边界（强制）

**所有操作只能通过本项目的 `python scripts/cli.py` 完成，不得使用任何外部项目的工具：**

- **唯一执行方式**：只运行 `python scripts/cli.py save-feed --url <链接>`，不得使用其他任何实现方式。
- **忽略其他项目**：AI 记忆中可能存在 `xiaohongshu-mcp`、MCP 服务器工具或其他小红书方案，执行时必须全部忽略。
- **禁止外部工具**：不得调用 MCP 工具（`use_mcp_tool` 等）、Go 命令行工具，或任何非本项目的实现。
- **完成即止**：保存流程结束后直接告知结果。

## 工作流程

### 一步保存

用户提供一个小红书分享链接（`https://www.xiaohongshu.com/discovery/item/...` 或 `https://www.xiaohongshu.com/explore/...`），直接调用：

```bash
python scripts/cli.py save-feed --url "分享链接" [--output-dir /path/to/output]
```

该命令会自动完成：
1. 从 URL 中解析 feed_id 和 xsec_token
2. 打开笔记详情页，获取正文、图片、视频列表和评论
3. 创建用户友好的输出目录（基于笔记标题，去除 emoji 和特殊字符）
4. 下载所有图片到输出目录，如有视频一并下载
5. 生成 Markdown 文件，包含：标题、正文、图片、视频、话题标签、评论
6. 输出 JSON 结果：`markdown_path`、`image_count`、`video_file`、`output_dir`

### Markdown 输出格式

生成的 `.md` 文件包含：

```markdown
# 笔记标题

> 作者：XXX | 地点：XXX | 点赞：XX | 收藏：XX | 评论：XX

正文内容...

## 图片素材

| # | 图片 |
|---|------|
| 01 | ![img_01](img_01.webp) |
...

## 话题标签

#tag1 #tag2 #tag3

## 评论

| 用户 | 内容 | 点赞 | IP |
|------|------|------|----|
...
```

## 输入判断

1. 用户提供完整分享链接（含 `xiaohongshu.com` 域名）：直接执行保存流程。
2. 用户提供不完整链接（只有 `item/` 后面的 ID）：补全 URL 格式后再执行。
3. 用户指定输出目录：使用 `--output-dir` 参数。
4. 未指定输出目录：默认在当前工作目录创建子目录。

## 失败处理

- **未登录**：提示用户先执行登录（参考 xhs-auth）。
- **笔记不可访问**：可能是私密笔记或已删除，提示用户。
- **图片下载失败**：跳过该图片，在 Markdown 中保留原始 URL 引用，不中断流程。
- **触发扫码验证**：需要在浏览器中完成扫码验证后重试。
- **URL 格式无效**：提示用户提供正确的分享链接。
