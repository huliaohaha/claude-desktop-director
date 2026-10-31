# 介绍图制作记录

- 文件：[`workflow.png`](workflow.png)
- 生成方式：内置 `image_gen` 工具；非 CLI/API 回退。
- 生成日期：2026-10-31。
- 用途：README 顶部的工作流程示意图。图中窗口是概念示意，不是真实 Claude 截图。
- 后期处理：原图复制到仓库，未进行图像编辑。

## 原始提示词

```text
Use case: infographic-diagram. Asset type: polished GitHub README hero and workflow illustration for an open-source macOS agent skill named Claude Desktop Director. Primary request: create one professional, exceptionally clear technical product infographic explaining how a Mac agent uses this skill to direct the Claude desktop app. Landscape 16:9 composition, high resolution. This is a workflow illustration, not a screenshot. Style: refined editorial software documentation, crisp modern typography, clean flat diagram with a few subtle dimensional app cards, generous spacing, consistent simple line icons, premium open-source project aesthetic. Background warm off-white, deep charcoal type, restrained terracotta orange and muted teal accents. No gradients that reduce legibility, no clutter. Layout: prominent title at top left 'Claude Desktop Director', directly underneath the Chinese subtitle '中文交代目标，英文指挥执行，持续跟进验收'. Main visual in the middle has three large connected zones read left to right: left speech card labelled '01  中文需求' with a minimal person icon; center control card labelled '02  Mac Agent + Skill' containing two neat short lines '英文任务' and '目标 · 约束 · 验收条件'; right a generic desktop app window with three small macOS window dots labelled '03  Claude Desktop', with two mode chips 'Chat' and 'Code' and a simple execution progress/check symbol. The top forward arrow goes left to center to right. Underneath, a clearly visible feedback arrow from Claude Desktop back to the Mac Agent + Skill card, labelled '读取回复 → 补充纠偏 → 核验产物'. A small final checkmarked output card below the central workflow labelled '中文汇报 · 可验证结果', connected from the controller only after verification. Footer small but readable exact text 'Requires an existing macOS computer-control tool'. Use exactly these texts, make all Chinese glyphs correct and readable, no extra copy, no tiny pseudo-code. Ensure arrow topology conveys a human sets objective, Mac agent prepares and sends English instructions, Claude executes and returns feedback, Mac agent checks artifacts and reports to human. Do not imply the skill itself is a standalone daemon or that it controls Claude through a CLI. Avoid official Anthropic, Apple or GitHub logos, fake badges, performance claims, visual watermarks, floating meaningless decorations. Do not reproduce the provided browser screenshot.
```
