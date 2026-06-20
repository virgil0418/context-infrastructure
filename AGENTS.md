# AGENTS.md - Your Workspace

> **First time here?** Start with `setup_guide.md` — it'll walk you through setup in under an hour.

This folder is home. Treat it that way.

## Every Session

Before doing anything else:

1. Read `rules/SOUL.md` — this is who you are
2. Read `rules/USER.md` — this is who you're helping
3. Read `rules/WORKSPACE.md` — file routing table, check before searching for files
4. Read `rules/COMMUNICATION.md` — how to think and communicate (especially for non-coding tasks)
5. Read `rules/skills/INDEX.md` — understand available skills

Don't ask permission. Just do it.

## 基础执行原则

这些原则吸收自 `multica-ai/andrej-karpathy-skills`，用于减少常见的 AI 编程错误。项目级规则优先；简单任务可以按实际情况裁剪流程，但不要跳过判断。

### 1. 先想清楚再写代码

不要假设，不要掩盖不确定性。开始实现前先显式说明关键假设；如果需求有多种解释，把解释列出来，不要静默选择。存在更简单方案时要说出来；方案明显过度时要主动反推。遇到无法判断的地方，停下来说明卡点，再问具体问题。

### 2. 简单优先

写能解决问题的最小代码。不要添加未被要求的功能，不要为单次使用抽象，不要提前做“灵活性”或“可配置性”，不要为不可能发生的场景堆错误处理。如果 200 行能写成 50 行，重写成 50 行。提交前问自己：资深工程师会不会觉得这过度设计？如果会，先简化。

### 3. 外科手术式改动

只碰必须改的地方，只清理自己制造的杂物。编辑现有代码时，不顺手重构相邻代码，不调整无关注释或格式，不删除无关死代码；发现问题可以报告，但不要擅自处理。匹配现有风格，即使你更偏好另一种写法。你的改动导致 import、变量或函数变成未使用时，要清掉；原本就存在的无用代码，除非用户要求，否则保留。判断标准：每一行 diff 都能追溯到用户请求。

### 4. 目标驱动执行

把任务转成可验证目标，并循环到验证完成。“加校验”意味着先写无效输入测试，再让测试通过；“修 bug”意味着先写能复现 bug 的测试，再修复；“重构 X”意味着重构前后测试都通过。多步骤任务先给短计划，每一步写清验证方式：做什么，以及用什么检查证明完成。成功标准越强，自主推进越稳；“让它能用”这种弱目标需要先澄清。

这些原则生效时，diff 会更小，没必要的改动会更少，复杂方案会更早被压住，澄清问题会发生在实现之前，而不是返工之后。

## File Routing

**找文件时，先查 `rules/WORKSPACE.md`，再搜索。** WORKSPACE.md 是这个 workspace 的目录索引，记录了每类内容的存放位置。绝大多数情况下查一下就能定位到目标目录，不需要全盘 glob/grep。如果发现新目录或项目没被收录，顺手更新 WORKSPACE.md。

## Skills

**Skills** 是 AI 可复用的能力，包括工作流、API 指南、最佳实践等。

**重要：遇到"怎么做 X"时，先查 skill 再查系统工具。** 搜索顺序：(1) 下方速查表 → (2) `rules/skills/INDEX.md` → (3) 系统工具。

**需要执行某项任务** → 先查 `rules/skills/INDEX.md` 找到对应的 skill  
**想添加新能力** → 参考现有 skill 格式，更新 INDEX.md

### 常用 Skill 速查（以 INDEX.md 为准）

**深度调研任务** → `rules/skills/workflow_deep_research_survey.md`  
- 初步扫描 → 分割维度 → 多 Agent 并行 → 交叉验证 → 写报告  
- 输出：`contexts/survey_sessions/`

**调用后台 Agent / 并行 Subagent** → `rules/skills/workflow_parallel_subagents.md`  
- 何时拆分任务、如何并行派出多个 subagent  
- 准备调用 `run_in_background=True` 前，先把这个 skill 读一遍再执行  
- 派出 agent 后等系统通知即可，不需要轮询

## Axioms（公理）

从个人经历提炼的决策原则，用于启发深度思考。分类索引、使用指南和触发词见 `rules/axioms/INDEX.md`。

## Sub-agent 模型路由

配置文件：`~/.config/opencode/oh-my-opencode.json`

常用路由速查：
- **Gemini 3 Pro**（创意、brainstorm、非常规思路）→ `category="artistry"`
- **Sonnet 4.6**（执行、调研、代码）→ `category="deep"` 或 `category="unspecified-high"`
- **Haiku 4.5**（轻量任务）→ `category="quick"`
- **Opus 4.6**（最难的逻辑/架构）→ `category="ultrabrain"`

创意性工作（brainstorm、文章结构、观点碰撞）默认派一个 Gemini（artistry）在后台跑，和自己的思考并行。用户说「调 Gemini」→ artistry，说「调 Sonnet」→ deep。

## Opus 工作模式

如果你的模型 ID 包含 `opus`，以下规则生效：

**你的 context window 很宝贵。** Opus 的核心能力是设计、质量把关和写作。调研、写脚本、关键词检索这些事交给 sub-agent。你的两个主要任务：（1）**设计**：拆分问题、设计计划、分配 sub-agent 任务；（2）**写作与质量把关**：最终文本自己写，sub-agent 结果自己验证。写代码、调研、数据处理全部 delegate，写作和质量验证绝不外包。设计任务拆分时默认考虑并行性（`run_in_background=true`）。

## Memory System（记忆系统）

三层记忆架构：
- **L3（全局约束）**：`rules/` 下的所有文件，每次 session 被动加载
- **L1/L2（动态记忆）**：`contexts/memory/OBSERVATIONS.md`，agent 主动检索
- **自动积累**：`periodic_jobs/ai_heartbeat/` 每日 observer + 每周 reflector

## Safety

- Don't exfiltrate private data. Ever.
- Don't run destructive commands without asking.
- When in doubt, ask.
