# Cursor CLI — Chef 使用指南

Audience: Chef agents

## 2026-06-25 重新审计：不要按 RUG 克隆来评估

Cursor CLI should be evaluated as a **Cursor-native manager/reviewer interface**, not as
a GitHub Copilot RUG clone. The useful question is not "can Cursor exactly reproduce
RUG?" but "which Cursor-native features can improve Resonova manager work?"

Current answer: Cursor CLI is a candidate for planning, review, model comparison,
isolated worktree trials, and structured automation output. It is not the default
implementation manager yet, and it does not replace the known Copilot/RUG path.

Native strengths to test:

- `--mode plan` / `--mode ask` for read-only planning and critique before execution.
- `-p --output-format text|json|stream-json` for scriptable manager runs and evidence capture.
- `--worktree` / `--worktree-base` for isolated product-code trials without dirtying `main`.
- Broad model access (`composer`, OpenAI/Codex, Claude, Gemini, Grok, Kimi, GLM).
- `.cursor/rules/` plus `AGENTS.md` for repo guidance.
- Custom subagents under `.cursor/agents/` per current Cursor docs; this still needs a
  local Resonova trial before we rely on it operationally.
- MCP / ACP / worker / cloud handoff as optional interface strengths, subject to privacy
  and approval boundaries.

## 概述

Cursor CLI (`agent`) 是 Cursor IDE 的命令行接口，支持从终端直接与 coding agent 交互。它支持多模型、非交互式 print 模式、plan/ask 模式、worktree 隔离、subagent 委派、MCP/ACP、worker/cloud workflows 和 plugin 加载。

在 Resonova 公司工具链中，Cursor CLI 暂定为 **候选 manager/reviewer interface**：用于规划、审查、模型对比、结构化输出和隔离 worktree 试验。不要把它评估成 Copilot/RUG 的一比一复制品。

## 安装

```powershell
# Windows PowerShell（需 Windows PowerShell 5.1，非 pwsh）
powershell.exe -Command "irm 'https://cursor.com/install?win32=true' | iex"
```

```bash
# macOS / Linux / WSL
curl https://cursor.com/install -fsS | bash
```

安装后二进制位于 `%LOCALAPPDATA%\cursor-agent\`。首次安装可能需重启终端使 PATH 生效。

验证：`agent --help`

### 已知安装问题

2026-06-23 安装时发现 wrapper 脚本 regex bug：版本目录名含时间戳（`2026.06.19-20-24-33-hash`），但 agent.ps1 的 regex 只匹配 `YYYY.MM.DD-hash` 格式。已修复：`agent.ps1` 第 46 行 regex 改为 `^\d{4}\.\d{1,2}\.\d{1,2}-\d{2}-\d{2}-\d{2}-[a-f0-9]+$`。

**更正 (Chef, 2026-06-23)**：实际被调用的 wrapper 是 **`cursor-agent.ps1`**（`cursor-agent.cmd` 和 `agent.cmd` 都走它），不是 `agent.ps1`——之前的修复改错了文件，标准命令 `cursor-agent --version` 仍报 "No version directories found"。已修正 `cursor-agent.ps1` 第 48 行 regex 为 `^\d{4}\.\d{1,2}\.\d{1,2}(-\d{2}){0,3}-[a-f0-9]+$`（兼容含/不含时间戳两种格式）。修复后 `cursor-agent --version` / `agent --version` 均正常返回版本。Chef 已实测无头 read + edit（`-p ... -f --output-format text --workspace <repo> --model gemini-3.5-flash`）均成功——比 agy 干净得多：无 cwd hack、无需绝对路径、输出正常捕获。

## 认证

```powershell
agent login
# 打开浏览器链接完成认证
# 或设置环境变量：$env:CURSOR_API_KEY = "..."
```

## 可用模型（部分亮点）

| 模型 | 备注 |
|---|---|
| `claude-opus-4-8-thinking-xhigh` | Anthropic 旗舰 + Thinking |
| `claude-4.6-sonnet-medium` | 性价比之选 |
| `gpt-5.5-high` | OpenAI 最新 |
| `gpt-5.3-codex-xhigh` | Codex 专业编码 |
| `composer-2.5` | Cursor 自有模型 |
| `gemini-3.5-flash` | Google 快速模型 |
| `grok-build-0.1` | xAI 模型 |

完整列表：`agent models`

## Chef 使用方式

### 基本命令模板

```powershell
# 非交互式单次执行
agent -p "<brief>" -f --output-format text --workspace "F:\GitHub\resonova" --model "claude-4.6-sonnet-medium"
```

```powershell
# 只读规划 / 评审
agent -p "<planning brief>" --mode plan --output-format text --workspace "F:\GitHub\resonova" --model "gpt-5.3-codex-high"
```

```powershell
# 隔离 worktree 的有界实现试验
agent -p "<bounded implementation brief>" -f --worktree cursor-risk-trial --workspace "F:\GitHub\resonova" --model "composer-2.5-fast"
```

```powershell
# 交互式会话
agent --workspace "F:\GitHub\resonova" --model "claude-opus-4-8-thinking-xhigh"
```

### 关键参数

| 参数 | 用途 |
|---|---|
| `-p, --print` | 非交互式单次执行 |
| `-f, --force` | 自动批准所有命令（等同于 `--yolo`） |
| `--output-format` | text / json / stream-json |
| `--model` | 选择模型 |
| `--workspace` | 工作目录 |
| `--plugin-dir` | 加载本地插件目录（可重复） |
| `--mode` | plan（只读规划）/ ask（问答） |
| `--worktree` | 在 Cursor 管理的隔离 worktree 中执行 |
| `--worktree-base` | 指定 worktree 基线分支 |
| `--sandbox` | command sandbox: enabled / disabled |
| `--stream-partial-output` | 与 `stream-json` 配合，流式输出部分结果 |
| `--trust` | 信任 workspace；只在已审计 repo 使用 |
| `--continue` | 继续上次会话 |
| `--resume` | 选择历史会话恢复 |

## Subagent 能力

### Cursor-native subagents（需重新本地试验）

旧记录只验证过 Task 工具能委派预定义类型。Current official Cursor docs say
subagents can be used in the editor, CLI, and Cloud Agents, with built-ins such as
Explore/Bash/Browser and custom subagents stored in `.cursor/agents/`.

Custom subagent file shape:

```markdown
---
name: resonova-verifier
description: Review a Resonova diff for scope, prompt-safety regressions, and missing validation.
model: inherit
readonly: true
is_background: false
---

You are a verifier. Inspect the diff and tests. Do not modify files.
Return findings first, then validation gaps and residual risk.
```

### Older Task record（✅ 已测试可用）

Cursor CLI 通过 `Task` 工具支持 subagent 委派。历史测试看到过这些类型：

| Subagent 类型 | 用途 |
|---|---|
| `generalPurpose` | 通用任务委派（最灵活） |
| `bugbot` | Bug 检测和分析 |
| `security-review` | 安全审查 |
| `best-of-n-runner` | 并行实验（独立 worktree） |
| `cursor-guide` | Cursor 使用指导 |

### Subagent 委派模板

```powershell
agent -p "Use the Task tool to launch a generalPurpose subagent.
Prompt the subagent with:
'<specific task with scope, acceptance criteria, constraints>'
Report the subagent's complete output." -f --output-format text --workspace "F:\GitHub\resonova"
```

### 限制 / gates

- **不要按 RUG 复刻打分**：Cursor has its own interface surface; use the features it has.
- **Custom subagents 未完成 Resonova 本地试验**：official docs support them, but company
  policy needs one bounded trial before operational trust.
- **`-f` / `--yolo` 必须配合隔离 worktree** for product-code trials unless Chef explicitly
  approves direct writes.
- **Cloud/worker handoff 需隐私边界**：product memory, keys, and customer-sensitive context
  should not be sent to cloud/background modes without explicit approval.
- **No approval authority**：Cursor manager/reviewer output still goes through Chef gate.

## 与 Copilot CLI 的对比

| 维度 | Copilot CLI | Cursor CLI |
|---|---|---|
| **自定义 agent** | ✅ `--agent` flag | ❌ 无 `--agent` flag |
| **Subagent 委派** | ✅ `runSubagent` / CLI subagent features | ✅ built-ins + custom `.cursor/agents/` per docs |
| **Subagent 角色** | 任意（SWE, QA, RUG...） | Custom subagents need Resonova trial |
| **评估框架** | RUG manager path remains proven | Cursor-native manager/reviewer interface |
| **模型选择** | BYOK（DeepSeek 等） | ✅ 50+ 内置模型 |
| **插件扩展** | Copilot plugin 系统 | ⚠️ `--plugin-dir`（格式待验证） |
| **Rules 系统** | `.github/` 约定 | `.cursor/rules/*.mdc` + `AGENTS.md` |
| **非交互式执行** | ✅ `-p` | ✅ `-p` |
| **Worktree 隔离** | 手动 git worktree | ✅ `--worktree` built in |
| **Cloud agent** | ❌ | ✅ `& prompt` 移交云端 |
| **成本** | DeepSeek BYOK 极低 | 取决于模型 + Cursor 订阅 |

## Chef 使用建议

### 何时用 Cursor CLI

- **只读规划/挑战**：`--mode plan` / `--mode ask` for product and code briefs.
- **模型对比**：Claude/OpenAI/Codex/Gemini/Composer/Grok 等多模型横向检查。
- **结构化 evidence capture**：`--output-format json|stream-json` for manager logs.
- **隔离实现试验**：`--worktree` for bounded docs/code trials.
- **Verifier subagent 试验**：try `.cursor/agents/` for read-only review roles.
- **Cloud/worker 后台任务**：只用于已批准的非敏感任务。

### 何时仍用 Copilot CLI

- **RUG Manager 指挥**：Copilot CLI 是唯一支持 `--agent` 加载自定义 agent 文件的 CLI
- **完整 SWE→QA 验证循环**：需要自定义 subagent 角色
- **DeepSeek 低成本运行**：Copilot CLI + DeepSeek BYOK 仍是预算最优方案

### 典型混合工作流

```
Chef 用 Cursor CLI 做只读规划/模型对比/快速审查
  → 形成 bounded brief
  → 用 Copilot CLI 调用 RUG Manager 执行实现（完整 RUG 协议）
  → Chef gate 验收
或
Chef 用 Cursor CLI 在 --worktree 中做 Cursor-native 试验
  → 可选 custom verifier subagent / structured output
  → Chef gate 验收
```

### 新试验建议

Run a docs-only trial before trusting Cursor with product code:

```powershell
agent -p "Use Cursor-native capabilities. In a Cursor worktree, create a concise docs-only audit note for one existing agent guide. Use AGENTS.md. Do not touch source. Run git diff --check. Return changed files, validation, risks." -f --worktree cursor-docs-trial --workspace "F:\GitHub\resonova" --model "composer-2.5-fast" --output-format text
```

## 安装验证记录

- 日期：2026-06-23
- 安装路径：`C:\Users\Administrator\AppData\Local\cursor-agent\`
- 认证账号：`xiaotianx@vt.edu`
- Wrapper 修复：regex 改为匹配时间戳格式
- Subagent 测试：`generalPurpose` Task ✅ 可用
- 状态：✅ 已安装可用

2026-06-25 重新审计：

- 本机 `agent --version`：`2026.06.19-20-24-33-653a7fb`
- 认证账号：`xiaotianx@vt.edu`
- `agent models` 可列出多模型；当前默认显示 Gemini 3.5 Flash。
- `agent mcp list` shows `chrome-devtools` pending approval.
- 未重新试验 custom `.cursor/agents/`、`--worktree` implementation, cloud, or worker.
- 状态：✅ installed usable; candidate manager/reviewer interface, pending Cursor-native trial.

2026-06-25 product-code trial:

- Trial: `agent -p ... -f --worktree cursor-spotify-init-trial --workspace F:\GitHub\resonova`.
- Scope: Android Spotify Web Playback SDK `init_error: Failed to initialize player`.
- Result: useful diagnosis and direction, not raw-acceptable code.
- Cursor correctly identified the product-level fix direction: avoid eager ungated `connect()`,
  use `activateElement()`, and route SDK connection through user gestures.
- Cursor's raw patch deferred SDK load too far, so the first Generate tap could still miss
  the synchronous user-activation window if the player was not built yet.
- Chef accepted the direction but rewrote the patch: load/build the SDK player early, defer
  only `activateElement()` and `connect()` to user gestures, keep reload fallback, and refresh
  `/auth/token`.
- Decision: Cursor CLI is **not untrustable for coding**, but it is not an autonomous product
  code owner. Use it for isolated worktree trials and second opinions; Chef must inspect and
  usually tighten the patch before merging.

## 已知限制

1. **无 `--agent` flag**：不能加载外部自定义 agent 文件
2. **Custom subagent 仍需本地试验**：docs support `.cursor/agents/`, but Resonova has not accepted it operationally yet
3. **Wrapper regex bug 是历史问题**：current local `agent --version` OK; reinstall may need re-check
4. **Plugin 格式未验证**：`--plugin-dir` 接受的插件格式待确认
5. **PATH 问题**：首次安装后需重启终端
6. **Cloud/worker 隐私边界**：must be explicitly approved for sensitive Resonova context
