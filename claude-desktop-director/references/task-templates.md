# 英文任务模板

模板是起点，按任务缩短和改写；不要把尖括号占位符发给 Claude。用户指定中文交付物时，在英文指令中明确要求该产物用中文。无关条目删除。

## 初始任务

```text
Task: <stable task ID and short title>

Objective
<What the user wants completed, with necessary context.>

Inputs and scope
<Relevant files, excerpts, links, confirmed project directory/environment,
and what this session can actually access.>

Requirements
<Concrete behavior, facts, constraints, and requested deliverable language.>

Deliverables and acceptance
<Observable outputs, output location, and how completion will be checked.>

Execution
<Choose a scope-appropriate instruction: research only, plan only,
review only, or implement and verify.>
Resolve routine implementation choices yourself. Ask only when a missing
fact or decision materially affects correctness or the authorized scope.
If you cannot access an input or perform an action, state the exact
limitation. Do not present a proposal or an unexecuted command as a
completed result. Keep the final report concise and include evidence
appropriate to this task and any remaining gaps.
```

软件项目适用时补充：

```text
Inspect the existing project and its AGENTS.md / CLAUDE.md instructions.
Before building a new solution, look for existing or similar GitHub
projects. Report the relevant repository links and the specific reuse
decision, then implement within the confirmed project scope.
Preserve unrelated work. Run the checks relevant to the changes and
report the actual results and changed files.
```

只有写计划权限时使用：

```text
Research and produce a concrete plan only. Do not modify files or start
implementation. Include the proposed approach, open decisions, and the
evidence needed to validate it.
```

不能访问本机文件的聊天中使用：

```text
You are working from the attached material and the excerpts below.
Do not assume you can read my local paths. If additional material is
needed, name the smallest specific excerpt or file required.
```

## 只给方案，尚未执行

```text
Task: <same ID>
The requested outcome is an implemented and verified result.
Your last response describes an approach, but <specific deliverable>
is still missing. Proceed with <next authorized step> in <confirmed scope>.
Return <artifact and evidence>. If this session lacks execution access,
identify that limitation explicitly instead of implying the work was done.
```

## 验收发现问题

```text
Task: <same ID>
The current result does not yet meet <specific acceptance criterion>.
Observed evidence: <exact error, counterexample, diff, or missing output>.
Expected result: <concrete expected behavior>.
Investigate the cause, make the necessary correction within the existing
scope, and verify <the affected behavior>. Preserve the parts already
verified: <short list if useful>. Return the corrected artifact and evidence.
```

## 中途补充与用户纠正

```text
Task: <same ID>
Update from the user: <new requirement or factual correction>.
This supersedes <the precise earlier assumption, if applicable>.
Continue from the current state. First assess whether this changes
completed work, then apply the necessary adjustment and verify the result.
```

不要把用户的状态询问误当成取消，也不要因为补充一个事实重做全部工作。

## 恢复长任务

```text
Resume task <same ID>.
Objective and scope: <concise restatement>.
Verified so far: <facts with artifact locations>.
Last observed state: <what actually happened, including uncertain sends>.
Remaining acceptance criteria: <specific gaps>.
Next step: <concrete action>.
Check the current files/session state before acting. Reuse completed work
and avoid repeating operations whose outcomes are uncertain.
```

## 要求补齐完成证据

```text
Task: <same ID>
Before closing this task, provide <the specific missing artifact,
source, verification result, or exact file location>.
Separate work actually performed from recommendations and unresolved
limitations. Do not rerun unrelated checks merely to fill a report.
```

## 具体例子：让 Claude 在项目中修一个测试失败

用户：“让 Claude 修一下这个项目登录后跳回登录页的问题，别动注册流程。”

先从上下文确认仓库路径、复现条件和期望；不要虚构原因。合适的英文下发可为：

```text
Task: login-redirect-fix

Fix the bug in the confirmed project where a user is redirected back to
the login page immediately after a successful login. The registration
flow must remain unchanged.

Inspect the existing auth flow and repository instructions. Establish a
reproduction before choosing a fix. Review existing project mechanisms
and relevant established implementations before adding a new mechanism.
Implement the fix, verify the login behavior, and check that registration
is unaffected using the project's relevant checks. Preserve unrelated work.

Return the changed file paths, the cause supported by evidence, the actual
verification results, and any remaining limitation. Ask only if a missing
reproduction detail cannot be established from the project.
```

仅在实际确认的桌面 Code/执行模式中要求本地修改。普通聊天无项目访问能力时，应先取得必要材料或选择用户授权的应用内执行入口，不能直接发送并宣称它正在修本地仓库。
