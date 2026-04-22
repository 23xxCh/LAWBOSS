# 出海法盾 CrossGuard

> 跨境电商智能合规审查平台

## 项目简介

出海法盾（CrossGuard）是一个面向跨境电商卖家的智能合规审查工具，帮助出海电商检测产品描述是否符合目标市场的法规要求。

平台采用**两级检测流水线**架构：关键词快速初筛 + AI 语义深度复筛，能够自动识别产品描述中的**医疗宣称**、**绝对化用语**、**虚假广告**、**缺失标签**、**禁用成分**、**隐含违规**等 6 类违规内容，生成合规报告，并提供修改建议和合规版本。

## 核心功能

- **两级检测流水线** — 关键词初筛（确定性、高召回）+ AI 语义复筛（深度理解、低误报）
- **6 类违规检测** — 医疗宣称、绝对化用语、虚假广告、缺失标签、禁用成分、隐含违规(AI)
- **图片合规检测** — OCR 识别图片文字 + 自动合规检测，支持 Amazon Listing 主图
- **词边界匹配** — 英文使用 `\b` 词边界匹配，避免子串误报（如 "painting" 不会误报 "pain"）
- **风险评分** — 0-100 分量化风险，高/中/低三级预警
- **合规版本生成** — 上下文感知替换，只替换被标记为违规的词汇
- **修改建议** — 针对每条违规给出具体修改建议和法规依据
- **批量检测** — 支持一次提交最多 100 条产品描述批量检测
- **报告导出** — 支持导出 PDF 格式合规检测报告
- **用户认证** — JWT + RBAC 角色权限控制（admin/user/viewer）
- **必需标签/认证查询** — 查询目标市场对产品类别的标签和认证要求
- **可插拔检测架构** — BaseChecker 抽象基类，支持动态添加新检测器

## 支持的市场与类别

| 市场 | 代码 | 产品类别 |
|------|------|----------|
| 欧盟 | EU | 化妆品、电子产品、食品、玩具、纺织品 |
| 美国 | US | 化妆品、电子产品、食品、膳食补充剂 |
| 新加坡 | SEA_SG | 化妆品、电子产品、食品、膳食补充剂 |
| 泰国 | SEA_TH | 化妆品、电子产品、食品、膳食补充剂 |
| 马来西亚 | SEA_MY | 化妆品、电子产品、食品、膳食补充剂 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Pydantic v2 |
| ORM | SQLAlchemy 2.0 + PostgreSQL / SQLite |
| AI 检测 | LLM API (GPT-4o / DeepSeek / Ollama) |
| OCR | Tesseract + Pillow |
| 认证 | JWT (python-jose) + bcrypt (passlib) |
| 报告导出 | Jinja2 + WeasyPrint (PDF) |
| 前端 | React 19 + TypeScript + Ant Design 6 |
| 构建工具 | Vite 8 |
| 容器化 | Docker + docker-compose + PostgreSQL |

## 项目结构

```
crossguard/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 应用入口
│   │   ├── config.py               # 全局配置
│   │   ├── database.py             # 数据库连接（PostgreSQL/SQLite）
│   │   ├── models/                 # ORM 模型
│   │   │   ├── report.py           # 检测报告模型
│   │   │   └── user.py             # 用户模型
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   │   ├── check.py            # 检测请求/响应
│   │   │   ├── auth.py             # 认证请求/响应
│   │   │   ├── common.py           # 通用响应模型
│   │   │   └── report.py           # 报告响应模型
│   │   ├── routers/                # API 路由
│   │   │   ├── check.py            # 合规检测端点
│   │   │   ├── image.py            # 图片检测端点
│   │   │   ├── auth.py             # 认证端点
│   │   │   ├── market.py           # 市场/类别/标签/认证端点
│   │   │   └── report.py           # 报告查询/导出端点
│   │   ├── services/
│   │   │   ├── compliance_checker.py  # 核心检测引擎（可插拔架构）
│   │   │   ├── ai_semantic_checker.py # AI 语义检测器（LLM）
│   │   │   ├── image_checker.py       # 图片 OCR 检测
│   │   │   ├── auth_service.py        # 认证服务（JWT+bcrypt）
│   │   │   ├── export_service.py      # 报告导出（PDF）
│   │   │   └── report_service.py      # 报告存储服务
│   │   └── utils/
│   ├── data/
│   │   ├── banned_words/           # 禁用词库（EU/US/SEA）
│   │   ├── cases/                  # 违规案例
│   │   ├── regulations/            # 法规数据
│   │   └── replacements/           # 替换映射
│   ├── templates/                  # PDF 报告模板
│   ├── tests/                      # 测试用例
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                    # API 客户端 + 类型定义
│   │   ├── components/             # 布局组件
│   │   └── pages/                  # 页面组件
│   │       ├── CheckPage.tsx       # 合规检测（文本+图片）
│   │       ├── BatchCheckPage.tsx  # 批量检测
│   │       ├── ReportsPage.tsx     # 检测历史
│   │       ├── ReportDetailPage.tsx# 报告详情
│   │       └── RulesPage.tsx       # 法规查询
│   └── Dockerfile
├── .github/workflows/ci.yml        # CI/CD 配置
├── docs/                           # 项目文档
├── docker-compose.yml              # 一键部署（含 PostgreSQL）
└── .gitignore
```

## 快速开始

### 方式一：本地开发

```bash
# 后端
cd crossguard/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd crossguard/frontend
npm install
npm run dev
```

### 方式二：Docker 一键部署

```bash
cd crossguard
docker-compose up --build
```

- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 前端界面：http://localhost:80 (Docker) 或 http://localhost:5173 (开发)

### 环境变量配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 | `sqlite:///./db/crossguard.db` |
| `LLM_API_KEY` | LLM API 密钥 | 空（不启用 AI 检测） |
| `LLM_API_BASE` | LLM API 地址 | `https://api.openai.com/v1` |
| `LLM_MODEL` | LLM 模型 | `gpt-4o-mini` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | 开发默认值 |

### 运行测试

```bash
cd crossguard/backend
pip install pytest httpx
python -m pytest tests/ -v
```

## 违规检测规则

| 违规类型 | 严重度 | 评分 | 说明 |
|----------|--------|------|------|
| 医疗宣称 | 高 | 25分/项 | 化妆品/食品声称治疗、预防疾病功能 |
| 绝对化用语 | 中 | 15分/项 | 使用"最好"、"100%"等绝对化表述 |
| 虚假广告 | 中 | 15分/项 | 功效宣称无科学依据，如"7天见效" |
| 缺失标签 | 中 | 10分/项 | 缺少目标市场强制要求的标签信息 |
| 禁用成分 | 高 | 30分/项 | 含有目标市场禁用的成分 |
| 隐含违规(AI) | 中-高 | 15-25分/项 | AI 语义检测发现的隐含违规 |

### 风险评分机制

- 基础分 = 各违规项评分之和
- 存在医疗宣称违规：额外 +20 分
- 存在禁用成分违规：额外 +15 分
- 违规项 >= 3：额外 +10 分
- 上限 100 分

| 风险等级 | 分数范围 | 说明 |
|----------|----------|------|
| 高风险 | >= 70 | 建议立即整改，否则可能面临下架/罚款 |
| 中风险 | >= 40 | 存在违规可能，建议修改 |
| 低风险 | < 40 | 基本合规，可进一步优化 |

## 默认账户

首次启动自动创建管理员账户：
- 用户名：`admin`
- 密码：`crossguard2024`

**请在生产环境中立即修改默认密码！**

## License

Private - All Rights Reserved
