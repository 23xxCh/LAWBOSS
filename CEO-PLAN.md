# CrossGuard 出海法盾 — CEO Plan

**状态:** APPROVED
**生成时间:** 2026-05-10
**Mode:** SELECTIVE EXPANSION (EU baseline + cherry-pick expansions)
**Skill:** /plan-ceo-review
**轮次:** Round 1, Phase 01

---

## 背景

CrossGuard 是一个跨境电商智能合规审查平台，帮助电商卖家检测产品描述是否符合目标市场法规要求。

**当前阶段:** Pre-product (MVP 开发前)

**关键约束:**
- 预算有限，需要快速验证
- 没有真实用户观察（纯推测需求）
- 市场切入太宽（EU/US/SEA 全覆盖但没做深）

---

## 市场策略: SELECTIVE EXPANSION

**基础: 聚焦 EU 市场（最小可行）**

### 方案选择: 方案 A (推荐)
- **市场:** EU (英语产品描述的中国跨境卖家)
- **客户:** Amazon EU 化妆品卖家
- **切入点:** 中文界面 + EU 法规检测
- **差异化:** 专门服务中国卖家，界面和 support 都中文

### 为什么选 EU
1. EU 法规最清晰，词库最全
2. 中国卖家有明确需求（Amazon EU 卖家）
3. 验证方法简单：找 10 个 Amazon EU 化妆品卖家访谈

---

## MVP 范围 (EU Baseline)

### P0 必须做
1. **EU 市场关键词检测准确性** — 词库维护
2. **合规报告生成（PDF）** — 用户需要提交给平台
3. **基础前端界面** — 检测页、报告历史、法规查询

### P1 应该做
1. US 市场词库补充（扩展选项）
2. 批量检测（10+ 条/次）
3. 报告历史（超过 100 条时需要）

### P2 可以不做
1. AI 语义检测 — 核心检测还不够准，先不做
2. 图片 OCR — 复杂，先不做
3. ERP 集成 — 用户没提需求，先不做

---

## 竞品对比与超越策略

| 竞品 | 定位 | CrossGuard 如何超越 |
|------|------|---------------------|
| Helium 10 | Amazon 运营工具集 | 专注合规检测，更准 |
| Legaloo | EU 企业合规 | SaaS 化，自助服务 |
| SellerArmor | 账户保护 | 主动检测，不只是保护 |

**核心差异化:**
1. 中文界面 + 中文 support
2. SaaS 自助式，中小卖家友好
3. 比律所更便宜，比通用工具更准

---

## 架构决策

### 当前架构 (EU MVP 适用)
```
Frontend (React 19) ←→ FastAPI Backend (:8000)
                         ↓
                   ComplianceChecker
                         ↓
              EU data files (banned_words)
```

### 关键设计决策

| 决策 | 原因 |
|------|------|
| 先不做 AI 检测 | 核心检测还不够准 |
| 先做 EU 市场 | 法规最清晰，词库最全 |
| 聚焦 Amazon 卖家 | 有明确场景和付费意愿 |
| 词边界匹配 (\b) | 避免子串误报 |

---

## 安全决策

### Critical (立即修复)
- **移除 start_dev.py 中的硬编码 API key** — 使用环境变量

### Medium (MVP 前修复)
- 添加 rate limiting 中间件
- 验证 CORS 配置

---

## 测试策略

### MVP 必须覆盖
1. EU 医疗宣称检测准确性
2. EU 禁用成分检测
3. EU 标签缺失检测
4. PDF 报告生成
5. Auth 流程 (login, JWT)

### 覆盖缺口
- 未知是否有完整 EU 测试套件
- 建议: Phase 09 前添加 targeted EU test suite

---

## 验证计划

1. **用户访谈:** 找 10 个 Amazon EU 化妆品卖家
2. **MVP 功能测试:** 确保 EU 检测准确率 >90%
3. **定价验证:** 问用户愿意付多少钱

---

## 扩展选项 (Cherry-pick 待选)

以下功能可后续加入，按优先级:

1. **US 市场支持** — 词库补充，法规文件
2. **批量检测** — 一次检测 10+ 条产品
3. **AI 语义检测** — 核心检测准确后再说
4. **报告历史** — 数据库存储 + 分页

---

## 下一步行动

**Phase 02: Adversarial Review #1**
- 使用 /review 对 CEO Plan 进行挑战
- 找出计划的漏洞和风险

**Phase 03: Engineering Plan**
- 使用 /plan-eng-review 制定架构方案

---

## 设计决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-05-10 | 先不做 AI 检测 | 核心检测还不够准 |
| 2026-05-10 | 先做 EU 市场 | 法规最清晰，词库最全 |
| 2026-05-10 | 聚焦 Amazon 卖家 | 有明确场景和付费意愿 |

---

*本文档由 /plan-ceo-review 生成*
*相关 PRD: crossguard/PRD.md*
*Supersedes: crossguard/docs/designs/crossguard-design-2026-05-10.md (整合)*