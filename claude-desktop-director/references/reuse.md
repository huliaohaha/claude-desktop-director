# 可复用项目与工具选择

2026-10-31 已按用户要求先检索 GitHub 同类项目。以下是本技能的工具选型依据，不是启动时必须安装的依赖；版本、维护状态和 API 使用前需要重新核实。

| 已有项目 | 可以复用什么 | 在本技能中的定位 |
|---|---|---|
| [openclaw/Peekaboo](https://github.com/openclaw/Peekaboo) | macOS 截图、Accessibility 状态和原生 UI 操作能力 | 没有现成电脑工具时的候选；不重写底层输入/定位框架 |
| [CursorTouch/MacOS-MCP](https://github.com/CursorTouch/MacOS-MCP) | 向 MCP 客户端提供 Mac 应用和界面操作 | 其他 Mac 智能体可评估的替代后端；不要同时叠装多个同类后端 |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | 官方终端编程代理与会话工作流 | 与桌面应用入口分清；不是控制桌面聊天的 API |
| [anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) | 消息循环、会话恢复及执行反馈设计 | 借鉴调度思路；本技能不需要额外安装 SDK |

本技能优先使用环境已有的原生电脑控制工具，在上层补齐英文任务组织、会话选择、读回确认、增量纠偏和独立验收。未复制这些项目的代码，也不需要克隆整个项目才能使用。

## 没有现成后端时

先查智能体工具清单中是否已有原生应用/Accessibility/截图控制。若有，读取其文档，并按 [桌面操作与恢复](desktop-control.md) 的观察与验证原则映射操作。

若完全没有电脑操作能力，明确报告缺少的能力，提供已完成的英文任务；不要声称能够仅靠 skill 文件驱动桌面。根据用户环境评估 Peekaboo 或 MacOS-MCP，核对官方仓库当前安装和权限说明；只有在用户授权的配置范围内安装或设置。需要用户启用系统权限的步骤清楚交接。

用户选择的是 Claude 桌面版，不能用“CLI 更稳定”作为自动改用 CLI 或新建 API 计费方式的理由。只有用户另外选择 CLI/SDK 工作流时，才读取 [Claude Code 官方程序化使用文档](https://code.claude.com/docs/en/headless)，并通过本机 `claude --help` 核实参数、认证、权限与会话机制；那属于后续单独适配的范围。
