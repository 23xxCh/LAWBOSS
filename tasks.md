# 出海法盾 CrossGuard — 开发任务清单 (tasks.md)

## 项目信息
- **Round:** 1
- **阶段:** Phase 01 / 13
- **进度:** 0/13

## 迭代历史
- Round 1: 进行中

---

## 待完成任务

### Phase 1: 后端 API 层

- [ ] Task 1.1: 修复 requirements.txt
- [ ] Task 1.2: 创建 Pydantic Schemas
- [ ] Task 1.3: 创建 FastAPI 应用入口
- [ ] Task 1.4: 创建 API 路由
- [ ] Task 1.5: 创建数据库模型与连接
- [ ] Task 1.6: 创建报告服务
- [ ] Task 1.7: 验证后端可运行

### Phase 2: 补全检测能力

- [ ] Task 2.1: 重构检测引擎为可插拔架构
- [ ] Task 2.2: 实现缺失标签检测
- [ ] Task 2.3: 实现禁用成分检测
- [ ] Task 2.4: 实现 US 市场规则
- [ ] Task 2.5: 丰富 EU 市场规则
- [ ] Task 2.6: 添加违规案例库

### Phase 3: 前端界面

- [ ] Task 3.1: 初始化前端项目
- [ ] Task 3.2: 合规检测页
- [ ] Task 3.3: 检测历史页
- [ ] Task 3.4: 报告详情页
- [ ] Task 3.5: 法规查询页
- [ ] Task 3.6: 首页

### Phase 4: 测试与质量

- [ ] Task 4.1: 核心引擎单元测试
- [ ] Task 4.2: API 集成测试
- [ ] Task 4.3: 前端组件测试

### Phase 5: 工程化

- [ ] Task 5.1: 项目配置文件
- [ ] Task 5.2: Docker 化
- [ ] Task 5.3: CI/CD

---

## 已完成任务

### Phase 1: 后端 API 层

- [x] Task 1.2: Pydantic Schemas 已存在（schemas/ 目录下）
- [x] Task 1.3: FastAPI 应用入口已存在（app/main.py）
- [x] Task 1.4: API 路由已存在（routers/ 目录下有 check, market, report 等）

### Phase 2: 补全检测能力

- [x] Task 2.1: 可插拔架构已实现（BaseChecker, MedicalClaimChecker 等）
- [x] Task 2.2: 缺失标签检测已实现（MissingLabelChecker）
- [x] Task 2.3: 禁用成分检测已实现（BannedIngredientChecker）
- [x] Task 2.4: US 市场规则已实现（us_cosmetics_medical.txt, us_food_medical.txt 等）

### Phase 3: 前端界面

- [x] Task 3.1: 前端项目已初始化（React 19 + TypeScript + Ant Design）
- [x] Task 3.2: 合规检测页已实现（CheckPage.tsx）
- [x] Task 3.3: 检测历史页已实现（ReportsPage.tsx）
- [x] Task 3.4: 报告详情页已实现（ReportDetailPage.tsx）
- [x] Task 3.5: 法规查询页已实现（RulesPage.tsx）
- [x] Task 3.6: 首页已实现（DashboardPage.tsx 作为首页）

---

## 建议开发顺序

1. **Phase 4** — 测试：Task 4.1, Task 4.2（确保核心功能正常）
2. **Phase 1** — Task 1.7 验证后端可运行
3. **Phase 2** — Task 2.5 丰富 EU 市场规则、Task 2.6 违规案例库
4. **Phase 3** — 优化前端 UX
5. **Phase 5** — 工程化

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