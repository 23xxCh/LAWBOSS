# CEO Plan — 完整审查报告

**项目:** CrossGuard 出海法盾
**日期:** 2026-05-10
**Mode:** SELECTIVE EXPANSION (EU baseline)
**审查:** Section 1-11 综合评估

---

## Section 1: Architecture Review

### 当前系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React 19)                          │
│                    localhost:5173 (Vite Dev Server)                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ proxy to :8000
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (:8000)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Routers    │  │  Services    │  │   Models     │               │
│  │  /check      │  │ compliance_  │  │   user.py    │               │
│  │  /report     │  │ checker.py  │  │   report.py  │               │
│  │  /auth       │  │ auth_service│  │   rule.py    │               │
│  │  /market     │  │ report_     │  │   feedback  │               │
│  │  /feedback   │  │ service     │  │              │               │
│  │  /regulation │  │ export_     │  │              │               │
│  │  /erp        │  │ service     │  │              │               │
│  │  /dashboard  │  │             │  │              │               │
│  │  /billing    │  │             │  │              │               │
│  │  /admin_rules│  │             │  │              │               │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘               │
│         │                 │                                         │
│         ▼                 ▼                                         │
│  ┌──────────────────────────────────────────────┐                 │
│  │           ComplianceChecker Engine            │                 │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐  │                 │
│  │  │ Medical   │ │ Absolute  │ │ FalseAd    │  │                 │
│  │  │ Claim     │ │ Term      │ │ Checker    │  │                 │
│  │  └────────────┘ └────────────┘ └────────────┘  │                 │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐  │                 │
│  │  │ Missing   │ │ Banned    │ │ AI         │  │                 │
│  │  │ Label     │ │ Ingredient│ │ Semantic*  │  │                 │
│  │  └────────────┘ └────────────┘ └────────────┘  │                 │
│  └──────────────────────────────────────────────┘                 │
│                         │                                          │
│                         ▼                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │   SQLite DB    │  │  data/banned_  │  │    reports/     │       │
│  │ (default dev)  │  │    words/      │  │    (PDFs)      │       │
│  └────────────────┘  └────────────────┘  └────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### 架构评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件边界 | 8/10 | 清晰的路由-服务-模型分层 |
| 扩展性 | 8/10 | 可插拔 checker 架构，易于添加新检测器 |
| 可测试性 | 7/10 | 核心引擎有单元测试，但缺少集成测试 |
| 安全性 | 6/10 | JWT 密钥使用默认值，CORS 配置宽松 |

### 架构问题

**Critical:**
1. `start_dev.py` 中硬编码 DeepSeek API key — 必须移除

**Medium:**
1. CORS 配置允许 `*` methods — 生产环境需限制
2. 缺少 rate limiting 中间件

### EU Baseline 适用性评估

当前架构 **完全满足** EU MVP 需求：
- 5 个检测器覆盖 EU 市场主要违规类型
- EU 法规文件和数据词库已存在
- PDF 报告生成已实现
- 中文界面支持已有（i18n）

---

## Section 2: Error & Rescue Paths

### 错误处理矩阵

| 场景 | 当前处理 | 评估 |
|------|----------|------|
| API 调用失败 | 返回 500 + 错误信息 | ❌ 未区分可重试/不可重试 |
| 数据库连接失败 | 返回 500 | ✅ 有基本错误处理 |
| 文件加载失败 | 异常退出 | ❌ 无降级策略 |
| LLM API 失败 | 跳过 AI 检测 | ✅ AISemanticChecker 有 fallback |
| 无效 JWT | 401 Unauthorized | ✅ 正确实现 |
| 权限不足 | 403 Forbidden | ✅ RBAC 正确实现 |

### 建议
1. 添加结构化错误响应（error_code + message + recovery_hint）
2. 文件加载失败时回退到数据库或缓存
3. 添加重试机制的 HTTP 客户端封装

---

## Section 3: Security Review

| 问题 | 严重度 | 建议 |
|------|--------|------|
| JWT 密钥默认值 | **Critical** | 启动时检测并警告，生产必须使用强随机密钥 |
| CORS 太宽松 | **Medium** | 通过环境变量限制允许的 origin |
| 缺少 Rate Limiting | **Medium** | 添加 aiod限流中间件 |
| 硬编码 API key (start_dev.py) | **Critical** | 移除或使用环境变量 |

---

## Section 4: Data Flow Review

### 合规检测数据流

```
User Input (产品描述)
       │
       ▼
┌──────────────────┐
│  /api/v1/check   │  ← FastAPI Router
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ ComplianceChecker│
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Keyword │ │   AI   │
│ Stage  │ │ Stage* │
└───┬────┘ └───┬────┘
    │         │
    ▼         ▼
  Violations ← ─ ─ ─ ─ ┘
         │
         ▼
┌──────────────────┐
│  Risk Score      │
│  Calculation     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  ComplianceReport│
│  (Pydantic Model)│
└──────────────────┘
```

**评估:** 数据流清晰，两阶段检测设计合理。

---

## Section 5: Code Quality Review

### 正面评价
- 清晰的目录结构（routers/services/models/schemas）
- 类型提示完整（Pydantic + dataclass）
- 词库与检测逻辑分离
- 英文使用 `\b` 词边界匹配，避免误报

### 问题
1. **重复代码:** MedicalClaimChecker 和 BannedIngredientChecker 有相似的 `_load_data` 模式
2. **魔法数字:** score=25, score=30 等硬编码
3. **缺少类型别名:** 没有使用 type alias 简化复杂类型

---

## Section 6: Test Coverage Review

| 组件 | 测试覆盖 | 说明 |
|------|----------|------|
| compliance_checker.py | 部分 | 有 test_compliance_checker.py |
| API endpoints | 部分 | 有 test_api.py |
| auth/feedback | 部分 | 有 test_auth_feedback.py |
| billing | 差 | 有 test_billing.py 但可能不完整 |
| 前端组件 | 无 | 缺少前端测试 |

**建议:** EU MVP 前需要补充：
1. EU 医疗宣称检测准确性测试
2. EU 禁用成分检测测试
3. EU 标签缺失检测测试

---

## Section 7: Performance Review

| 指标 | 当前值 | 评估 |
|------|--------|------|
| API 响应时间 | 未知 | 需要 benchmark |
| 词库加载 | 懒加载 | ✅ 优化启动时间 |
| 数据库连接池 | 10 connections | ✅ 合理 |
| 前端 bundle size | 未知 | 需要优化 |

---

## Section 8: Observability Review

| 方面 | 现状 | 建议 |
|------|------|------|
| 日志 | basic logging | 添加结构化日志 |
| Health check | 有 `/` 根路径 | ✅ 有基本健康检查 |
| 指标 | 无 | 添加 /metrics 端点 |
| 分布式追踪 | 无 | 考虑 Jaeger/Zipkin |

---

## Section 9: Deployment Review

当前部署方式：
- 开发: `python start_dev.py` (uvicorn)
- 生产: Docker / 云服务器

**建议:**
1. 添加 health check endpoint
2. 配置 graceful shutdown
3. 添加 Dockerfile

---

## Section 10: Long-Term Trajectory Review

### 技术债务

| 类型 | 严重度 | 描述 |
|------|--------|------|
| 代码债务 | Medium | 重复的 _load_data 实现 |
| 测试债务 | High | 前端无测试，API 测试覆盖不足 |
| 文档债务 | Low | 缺少 API 文档 |
| 架构债务 | Low | 服务层可以进一步拆分 |

### 可逆性评估

| 决策 | 可逆性 | 说明 |
|------|--------|------|
| SQLite → PostgreSQL | 高 | DATABASE_URL 环境变量切换 |
| 词库文件 → DB | 高 | 已有迁移脚本 |
| AI 检测 optional | 高 | 环境变量控制 |

---

## Section 11: Design & UX Review

**Skip — No UI scope changes in EU MVP baseline**

### 设计考量

当前 UI 已实现：
- Dashboard (首页)
- 合规检测页 (CheckPage)
- 报告历史页 (ReportsPage)
- 报告详情页 (ReportDetailPage)
- 法规查询页 (RulesPage)
- 登录/注册页

**EU MVP 不涉及 UI 变更，Design Review 在后续阶段按需进行。**

---

## CEO Plan 最终评估

### 关键优势
1. **架构清晰:** 可插拔 checker 模式，易于扩展
2. **词库管理:** 数据库 + 文件双模式，支持动态更新
3. **中文支持:** i18n 已配置，中文界面友好
4. **MVP 聚焦:** EU baseline 小而美，快速验证

### 关键风险
1. **Critical:** JWT 密钥和 start_dev.py 硬编码 API key
2. **High:** 无真实用户验证，需求可能不准确
3. **Medium:** 测试覆盖不足

### 改进建议

**必须修复（启动前）:**
1. 移除 start_dev.py 中的硬编码 API key
2. 添加 JWT 密钥默认检测警告

**应该改进（MVP 前）:**
1. 补充 EU 市场测试套件
2. 添加 rate limiting 中间件

**可以优化（后续）:**
1. 添加结构化错误响应
2. 完善日志和监控
3. 添加 API 文档

---

## 决策总结

| 决策 | 选择 | 原因 |
|------|------|------|
| 市场聚焦 | EU baseline | 法规清晰，词库完整 |
| AI 检测 | 后置 | 核心检测还不够准 |
| 扩展策略 | Cherry-pick | 用户按需选择 |
| 优先级 | P0 功能优先 | 核心场景先打磨 |

---

*Generated by /plan-ceo-review Section 1-11 review*
*Status: APPROVED WITH MINOR FIXES REQUIRED*