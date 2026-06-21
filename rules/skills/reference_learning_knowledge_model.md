---
title: 学习知识模型 Reference
category: Reference
tags: [learning, reference, concept-map, book-model, question-design, html]
difficulty: Medium
created: 2026-06-22
---

# 学习知识模型 Reference

## 作用

这是学习系列 skill 的共享参考标准。它不直接负责教学，也不直接生成 HTML；它定义学习、拆书、概念地图、原子笔记和交互式页面共用的知识模型。

当任务涉及以下产物时，应优先对齐本 reference：

- 概念卡片
- 概念关系图
- 学习路径
- 诊断问题
- 学习单元练习与反馈状态
- 读书拆解模型
- `book_model.json`
- 交互式学习 HTML

## 系列分工

学习系列分三层：

1. **Learning Skill**：负责教学交互。判断用户要直接解释、苏格拉底式引导，还是混合模式。
2. **Reference Skill**：负责共享模型。定义概念、关系、问题、路径、状态、HTML 模型 schema。
3. **Output Skill**：负责产物形态。比如 Markdown 原子笔记、交互式 HTML、复习题库、学习会话记录。

这三层的关系是：Learning 调用 Reference 形成稳定模型，Output 根据模型生成不同界面或文件。

学习单元、练习反馈和掌握状态更新对齐 [`reference_learning_feedback.md`](./reference_learning_feedback.md)。本文件定义知识对象，本反馈 reference 定义学习单元切分、练习反馈对象和状态更新。

## 核心对象模型

### Concept

概念是最小学习单元。一个概念必须能独立回答「是什么、为什么需要、解决什么问题」。

```json
{
  "id": "concept_id",
  "name": "概念名",
  "aliases": ["别名"],
  "one_liner": "一句话定义",
  "why_needed": "为什么需要这个概念",
  "solves": "它解决了什么问题",
  "mechanism": "它如何工作",
  "boundaries": ["不能解决什么", "常见误解"],
  "examples": ["最小例子"],
  "source_refs": ["来源学习单元或文件"],
  "question_ids": ["question_id"]
}
```

合格概念卡：

- `one_liner` 让用户先抓住概念轮廓
- `why_needed` 说明旧方法或直觉在哪里不够用
- `solves` 说明概念引入后让什么事变得可表达、可计算、可控制或可复用
- `mechanism` 解释内部工作方式
- `boundaries` 防止用户把概念泛化过度

### Relation

关系用于把概念从列表变成地图。每条关系都要解释原因。

```json
{
  "from": "concept_a",
  "to": "concept_b",
  "type": "prerequisite",
  "label": "前置",
  "explanation": "为什么 A 是理解 B 的前提"
}
```

推荐关系类型：

- `prerequisite`：A 是理解 B 的前置概念
- `part_of`：A 是 B 的组成部分
- `causes`：A 导致 B
- `solves`：A 解决 B
- `contrast`：A 和 B 容易混淆，需要对比
- `example_of`：A 是 B 的例子
- `applies_to`：A 应用于 B 场景
- `tradeoff`：A 和 B 是一组取舍
- `sequence`：A 在流程上先于 B

### Question

问题用于诊断理解，而不是制造互动。每个问题都要绑定一个概念或关系。

```json
{
  "id": "question_id",
  "concept_id": "concept_id",
  "relation_id": "optional_relation_id",
  "type": "diagnostic",
  "prompt": "问题正文",
  "purpose": "这个问题检查什么",
  "hint": "轻提示",
  "answer": "参考答案"
}
```

推荐问题类型：

- `diagnostic`：定位当前理解
- `motivation`：检查为什么需要这个概念
- `mechanism`：检查内部机制
- `boundary`：检查概念边界
- `contrast`：检查相邻概念差异
- `counterexample`：用反例测试定义
- `transfer`：迁移到新场景

一次教学交互最多抛出 1-3 个问题。问题太多会降低回答质量。

### Learning Path

学习路径是概念的有序子图，不是学习单元目录的复制。

```json
{
  "id": "path_core",
  "name": "核心主干路径",
  "description": "适合快速建立全局骨架",
  "concept_ids": ["concept_a", "concept_b"],
  "entry_condition": "适合已有基础但不系统的学习者",
  "exit_check": "能解释 A 如何导向 B，并完成迁移题"
}
```

常见路径：

- 核心主干路径：先建立全局框架
- 查漏补缺路径：针对半掌握概念
- 应用路径：从场景倒推概念
- 误区修正路径：围绕常见误解组织
- 考试/面试路径：围绕可测试问题组织

### Learner State

学习状态记录概念掌握情况。

```json
{
  "concept_id": "concept_id",
  "status": "partial",
  "evidence": "用户能说出定义，但说不清 why_needed",
  "next_review": "YYYY-MM-DD",
  "notes": "下次先问一个 motivation 问题"
}
```

状态建议：

- `unknown`：未接触
- `seen`：见过术语
- `partial`：知道定义，动机/机制/边界不稳
- `usable`：能在熟悉场景中使用
- `transferable`：能迁移到新场景并举反例

### Learning Unit / Practice / Feedback

学习单元反馈使用独立 reference 扩展本模型：

- `Learning Unit`：可按章节、单元、概念、主题或自定义范围切分，记录它在整体材料或概念地图中的位置、核心问题、关联概念和练习。
- `Practice`：绑定学习单元和概念的练习，包含检查目的、好答案标准和常见误区。
- `Feedback Event`：记录用户回答后的有效部分、缺口、修正版、追问和学习状态更新。

详细 schema 见 [`reference_learning_feedback.md`](./reference_learning_feedback.md)。不要把学习单元练习只写成自由文本；长期学习时应能回写到 `learner_state`。

## 原子概念卡片模板

```markdown
# [概念名]

## 一句话定义
[它是什么]

## 为什么需要它
[没有它时遇到什么问题]

## 它解决了什么问题
[它让什么事变得可表达、可计算、可控制或可复用]

## 机制
[它如何工作]

## 边界
- [不能解决什么]
- [常见误解]
- [相邻概念区别]

## 例子
[最小例子]

## 检查问题
1. [定义检查]
2. [动机检查]
3. [迁移/反例检查]

## 相关概念
- [[概念 A]]
- [[概念 B]]
```

## Book Model Schema

交互式拆书、HTML 学习页和读书模型统一使用这个 schema。

```json
{
  "book": {
    "title": "书名",
    "author": "作者",
    "source": "来源路径",
    "generated_at": "YYYY-MM-DD"
  },
  "learning_units": [
    {
      "id": "unit_01",
      "title": "学习单元标题",
      "scope_type": "chapter",
      "scope_ref": "第 1 章",
      "summary": "这个学习单元解决什么问题",
      "concept_ids": ["concept_id"],
      "practice_ids": ["practice_id"]
    }
  ],
  "concepts": [],
  "relations": [],
  "questions": [],
  "practices": [],
  "feedback_events": [],
  "learning_paths": [],
  "learner_state": []
}
```

`concepts`、`relations`、`questions`、`learning_paths`、`learner_state` 分别使用上面的对象模型。`learning_units`、`practices` 和 `feedback_events` 使用学习单元反馈 reference 中的对象模型。

## MVC HTML 输出约定

交互式学习 HTML 使用 Model-View-Controller 分层：

- **Model**：`data/book_model.json`。核心知识模型，不能散落在视图和控制器里。
- **View**：`src/view.js` + `styles/main.css`。负责把模型渲染成概念地图、卡片、问题面板。
- **Controller**：`src/controller.js`。负责搜索、筛选、点击、显示提示、显示答案、掌握状态。

推荐目录：

```text
interactive_html/
├── index.html
├── data/book_model.json
├── src/model.js
├── src/view.js
├── src/controller.js
├── styles/main.css
└── README.md
```

小型原型可以用单文件 HTML，但文件内部仍要清楚分区：

- `DATA_MODEL`
- `Model`
- `View`
- `Controller`
- `init()`

## 图示选择

图示由模型决定，而不是由美观偏好决定。

- 概念依赖复杂：用概念依赖图
- 作者在回答一个总问题：用问题树
- 方法有步骤：用流程图
- 概念之间是取舍：用二维矩阵
- 学习单元与概念交叉：用学习单元-概念矩阵

图中节点最好能点击到概念卡。做不到时，图下方要有同名概念入口。

## 验收标准

使用本 reference 的产物需要满足：

- 核心概念包含 `one_liner`、`why_needed`、`solves`
- 核心关系包含 `type`、`label`、`explanation`
- 问题包含 `purpose`，能说明它检查什么
- 学习单元练习包含 `purpose`、好答案标准和常见误区
- 用户回答后的反馈能更新 `learner_state`
- 学习路径不是目录复制，而是概念子图
- HTML 页面从模型渲染，而不是把数据写死在视图中
- 长期学习记录区分 `unknown`、`seen`、`partial`、`usable`、`transferable`
