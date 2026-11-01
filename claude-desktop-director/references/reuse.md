# 可复用项目：借鉴机制，不扩张依赖

审查基于 2026-10-31 本次读取的公开 main/文档；未取得全部项目固定 commit，不把分支内容当永久版本承诺。

| 项目 | 借鉴什么 | 不应照搬什么 |
|---|---|---|
| [openclaw/Peekaboo](https://github.com/openclaw/Peekaboo) | 目标窗口绑定、当前观察/快照、动作结果不确定后的重新验证 | 不硬编码 UI 编号；未经本机验证不宣称适配完成 |
| [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | ref 的上下文与生命周期、内容来源边界、策略分层 | 它是浏览器工具，不因可借鉴就把桌面入口改为浏览器；当前持久 DOM ref 不因每次快照都作废 |
| [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/skill-creator) | 旧版/新版对照、独立评估、trigger 测试、可核查 expectations | 格式检查不替代模型行为评估，也不替代桌面 E2E |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | checkpoint/interrupt、恢复时副作用重复的风险 | 不为这个小 skill 强制引入框架或数据库；检查点不能使 UI 点击幂等 |

本候选版未复制这些项目的实现代码；文档与工具协议只作设计参考。已有 CursorTouch/MacOS-MCP 和 Claude Agent SDK 选型可保留为后续调研，不能据此宣称桌面通道已支持。

本轮核对的具体来源：

- [Peekaboo 的动作与窗口绑定](https://github.com/openclaw/Peekaboo/blob/main/docs/automation.md)、[click 约定](https://github.com/openclaw/Peekaboo/blob/main/docs/commands/click.md)。
- [agent-browser 核心规则](https://github.com/vercel-labs/agent-browser/blob/main/skill-data/core/SKILL.md)、[信任边界](https://github.com/vercel-labs/agent-browser/blob/main/skill-data/core/references/trust-boundaries.md)。
- [Anthropic skill-creator 的对照评估](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)。
- [LangGraph 中断与重复副作用](https://docs.langchain.com/oss/python/langgraph/interrupts)。
- [Agent Skills 格式规范](https://agentskills.io/specification)。
