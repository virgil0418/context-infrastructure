---
title: 学习单元反馈 Reference
category: Reference
tags: [learning, reference, book, practice, feedback, unit]
difficulty: Medium
created: 2026-06-22
---

# 学习单元反馈 Reference

## 作用

这是学习系列 skill 的反馈层参考标准。它不单独承担完整教学任务，而是给主学习 workflow 提供一套稳定的「学习单元 → 练习 → 反馈 → 状态更新」模型。

这里的学习单元是一个抽象切分单位，可以是一章、一个小节、一个课程单元、一个概念、一组概念、一篇论文的一个段落，或者用户自己定义的一块材料。切分标准不是材料目录，而是这一块内容能否围绕一个核心问题形成练习和反馈。

当用户正在读一本书、教材、课程或长文，并且希望对某个学习单元检查理解时，主学习 workflow 应引用本 reference。它和 [`reference_learning_knowledge_model.md`](./reference_learning_knowledge_model.md) 的关系是：

- `reference_learning_knowledge_model.md` 定义概念、关系、问题、学习路径和学习状态。
- 本 reference 定义学习单元推进、练习组织、反馈事件和状态更新。
- [`workflow_socratic_concept_learning.md`](./workflow_socratic_concept_learning.md) 负责实际教学交互。

## 适用场景

使用本 reference 的典型信号：

- 用户说自己刚读完某一章
- 用户说自己学完一个单元、小节、概念或主题
- 用户想知道某个范围里讲了哪些概念
- 用户想检查这些概念为什么有效
- 用户想把当前学习范围变成练习
- 用户希望形成长期学习反馈记录
- 用户已经有总体学习地图，现在需要按某种粒度推进

如果用户只需要整本书或整门课概览，先用主学习 workflow 建立总体架构；进入具体学习单元后，再引入本 reference。

## 反馈闭环

反馈闭环是：

```text
范围定位
→ 核心概念
→ 有效性机制
→ 现实应用
→ 练习回答
→ 反馈修正
→ 学习状态更新
```

每个学习单元默认抓 1-5 个核心概念。概念型学习单元可以只围绕 1 个概念；章节或课程单元可以抓 3-5 个概念。优先选择能改变判断和行动的概念，而不是搬运所有术语。

## Learning Unit Model

学习单元是一组概念和练习的承载单元。它可以对应目录里的章节，也可以对应用户临时指定的范围。

```json
{
  "id": "unit_03",
  "title": "学习单元标题",
  "scope_type": "chapter",
  "scope_ref": "第 3 章",
  "role": "这个学习单元在整体材料里的作用",
  "core_question": "这个学习单元试图回答的问题",
  "concept_ids": ["concept_id"],
  "practice_ids": ["practice_id"],
  "source_refs": ["第 3 章"]
}
```

字段说明：

- `scope_type`：说明切分方式，可用 `chapter`、`section`、`unit`、`concept`、`concept_group`、`topic`、`paper_part`、`custom`。
- `scope_ref`：说明来源范围，比如第 3 章、第二单元、概念 CAN SLIM、论文方法部分。
- `role`：说明这个学习单元在整体材料里的作用；概念型单元可写它在概念地图中的位置。
- `core_question`：把学习单元从内容列表变成问题驱动的学习单元。
- `concept_ids`：引用知识模型里的 `Concept`，不要在学习单元里重复定义概念。
- `practice_ids`：引用本学习单元练习。

## Practice Model

练习用于迁移，不只是检查记忆。

```json
{
  "id": "practice_unit_03_01",
  "unit_id": "unit_03",
  "concept_ids": ["concept_id"],
  "type": "mechanism",
  "prompt": "练习题正文",
  "purpose": "这个练习检查什么",
  "good_answer": ["好答案应包含的判断点"],
  "common_mistakes": ["常见误区"],
  "next_if_failed": ["需要回到的概念或学习单元"]
}
```

推荐练习类型：

- `definition`：让用户用自己的话定义概念。
- `mechanism`：让用户解释概念为什么可能有效。
- `contrast`：区分相似概念。
- `application`：给现实场景，让用户选择行动并说明理由。
- `counterexample`：给失效场景，让用户识别边界。
- `reflection`：把概念应用到用户自己的经历、项目或决策。

每个学习单元默认 3 道题：

1. `definition`：确认用户知道概念是什么。
2. `mechanism`：确认用户知道为什么有效。
3. `application`：确认用户能迁移到现实判断。

用户回答质量高时增加 `counterexample`。用户回答不稳定时减少题量，先修正一个关键误解。

## Feedback Event Model

反馈事件记录一次练习回答后的判断。

```json
{
  "id": "feedback_20260622_001",
  "practice_id": "practice_ch03_01",
  "user_answer": "用户原始回答",
  "valid_parts": ["回答中成立的判断"],
  "gap_type": "mechanism",
  "gap": "具体缺口",
  "corrected_answer": "更准确的说法",
  "followup_question": "下一问",
  "state_updates": [
    {
      "concept_id": "concept_id",
      "from": "seen",
      "to": "partial",
      "evidence": "用户能说出定义，但解释不出机制"
    }
  ]
}
```

`gap_type` 建议使用：

- `definition`：定义不稳。
- `motivation`：不知道为什么提出这个概念。
- `mechanism`：不知道为什么有效或如何工作。
- `boundary`：适用边界不清楚。
- `application`：无法迁移到现实场景。
- `contrast`：和相邻概念混淆。

反馈顺序：

1. 保留有效部分。
2. 定位缺口。
3. 给出修正版。
4. 追问一个问题。
5. 更新学习状态。

## 学习单元输出模板

```markdown
## 范围定位
[这个学习单元是什么范围：章节、单元、概念、主题或自定义范围。它在整体材料或概念地图里的作用是什么。]

## 核心概念
- [概念 A]：[一句话定义]
- [概念 B]：[一句话定义]
- [概念 C]：[一句话定义]

## 为什么有效
[逐个解释这些概念背后的机制。不要只说作者认为有效，要说明它在现实中依赖什么条件。]

## 如何应用
- [应用场景 1]：[具体动作]
- [应用场景 2]：[具体动作]
- [应用场景 3]：[具体动作]

## 练习
1. [定义题]
2. [机制题]
3. [应用题]

## 反馈标准
- 好答案应该包含：[关键判断点]
- 常见误区：[容易混淆或过度泛化的点]
- 如果答偏了，下一步补：[需要回到的学习单元或概念]
```

## 用户回答后的反馈模板

```markdown
## 反馈

你答对的是：[有效部分]

缺口在：[定义 / 动机 / 机制 / 边界 / 应用 / 对比]

更准确的说法是：[修正版]

下一问：[一个追问]

## 学习状态
- 已掌握：[概念]
- 半掌握：[概念]
- 待补齐：[概念]
```

## 长期学习记录

持续学习任务建议落到：

```text
contexts/learning_sessions/<topic>/
├── README.md
├── learning_map.md
├── concept_cards/
├── unit_map.md
├── unit_notes/
├── question_bank.md
├── practice_log.md
├── feedback_state.md
└── session_log.md
```

最小可用版本：

```text
contexts/learning_sessions/<topic>/
├── learning_map.md
├── unit_map.md
├── practice_log.md
└── feedback_state.md
```

### unit_map.md

```markdown
| 学习单元 | 范围类型 | 核心问题 | 核心概念 | 练习状态 |
|---|---|---|---|---|
| 第 1 章 | chapter | ... | ... | 未练习 / 半掌握 / 已掌握 |
| CAN SLIM | concept_group | ... | ... | 未练习 / 半掌握 / 已掌握 |
```

### practice_log.md

```markdown
## 2026-06-22 [学习单元]

### 题目
[练习题]

### 用户回答
[保留原始回答]

### 反馈
[有效部分、缺口、修正版]

### 下一步
[下次优先复习什么]
```

### feedback_state.md

```markdown
## 已掌握
- [概念]：[证据]

## 半掌握
- [概念]：[缺口]

## 待补齐
- [概念]：[需要补的前置知识]
```

## 金融类书籍使用注意

如果材料是投资、交易、理财或金融市场相关书籍，反馈时区分三层：

1. **作者主张**：书中明确说了什么。
2. **机制解释**：这个主张可能依赖什么市场机制。
3. **个人应用**：用户能做什么练习或观察。

不要把书中策略包装成确定收益。涉及实盘时，优先建议模拟记录、历史回测、仓位控制和风险边界。学习反馈可以评估理解质量，但不能替代投资建议。

## 验收标准

使用本 reference 的学习单元输出应满足：

- 标明本学习单元在整本书里的位置
- 提取 3-5 个核心概念，并映射到 `Concept`
- 对每个概念说明为什么有效或可能有效
- 至少提供定义、机制、应用三类练习
- 每道练习包含 `purpose`、`good_answer` 和 `common_mistakes`
- 用户回答后生成反馈事件，并更新学习状态
- 持续学习时维护 `unit_map.md`、`practice_log.md` 和 `feedback_state.md`

不合格表现：

- 只做学习单元摘要
- 只问记忆题
- 只给标准答案，没有反馈事件
- 把作者观点直接当成事实
- 一次问太多题，用户不知道先答哪个
