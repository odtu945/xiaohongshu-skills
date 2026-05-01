"""小红书笔记保存为 Markdown（含图片下载）。"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from .feed_detail import get_feed_detail
from .types import FeedDetailResponse

logger = logging.getLogger(__name__)

# URL 中 feed_id 的路径模式
_FEED_ID_PATTERNS = [
    re.compile(r"/discovery/item/([0-9a-f]{24})"),
    re.compile(r"/explore/([0-9a-f]{24})"),
]


def parse_share_url(url: str) -> tuple[str, str]:
    """从分享链接中提取 feed_id 和 xsec_token。

    支持的 URL 格式：
    - https://www.xiaohongshu.com/discovery/item/{feed_id}?xsec_token=XXX...
    - https://www.xiaohongshu.com/explore/{feed_id}?xsec_token=XXX...

    Raises:
        ValueError: URL 格式无效或无法提取必要参数。
    """
    parsed = urlparse(url)
    path = parsed.path

    feed_id = ""
    for pattern in _FEED_ID_PATTERNS:
        match = pattern.search(path)
        if match:
            feed_id = match.group(1)
            break

    if not feed_id:
        raise ValueError(f"无法从 URL 中提取 feed_id: {url}")

    qs = parse_qs(parsed.query)
    xsec_token = qs.get("xsec_token", [""])[0]
    if not xsec_token:
        raise ValueError(f"URL 中缺少 xsec_token 参数: {url}")

    return feed_id, xsec_token


def sanitize_dir_name(title: str) -> str:
    """将标题转为用户友好的目录名。

    去除 emoji、特殊字符，截断过长标题，确保文件系统安全。
    """
    # 去除 emoji 和特殊 unicode 符号
    cleaned = re.sub(r"[^\w\s一-鿿㐀-䶿\-\.]", "", title)
    # 去除多余空格
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    # 截断到 50 字符
    if len(cleaned) > 50:
        cleaned = cleaned[:50]
    # 去除首尾的连字符和点
    cleaned = cleaned.strip("-.")
    if not cleaned:
        cleaned = "xhs-note"
    return cleaned


def _format_timestamp(ts: int) -> str:
    """将毫秒时间戳转为可读日期。"""
    if not ts:
        return ""
    return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")


def _extract_tags(desc: str) -> list[str]:
    """从正文描述中提取话题标签。"""
    return re.findall(r"#([^#]+?)#", desc)


def _strip_tags(desc: str) -> str:
    """从正文描述中去除话题标签。"""
    return re.sub(r"#[^#]+?#", "", desc).strip()


def generate_markdown(
    detail: FeedDetailResponse,
    image_filenames: list[str],
    video_filename: str,
    original_url: str,
) -> str:
    """生成 Markdown 内容。

    Args:
        detail: 笔记详情响应。
        image_filenames: 已下载的图片文件名列表（与 image_list 顺序对应）。
        video_filename: 已下载的视频文件名（空字符串表示无视频）。
        original_url: 原始分享链接。
    """
    note = detail.note
    interact = note.interact_info

    # 元信息行
    meta_parts = [
        f"作者：{note.user.nickname or note.user.nick_name}",
    ]
    if note.ip_location:
        meta_parts.append(f"地点：{note.ip_location}")
    if interact.liked_count:
        meta_parts.append(f"点赞：{interact.liked_count}")
    if interact.collected_count:
        meta_parts.append(f"收藏：{interact.collected_count}")
    if interact.comment_count:
        meta_parts.append(f"评论：{interact.comment_count}")

    meta_line = " | ".join(meta_parts)

    # 正文（去除标签部分）
    body_text = _strip_tags(note.desc)

    # 图片表格
    img_lines = []
    for i, fname in enumerate(image_filenames, 1):
        img_lines.append(f"| {i:02d} | ![img_{i:02d}]({fname}) |")
    img_table = ""
    if img_lines:
        img_table = "\n| # | 图片 |\n|---|------|\n" + "\n".join(img_lines) + "\n"

    # 话题标签
    tags = _extract_tags(note.desc)
    tags_line = " ".join(f"#{t}" for t in tags) if tags else ""

    # 评论
    comment_lines = []
    for c in detail.comments.list_:
        nickname = c.user_info.nickname or c.user_info.nick_name
        row = f"| {nickname} | {c.content} | {c.like_count} | {c.ip_location} |"
        comment_lines.append(row)
    comment_table = ""
    if comment_lines:
        comment_table = (
            "\n| 用户 | 内容 | 点赞 | IP |\n|------|------|------|----|\n"
            + "\n".join(comment_lines)
            + "\n"
        )

    # 子评论
    sub_comment_lines = []
    for c in detail.comments.list_:
        for sc in c.sub_comments:
            sc_nick = sc.user_info.nickname or sc.user_info.nick_name
            parent_nick = c.user_info.nickname or c.user_info.nick_name
            sub_comment_lines.append(
                f"- **{sc_nick}** 回复 {parent_nick}：{sc.content}（IP: {sc.ip_location})"
            )
    sub_comment_section = ""
    if sub_comment_lines:
        sub_comment_section = "\n### 子评论\n\n" + "\n".join(sub_comment_lines) + "\n"

    # 组装 markdown
    parts = [
        f"# {note.title}\n",
        f"> {meta_line}\n",
        f"{body_text}\n",
    ]

    if img_table:
        parts.append(f"## 图片素材\n{img_table}")

    if video_filename:
        video_section = f"\n## 视频\n\n[{video_filename}]({video_filename})\n"
        parts.append(video_section)

    if tags_line:
        parts.append(f"\n## 话题标签\n\n{tags_line}\n")

    if comment_table:
        parts.append(f"\n## 评论\n{comment_table}")

    if sub_comment_section:
        parts.append(sub_comment_section)

    parts.append(f"\n---\n\n原文链接：{original_url}\n")

    return "\n".join(parts)


def save_feed_as_markdown(
    page,
    url: str,
    output_dir: str | None = None,
) -> dict:
    """将小红书笔记保存为 Markdown 文件（含图片下载）。

    Args:
        page: CDP/Bridge 页面对象。
        url: 小红书分享链接。
        output_dir: 输出目录（默认为当前工作目录）。

    Returns:
        dict: 包含 markdown_path, image_count, output_dir 等信息。
    """
    from image_downloader import ImageDownloader

    # 1. 解析 URL
    feed_id, xsec_token = parse_share_url(url)
    logger.info("解析 URL: feed_id=%s, xsec_token=%s", feed_id, xsec_token[:8] + "...")

    # 2. 获取笔记详情
    detail = get_feed_detail(page, feed_id, xsec_token)
    note = detail.note

    # 3. 创建输出目录
    if not output_dir:
        output_dir = os.getcwd()
    dir_name = sanitize_dir_name(note.title)
    save_dir = os.path.join(output_dir, dir_name)
    os.makedirs(save_dir, exist_ok=True)
    logger.info("输出目录: %s", save_dir)

    # 4. 下载图片
    downloader = ImageDownloader(save_dir)
    image_filenames: list[str] = []
    for i, img in enumerate(note.image_list, 1):
        if not img.url_default:
            continue
        # 确保使用 https 协议
        img_url = img.url_default
        if img_url.startswith("http://"):
            img_url = "https://" + img_url[7:]
        try:
            local_path = downloader.download_image(img_url)
            filename = os.path.basename(local_path)
            image_filenames.append(filename)
            logger.info("下载图片 %d/%d: %s", i, len(note.image_list), filename)
        except Exception as e:
            logger.warning("下载图片失败 %d: %s", i, e)
            image_filenames.append(img.url_default)

    # 5. 下载视频
    video_filename = ""
    if note.video and note.video.best_url:
        video_url = note.video.best_url
        if video_url.startswith("http://"):
            video_url = "https://" + video_url[7:]
        try:
            import requests as _requests
            parsed_video = urlparse(video_url)
            resp = _requests.get(
                video_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://www.xiaohongshu.com/",
                },
                timeout=300,
            )
            if resp.status_code == 200:
                # 从 URL 推断扩展名
                video_ext = ".mp4"
                for ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
                    if parsed_video.path.lower().endswith(ext):
                        video_ext = ext
                        break
                video_filename = f"video_{int(time.time())}{video_ext}"
                video_path = os.path.join(save_dir, video_filename)
                with open(video_path, "wb") as f:
                    f.write(resp.content)
                size_mb = len(resp.content) / 1024 / 1024
                logger.info("下载视频完成: %s (%.1f MB)", video_filename, size_mb)
            else:
                logger.warning("下载视频失败 (status=%d)", resp.status_code)
        except Exception as e:
            logger.warning("下载视频失败: %s", e)

    # 6. 生成 markdown
    md_content = generate_markdown(detail, image_filenames, video_filename, url)
    md_filename = f"{dir_name}.md"
    md_path = os.path.join(save_dir, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("Markdown 已保存: %s", md_path)

    return {
        "success": True,
        "markdown_path": md_path,
        "output_dir": save_dir,
        "image_count": len(image_filenames),
        "video_file": video_filename or None,
        "title": note.title,
        "feed_id": feed_id,
    }
