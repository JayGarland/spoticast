# se-security-reviewer — Chef 使用指南

Audience: Chef agents

## 概述

`se-security-reviewer` 是来自 `github/awesome-copilot` 的独立安全审计 agent。直接可调用，无需 orchestrator 上下文。专注 OWASP Top 10、OWASP LLM Top 10、Zero Trust，GPT-5 模型偏好。

在 Resonova 工具链中定位：**独立安全 brief**。当需要对 Flask server、Spotify OAuth、JWT 处理、用户数据隔离、Gemini 提示管道做深度安全审计时使用，不需要嵌入 gem 工作流。

本地文件：`C:\Users\Administrator\.copilot\agents\se-security-reviewer.agent.md`

## 能力范围

| 审计类型 | 说明 |
|---|---|
| OWASP A01 | Broken Access Control — auth decorator, 用户作用域数据访问 |
| OWASP A02 | Cryptographic Failures — 哈希算法、token 存储、秘钥暴露 |
| OWASP A03 | Injection — SQL、命令、提示注入 |
| OWASP LLM01 | Prompt Injection — 用户输入未消毒直接拼入 prompt |
| OWASP LLM06 | Information Disclosure — 敏感数据泄漏到 LLM 上下文 |
| Zero Trust | 内部 API 的互相认证，不只在边界鉴权 |
| 可靠性 | 外部调用超时、重试、证书验证 |
| 报告输出 | 保存到 `docs/code-review/[date]-[component]-review.md` |

## 调用方式

```powershell
$job = Start-Job -ScriptBlock {
    copilot --agent se-security-reviewer `
        --allow-all `
        -C "F:\GitHub\resonova" `
        "<brief>"
}
Wait-Job $job -Timeout 120
Receive-Job $job
Remove-Job $job
```

### Brief 模板

```
Security audit of [component/file].

Code type: Web API + LLM integration
Risk level: High (auth + AI model + user data)
Focus: OWASP Top 10 (A01, A02, A03) + OWASP LLM Top 10 (LLM01, LLM06)

Files to review:
- [e.g. resonova/server.py]
- [e.g. resonova/api/gemini.py]

Required output:
- Save report to docs/code-review/[date]-[component]-review.md
- Priority 1 (must fix) with vulnerable + secure code example
- Priority 2 (recommended)
- "Ready for Production: Yes/No" verdict

Do not implement fixes unless explicitly assigned.
```

### Resonova 特定重点 brief

```
Audit resonova/server.py and resonova/api/spotify.py for:
1. A01: /auth/callback and allowlist enforcement — is user ID gating correct?
2. A02: session cookie signing and JWT token handling
3. A03: any f-string interpolation into SQL or shell commands
4. LLM01: Gemini prompt construction in resonova/api/gemini.py — is user-supplied
   data (profile, feedback) safely bounded before entering the prompt?
5. Zero Trust: internal service calls between server.py endpoints

Save report to docs/code-review/[date]-resonova-auth-security-review.md
```

## 输出格式

Markdown 报告，结构：

```markdown
# Code Review: [Component]
**Ready for Production**: Yes/No
**Critical Issues**: [count]

## Priority 1 (Must Fix) ⛔
- [issue] — [file:line]
  - Vulnerable: [code snippet]
  - Secure: [fixed snippet]

## Priority 2 (Recommended)
- [issue] — [file:line]
```

Chef 验收标准：
- 每个 Priority 1 发现必须有文件和行号
- 必须区分 OWASP Top 10 和 LLM Top 10 问题
- "Ready for Production" 判断必须有明确依据
- 不接受无证据的 "no issues found"

## 与 gem-reviewer 的区别

| 场景 | 推荐 |
|---|---|
| 嵌入 gem 工作流的安全检查 | gem-reviewer（via gem-orchestrator）|
| 独立安全 brief，重点 LLM + Zero Trust | se-security-reviewer |
| 需要 JSON 结构化输出 | gem-reviewer |
| 需要 Markdown 报告保存到 docs/ | se-security-reviewer |
| 移动端安全 8 向量 | gem-reviewer |
| Flask server + Spotify OAuth + JWT 深审 | se-security-reviewer |

## 安装验证记录

- 日期：2026-06-25
- 来源：github/awesome-copilot（raw fetch）
- 文件：`C:\Users\Administrator\.copilot\agents\se-security-reviewer.agent.md`
- 模型偏好：GPT-5
- 状态：✅ 已安装，待首次 trial
- 性能初始权重：0.65（试用，strict gate）
