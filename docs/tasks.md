# 出海法盾 CrossGuard — 开发任务文档 (tasks.md)

## 当前进度

- [x] 核心合规检测引擎（ComplianceChecker）
- [x] 禁用词库（绝对化用语、EU 化妆品医疗宣称）
- [x] 全局配置（市场、类别、风险等级）
- [ ] API 路由层
- [ ] 数据模型层
- [ ] 前端界面
- [ ] 测试用例
- [ ] US 市场规则
- [ ] 缺失标签检测
- [ ] 禁用成分检测

---

## Phase 1: 后端 API 层（让项目可运行）

### Task 1.1: 修复 requirements.txt

- **优先级**: P0
- **状态**: 待开发
- **内容**:
  - 移除标准库依赖（re、json、os）
  - 添加 SQLAlchemy 2.0 依赖
  - 添加 alembic 依赖（数据库迁移）

### Task 1.2: 创建 Pydantic Schemas

- **优先级**: P0
- **状态**: 待开发
- **内容**:
  - `schemas/check.py` — CheckRequest, CheckResponse, ViolationItem, BatchCheckRequest, BatchCheckResponse
  - `schemas/report.py` — ReportResponse, ReportListResponse
  - `schemas/common.py` — MarketResponse, CategoryResponse, LabelResponse, CertificationResponse
- **依赖**: 无

### Task 1.3: 创建 FastAPI 应用入口

- **优先级**: P0
- **状态**: 待开发
- **内容**:
  - `app/main.py` — 创建 FastAPI app 实例
  - 注册路由
  - 配置 CORS
  - 挂载 lifespan 事件（初始化 ComplianceChecker）
- **依赖**: Task 1.4

### Task 1.4: 创建 API 路由

- **优先级**: P0
- **状态**: 待开发
- **内容**:
  - `routers/check.py` — POST /api/v1/check, POST /api/v1/check/batch
  - `routers/market.py` — GET /api/v1/markets, GET /api/v1/markets/{market}/categories
  - `routers/label.py` — GET /api/v1/labels, GET /api/v1/certifications
- **依赖**: Task 1.2

### Task 1.5: 创建数据库模型与连接

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - `app/database.py` — SQLite 连接、会话管理
  - `models/report.py` — CheckReport ORM 模型
  - 初始化数据库脚本
- **依赖**: 无

### Task 1.6: 创建报告服务

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - `services/report_service.py` — 报告存储、查询、删除
  - `routers/report.py` — GET /api/v1/reports, GET /api/v1/reports/{id}, DELETE /api/v1/reports/{id}
- **依赖**: Task 1.5

### Task 1.7: 验证后端可运行

- **优先级**: P0
- **状态**: 待开发
- **内容**:
  - 启动 FastAPI 服务
  - 访问 /docs 验证 Swagger 文档
  - 手动测试 /api/v1/check 端点
- **依赖**: Task 1.3, Task 1.4

---

## Phase 2: 补全检测能力

### Task 2.1: 重构检测引擎为可插拔架构

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - 定义 `BaseChecker` 抽象基类
  - 将现有检测逻辑拆分为独立 Checker 类
    - `MedicalClaimChecker`
    - `AbsoluteTermChecker`
    - `FalseAdChecker`
  - `ComplianceChecker` 通过注册机制管理检测器
- **依赖**: 无

### Task 2.2: 实现缺失标签检测

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - `MissingLabelChecker` — 检测产品描述中是否缺少必需标签信息
  - 定义各市场+类别的必需标签关键词
  - 在 `ComplianceChecker` 中注册
- **依赖**: Task 2.1

### Task 2.3: 实现禁用成分检测

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - `BannedIngredientChecker` — 检测产品描述中是否含有禁用成分
  - 创建禁用成分词库文件
    - `data/banned_words/eu_cosmetics_ingredients.txt`
  - 在 `ComplianceChecker` 中注册
- **依赖**: Task 2.1

### Task 2.4: 实现 US 市场规则

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - 创建 US 市场禁用词库
    - `data/banned_words/us_cosmetics_medical.txt`（FDA 相关）
    - `data/banned_words/us_cosmetics_absolute.txt`
  - 创建 US 市场法规数据
    - `data/regulations/us_cosmetics.json`
  - 创建 US 市场替换映射
    - `data/replacements/us_cosmetics.json`
  - 在检测引擎中添加 US 市场分支逻辑
- **依赖**: Task 2.1

### Task 2.5: 丰富 EU 市场规则

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - 添加 EU 电子产品、食品、玩具、纺织品的禁用词库
  - 添加对应法规数据文件
  - 添加对应替换映射文件
  - 添加必需标签和认证数据
- **依赖**: Task 2.1

### Task 2.6: 添加违规案例库

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - 收集真实违规案例
  - 创建 `data/cases/` 下的案例文件
  - 在 API 中提供案例查询接口
- **依赖**: 无

---

## Phase 3: 前端界面

### Task 3.1: 初始化前端项目

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - 使用 Vite + React + TypeScript 初始化项目
  - 安装 Ant Design、Axios、React Router、Recharts
  - 配置代理到后端 API
  - 基础布局（Header + Content + Footer）
- **依赖**: Task 1.7

### Task 3.2: 合规检测页

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - 市场选择下拉框
  - 产品类别选择下拉框
  - 产品描述输入框（TextArea）
  - 检测按钮
  - 检测结果展示：
    - 风险评分仪表盘（Recharts Gauge）
    - 风险等级标签
    - 违规项列表（高亮违规内容）
    - 合规版本展示（diff 对比）
    - 必需标签/认证列表
    - 修改建议列表
- **依赖**: Task 3.1

### Task 3.3: 检测历史页

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - 历史记录表格（Ant Design Table）
  - 筛选条件（市场、类别、风险等级、时间范围）
  - 分页
  - 查看详情跳转
  - 删除操作
- **依赖**: Task 3.1, Task 1.6

### Task 3.4: 报告详情页

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - 完整报告展示（复用检测页的结果组件）
  - 原始描述与合规版本对比
- **依赖**: Task 3.3

### Task 3.5: 法规查询页

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - 按市场+类别查询标签要求
  - 按市场+类别查询认证要求
  - 法规原文链接
- **依赖**: Task 3.1

### Task 3.6: 首页

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - 产品介绍
  - 功能亮点
  - 快速检测入口
- **依赖**: Task 3.1

---

## Phase 4: 测试与质量

### Task 4.1: 核心引擎单元测试

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - `tests/test_compliance_checker.py`
  - 测试医疗宣称检测
  - 测试绝对化用语检测
  - 测试虚假广告检测
  - 测试风险评分计算
  - 测试合规版本生成
  - 测试边界情况（空文本、纯英文、混合语言）
- **依赖**: Task 2.1

### Task 4.2: API 集成测试

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - `tests/test_api_check.py` — 测试 /api/v1/check 端点
  - `tests/test_api_market.py` — 测试市场/类别查询端点
  - 使用 FastAPI TestClient
- **依赖**: Task 1.7

### Task 4.3: 前端组件测试

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - 检测页组件测试
  - 使用 Vitest + React Testing Library
- **依赖**: Task 3.2

---

## Phase 5: 工程化

### Task 5.1: 项目配置文件

- **优先级**: P1
- **状态**: 待开发
- **内容**:
  - `.gitignore` — Python + Node.js 通用忽略规则
  - `.env.example` — 环境变量模板
  - `pyproject.toml` — Python 项目配置（可选）

### Task 5.2: Docker 化

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - `backend/Dockerfile`
  - `frontend/Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`
- **依赖**: Task 1.7, Task 3.1

### Task 5.3: CI/CD

- **优先级**: P2
- **状态**: 待开发
- **内容**:
  - GitHub Actions 配置
  - 后端：lint + test
  - 前端：lint + test + build
- **依赖**: Task 4.1, Task 4.2

---

## 任务依赖关系

```
Phase 1 (后端 API):
  1.2 Schemas ──→ 1.4 Routers ──→ 1.3 Main ──→ 1.7 验证
  1.5 Database ──→ 1.6 Report Service

Phase 2 (检测能力):
  2.1 重构引擎 ──→ 2.2 缺失标签
                  ──→ 2.3 禁用成分
                  ──→ 2.4 US 市场
                  ──→ 2.5 EU 丰富

Phase 3 (前端):
  1.7 后端可运行 ──→ 3.1 初始化 ──→ 3.2 检测页
                                 ──→ 3.5 法规页
                                 ──→ 3.6 首页
  3.1 + 1.6 ──→ 3.3 历史页 ──→ 3.4 详情页

Phase 4 (测试):
  2.1 ──→ 4.1 引擎测试
  1.7 ──→ 4.2 API 测试
  3.2 ──→ 4.3 前端测试
```

---

## 建议开发顺序

1. **Task 1.2** → **Task 1.4** → **Task 1.3** → **Task 1.1** → **Task 1.7** — 让后端 API 跑起来
2. **Task 1.5** → **Task 1.6** — 加入数据库和报告存储
3. **Task 2.1** → **Task 2.2** → **Task 2.3** → **Task 2.4** — 补全检测能力
4. **Task 3.1** → **Task 3.2** — 前端核心页面
5. **Task 4.1** → **Task 4.2** — 测试
6. 其余任务按需推进
