# 桌面操作与恢复

## 选择已存在的电脑工具

优先使用当前环境提供的原生应用控制工具。工具名和 API 会变化，先读实际返回的文档。没有工具时才查 [可复用工具](reuse.md)，不要假装纯文本 skill 本身能点击 Mac。不要为普通应用控制读取 Claude 的 cookie、令牌、Keychain、私有应用数据库或内部网络接口。

在提供 `mcp__cua_repl.js` 的环境中，首次调用只执行一个文档规定的初始化 API，例如：

```javascript
var claudeApp = await cua.getApp("Claude");
```

这会返回文档与当前界面；先读返回内容再行动。显示名解析失败时，用文档提供的应用清单核实 bundle ID。以下方法只是本次编写时实际可用 API 的示例，使用时以当前工具文档为准：

```javascript
await claudeApp.getAXState();
// 从刚返回的状态获取编辑框编号，不能照抄旧编号。
await claudeApp.click(promptIndex);
await claudeApp.paste(englishTask, { format: "text" });
await claudeApp.getAXState();
// 读回内容并取得当前发送按钮编号之后，才发送。
await claudeApp.click(sendIndex);
await claudeApp.getAXState();
```

`promptIndex`、`sendIndex` 和 `englishTask` 是运行时变量，必须先从观察与任务中取得。每组动作之后重新观察，再决定下一组动作。滚动、切换页面或重开窗口后元素编号可能变化。不要复制某次截图坐标作为固定定位器。

2026-10-31 的本机只读检查中，Claude 桌面应用显示 `Claude` / `Code` 入口，以及提示输入、环境、目录、模型、权限、额度等控件。这仅用于说明必须检查模式和目录；不要依赖这些标签永久存在，也不要硬编码本机项目名、模型名或版本。

## 输入长英文与混合语言内容

1. 先确认窗口、模式、会话、目录和编辑框，检查是否有未发送草稿、正在生成的回复或用户正在编辑的内容。有冲突就保留现场，选择可确认的独立会话或询问目标，不要抢占。
2. 优先用工具的文本设置或粘贴能力一次写入多行任务，避免逐字模拟输入受中文输入法影响。按当前工具文档确认粘贴是否保留或恢复原剪贴板；未确认时，不承诺剪贴板恢复。
3. 读取编辑框完整内容；树被截断时分段观察或改用工具支持的文本读取。至少核对任务开头、关键限制、路径/数字和末尾验收条件。不要把截图中“似乎有文字”当成完整验证。
4. 长文本可能被应用折叠或作为附件。确认应用实际采用的形式，以及 Claude 能否读取。优先压缩无关背景；必须分块时标明 `Context 1/N`，写清收到最后一块前不执行，最终另发完整指令。任务身份、范围和关键限制要在首块与最终执行指令中都清楚。
5. 未确认编辑框是空白或仅含本次草稿时，不使用全选替换。不要先清空用户草稿再补救。
6. 核对完成后点击当前可见发送按钮。Enter 的行为取决于应用与设置，不猜测它是换行还是发送；也不为此更改用户设置。
7. 发送后找到新的用户消息和相应生成状态。如果状态不明确，重新观察/检查末尾记录；未证明上次发送失败前不重复提交。发现发送了错误任务时先停止进一步调度，根据当前执行状态处理，明确告知用户实际影响。

## 文件与权限

普通聊天看到 `/Users/.../report.pdf` 不等于有文件访问权。需要文件时，在用户授权范围内用实际可用的附件或项目入口提供；附件上传后核对文件名和就绪状态。目录是共享范围，不能为了访问一个文件顺手选择整个主目录。

在桌面 Code 等具有执行能力的模式中，下发前核对实际项目目录、环境及用户要求。改变模型、付费模式、权限策略和全局设置不是输入任务的必要步骤，未经用户要求不改变。对于出现的动作批准，查看它实际会访问/修改什么；用户已授权的普通项目步骤按当前工具规则处理，不全局点击“一律允许”。

## 生成、失败与恢复

用新输出、工具运行标记、停止按钮、发送按钮是否可用和错误提示共同判断状态。不能只因几秒没新字或出现 `Done` 就认定完成。

- Accessibility 树缺正文或控件：用当前截图辅助定位；后续使用编号前再读新树。必要时滚动到最后一条消息。不同工具返回 diff/全树的机制以当前文档为准。
- 看不到回复尾部：先定位对话滚动容器，滚动后读状态；不要把侧栏滚动当作对话滚动。
- 输出截断或上下文不足：保留最后完整结果，发送缺项明确的接续指令。仅在旧会话无法继续或用户要求时新开，并带已核验摘要；别因上下文长就丢弃全部进度。
- 网络错误或应用卡住：先核对是否已有消息/后台工具在运行，再尝试一次界面提供的恢复动作。重发可能产生重复执行，不能当成无害重试。
- 限额：记录界面显示的重置时间及其时区（可见时），保存下一步。不要猜时间、升级付费、换身份或自动切 CLI。
- 登录/系统权限请求：说明缺少哪项实际能力；按当前工具与用户授权处理，需要用户接管的步骤交接，不绕过。
- 连续两次同类 UI 动作失败：切换观察方式或定位策略；若仍受缺失权限/控件不可达阻塞，交付可直接使用的英文任务和具体阻塞，不能声称已下发。

## 跨回合工作记录

长期任务可在 `.claude-director/<task-id>/` 中保留 `brief.en.md`（当前任务）、`state.md`（进度）、`last-message.en.md`（最后实际发送的指令）。复用已有记录布局更优；不要求为短任务写文件。

`state.md` 只需记录：

```text
Task: <stable task ID>
Goal: <one sentence>
App/mode: <observed app and mode>
Session: <visible title and UI-observed link/identifier, if available>
Working directory/environment: <confirmed scope, or not applicable>
Stage: drafted | sent | running | awaiting-input | blocked | verifying | complete
Last observed: <timestamp with timezone, newest message/tool state>
Verified: <facts and evidence paths; distinguish Claude claims>
Pending: <acceptance criteria still open>
Last sent: <message identifier/excerpt and path if saved>
Next action: <one concrete action; note uncertain send status>
Blocker: <only when observed>
```

恢复时先看本地记录，再核对实际应用和产物。只有最后一条已发送指令确实未产生预期结果时，才决定补发或修正；不能因记录停在 `sent` 就直接重发。不要从应用私有文件反查会话标识；界面没有可用链接时记录标题和可识别的任务标记即可。
