# CrossGuard MCP Server

跨境电商智能合规审查 MCP 服务，为 AI Agent (Claude Code, OpenClaw 等) 提供合规检测工具。

## 一键安装

**Linux/macOS:**
```bash
curl -sSL https://crossguard.ai/install.sh | bash
```

**Windows (PowerShell):**
```powershell
iwr -useb https://crossguard.ai/install.ps1 | iex
```

安装脚本会自动完成以下操作：
1. 检测并安装 uv（如未安装）
2. 克隆 CrossGuard 仓库到 `~/.crossguard/`
3. 安装 MCP 服务依赖
4. 自动检测 OpenClaw/Claude Code 配置目录
5. 写入 MCP 配置
6. 复制 skill 文件（OpenClaw）

## 手动安装

```bash
# 克隆仓库
git clone https://github.com/23xxCh/LAWBOSS.git
cd LAWBOSS/mcp-server

# 使用 uv 安装依赖
uv sync
```

## 托管 MCP 端点 (HTTP/SSE)

如果你有自己的 CrossGuard 后端部署，可以使用 HTTP MCP 端点：

```bash
# 启动 HTTP MCP 服务器
CROSSGUARD_API_URL=https://your-api.crossguard.ai \
CROSSGUARD_REQUIRE_API_KEY=true \
uv run crossguard_mcp_http.py
```

**环境变量:**
| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CROSSGUARD_API_URL` | 后端 API 地址 | `http://localhost:8000` |
| `CROSSGUARD_REQUIRE_API_KEY` | 是否要求 API Key | `false` |
| `CROSSGUARD_HOST` | 监听地址 | `0.0.0.0` |
| `CROSSGUARD_PORT` | 监听端口 | `8080` |

**用户配置 (OpenClaw/Claude Code):**
```json
{
  "mcpServers": {
    "crossguard": {
      "url": "https://mcp.crossguard.ai/sse",
      "headers": {"Authorization": "Bearer YOUR_API_KEY"}
    }
  }
}
```

## Claude Code 配置

在 Claude Code 的 MCP 配置文件中添加：

**macOS/Linux:** `~/.config/claude-code/mcp.json`
**Windows:** `%APPDATA%\Claude Code\mcp.json`

```json
{
  "mcpServers": {
    "crossguard": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/LAWBOSS/mcp-server", "crossguard_mcp_server.py"]
    }
  }
}
```

## OpenClaw 配置

将 `skills/crossguard/` 目录复制到 OpenClaw 的 skills 目录中。

## 可用工具

### check_compliance

检测产品描述在目标市场的合规性。

**参数:**
- `description` (string, 必需): 产品描述文本
- `market` (string, 默认 "EU"): 目标市场 (EU/US/SEA_SG/SEA_TH/SEA_MY)
- `category` (string, 默认 "化妆品"): 产品类别

**返回:**
```json
{
  "risk_score": 85,
  "risk_level": "高风险",
  "violations": [
    {
      "type": "medical_claim",
      "content": "治疗痘痘",
      "suggestion": "舒缓痘痘"
    }
  ],
  "suggestions": ["建议删除绝对化用语"],
  "compliant_version": "这款面霜具有舒缓保湿功效"
}
```

### list_markets

列出所有支持的市场和类别。

## 支持的市场

| 市场代码 | 市场 |
|----------|------|
| EU | 欧盟 |
| US | 美国 |
| SEA_SG | 新加坡 |
| SEA_TH | 泰国 |
| SEA_MY | 马来西亚 |

## 支持的类别

- 化妆品
- 电子产品
- 食品
- 玩具
- 纺织品
- 膳食补充剂

## 检测类型

1. **医疗宣称** (medical_claim): 宣称治疗效果、疾病预防等
2. **绝对化用语** (absolute_term): "最好"、"第一"、"100%"等
3. **虚假广告** (false_advertising): 误导性描述
4. **缺失标签** (missing_label): 缺少必需的标签声明
5. **禁用成分** (banned_ingredient): 含有法规禁止的成分

## CLI 使用

```bash
# 单条检测
uv run crossguard check "这款面霜能治疗痘痘" --market EU --category 化妆品

# JSON 输出
uv run crossguard check "这款面霜能治疗痘痘" --json

# 批量检测
uv run crossguard batch items.jsonl
```

## 开发

```bash
# 运行测试
uv run pytest tests/ -v

# 启动 MCP 服务器
uv run crossguard_mcp_server.py
```

## 许可证

MIT
