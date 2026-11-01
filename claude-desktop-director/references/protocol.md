# 任务与发送状态协议（候选版）

该协议约束智能体行为，不是 UI 层安全隔离。随附脚本只检查记录的内部一致性，不拦截点击、不验证真实屏幕、不实现服务端幂等。

## 三条独立状态轴

- `phase`: draft / ready / sending / sent / running / awaiting-user / blocked / verifying / complete / cancelled。
- `delivery`: not-sent / sending / unknown / confirmed / failed-no-effect。
- 每个验收条件 `status`: pending / pass / fail / unverifiable。

`confirmed` 仅表示匹配的用户消息出现在正确会话；不等于 Claude 开始执行，更不等于结果正确。`unknown` 和 `failed-no-effect` 不相同：后者要求有可靠证据证明没有派发或任何副作用。缺少回显、网络报错和编辑框仍有文字都不能单独证明 failed-no-effect。

## 单次消息协议

准备：Task-ID 稳定；Message-ID 每条消息唯一，修正或重试采用新 Message-ID。`payload_sha256` 对实际待发 UTF-8 字节计算，包含 Task-ID/Message-ID；不自动 trim、改换行或做 Unicode 归一化。哈希不是隐私脱敏，也不是服务器幂等键。

发送前：保留目标（应用、模式、任务会话标记、可见会话定位、工作范围）、完整待发文本与读回证据。采用 JSON 记录时，`message.readback` 包含 `payload_sha256`、`target_anchor`、`observed_at`、`evidence_ref` 和 `complete: true`；只有实际完成全文核对后才填写。读回必须属于这次准备之后、发送开始之前的同一目标。应用只做可说明的 CRLF 转换时，先确定实际待发送文本，再对实际字节计算哈希；不忽略其他差异。

临界步骤：在调用发送前于宿主可恢复任务上下文记录 `sending`，再执行一次动作。已有对话中的待发文本、目标及工具事件可以作为短任务记录，不要求先创建本地日志或运行校验器。长任务使用受保护持久记录时，发送意图写入失败就先解决记录问题，不冒险发送。中途退出或失去工具连接后按可能已发送恢复；没有先前意图或证据时不补造历史。

动作后：正确会话内出现含匹配 Task-ID/Message-ID 和内容的用户消息才标 confirmed。全文不可见时，保留未确认状态，使用真实可用的展开/读正文方式核验。无消息却见 spinner 不是充分证据。

不确定：进入 `blocked + unknown`，先观察、检查目标与历史。找到原消息的完整匹配回显可转 `confirmed`；再按当前运行状态继续观察或发不同的必要续问。仅在可靠证明 `failed-no-effect` 后，才可用新 Message-ID 重试同一意图。尚未查清时不在受影响会话新增下发；无法继续判断才交接。单写者约定不排除用户或其他进程，因此不宣称 exactly-once。

消息历史不能被下一条草稿覆盖。使用文件时保留发送意图的关联历史，状态快照应使用宿主支持的安全写入方式；原子替换只能减少单文件损坏，不能使发送和写盘成为一个事务。本包没有实现记录写入器、跨进程锁或持久化事务，不能把文字规则当已实现代码。JSON 校验器是可选的离线诊断，不是每次发送的运行时门控。

## 预算

先遵守用户明确的时间、费用、纠偏轮次或工具调用预算及宿主实际限制。未提供整体预算时不凭空设置停工截止时间；保持进展就继续。局部防循环策略：同类 UI 失败两次改策略，多轮纠偏无新增证据时重新诊断；可将数分钟无进展用作诊断提醒，但不把它等同于失败或完成。光标闪烁与计时器变化不是任务进展，既定总预算不能因新消息而重置。

达到用户预算或宿主限制：停止本轮新增下发、记录 `blocked` 与原因并交付已证实部分；不是自动终止 Claude 的计算，也不是任务完成或失败结论。若工作仍在运行，说明是否已观察到停止；需要额外预算时再提出具体缺口。不能通过一条很长的阻塞 sleep 假装监控。

## 验收与校验

每个条件有独立 ID、要求、验证方式、状态与证据引用。`pass` 要求 evidence.kind=independent-check；证据应说明对象、时间/版本和实际结果。无法读取产物则 unverifiable。complete 要求所有必需条件 pass；取消、阻塞和部分结果单独报告。

示例格式见 [JSON 状态记录](../assets/task-state.example.json)；在仓库根目录运行可选校验：

```sh
python3 claude-desktop-director/scripts/check_state.py /path/to/task-state.json
```

这只能检查声明之间有无矛盾，不能证明声明是真的。旧 state.md 不自动迁移；恢复时核对现场，再生成新记录。缺失状态按未知，不补造历史。
