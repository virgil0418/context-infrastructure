# WORKSPACE.md - 目录路由速查

目标：让 AI 每轮 session 都能快速知道"去哪里找/放什么"。**找任何文件前先查这里。**

## 路由规则

### 项目与代码
- 写代码 / 跑脚本 / 一次性项目：`adhoc_jobs/<project>/`
- 工具脚本（邮件、语义搜索、分享报告等）：`tools/`
- 定时任务：`periodic_jobs/`

### 知识与记录
- 通用调研报告：`contexts/survey_sessions/`
- 读书笔记 / 电子书拆解 / 拆书 HTML：`contexts/book_notes/`
- 长期学习会话 / 概念地图：`contexts/learning_sessions/`
- 思考 / 复盘 / 方法论：`contexts/thought_review/`
- 每日日志：`contexts/daily_records/`

### 系统与规则
- 可复用技术方案 / Skill：`rules/skills/`
- 核心公理（Axioms）：`rules/axioms/`
- 记忆系统：`contexts/memory/` + `periodic_jobs/ai_heartbeat/`

## 命名规则
- 目录和文件名：小写 + 下划线 (snake_case)
- 临时一次性项目：`tmp_<name>/`

## Python 环境
- 根目录 `.venv/` 为工作区级环境，用 `uv pip install` 管理依赖
- 需要隔离时在 `adhoc_jobs/<project>/.venv/` 建独立环境

## 快速查询

<!-- 随着你的项目增长，在这里添加活跃项目的快捷路由 -->
<!-- 格式：- `project-name` → `adhoc_jobs/project_name/` (说明) -->
- `e-commerce-ddd` → `/Users/howie/project/e-commerce-ddd/`（电商独立站 DDD 项目）
- `ddd-skills` → `/Users/howie/project/ddd-skills/`（DDD / sugar-boot 开发流程与技能仓库）
- `zettaranc-skill` → `/Users/howie/project/zettaranc-skill/`（万千交易思维与量化工具源码；当前 workspace 仅保留软链接）
- `trading-workflow-skill` → `/Users/howie/project/trading-workflow-skill/`（拟新建的纯交易工作流 Skill 仓库；当前 workspace 仅保留软链接）
- `personal-knowledge-vault` → `/Users/howie/project/personal-knowledge-vault/`（个人 Obsidian 知识库；承载来源、概念、观点、反馈、练习和决策记录）
