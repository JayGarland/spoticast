# gem-reviewer — Chef 使用指南

Audience: Chef agents

## 概述

`gem-reviewer` 是 gem-team 的安全审计 subagent，与 `gem-orchestrator` 配套使用。它不能直接通过 `--agent gem-reviewer` 调用——它的运行依赖 gem-orchestrator 提供的 `context_envelope_snapshot`（执行上下文）。正确路径：给 gem-orchestrator 一个 review brief，由 gem-orchestrator 在内部调用 gem-reviewer。

在 Resonova 工具链中定位：**安全审计与 PRD 合规检查**，填补 HIGH PRIORITY 的 Internal Auditor / Product Reviewer 招募空缺。

本地文件：`C:\Users\Administrator\.copilot\agents\gem-reviewer.agent.md`（5.3KB）

## 能力范围

| 审计类型 | 说明 |
|---|---|
| 安全扫描 | 秘钥/PII/SQLi/XSS grep + 语义扫描 |
| OWASP Top 10 | A01-A10 全覆盖 |
| 移动端安全 | 8 个向量：Keychain/Keystore、证书固定、越狱检测、深链接、安全存储、生物认证、网络安全、HTTPS/PII 传输 |
| PRD 合规 | 每个需求至少有一个任务 + 验收标准 |
| 计划审查 | 原子性、循环依赖、Wave 并行冲突、合约完整性 |
| Wave 审查 | 仅审查变更行 + 直接上下文（不重读整个文件） |

## 调用方式

gem-reviewer 是 `mode: subagent`，不能单独用 `--agent` 调用。必须通过 gem-orchestrator：

```powershell
$job = Start-Job -ScriptBlock {
    copilot --agent gem-orchestrator `
        --allow-all `
        -C "F:\GitHub\resonova" `
        "Using gem-reviewer, audit [scope] for security vulnerabilities and OWASP compliance. Review scope: wave. Return structured findings with file:line citations."
}
Wait-Job $job -Timeout 120
Receive-Job $job
Remove-Job $job
```

### Brief 模板（安全审计）

```
Using gem-reviewer, conduct a security audit of [files/scope].

Review scope: wave
Security focus: OWASP A01-A10
Files to audit: [e.g. resonova/server.py, resonova/api/gemini.py]

Required output:
- critical_findings: file:line format
- status: completed | failed | needs_revision
- prd_score (if PRD file present)

Do not patch code. Return findings only.
```

### Brief 模板（计划审查）

```
Using gem-reviewer, review the implementation plan at [plan_path].

Review scope: plan
Check: PRD coverage, atomicity, circular deps, wave parallelism, missing contracts.

Return: status + critical_findings.
```

## 输出格式

gem-reviewer 返回 JSON：

```json
{
  "status": "completed | failed | needs_revision",
  "critical_findings": ["SEVERITY file:line — issue description"],
  "files_reviewed": 5,
  "prd_score": 82,
  "acceptance_criteria_missing": 2
}
```

Chef 验收标准：
- `critical_findings` 中每条必须有 `file:line`
- 不接受 "no issues" 而没有扫描证据
- 移动端相关代码必须覆盖 8 个向量

## 与其他审计管理器对比

| 维度 | gem-reviewer | se-security-reviewer | agent-governance-reviewer |
|---|---|---|---|
| **调用方式** | 通过 gem-orchestrator | 直接调用 | 直接调用 |
| **安全重点** | OWASP + PRD 合规 + 移动端 | OWASP + LLM Top 10 + Zero Trust | 多 agent 治理 + 审计链 |
| **输出格式** | JSON（结构化） | Markdown 报告 | Markdown 建议 |
| **适用场景** | wave/plan 审查，嵌入 gem 工作流 | 独立安全扫描 brief | agent 系统治理审计 |
| **模型** | gem-team 默认 | GPT-5 | GPT-4o |

## 何时用 gem-reviewer vs se-security-reviewer

- **嵌入 gem 工作流**（gem-orchestrator 已在运行）→ 用 gem-reviewer
- **独立安全 brief**（不需要 gem 工作流开销）→ 用 se-security-reviewer
- **LLM 提示注入、AI 系统安全**重点 → 用 se-security-reviewer
- **agent 系统治理**（trust boundary、audit trail）→ 用 agent-governance-reviewer

## 安装验证记录

- 日期：2026-06-25
- 来源：gem-team plugin（已本地安装）
- 文件：`C:\Users\Administrator\.copilot\agents\gem-reviewer.agent.md`（5,461 bytes）
- 状态：✅ 文件存在，subagent 模式，通过 gem-orchestrator 调用
- 性能初始权重：0.70（试用，normal gate）
