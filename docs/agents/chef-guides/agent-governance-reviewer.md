# agent-governance-reviewer — Chef 使用指南

Audience: Chef agents

## 概述

`agent-governance-reviewer` 是来自 `github/awesome-copilot` 的 AI agent 治理专家。直接可调用，无需 orchestrator。专注多 agent 系统的治理控制：trust boundary、审计链、权限策略、语义意图分类，GPT-4o 模型。

在 Resonova 工具链中定位：**唯一的 agent 系统治理审计角色**。当需要审计 Resonova 多 agent 公司模型本身——authority chain、chef/manager/boss 边界、agent 配置中的治理控制缺口——时使用。不是产品代码安全审计，而是 agent 系统安全。

本地文件：`C:\Users\Administrator\.copilot\agents\agent-governance-reviewer.agent.md`

## 能力范围

| 治理领域 | 说明 |
|---|---|
| 信任边界 | 验证 agent 之间不能越权（manager 不能自我审批，chef 不能绕过 boss） |
| 审计链 | 检查 tool calls 和治理决策是否有 append-only 日志 |
| 策略设计 | allowlist 优先（比 blocklist 更安全），fail-closed 模式 |
| 凭据泄露 | agent 配置文件中是否有硬编码 API key / 秘钥 |
| 访问控制装饰器 | tool 函数是否有 governance decorator 或 policy check |
| Trust Scoring | 多 agent 委派链中是否有时间衰减的信任评分 |
| 意图分类 | 用户输入是否在进入 agent 处理前进行威胁信号扫描 |

## 调用方式

```powershell
$job = Start-Job -ScriptBlock {
    copilot --agent agent-governance-reviewer `
        --allow-all `
        -C "F:\GitHub\resonova" `
        "<brief>"
}
Wait-Job $job -Timeout 120
Receive-Job $job
Remove-Job $job
```

### Brief 模板（agent 系统治理审计）

```
Governance audit of Resonova's multi-agent operating model.

Scope: [choose one or more]
- docs/agents/operating-model.md — authority chain and role separation
- AGENTS.md — agent instructions and trust rules
- docs/agents/job-specs.md — role boundaries and self-approval controls
- C:\Users\Administrator\.copilot\agents\ — agent config files for hardcoded credentials

Focus areas:
1. Trust boundary violations: can any agent approve its own work?
2. Audit trail gaps: are tool calls and governance decisions logged?
3. Hardcoded credentials in agent .agent.md files
4. Rate limit controls: are tool invocations bounded?
5. Fail-closed patterns: does the system deny on ambiguity or allow?

Required output:
- Governance gap report (what is missing vs present)
- Risk ranking by category
- Minimum recommended controls only (no over-engineering)
- Do not remove existing controls
```

### Brief 模板（agent 配置文件审查）

```
Review all agent .agent.md files in C:\Users\Administrator\.copilot\agents\ for:
1. Hardcoded API keys or secrets
2. Missing tool restrictions (are tools scoped appropriately?)
3. Missing user-invocable / mode declarations
4. Overly broad tool permissions (should use minimal tools)

Return findings with specific file names and governance recommendations.
```

## 输出格式

Markdown 治理报告：

```markdown
## Governance Audit: [scope]

### Present Controls ✅
- [what exists and works]

### Governance Gaps ⚠️
- [gap] — [file/config ref]
  - Risk: [impact]
  - Minimum control: [specific recommendation]

### Recommended Additions (minimum viable)
- [config-driven policy or decorator suggestion]
```

Chef 验收标准：
- 每个 gap 必须有具体文件/行引用
- 建议必须是最小必要控制，不是框架重写
- 不接受建议可变 audit log（必须 append-only）
- 不接受将 boss 权威降低的建议

## 核心使用场景

| 场景 | Brief 重点 |
|---|---|
| 新 agent 入职后安全检查 | 检查新 agent 配置的 tool 权限和 mode 声明 |
| 治理定期审计（季度/事件驱动）| operating-model.md + job-specs.md 的 authority chain |
| 发现 agent 自我审批事件 | trust boundary 专项审查 |
| chef 怀疑 manager 越权 | 审查 manager 的配置和调用边界 |
| 敏感 agent 配置变更后 | agent .agent.md 文件凭据扫描 |

## 与其他审计 agent 的区别

| 维度 | gem-reviewer | se-security-reviewer | agent-governance-reviewer |
|---|---|---|---|
| **审计对象** | 产品代码（波次/计划）| 产品代码（安全漏洞）| agent 系统本身 |
| **重点** | OWASP + PRD 合规 | OWASP + LLM + Zero Trust | trust boundary + audit trail |
| **场景** | 嵌入 gem 工作流 | 独立安全 brief | agent 系统治理 |
| **调用方式** | 通过 gem-orchestrator | 直接调用 | 直接调用 |
| **模型** | gem-team 默认 | GPT-5 | GPT-4o |

## 安装验证记录

- 日期：2026-06-25
- 来源：github/awesome-copilot（raw fetch）
- 文件：`C:\Users\Administrator\.copilot\agents\agent-governance-reviewer.agent.md`
- 模型偏好：GPT-4o
- 状态：✅ 已安装，待首次 trial
- 性能初始权重：0.65（试用，strict gate）
