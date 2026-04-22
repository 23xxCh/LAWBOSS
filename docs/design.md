# 出海法盾 CrossGuard — 技术设计文档 (design.md)

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│            (React + TypeScript)                  │
├─────────────────────────────────────────────────┤
│                   Nginx                          │
│            (反向代理 + 静态资源)                   │
├─────────────────────────────────────────────────┤
│                FastAPI Backend                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ Routers  │ │ Services │ │   Models     │    │
│  │ (API层)  │ │ (业务层) │ │  (数据模型)  │    │
│  └──────────┘ └──────────┘ └──────────────┘    │
├─────────────────────────────────────────────────┤
│              Data Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ SQLite   │ │ 文件系统  │ │  缓存层     │    │
│  │(检测历史)│ │(禁用词库)│ │  (内存)     │    │
│  └──────────┘ └──────────┘ └──────────────┘    │
└─────────────────────────────────────────────────┘
```

### 1.2 技术选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| **后端框架** | FastAPI | 高性能异步、自动 OpenAPI 文档、Pydantic 数据验证 |
| **数据验证** | Pydantic v2 | 与 FastAPI 深度集成，类型安全 |
| **数据库** | SQLite (SQLAlchemy) | 轻境电商工具轻量级场景，无需重型数据库 |
| **ORM** | SQLAlchemy 2.0 | Python 生态最成熟的 ORM，异步支持 |
| **前端框架** | React 18 + TypeScript | 组件化、类型安全、生态丰富 |
| **UI 组件库** | Ant Design 5 | 企业级 UI，中文友好，开箱即用 |
| **构建工具** | Vite | 极速 HMR，React 项目标配 |
| **ASGI 服务器** | Uvicorn | FastAPI 官方推荐 |
| **模板引擎** | Jinja2 | 报告导出（HTML/PDF） |

---

## 2. 后端设计

### 2.1 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── config.py                  # 全局配置
│   ├── database.py                # 数据库连接与会话
│   ├── models/                    # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── report.py              # 检测报告模型
│   │   └── user.py                # 用户模型（后续）
│   ├── schemas/                   # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   ├── check.py               # 检测请求/响应
│   │   ├── report.py              # 报告响应
│   │   └── common.py              # 通用模型
│   ├── routers/                   # API 路由
│   │   ├── __init__.py
│   │   ├── check.py               # 合规检测端点
│   │   ├── report.py              # 报告查询端点
│   │   ├── market.py              # 市场/类别查询端点
│   │   └── admin.py               # 管理端点（词库管理）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── compliance_checker.py  # 核心合规检测引擎
│   │   ├── report_service.py      # 报告存储与查询
│   │   └── word_loader.py         # 禁用词库加载与缓存
│   └── utils/
│       ├── __init__.py
│       └── text.py                # 文本处理工具
├── data/
│   ├── banned_words/              # 禁用词库文件
│   ├── cases/                     # 违规案例
│   └── regulations/              # 法规数据
├── alembic/                       # 数据库迁移
├── requirements.txt
└── tests/
```

### 2.2 数据模型设计

#### 2.2.1 Pydantic Schemas

```python
# schemas/check.py

class CheckRequest(BaseModel):
    """合规检测请求"""
    description: str = Field(..., min_length=1, max_length=10000, description="产品描述")
    category: str = Field(..., description="产品类别")
    market: str = Field(default="EU", description="目标市场")

class ViolationItem(BaseModel):
    """违规项"""
    type: str                    # 违规类型标识
    type_label: str              # 违规类型中文名
    content: str                 # 违规内容
    regulation: str              # 法规依据
    regulation_detail: str       # 法规详情
    severity: str                # 严重度 high/medium/low
    severity_label: str          # 严重度中文名
    suggestion: str              # 修改建议
    score: int                   # 扣分

class CheckResponse(BaseModel):
    """合规检测响应"""
    risk_score: int              # 风险评分 0-100
    risk_level: str              # 风险等级
    risk_description: str        # 风险描述
    market: str                  # 目标市场
    category: str                # 产品类别
    violations: List[ViolationItem]  # 违规列表
    compliant_version: str       # 合规版本
    required_labels: List[str]   # 必需标签
    required_certifications: List[str]  # 必需认证
    suggestions: List[str]       # 修改建议汇总

class BatchCheckRequest(BaseModel):
    """批量检测请求"""
    items: List[CheckRequest] = Field(..., max_length=100)

class BatchCheckResponse(BaseModel):
    """批量检测响应"""
    results: List[CheckResponse]
    total: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
```

#### 2.2.2 SQLAlchemy ORM Models

```python
# models/report.py

class CheckReport(Base):
    """检测报告持久化模型"""
    __tablename__ = "check_reports"

    id: Mapped[str]              # UUID
    description: Mapped[str]     # 原始描述
    category: Mapped[str]        # 产品类别
    market: Mapped[str]          # 目标市场
    risk_score: Mapped[int]      # 风险评分
    risk_level: Mapped[str]      # 风险等级
    violations_json: Mapped[str] # 违规项 JSON
    compliant_version: Mapped[str]  # 合规版本
    created_at: Mapped[datetime] # 创建时间
```

### 2.3 API 路由设计

#### 2.3.1 合规检测

```
POST /api/v1/check
```
- 请求体：`CheckRequest`
- 响应体：`CheckResponse`
- 说明：提交单条产品描述进行合规检测

```
POST /api/v1/check/batch
```
- 请求体：`BatchCheckRequest`
- 响应体：`BatchCheckResponse`
- 说明：批量提交检测，最多 100 条

#### 2.3.2 报告查询

```
GET /api/v1/reports
```
- 查询参数：`page`, `page_size`, `market`, `category`, `risk_level`, `start_date`, `end_date`
- 说明：分页查询检测历史

```
GET /api/v1/reports/{report_id}
```
- 说明：获取单条检测报告详情

```
DELETE /api/v1/reports/{report_id}
```
- 说明：删除检测报告

#### 2.3.3 市场与类别

```
GET /api/v1/markets
```
- 说明：获取支持的市场列表

```
GET /api/v1/markets/{market}/categories
```
- 说明：获取指定市场支持的产品类别

#### 2.3.4 标签与认证

```
GET /api/v1/labels?market=EU&category=化妆品
```
- 说明：查询必需标签

```
GET /api/v1/certifications?market=EU&category=化妆品
```
- 说明：查询必需认证

#### 2.3.5 管理接口（后续版本）

```
GET /api/v1/admin/words?type=medical&market=EU
POST /api/v1/admin/words
PUT /api/v1/admin/words/{word_id}
DELETE /api/v1/admin/words/{word_id}
```

### 2.4 合规检测引擎设计

#### 2.4.1 检测流程

```
输入: description, category, market
  │
  ├─→ 1. 文本预处理（分词、大小写归一化）
  │
  ├─→ 2. 加载规则（禁用词库 + 正则模式 + 类别规则）
  │
  ├─→ 3. 并行执行检测器
  │     ├─→ MedicalClaimChecker    → 医疗宣称检测
  │     ├─→ AbsoluteTermChecker    → 绝对化用语检测
  │     ├─→ FalseAdChecker         → 虚假广告检测
  │     ├─→ MissingLabelChecker    → 缺失标签检测
  │     └─→ BannedIngredientChecker→ 禁用成分检测
  │
  ├─→ 4. 汇总违规项
  │
  ├─→ 5. 计算风险评分
  │
  ├─→ 6. 生成合规版本
  │
  ├─→ 7. 查询必需标签/认证
  │
  └─→ 8. 生成修改建议
        │
        └─→ 输出: ComplianceReport
```

#### 2.4.2 检测器接口

```python
class BaseChecker(ABC):
    """检测器基类"""

    @abstractmethod
    def check(self, description: str, category: str, market: str) -> List[Violation]:
        """执行检测，返回违规列表"""
        pass

    @abstractmethod
    def get_replacement(self, content: str) -> Optional[str]:
        """获取合规替换词"""
        pass
```

各检测器继承 `BaseChecker`，实现 `check` 和 `get_replacement` 方法。检测引擎通过注册机制管理检测器，支持动态添加新检测器。

#### 2.4.3 禁用词库加载策略

- 启动时加载所有词库到内存（词库总量小，< 1MB）
- 按市场+类别+违规类型建立索引
- 支持热更新：通过管理接口修改词库后，触发重新加载
- 词库文件格式：每行一个词，`#` 开头为注释，空行忽略

### 2.5 数据库设计

#### 表结构

**check_reports** — 检测报告

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(36) PK | UUID |
| description | TEXT | 原始产品描述 |
| category | VARCHAR(50) | 产品类别 |
| market | VARCHAR(10) | 目标市场 |
| risk_score | INTEGER | 风险评分 |
| risk_level | VARCHAR(10) | 风险等级 |
| violations_json | TEXT | 违规项 JSON |
| compliant_version | TEXT | 合规版本 |
| required_labels_json | TEXT | 必需标签 JSON |
| required_certifications_json | TEXT | 必需认证 JSON |
| created_at | DATETIME | 创建时间 |

---

## 3. 前端设计

### 3.1 技术选型

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18 | UI 框架 |
| TypeScript | 5 | 类型安全 |
| Ant Design | 5 | UI 组件库 |
| Vite | 5 | 构建工具 |
| Axios | 1 | HTTP 客户端 |
| React Router | 6 | 路由 |
| Recharts | 2 | 图表可视化 |

### 3.2 页面结构

```
/                    → 首页（产品介绍 + 快速检测入口）
/check               → 合规检测页（核心页面）
/reports             → 检测历史页
/reports/:id         → 报告详情页
/rules               → 法规查询页
/rules/labels        → 标签要求查询
/rules/certifications→ 认证要求查询
```

### 3.3 核心页面设计

#### 3.3.1 合规检测页 `/check`

```
┌──────────────────────────────────────────────────┐
│  出海法盾 CrossGuard                              │
├──────────────────────────────────────────────────┤
│                                                  │
│  目标市场: [EU ▼]    产品类别: [化妆品 ▼]         │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │                                            │  │
│  │  请输入产品描述...                          │  │
│  │                                            │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│              [ 开始检测 ]                         │
│                                                  │
├──────────────────────────────────────────────────┤
│  检测结果                                        │
│                                                  │
│  ┌─────────┐  风险等级: 高风险                   │
│  │  75/100 │  建议立即整改                       │
│  └─────────┘                                    │
│                                                  │
│  违规项 (3):                                     │
│  ┌────────────────────────────────────────────┐  │
│  │ 🔴 医疗宣称: "治疗"                         │  │
│  │    法规: EC No 1223/2009 第20条             │  │
│  │    建议: 删除"治疗"，改为"舒缓"              │  │
│  ├────────────────────────────────────────────┤  │
│  │ 🟡 绝对化用语: "最好"                       │  │
│  │    法规: 欧盟不公平商业行为指令              │  │
│  │    建议: 将"最好"改为"优质"                 │  │
│  ├────────────────────────────────────────────┤  │
│  │ 🟡 虚假广告: "7天见效"                     │  │
│  │    法规: EC No 655/2013                    │  │
│  │    建议: 改为"持续使用，效果更佳"           │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  合规版本:                                       │
│  ┌────────────────────────────────────────────┐  │
│  │ 这款面霜能舒缓痘痘，持续使用效果更佳，      │  │
│  │ 是市面上优质的产品                          │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  必需标签: 产品名称 | 成分表 | 使用期限 | ...    │
│  必需认证: CPNP备案 | CPSR报告 | PIF            │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### 3.3.2 检测历史页 `/reports`

- 表格展示历史检测记录
- 列：时间、市场、类别、风险评分、风险等级、操作
- 筛选：按市场、类别、风险等级、时间范围
- 操作：查看详情、删除、导出

#### 3.3.3 法规查询页 `/rules`

- 按市场+类别查询标签要求和认证要求
- 卡片式展示，法规原文链接

---

## 4. 数据文件设计

### 4.1 禁用词库文件命名规范

```
banned_words/
├── {market}_{category}_{type}.txt
├── eu_cosmetics_medical.txt      # EU 化妆品医疗宣称
├── eu_cosmetics_absolute.txt     # EU 化妆品绝对化用语（复用通用）
├── us_cosmetics_medical.txt      # US 化妆品医疗宣称
├── us_cosmetics_absolute.txt     # US 化妆品绝对化用语
├── absolute_terms.txt            # 通用绝对化用语
└── ...
```

### 4.2 法规数据文件

```json
// regulations/eu_cosmetics.json
{
  "market": "EU",
  "category": "化妆品",
  "regulations": [
    {
      "id": "ec_1223_2009",
      "name": "欧盟化妆品法规 (EC) No 1223/2009",
      "article": "第20条",
      "description": "化妆品不得宣称具有治疗、预防疾病的功能",
      "url": "https://eur-lex.europa.eu/..."
    }
  ],
  "required_labels": [...],
  "required_certifications": [...]
}
```

### 4.3 替换映射文件

```json
// replacements/eu_cosmetics.json
{
  "market": "EU",
  "category": "化妆品",
  "replacements": {
    "治疗": "舒缓",
    "治愈": "改善",
    "最好": "优质",
    "7天见效": "持续使用，效果更佳"
  }
}
```

---

## 5. 部署设计

### 5.1 开发环境

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev  # 默认端口 5173
```

### 5.2 生产部署

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./data:/app/data"]

  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [backend]
```

Nginx 反向代理前端请求到后端 API。

---

## 6. 扩展性设计

### 6.1 新增市场

1. 在 `config.py` 的 `SUPPORTED_CATEGORIES` 中添加市场及类别
2. 在 `data/banned_words/` 下添加对应禁用词库文件
3. 在 `data/regulations/` 下添加法规数据文件
4. 在 `data/replacements/` 下添加替换映射文件
5. 在 `ComplianceChecker` 中注册新市场的检测规则

### 6.2 新增检测器

1. 继承 `BaseChecker` 实现 `check` 和 `get_replacement` 方法
2. 在 `ComplianceChecker` 中注册新检测器
3. 在 `ViolationType` 枚举中添加新类型

### 6.3 后续演进方向

- **AI 语义检测** — 接入 LLM 进行语义级违规检测，弥补关键词匹配的不足
- **图片检测** — OCR 提取图片文字后进行合规检测
- **实时监控** — 对已上架 Listing 进行定期合规巡检
- **多平台对接** — 对接 Amazon/eBay API 自动拉取 Listing 检测
- **用户系统** — 多用户、团队协作、权限管理
