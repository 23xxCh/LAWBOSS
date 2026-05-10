#!/bin/bash
#
# CrossGuard MCP Installer
# 一键安装 CrossGuard MCP 服务到 OpenClaw
#
# 用法: curl -sSL https://crossguard.ai/install.sh | bash
#

set -e

# 配置
REPO_URL="https://github.com/23xxCh/LAWBOSS"
INSTALL_DIR="$HOME/.crossguard"
VERSION="0.2.0"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测操作系统
detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)     echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*)    echo "windows" ;;
        *)          echo "unknown" ;;
    esac
}

# 检测 OpenClaw 配置目录
detect_openclaw_dir() {
    local os=$(detect_os)
    local dirs=()

    case "$os" in
        macos)
            dirs=(
                "$HOME/.openclaw"
                "$HOME/Library/Application Support/openclaw"
                "$HOME/.config/openclaw"
            )
            ;;
        linux)
            dirs=(
                "$HOME/.openclaw"
                "$HOME/.config/openclaw"
                "$XDG_CONFIG_HOME/openclaw"
            )
            ;;
        windows)
            dirs=(
                "$APPDATA/openclaw"
                "$HOME/.openclaw"
            )
            ;;
    esac

    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            echo "$dir"
            return 0
        fi
    done

    # 默认目录
    echo "$HOME/.openclaw"
}

# 检查 uv 是否安装
check_uv() {
    if command -v uv &> /dev/null; then
        log_info "uv 已安装: $(uv --version)"
        return 0
    else
        return 1
    fi
}

# 安装 uv
install_uv() {
    log_info "正在安装 uv..."

    if command -v curl &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &> /dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        log_error "需要 curl 或 wget 来安装 uv"
        exit 1
    fi

    # 添加到 PATH
    export PATH="$HOME/.local/bin:$PATH"
}

# 克隆或更新仓库
clone_repo() {
    log_info "正在克隆 CrossGuard 仓库..."

    if [ -d "$INSTALL_DIR/repo" ]; then
        log_info "仓库已存在，正在更新..."
        cd "$INSTALL_DIR/repo"
        git pull --quiet
    else
        mkdir -p "$INSTALL_DIR"
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR/repo"
    fi
}

# 安装 MCP 服务
install_mcp() {
    log_info "正在安装 CrossGuard MCP 服务..."

    cd "$INSTALL_DIR/repo/mcp-server"

    # 使用 uv 同步依赖
    uv sync --quiet

    log_success "MCP 服务安装完成"
}

# 配置 OpenClaw
configure_openclaw() {
    local openclaw_dir=$(detect_openclaw_dir)
    local mcp_dir="$INSTALL_DIR/repo/mcp-server"

    log_info "正在配置 OpenClaw..."
    log_info "OpenClaw 目录: $openclaw_dir"

    # 创建目录
    mkdir -p "$openclaw_dir/skills"
    mkdir -p "$openclaw_dir/mcp"

    # 复制 skill 文件
    if [ -d "$INSTALL_DIR/repo/skills/crossguard" ]; then
        cp -r "$INSTALL_DIR/repo/skills/crossguard" "$openclaw_dir/skills/"
        log_success "Skill 文件已复制到: $openclaw_dir/skills/crossguard"
    else
        log_warn "未找到 skill 文件，跳过"
    fi

    # 生成 MCP 配置
    local mcp_config="$openclaw_dir/mcp/mcp.json"
    local mcp_config_content=$(cat <<EOF
{
  "mcpServers": {
    "crossguard": {
      "command": "uv",
      "args": ["run", "--directory", "$mcp_dir", "crossguard_mcp_server.py"],
      "env": {}
    }
  }
}
EOF
)

    # 如果配置文件已存在，合并配置
    if [ -f "$mcp_config" ]; then
        log_info "MCP 配置文件已存在，正在合并..."
        # 使用 Python 合并 JSON (更可靠)
        python3 << PYTHON_SCRIPT
import json
import sys

try:
    with open("$mcp_config", "r") as f:
        config = json.load(f)
except:
    config = {"mcpServers": {}}

new_server = {
    "crossguard": {
        "command": "uv",
        "args": ["run", "--directory", "$mcp_dir", "crossguard_mcp_server.py"],
        "env": {}
    }
}

config.setdefault("mcpServers", {})
config["mcpServers"].update(new_server)

with open("$mcp_config", "w") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("配置合并成功")
PYTHON_SCRIPT
    else
        echo "$mcp_config_content" > "$mcp_config"
    fi

    log_success "MCP 配置已写入: $mcp_config"
}

# 验证安装
verify_installation() {
    log_info "正在验证安装..."

    cd "$INSTALL_DIR/repo/mcp-server"

    # 测试 MCP 服务是否能启动
    if timeout 10 uv run python -c "
import sys
sys.path.insert(0, '../backend')
from app.services.compliance_checker import ComplianceChecker
print('合规检测引擎加载成功')
" 2>/dev/null; then
        log_success "验证通过"
        return 0
    else
        log_warn "验证失败，请检查安装"
        return 1
    fi
}

# 打印使用说明
print_usage() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  CrossGuard MCP 安装完成!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "安装目录: $INSTALL_DIR/repo"
    echo ""
    echo "下一步:"
    echo "  1. 重启 OpenClaw 或重新加载配置"
    echo "  2. 在对话中使用以下触发词:"
    echo "     - 检测合规"
    echo "     - 合规检查"
    echo "     - violation check"
    echo "     - compliance check"
    echo ""
    echo "示例:"
    echo '  "帮我检测这段产品描述的合规性: 这款面霜能有效治疗痘痘"'
    echo ""
    echo "文档: https://github.com/23xxCh/LAWBOSS"
    echo ""
}

# 主流程
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  CrossGuard MCP Installer v${VERSION}${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # 检查 git
    if ! command -v git &> /dev/null; then
        log_error "需要 git，请先安装 git"
        exit 1
    fi

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "需要 Python 3.10+，请先安装 Python"
        exit 1
    fi

    # 检查/安装 uv
    if ! check_uv; then
        install_uv
    fi

    # 克隆仓库
    clone_repo

    # 安装 MCP
    install_mcp

    # 配置 OpenClaw
    configure_openclaw

    # 验证
    verify_installation

    # 打印使用说明
    print_usage
}

# 运行
main "$@"
