# CrossGuard MCP Installer for Windows
# 一键安装 CrossGuard MCP 服务到 OpenClaw
#
# 用法: iwr -useb https://crossguard.ai/install.ps1 | iex
#

param(
    [string]$InstallDir = "$env:USERPROFILE\.crossguard",
    [string]$Version = "0.2.0"
)

# 配置
$RepoUrl = "https://github.com/23xxCh/LAWBOSS"
$ErrorActionPreference = "Stop"

# 颜色输出函数
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

# 检测 OpenClaw 配置目录
function Get-OpenClawDir {
    $dirs = @(
        "$env:APPDATA\openclaw",
        "$env:USERPROFILE\.openclaw",
        "$env:LOCALAPPDATA\openclaw"
    )

    foreach ($dir in $dirs) {
        if (Test-Path $dir) {
            return $dir
        }
    }

    # 默认目录
    return "$env:USERPROFILE\.openclaw"
}

# 检查 uv 是否安装
function Test-UvInstalled {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        Write-Info "uv 已安装: $(uv --version)"
        return $true
    }
    return $false
}

# 安装 uv
function Install-Uv {
    Write-Info "正在安装 uv..."

    # 使用 PowerShell 安装 uv
    $installScript = Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1"
    Invoke-Expression $installScript

    # 刷新环境变量
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
}

# 克隆或更新仓库
function Update-Repo {
    Write-Info "正在克隆 CrossGuard 仓库..."

    $repoDir = Join-Path $InstallDir "repo"

    if (Test-Path $repoDir) {
        Write-Info "仓库已存在，正在更新..."
        Push-Location $repoDir
        git pull --quiet
        Pop-Location
    } else {
        New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
        git clone --depth 1 $RepoUrl $repoDir
    }
}

# 安装 MCP 服务
function Install-Mcp {
    Write-Info "正在安装 CrossGuard MCP 服务..."

    $mcpDir = Join-Path $InstallDir "repo\mcp-server"
    Push-Location $mcpDir

    # 使用 uv 同步依赖
    uv sync --quiet

    Pop-Location

    Write-Success "MCP 服务安装完成"
}

# 配置 OpenClaw
function Configure-OpenClaw {
    $openclawDir = Get-OpenClawDir
    $mcpDir = Join-Path $InstallDir "repo\mcp-server"

    Write-Info "正在配置 OpenClaw..."
    Write-Info "OpenClaw 目录: $openclawDir"

    # 创建目录
    $skillsDir = Join-Path $openclawDir "skills"
    $mcpConfigDir = Join-Path $openclawDir "mcp"

    New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
    New-Item -ItemType Directory -Force -Path $mcpConfigDir | Out-Null

    # 复制 skill 文件
    $skillSrc = Join-Path $InstallDir "repo\skills\crossguard"
    if (Test-Path $skillSrc) {
        $skillDest = Join-Path $skillsDir "crossguard"
        Copy-Item -Path $skillSrc -Destination $skillDest -Recurse -Force
        Write-Success "Skill 文件已复制到: $skillDest"
    } else {
        Write-Warning "未找到 skill 文件，跳过"
    }

    # 生成 MCP 配置
    $mcpConfigFile = Join-Path $mcpConfigDir "mcp.json"

    $newConfig = @{
        mcpServers = @{
            crossguard = @{
                command = "uv"
                args = @("run", "--directory", $mcpDir, "crossguard_mcp_server.py")
                env = @{}
            }
        }
    }

    if (Test-Path $mcpConfigFile) {
        Write-Info "MCP 配置文件已存在，正在合并..."

        try {
            $existingConfig = Get-Content $mcpConfigFile -Raw | ConvertFrom-Json

            # 确保 mcpServers 存在
            if (-not $existingConfig.mcpServers) {
                $existingConfig | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{} -Force
            }

            # 添加 crossguard 配置
            $existingConfig.mcpServers | Add-Member -MemberType NoteProperty -Name "crossguard" -Value $newConfig.mcpServers.crossguard -Force

            $existingConfig | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigFile -Encoding UTF8
        } catch {
            Write-Warning "合并配置失败，将覆盖原配置"
            $newConfig | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigFile -Encoding UTF8
        }
    } else {
        $newConfig | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigFile -Encoding UTF8
    }

    Write-Success "MCP 配置已写入: $mcpConfigFile"
}

# 验证安装
function Test-Installation {
    Write-Info "正在验证安装..."

    $mcpDir = Join-Path $InstallDir "repo\mcp-server"
    Push-Location $mcpDir

    try {
        $env:PYTHONPATH = Join-Path $InstallDir "repo\backend"
        $result = uv run python -c @"
import sys
sys.path.insert(0, '../backend')
from app.services.compliance_checker import ComplianceChecker
print('合规检测引擎加载成功')
"@ 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Success "验证通过"
            return $true
        } else {
            Write-Warning "验证失败，请检查安装"
            return $false
        }
    } catch {
        Write-Warning "验证失败: $_"
        return $false
    } finally {
        Pop-Location
    }
}

# 打印使用说明
function Show-Usage {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  CrossGuard MCP 安装完成!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "安装目录: $InstallDir\repo"
    Write-Host ""
    Write-Host "下一步:"
    Write-Host "  1. 重启 OpenClaw 或重新加载配置"
    Write-Host "  2. 在对话中使用以下触发词:"
    Write-Host "     - 检测合规"
    Write-Host "     - 合规检查"
    Write-Host "     - violation check"
    Write-Host "     - compliance check"
    Write-Host ""
    Write-Host "示例:"
    Write-Host '  "帮我检测这段产品描述的合规性: 这款面霜能有效治疗痘痘"'
    Write-Host ""
    Write-Host "文档: https://github.com/23xxCh/LAWBOSS"
    Write-Host ""
}

# 主流程
function Main {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host "  CrossGuard MCP Installer v$Version" -ForegroundColor Blue
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host ""

    # 检查 git
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        Write-Error "需要 git，请先安装 git"
        Write-Info "下载地址: https://git-scm.com/download/win"
        exit 1
    }

    # 检查 Python
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error "需要 Python 3.10+，请先安装 Python"
        Write-Info "下载地址: https://www.python.org/downloads/"
        exit 1
    }

    # 检查/安装 uv
    if (-not (Test-UvInstalled)) {
        Install-Uv
    }

    # 克隆仓库
    Update-Repo

    # 安装 MCP
    Install-Mcp

    # 配置 OpenClaw
    Configure-OpenClaw

    # 验证
    Test-Installation | Out-Null

    # 打印使用说明
    Show-Usage
}

# 运行
Main
