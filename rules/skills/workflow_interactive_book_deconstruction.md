---
title: 交互式拆书 HTML 工作流
category: Workflow
tags: [book, reading, deconstruction, concept-map, html, mvc, learning]
difficulty: Medium
created: 2026-06-22
---

# 交互式拆书 HTML 工作流

## 目标

把一本书、一本教材、一个 EPUB/PDF 转换稿或一组读书笔记，拆成可学习的知识模型，并生成一个本地静态 HTML 学习界面。重点不是把书做成网页，而是先构建「模型」，再用 HTML 把模型变成可浏览、可筛选、可追问、可复习的学习工具。

使用这个 skill 时，默认产物要满足 MVC 思路：

- **Model**：书的知识结构。包括章节、概念、概念关系、问题、例子、应用场景、学习路径。
- **View**：HTML/CSS 呈现。包括概念地图、章节视图、概念卡片、关系图、问题面板。
- **Controller**：交互逻辑。包括搜索、筛选、展开、切换路径、标记掌握状态、题目切换。

本 skill 属于学习系列的 **Output Skill**。概念、关系、问题、学习路径和状态模型统一对齐 [`reference_learning_knowledge_model.md`](./reference_learning_knowledge_model.md)。如果用户需要一边学一边被提问，引导部分使用 [`workflow_socratic_concept_learning.md`](./workflow_socratic_concept_learning.md)。

## 触发场景

用户表达以下意图时使用：

- 想「拆书」「拆教材」「把电子书变成学习网页」
- 想通过 HTML 快速学习一本书
- 想把概念地图、图示、问题引导和原子笔记放到一个可交互界面里
- 想先构建概念模型，再做界面
- 想把读书笔记变成可视化学习系统

如果用户只想要 Markdown 原子笔记，用读书笔记工作流即可；如果用户要「看 HTML 学」「图 + 概念 + 交互」，使用本 skill。

## 核心原则

先做模型，再做页面。页面设计不应该先从布局开始，而应该先问：这本书的知识对象是什么、对象之间有哪些关系、学习者要完成哪些操作。

一本书至少有三层模型：

1. **内容层**：章节、段落、图表、案例、术语。
2. **概念层**：核心概念、相邻概念、前置概念、误区、应用。
3. **学习层**：学习路径、检查问题、掌握状态、复习入口。

HTML 只负责把这三层变成可操作界面。不要把 HTML 写成一篇长文章，也不要把每章摘要堆在一个页面里。

## 输出位置

默认输出到：

```text
contexts/book_notes/<book_slug>/interactive_html/
```

推荐结构：

```text
interactive_html/
├── index.html               # 主入口
├── data/
│   └── book_model.json      # Model：书的结构化知识模型
├── src/
│   ├── model.js             # Model 读取、查询、派生索引
│   ├── view.js              # View 渲染函数
│   └── controller.js        # Controller 事件绑定与状态切换
├── styles/
│   └── main.css
└── README.md                # 使用说明与生成记录
```

小书或一次性原型可以生成单文件 `index.html`，但文件内部仍要按 MVC 分区：`DATA_MODEL`、`View`、`Controller`。长期维护的拆书系统优先使用多文件结构。

## Model 规格

`book_model.json` 是最重要的产物。HTML 质量取决于模型质量。

最小 schema：

```json
{
  "book": {
    "title": "书名",
    "author": "作者",
    "source": "来源路径",
    "generated_at": "YYYY-MM-DD"
  },
  "chapters": [
    {
      "id": "ch01",
      "title": "章节标题",
      "summary": "这一章解决什么问题",
      "concept_ids": ["concept_process"]
    }
  ],
  "concepts": [
    {
      "id": "concept_process",
      "name": "进程",
      "one_liner": "一句话定义",
      "why_needed": "为什么需要这个概念",
      "solves": "它解决了什么问题",
      "mechanism": "它如何工作",
      "boundaries": ["不能解决什么", "常见误解"],
      "examples": ["最小例子"],
      "source_refs": ["第 3 章"],
      "question_ids": ["q_process_01"]
    }
  ],
  "relations": [
    {
      "from": "concept_process",
      "to": "concept_thread",
      "type": "contrast",
      "label": "对比",
      "explanation": "二者差异在哪里"
    }
  ],
  "questions": [
    {
      "id": "q_process_01",
      "concept_id": "concept_process",
      "type": "diagnostic",
      "prompt": "为什么操作系统需要进程这个抽象？",
      "hint": "从 CPU、内存和程序并发的矛盾想。",
      "answer": "参考答案，简洁说明。"
    }
  ],
  "learning_paths": [
    {
      "id": "path_core",
      "name": "核心概念路径",
      "concept_ids": ["concept_process", "concept_thread"],
      "description": "适合快速建立主干。"
    }
  ]
}
```

Model 中每个概念都要回答三个问题：

- 它是什么
- 为什么需要它
- 它解决了什么问题

缺少「为什么需要」的概念不算完成。只摘录原文定义也不算完成。

## 概念关系类型

关系要比概念列表更重要。拆书时至少识别这些关系：

- `prerequisite`：A 是理解 B 的前置概念
- `part_of`：A 是 B 的组成部分
- `causes`：A 导致 B
- `solves`：A 解决 B
- `contrast`：A 和 B 容易混淆，需要对比
- `example_of`：A 是 B 的例子
- `applies_to`：A 应用于 B 场景
- `tradeoff`：A 和 B 是一组取舍

关系必须带解释。只有 `from/to/type`，没有解释，学习价值不够。

## 拆书方法

拆书时不要按章节机械摘要。先把书当成一个问题解决系统。

建议从这些视角抽取模型：

- **问题树**：这本书要解决的总问题是什么？子问题是什么？
- **概念树**：作者引入了哪些概念？概念之间谁依赖谁？
- **论证链**：作者如何从前提推到结论？
- **操作链**：如果这是一本方法书，读者要执行哪些动作？
- **误区表**：作者反复反对什么、纠正什么？
- **案例索引**：哪些案例支撑哪些概念？

章节摘要只作为辅助，不是最终模型。一本好书的结构通常不是目录结构本身，而是目录背后的问题结构。

## View 规格

HTML 界面至少包含这些区域：

1. **总览区**：书的一句话、核心问题、学习路径入口。
2. **概念地图区**：展示概念节点和关系。可以用 SVG、Canvas、Mermaid 渲染后的静态图，或简单的 HTML 关系列表。
3. **概念卡片区**：展示定义、动机、解决的问题、机制、边界、例子。
4. **章节索引区**：从章节回到概念，避免脱离原书。
5. **问题训练区**：诊断题、提示、参考答案。
6. **筛选/搜索区**：按章节、概念类型、关系类型、学习路径筛选。

界面优先保证阅读效率。样式可以克制，但层级要清楚。

## Controller 规格

交互逻辑围绕学习动作设计：

- 点击概念节点 → 打开概念卡片
- 点击关系 → 显示为什么两者有关
- 切换学习路径 → 按路径过滤概念
- 搜索术语 → 高亮概念和章节
- 点击「检查我」 → 展示问题，不立即展示答案
- 点击「显示提示」 → 给 hint
- 点击「显示答案」 → 给参考答案
- 标记掌握状态 → 写入 `localStorage`

`localStorage` 只保存用户侧状态，例如掌握状态、展开状态、当前路径。不要把核心书籍模型写死在 controller 里。

## 图示策略

有需要时使用图，但图必须服务理解。

优先图示：

- **概念依赖图**：适合教材、技术书。
- **问题树**：适合方法论、哲学、商业书。
- **流程图**：适合操作流程、系统机制。
- **二维矩阵**：适合流派、概念对比、策略取舍。
- **章节-概念矩阵**：适合快速定位每章贡献。

不要为了好看画图。图中每个节点都要能点击或对应到概念卡片；如果做不到，至少要在旁边提供同名概念入口。

## HTML 技术边界

默认生成本地静态 HTML，不依赖后端。

建议：

- 优先使用原生 HTML/CSS/JS。
- 外部库只有在明显提高图表质量时才使用。
- 如果使用外部库，优先本地 vendored 文件，避免 CDN 失效。
- 页面要能用浏览器直接打开。
- 不引入构建工具，除非用户明确要求。

验收时检查：

- `index.html` 能打开
- 控制台没有明显 JS 报错
- 搜索、概念点击、问题提示、答案展开能工作
- `book_model.json` 是合法 JSON
- View 不直接包含大量业务数据，Controller 不混入大段渲染模板

## 与原子笔记的关系

原子笔记和 HTML 模型互相补充：

- 原子笔记适合长期沉淀到知识库。
- HTML 适合快速浏览、学习路径和交互式复习。
- `book_model.json` 可以从原子笔记生成，也可以反过来生成原子笔记。

如果已经有 `atomic_notes/`，优先把它们转成 `concepts`。如果只有完整 Markdown，先抽概念和关系，再生成原子笔记和 HTML。

## 版权边界

拆书产物应以概念、结构、问题和简短引用为主。不要把整章原文塞进 HTML。必要引用应短，并标明来源章节。完整原文转换稿可以留在本地 `source_markdown/` 供个人回查，但 HTML 学习界面不应复刻原书。

## 验收标准

一次完整交付需要满足：

- 有 `book_model.json`，且包含 `book`、`chapters`、`concepts`、`relations`、`questions`、`learning_paths`
- 每个核心概念都有 `one_liner`、`why_needed`、`solves`
- 每条核心关系都有 `type` 和 `explanation`
- HTML 能从 Model 渲染界面，而不是手写静态内容堆叠
- 页面至少支持概念点击、搜索、问题提示/答案展开
- 有一张概念图或问题树；图中节点能回到概念卡片
- 有 README 说明如何打开、模型来源、生成时间

不合格表现：

- 只有章节摘要，没有概念模型
- HTML 只是 Markdown 转网页，没有学习操作
- 概念之间没有关系
- JS、CSS、数据混在一起且无法维护
- 页面看起来漂亮，但无法回答「这本书的核心模型是什么」

## 推荐提示词

```text
把这本书拆成一个交互式 HTML 学习系统。先构建 book_model.json：章节、概念、概念关系、问题、学习路径。再按 MVC 写本地静态 HTML，让我可以看概念地图、点概念卡、搜索、做检查题。
```

```text
基于 contexts/book_notes/<book>/atomic_notes/ 生成 interactive_html/。HTML 要符合 MVC：data/book_model.json 作为模型，src/view.js 负责渲染，src/controller.js 负责交互。
```

```text
不要只做章节摘要。先找这本书的问题树和概念关系，再做一个能快速学习的 HTML 页面。
```
