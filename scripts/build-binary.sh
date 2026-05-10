#!/bin/bash
#
# CrossGuard MCP Binary Builder
# 使用 PyInstaller 打包 MCP 服务器为独立二进制
#
# 用法: ./build-binary.sh [platform]
#   platform: linux, macos, windows (默认: 当前系统)
#

set -e

# 配置
VERSION="0.2.0"
DIST_DIR="./dist"
BUILD_DIR="./build"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
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

# 构建二进制
build_binary() {
    local os=$1
    local output_name="crossguard-mcp-${VERSION}-${os}-x64"

    log_info "正在为 $os 构建二进制..."

    # 清理
    rm -rf "$BUILD_DIR" "$DIST_DIR"
    mkdir -p "$DIST_DIR"

    # 确定后端目录
    BACKEND_DIR="../backend"
    DATA_DIR="$BACKEND_DIR/data"

    if [ ! -d "$DATA_DIR" ]; then
        log_error "数据目录不存在: $DATA_DIR"
        exit 1
    fi

    # PyInstaller 参数
    local hidden_imports=(
        "--hidden-import=mcp"
        "--hidden-import=mcp.server"
        "--hidden-import=mcp.server.fastmcp"
        "--hidden-import=httpx"
    )

    local data_files=(
        "--add-data=$DATA_DIR:data"
    )

    # 添加后端模块
    local backend_modules=(
        "--hidden-import=app"
        "--hidden-import=app.services"
        "--hidden-import=app.services.compliance_checker"
        "--hidden-import=app.config"
        "--hidden-import=utils"
        "--add-data=$BACKEND_DIR/app:app"
    )

    # 构建
    pyinstaller --onefile \
        --name "$output_name" \
        "${hidden_imports[@]}" \
        "${data_files[@]}" \
        "${backend_modules[@]}" \
        --clean \
        --noconfirm \
        crossguard_mcp_server.py

    # 移动到 dist
    if [ -f "dist/$output_name" ]; then
        mv "dist/$output_name" "$DIST_DIR/"
        chmod +x "$DIST_DIR/$output_name"
    elif [ -f "dist/${output_name}.exe" ]; then
        mv "dist/${output_name}.exe" "$DIST_DIR/"
    fi

    log_success "构建完成: $DIST_DIR/$output_name"
}

# 打包数据文件
package_data() {
    log_info "正在打包数据文件..."

    local data_tar="$DIST_DIR/crossguard-data-${VERSION}.tar.gz"

    tar -czvf "$data_tar" -C ../backend data/

    log_success "数据文件已打包: $data_tar"
}

# 创建发布包
create_release() {
    local os=$1
    local release_name="crossguard-mcp-${VERSION}-${os}-x64"
    local release_dir="$DIST_DIR/$release_name"
    local release_tar="$DIST_DIR/${release_name}.tar.gz"

    log_info "正在创建发布包..."

    mkdir -p "$release_dir"

    # 复制二进制
    if [ -f "$DIST_DIR/$release_name" ]; then
        cp "$DIST_DIR/$release_name" "$release_dir/"
    elif [ -f "$DIST_DIR/${release_name}.exe" ]; then
        cp "$DIST_DIR/${release_name}.exe" "$release_dir/"
    fi

    # 复制数据文件
    if [ -f "$DIST_DIR/crossguard-data-${VERSION}.tar.gz" ]; then
        cp "$DIST_DIR/crossguard-data-${VERSION}.tar.gz" "$release_dir/"
    fi

    # 复制文档
    cp ../README.md "$release_dir/" 2>/dev/null || true
    cp ../LICENSE "$release_dir/" 2>/dev/null || true

    # 打包
    tar -czvf "$release_tar" -C "$DIST_DIR" "$release_name"

    log_success "发布包已创建: $release_tar"
}

# 主流程
main() {
    local target_os=${1:-$(detect_os)}

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  CrossGuard MCP Binary Builder${NC}"
    echo -e "${BLUE}  Version: $VERSION${NC}"
    echo -e "${BLUE}  Target: $target_os${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # 检查 PyInstaller
    if ! command -v pyinstaller &> /dev/null; then
        log_info "正在安装 PyInstaller..."
        pip install pyinstaller
    fi

    # 切换到 MCP 服务器目录
    cd "$(dirname "$0")/../mcp-server"

    # 构建
    build_binary "$target_os"

    # 打包数据
    package_data

    # 创建发布包
    create_release "$target_os"

    echo ""
    log_success "构建完成!"
    echo ""
    echo "输出文件:"
    ls -la "$DIST_DIR"
}

# 运行
main "$@"
