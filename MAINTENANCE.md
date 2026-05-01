# 项目维护指南

## 项目归属

| 内容 | 来源 | 文件 |
|------|------|------|
| 核心框架 | [autoclaw-cc/xiaohongshu-skills](https://github.com/autoclaw-cc/xiaohongshu-skills)（上游） | 大部分文件 |
| save-markdown 功能 | 自定义开发（本 fork 独有） | 见下方列表 |

### 自定义开发文件清单

| 文件 | 说明 |
|------|------|
| `scripts/xhs/save.py` | 新增：笔记保存为 Markdown 的核心逻辑 |
| `skills/xhs-save/SKILL.md` | 新增：xhs-save 技能定义 |
| `scripts/cli.py` | 修改：新增 `save-feed` 子命令 |
| `scripts/xhs/types.py` | 修改：新增 `VideoStream`、`VideoInfo` 类型，`FeedDetail` 增加 video 字段 |
| `scripts/image_downloader.py` | 修改：修复 Referer 为固定值，解决 CDN 403 |
| `SKILL.md` | 修改：新增内容保存路由 |
| `CLAUDE.md` | 修改：新增 `save-feed` 子命令 |

## 上游更新流程

当上游有新 commit 时，按以下步骤同步：

```bash
# 1. 获取上游最新代码
git fetch upstream

# 2. 查看上游有哪些新变更
git log main..upstream/main --oneline

# 3. 切换到 main 分支，合并上游更新
git checkout main
git merge upstream/main

# 4. 推送合并后的 main 到你的 fork
git push origin main

# 5. 将更新合并到你的功能分支
git checkout feat/save-markdown
git merge main
```

### 冲突处理

如果上游修改了你改动过的文件（`cli.py`、`types.py`、`image_downloader.py`、`SKILL.md`），解决冲突时注意：
- 保留你的 `save-feed` 相关代码
- 保留你的 `VideoStream`/`VideoInfo` 类型改动
- 保留你的 image_downloader Referer 修复
- 接受上游的其他改进（bugfix、新功能等）

```bash
# 发生冲突时，手动编辑冲突文件后：
git add <冲突文件>
git commit -m "merge: 合入上游更新，保留 save-markdown 功能"
```

## 迁移到其他电脑

### 方案一：克隆你的 fork（推荐）

```bash
git clone https://github.com/odtu945/xiaohongshu-skills.git
cd xiaohongshu-skills

# 安装依赖
uv sync

# 安装 Chrome 扩展
# 打开 chrome://extensions/ -> 开发者模式 -> 加载 extension/ 目录
```

克隆后自动包含你的 fork 分支上所有 save-markdown 功能的提交。

### 方案二：从其他分支/电脑同步

```bash
# 已经在另一台电脑上有了初始 clone
git pull origin feat/save-markdown
uv sync
```

## Git 分支策略

```
upstream/main (autoclaw-cc)
        ↑
        | 定期 fetch + merge
        |
main (你的 fork)
        ↑
        | 开发时 merge 或 rebase
        |
feat/save-markdown (你的功能分支)
```

- `main` 保持与上游同步，定期合入 `upstream/main`
- 新功能在独立分支开发，完成后合入 `main`
- 合入上游时优先 `merge`（保留历史），不建议 `rebase`

## 依赖更新

上游可能新增 Python 依赖或修改 `pyproject.toml`，合入上游后执行：

```bash
uv sync
```

如果 `uv sync` 失败，检查 `pyproject.toml` 是否有冲突未解决。
