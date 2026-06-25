# OpenAI Codex CLI — Chef 使用指南

Audience: Chef agents

## 概述

OpenAI Codex CLI（`@openai/codex` v0.142.0，Rust 编译二进制）是无头执行的单 agent 管理器接口。它比 agy 更干净，不需要 cwd hack 或绝对路径技巧；比 Cursor CLI 更轻量，适合无头委派和快速侦察。自动读取仓库根目录的 `AGENTS.md`。

在 Resonova 工具链中定位：**轻量单 agent 委派**，补充 Copilot CLI（RUG 协议）和 Cursor CLI（多模型/subagent）。

## 安装

```powershell
npm install -g @openai/codex
```

验证：`codex --version`（应返回 `codex-cli 0.142.0`）

## Auth 配置 — 关键（2026-06-25 已验证）

APIKEY.FUN 代理需要特定格式。**根本原因**：auth.json 中若存在 `auth_mode = "chatgpt"`，CLI 会用 ChatGPT JWT 替代 API Key 作为 Bearer Token，导致 401。

**`C:\Users\Administrator\.codex\auth.json`**（必须只含此内容，无 tokens 字段）：

```json
{
  "OPENAI_API_KEY": "sk-7c04ebe164bcc6f931753c85b7ca530324847923e3f18411fe1054d141349c17"
}
```

**`C:\Users\Administrator\.codex\config.toml`** — provider 相关字段：

```toml
model_provider = "codex"

[model_providers.codex]
name = "codex"
base_url = "https://api.apikey.fun"
wire_api = "responses"
requires_openai_auth = true
```

注意：
- provider 名必须是 `codex`，不能是 `custom`
- `base_url` 不含 `/v1` 后缀
- 清空 auth.json 会移除 Codex 桌面端的 ChatGPT OAuth Tokens，桌面端需重新登录

## 可用模型（APIKEY.FUN，93% 折扣）

| 模型 | 说明 |
|---|---|
| `gpt-5.5` | 旗舰，最强 |
| `gpt-5.4` | 平衡 |
| `gpt-5.4-mini` | 快速轻量 |

## Chef 使用方式

### 基本无头命令模板

```powershell
$job = Start-Job -ScriptBlock {
    codex exec `
        -C "F:\GitHub\resonova" `
        -m "gpt-5.5" `
        -s read-only `
        --ephemeral `
        --color never `
        "<brief>"
}
$result = Wait-Job $job -Timeout 90
Receive-Job $job
Remove-Job $job
```

### 关键参数

| 参数 | 用途 |
|---|---|
| `-C <dir>` | 工作目录（直接生效，无需 cwd hack） |
| `-m <model>` | 模型名称 |
| `-s <mode>` | sandbox 策略：read-only / workspace-write / danger-full-access |
| `--ephemeral` | 不持久化 session 文件 |
| `--color never` | 无 ANSI 颜色（无头捕获必备） |
| `--dangerously-bypass-approvals-and-sandbox` | 跳过所有审批和沙盒（**需 boss 明确授权**） |
| `--dangerously-bypass-hook-trust` | 跳过 hook 信任验证（**需 boss 明确授权**） |
| `--ignore-user-config` | 忽略 config.toml（auth 仍从 auth.json 读取） |
| `-c key=value` | 覆盖单个 config 值（如 `-c model="gpt-5.4"`） |
| `--ephemeral` | 不写 session 文件 |
| `--json` | 输出 JSONL 事件流 |

### Resume / Review 子命令

```powershell
codex exec resume --last              # 恢复上一次 session
codex exec review -C F:\GitHub\resonova  # 代码审查模式
```

## Subagent / MCP 潜力

| 特性 | 状态 |
|---|---|
| 原生 subagent | ❌ 无 `invoke_subagent` |
| `--agent` 自定义 agent 文件 | ❌ 无此 flag（Copilot CLI 独有） |
| `codex mcp-server` | ✅ 将 Codex 暴露为 stdio MCP 服务 |
| MCP 桥接 RUG | ⚠️ 理论可行，注册到 Copilot config 后 RUG 可调用 Codex 工具（未测试） |

**MCP 暴露命令**：`codex mcp-server`（stdio 协议，可注册进 Copilot MCP 配置）

## 与其他管理器对比

| 维度 | Copilot CLI | Cursor CLI | Codex CLI |
|---|---|---|---|
| **RUG 协议** | ✅ 完整 | ⚠️ 部分 | ❌ 无 |
| **自定义 subagent** | ✅ 任意角色 | ✅ 预定义类型 | ❌ |
| **模型选择** | DeepSeek BYOK | 50+ 内置 | APIKEY.FUN gpt-5.x |
| **AGENTS.md 自动读取** | ✅ | ✅ | ✅ |
| **cwd/路径 hack** | 不需要 | 不需要 | 不需要 |
| **安装复杂度** | 高 | 中 | 低（`npm i -g`） |
| **无头执行** | ✅ | ✅ | ✅ |
| **成本** | DeepSeek 极低 | Cursor 订阅 | APIKEY.FUN 93% 折扣 |

## Chef 使用建议

### 何时用 Codex CLI

- **有界单 agent 任务**：不需要 SWE/QA 分离的实现委派
- **快速无头侦察**：`-s read-only` 模式探查代码
- **代码审查**：`codex exec review` 子命令
- **预算限制场景**：APIKEY.FUN 93% 折扣 vs 官方价格

### 何时仍用其他管理器

- **RUG 协议**：只能用 Copilot CLI（`--agent` flag）
- **多模型 A/B 对比**：Cursor CLI（50+ 模型）
- **Claude 模型访问**：Cursor CLI（有 Claude 4 系列）

## 安装验证记录

- 日期：2026-06-25
- 版本：`@openai/codex` v0.142.0，Rust binary `codex-cli 0.142.0`
- 安装路径：`C:\Users\Administrator\AppData\Roaming\npm\` (wrapper)
- Provider：APIKEY.FUN（gpt-5.5, gpt-5.4, gpt-5.4-mini）
- Auth 问题：auth_mode="chatgpt" + tokens → 401；修复：仅保留 OPENAI_API_KEY
- 测试任务：列出 `resonova/` 下的 Python 模块 ✅（17,787 tokens，正确输出）
- 状态：✅ 已安装可用
