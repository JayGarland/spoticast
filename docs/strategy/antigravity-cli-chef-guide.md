# Antigravity CLI — Chef 使用指南

Audience: Chef agents

## 概述

Antigravity CLI (`agy`) 是 Google Gemini CLI 的继任者（Gemini CLI 已于 2026-06-18 对个人用户退役）。它支持多模型、插件扩展和非交互式 prompt 执行。

在 Resonova 公司工具链中，Antigravity CLI 定位为 **Copilot CLI 的补充方案**，而非替代品。

## 安装

```powershell
# Windows PowerShell
irm https://antigravity.google/cli/install.ps1 | iex
```

```bash
# macOS / Linux
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

```cmd
# Windows CMD
curl -fsSL https://antigravity.google/cli/install.cmd -o install.cmd && install.cmd && del install.cmd
```

安装后二进制位于 `%LOCALAPPDATA%\agy\bin\agy.exe`（Windows）或 `~/.agy/bin/agy`（macOS/Linux）。需重启终端或手动添加到 PATH。

验证：`agy --version`（当前版本 1.0.10）。

## 可用模型

```
agy models
```

| 模型 | 备注 |
|---|---|
| Gemini 3.5 Flash (Low/Medium/High) | Google 主力，三级推理力度 |
| Gemini 3.1 Pro (Low/High) | 上一代 Pro |
| Claude Sonnet 4.6 (Thinking) | Anthropic |
| Claude Opus 4.6 (Thinking) | Anthropic 旗舰 |
| GPT-OSS 120B (Medium) | 开源级模型 |

## Chef 使用方式

### 基本命令模板

```powershell
# 非交互式单次执行（类比 Copilot CLI 的 -p）
agy --add-dir "F:\GitHub\resonova" --model "Gemini 3.5 Flash (High)" --print "<brief>" --dangerously-skip-permissions
```

```powershell
# 交互式会话
agy --add-dir "F:\GitHub\resonova" --model "Claude Sonnet 4.6 (Thinking)" --prompt-interactive "<brief>"
```

### 关键参数

| 参数 | 用途 |
|---|---|
| `--add-dir` | 添加工作目录（可重复，如 `--add-dir A --add-dir B`） |
| `--model` | 选择模型 |
| `--print` / `-p` | 非交互式单次执行，打印响应后退出 |
| `--print-timeout` | print 模式超时（默认 5m） |
| `--prompt-interactive` / `-i` | 交互式会话 |
| `--continue` / `-c` | 继续最近的会话 |
| `--conversation` | 按 ID 恢复历史会话 |
| `--dangerously-skip-permissions` | 自动批准所有工具权限（CI/脚本场景） |
| `--sandbox` | 终端限制沙箱模式 |

## Agent 定制能力

Antigravity CLI 没有 `--agent` CLI flag（不像 Copilot CLI 那样从命令行指定外部 agent 文件），但 Antigravity **平台** 有完整的 agent 定制机制：

### Sub-agent 工具（会话中可用）

| 工具 | 用途 |
|---|---|
| `define_subagent` | 创建自定义 sub-agent（name, description, system_prompt, 工具权限） |
| `invoke_subagent` | 生成 sub-agent 并委派任务（Prompt, Role, TypeName, Workspace） |
| `manage_subagents` | 列出/终止活跃 sub-agents |
| `send_message` | Agent 间通信 |

这意味着 Chef 可以在 prompt 中指示 agent 定义类似 RUG 的 sub-agent 并委派工作——不需要 CLI flag。

### 其他定制路径

- **Plugins**：`agy plugin import gemini` 或 `agy plugin import claude` 导入已有插件
- **Skills**：`SKILL.md` 文件定义领域技能（类似 VS Code Copilot 的 skill 机制）
- **Hooks**：`hooks.json` 在 `.agents/` 目录配置执行生命周期拦截（PreToolUse, PostToolUse 等）

### RUG 插件（已安装）

Copilot 的 RUG 三 agent 工作流已适配为 Antigravity 插件，位于 `.agents/plugins/rug-agentic-workflow/`。

```
.agents/plugins/rug-agentic-workflow/
├── plugin.json              ← Antigravity 插件标记
├── hooks.json               ← 平台级强制：工具白名单 + 协议注入 + 防提前退出
├── scripts/
│   ├── rug-pre-tool-use.ps1     ← PreToolUse: 仅允许 define/invoke/manage_subagent + todo
│   ├── rug-pre-invocation.ps1   ← PreInvocation: 每次模型调用前注入 RUG 协议
│   └── rug-stop.ps1             ← Stop: 未完成时强制继续
├── skills/
│   ├── rug-orchestrator/SKILL.md  ← RUG 协议（纯编排者，绝不自己干活）
│   ├── swe-subagent/SKILL.md      ← SWE 角色（define_subagent 时的 system_prompt）
│   └── qa-subagent/SKILL.md       ← QA 角色（define_subagent 时的 system_prompt）
└── rules/
    └── rug-enforcement.md         ← Always On 规则：委托一切
```

**隔离保证**：插件在 `.agents/` 目录下，仅 Antigravity 扫描此路径。Copilot CLI 读取 `.github/`，Codex CLI 有自己的约定——互不干扰。

**Chef 命令模板（RUG 模式）**：
```powershell
agy --add-dir "F:\GitHub\resonova" --model "Claude Sonnet 4.6 (Thinking)" --print "
Load the rug-orchestrator skill and execute the RUG protocol on this task:
<brief>
" --dangerously-skip-permissions
```

**三层强制体系**（2026-06-23 smoke test 后发现 CLI 不支持 subagent）：

| 层级 | 机制 | 状态 |
|---|---|---|
| 1. Skills | `rug-orchestrator/SKILL.md` | ✅ Agent 可加载编排知识 |
| 2. Rules | `rug-enforcement.md` (Always On) | ✅ 持久约束注入 |
| 3. Hooks — PreToolUse | 工具白名单 | ❌ 已禁用——CLI 不支持 `invoke_subagent`，白名单会瘫痪 agent |
| 3. Hooks — PreInvocation | 协议注入 | ✅ 可用（每次模型调用前注入 RUG 协议） |
| 3. Hooks — Stop | 防提前退出 | ⚠️ 保守策略：`model_stop` 时强制继续 |

**已知 CLI 限制**：`invoke_subagent` 返回 `subagent not found or not allowed to be invoked`。Subagent 功能似乎是 Antigravity IDE 独占，CLI 的 `--print` 模式不支持多进程编排。RUG 插件当前降级为 Skills + Rules 模式（劝告性约束，非平台级强制）。

## 与 Copilot CLI 的对比

| 维度 | Copilot CLI | Antigravity CLI |
|---|---|---|
| **CLI 级 agent 指定** | ✅ `--agent` flag | ❌ 无 `--agent` flag |
| **会话内 agent 定义** | ✅ `agent/runSubagent` | ✅ `define_subagent` + `invoke_subagent` |
| **Subagent 编排** | ✅ `/fleet` 并行 subagents | ✅ `invoke_subagent` 多 sub-agent 委派 |
| **模型选择** | 通过 BYOK 环境变量 | ✅ 内置多模型（Gemini/Claude/GPT-OSS） |
| **插件扩展** | 有限 | ✅ `agy plugin` 系统 + import from Gemini/Claude |
| **非交互式执行** | ✅ `-p` | ✅ `--print` |
| **工作目录** | `-C` | `--add-dir` |
| **成本** | DeepSeek BYOK 极低 | 取决于所选模型 |
| **适合场景** | RUG/Manager 指挥（CLI flag 方式） | 直接 prompt 执行、prompt 内 agent 委派、模型对比 |

## Chef 使用建议

### 何时用 Antigravity CLI

- **直接侦察/探索**：简单代码库查询，不需要完整的 RUG 编排
- **Prompt 内 agent 委派**：用 `define_subagent` + `invoke_subagent` 在会话中动态创建 Manager 类 sub-agent
- **模型对比**：同一 prompt 在不同模型下测试
- **快速诊断**：`--print` 单次执行，结果即返回
- **预算友好的 Claude 访问**：通过 Antigravity CLI 用 Claude 模型，无需单独订阅

### 何时仍用 Copilot CLI

- **预定义 RUG Manager**：Copilot CLI 的 `--agent` flag 可直接加载 `.agent.md` 文件，无需在 prompt 中重新定义 agent
- **成熟的工作流**：RUG + Chef gate 流程已经验证，风险更低
- **DeepSeek 低成本运行**：Copilot CLI + DeepSeek BYOK 仍是预算最优方案

### 两种 Manager 指挥模式

**模式 A：Copilot CLI（当前默认）**
```powershell
copilot -C "F:\GitHub\resonova" --agent "rug-agentic-workflow:rug-orchestrator" --allow-all --no-ask-user -p "<brief>"
```
优点：预加载 agent 文件，一致性强；已验证流程。

**模式 B：Antigravity CLI（实验性）**
```powershell
agy --add-dir "F:\GitHub\resonova" --model "Claude Sonnet 4.6 (Thinking)" --print "
Define a subagent called 'manager' with system_prompt from docs/strategy/ai-agent-role-job-specs.md (Manager section).
Then invoke the manager subagent to: <brief>
" --dangerously-skip-permissions
```
优点：跨模型灵活选择；动态 agent 定义。缺点：需在 prompt 中定义 agent 规格。

### 典型混合工作流

```
Chef 用 Antigravity CLI 做侦察/诊断/模型对比 → 形成 bounded brief
  → 用 Copilot CLI 调用 RUG Manager 执行实现（成熟路径）
  或 用 Antigravity CLI invoke_subagent 执行（实验路径）
  → Chef gate 验收
```

## 已知限制

1. **无 CLI 级 `--agent` flag**：不能像 Copilot CLI 那样从命令行直接加载外部 `.agent.md` 文件。但可在 prompt 中使用 `define_subagent` + `invoke_subagent` 实现等效功能。
2. **Agent 定义在 prompt 中**：每次会话需在 prompt 中描述 agent 规格（或用 plugins/skills 持久化），不如 Copilot CLI 的 `--agent` 方便。
3. **Plugin 和 Skills 系统未充分验证**：`agy plugin import` 和 `SKILL.md` 机制待实际测试。
4. **PATH 需手动配置**：安装后需重启终端或手动添加 `%LOCALAPPDATA%\agy\bin` 到 PATH。
5. **Sub-agent 工具的权限范围**：`define_subagent` 的子 agent 工具权限（enable_mcp_tools, enable_write_tools, enable_subagent_tools）需要在定义时明确指定。

## 安装验证记录

- 日期：2026-06-23
- 版本：1.0.10
- 平台：Windows x64
- 安装路径：`C:\Users\Administrator\AppData\Local\agy\bin\agy.exe`
- 状态：✅ 已安装可用
