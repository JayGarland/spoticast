# Cursor CLI — Chef 使用指南

Audience: Chef agents

## 概述

Cursor CLI (`agent`) 是 Cursor IDE 的命令行接口，支持从终端直接与 coding agent 交互。它支持 50+ 模型、非交互式 print 模式、Task subagent 委派和 plugin 加载。

在 Resonova 公司工具链中，Cursor CLI 定位为 **Copilot CLI 的补充方案**，适合单 agent 委派和模型对比场景。

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
| `--continue` | 继续上次会话 |
| `--resume` | 选择历史会话恢复 |

## Subagent 能力

### Task 工具（✅ 已测试可用）

Cursor CLI 通过 `Task` 工具支持 subagent 委派。Subagent 类型是**预定义的**：

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

### 限制

- **不能自定义 subagent 类型** — 没有 `define_subagent` 等效工具
- **Subagent 无独立 system_prompt** — 通过 Task prompt 传递角色描述
- **无 SWE/QA 角色区分** — 完整的 RUG 协议（SWE→QA 验证循环）无法在 Cursor CLI 复现

## 与 Copilot CLI 的对比

| 维度 | Copilot CLI | Cursor CLI |
|---|---|---|
| **自定义 agent** | ✅ `--agent` flag | ❌ 无 `--agent` flag |
| **Subagent 委派** | ✅ `runSubagent`（自定义类型） | ✅ `Task`（预定义类型） |
| **Subagent 角色** | 任意（SWE, QA, RUG...） | 固定（generalPurpose 等） |
| **RUG 协议复刻** | ✅ 完整 | ⚠️ 部分（可委派但无角色区分） |
| **模型选择** | BYOK（DeepSeek 等） | ✅ 50+ 内置模型 |
| **插件扩展** | Copilot plugin 系统 | ⚠️ `--plugin-dir`（格式待验证） |
| **Rules 系统** | `.github/` 约定 | `.cursor/rules/*.mdc` + `AGENTS.md` |
| **非交互式执行** | ✅ `-p` | ✅ `-p` |
| **Cloud agent** | ❌ | ✅ `& prompt` 移交云端 |
| **成本** | DeepSeek BYOK 极低 | 取决于模型 + Cursor 订阅 |

## Chef 使用建议

### 何时用 Cursor CLI

- **单 agent 委派**：用 `generalPurpose` Task 做有界实现任务
- **模型对比**：50+ 模型，Claude/OpenAI/Gemini 全有
- **快速侦察/诊断**：`-p` 单次执行
- **Cloud 后台任务**：`& prompt` 移交云端，不阻塞终端
- **预算灵活的 Claude 访问**：通过 Cursor 订阅用 Claude 模型

### 何时仍用 Copilot CLI

- **RUG Manager 指挥**：Copilot CLI 是唯一支持 `--agent` 加载自定义 agent 文件的 CLI
- **完整 SWE→QA 验证循环**：需要自定义 subagent 角色
- **DeepSeek 低成本运行**：Copilot CLI + DeepSeek BYOK 仍是预算最优方案

### 典型混合工作流

```
Chef 用 Cursor CLI 做模型对比/快速侦察
  → 形成 bounded brief
  → 用 Copilot CLI 调用 RUG Manager 执行实现（完整 RUG 协议）
  → Chef gate 验收
或
Chef 用 Cursor CLI 的 generalPurpose Task 做简单有界任务
  → 单 agent 委派，不需要 SWE/QA 分离
  → Chef gate 验收
```

## 安装验证记录

- 日期：2026-06-23
- 安装路径：`C:\Users\Administrator\AppData\Local\cursor-agent\`
- 认证账号：`xiaotianx@vt.edu`
- Wrapper 修复：regex 改为匹配时间戳格式
- Subagent 测试：`generalPurpose` Task ✅ 可用
- 状态：✅ 已安装可用

## 已知限制

1. **无 `--agent` flag**：不能加载外部自定义 agent 文件
2. **Subagent 类型固定**：只有预定义类型，不能动态定义 SWE/QA
3. **Wrapper regex bug**：需手动修复 agent.ps1（或等待官方更新）
4. **Plugin 格式未验证**：`--plugin-dir` 接受的插件格式待确认
5. **PATH 问题**：首次安装后需重启终端
