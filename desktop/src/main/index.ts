import { app, shell, BrowserWindow, Tray, Menu, ipcMain, globalShortcut, dialog, nativeImage, Notification } from 'electron'
import { autoUpdater } from 'electron-updater'
import { join, resolve, dirname } from 'path'
import { existsSync, readFileSync, writeFileSync, mkdirSync, readdirSync, statSync } from 'fs'
import { spawn, ChildProcess } from 'child_process'

// ===== 环境判断（延迟到 app ready 后使用） =====
let isDev = false

// ===== 简易持久化配置（替代 electron-store，避免 ESM 兼容问题） =====
class SimpleStore {
  private path: string = ''
  private data: Record<string, any> = {}
  private initialized = false
  private defaults: Record<string, any>

  constructor(options: { defaults?: Record<string, any> } = {}) {
    this.defaults = options.defaults || {}
  }

  private init(): void {
    if (this.initialized) return
    this.path = join(app.getPath('userData'), 'config.json')
    try {
      this.data = JSON.parse(readFileSync(this.path, 'utf-8'))
    } catch {
      this.data = { ...this.defaults }
    }
    this.initialized = true
  }

  get(key: string): any {
    this.init()
    return this.data[key]
  }
  set(key: string, value: any): void {
    this.init()
    this.data[key] = value
    try {
      const dir = dirname(this.path)
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
      writeFileSync(this.path, JSON.stringify(this.data, null, 2), 'utf-8')
    } catch { /* ignore write errors */ }
  }
}

const store = new SimpleStore({
  defaults: {
    windowBounds: { x: undefined, y: undefined, width: 1280, height: 800 },
    autoStart: false,
    apiBaseUrl: 'http://127.0.0.1:8000',
    minimizeToTray: true,
    closeToTray: true,
  }
})

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let isQuitting = false
let backendProcess: ChildProcess | null = null

// ===== Python 后端进程管理 =====
function getBackendDir(): string {
  if (isDev) {
    return join(__dirname, '../../resources/backend')
  }
  return join(process.resourcesPath, 'backend')
}

function getPythonPath(): string {
  // 优先使用嵌入的 Python，否则用系统 Python
  const embeddedPython = join(getBackendDir(), '..', 'python', process.platform === 'win32' ? 'python.exe' : 'python3')
  if (existsSync(embeddedPython)) {
    return embeddedPython
  }
  // 系统 Python
  return process.platform === 'win32' ? 'python' : 'python3'
}

function startBackend(): Promise<void> {
  return new Promise((resolve) => {
    const backendDir = getBackendDir()
    const pythonPath = getPythonPath()
    const scriptPath = join(backendDir, 'start_server.py')

    if (!existsSync(scriptPath)) {
      console.warn('[CrossGuard] 后端脚本不存在，跳过后端启动（可能使用外部后端）')
      resolve()
      return
    }

    console.log(`[CrossGuard] 启动后端: ${pythonPath} ${scriptPath}`)
    console.log(`[CrossGuard] 后端目录: ${backendDir}`)

    backendProcess = spawn(pythonPath, [scriptPath], {
      cwd: backendDir,
      env: {
        ...process.env,
        PYTHONPATH: backendDir,
        PYTHONUNBUFFERED: '1',
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    backendProcess.stdout?.on('data', (data: Buffer) => {
      const msg = data.toString().trim()
      console.log(`[Backend] ${msg}`)
      // 检测 uvicorn 启动成功
      if (msg.includes('Uvicorn running on')) {
        resolve()
      }
    })

    backendProcess.stderr?.on('data', (data: Buffer) => {
      const msg = data.toString().trim()
      console.error(`[Backend] ${msg}`)
      if (msg.includes('Uvicorn running on')) {
        resolve()
      }
    })

    backendProcess.on('error', (err) => {
      console.error(`[CrossGuard] 后端启动失败: ${err.message}`)
      resolve() // 即使失败也继续，用户可能手动启动了后端
    })

    backendProcess.on('exit', (code) => {
      console.log(`[CrossGuard] 后端进程退出: code=${code}`)
      backendProcess = null
    })

    // 超时：5秒后无论后端是否启动成功都继续
    setTimeout(resolve, 5000)
  })
}

function stopBackend(): void {
  if (backendProcess && !backendProcess.killed) {
    console.log('[CrossGuard] 停止后端进程...')
    backendProcess.kill('SIGTERM')
    // Windows 下 SIGTERM 可能不够，给 3 秒后强制杀
    setTimeout(() => {
      if (backendProcess && !backendProcess.killed) {
        backendProcess.kill('SIGKILL')
      }
    }, 3000)
  }
}

// ===== 创建主窗口 =====
function createWindow(): void {
  const bounds = store.get('windowBounds') as { x?: number; y?: number; width: number; height: number }

  mainWindow = new BrowserWindow({
    width: bounds.width || 1280,
    height: bounds.height || 800,
    x: bounds.x,
    y: bounds.y,
    minWidth: 900,
    minHeight: 600,
    show: false,
    frame: false,
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#001529',
      symbolColor: '#ffffff',
      height: 36
    },
    icon: getIcon(),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
    }
  })

  // 窗口就绪后显示（防抖/防闪）
  mainWindow.on('ready-to-show', () => {
    mainWindow!.show()
  })

  // 记住窗口位置
  mainWindow.on('resize', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      const [width, height] = mainWindow.getSize()
      store.set('windowBounds', { ...store.get('windowBounds') as any, width, height })
    }
  })
  mainWindow.on('move', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      const [x, y] = mainWindow.getPosition()
      store.set('windowBounds', { ...store.get('windowBounds') as any, x, y })
    }
  })

  // 关闭行为：最小化到托盘
  mainWindow.on('close', (e) => {
    if (!isQuitting && store.get('closeToTray')) {
      e.preventDefault()
      mainWindow!.hide()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // 外部链接用系统浏览器打开
  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // 加载页面
  if (isDev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// ===== 获取图标 =====
function getIcon(): nativeImage {
  const iconPath = isDev
    ? join(__dirname, '../../resources/icon.png')
    : join(process.resourcesPath, 'icon.png')
  if (existsSync(iconPath)) {
    return nativeImage.createFromPath(iconPath)
  }
  // fallback: 16x16 透明图标
  return nativeImage.createEmpty()
}

// ===== 系统托盘 =====
function createTray(): void {
  const icon = getIcon()
  tray = new Tray(icon.isEmpty() ? nativeImage.createFromBuffer(Buffer.alloc(0)) : icon)
  tray.setToolTip('出海法盾 CrossGuard')

  const contextMenu = Menu.buildFromTemplate([
    { label: '显示主窗口', click: () => showWindow() },
    { label: '合规检测', click: () => { showWindow(); mainWindow?.webContents.send('navigate', '/check') } },
    { label: '批量检测', click: () => { showWindow(); mainWindow?.webContents.send('navigate', '/batch') } },
    { type: 'separator' },
    { label: '开机自启', type: 'checkbox', checked: store.get('autoStart') as boolean, click: (item) => {
      app.setLoginItemSettings({ openAtLogin: item.checked })
      store.set('autoStart', item.checked)
    }},
    { type: 'separator' },
    { label: '重启后端', click: async () => {
      stopBackend()
      await startBackend()
      dialog.showMessageBox({ type: 'info', title: '提示', message: '后端服务已重启' })
    }},
    { label: '检查更新', click: () => { updateCheckManual = true; autoUpdater.checkForUpdates() } },
    { label: '关于', click: () => {
      dialog.showMessageBox({
        type: 'info',
        title: '关于 出海法盾 CrossGuard',
        message: `出海法盾 CrossGuard v${app.getVersion()}`,
        detail: '跨境电商智能合规审查平台\nAI驱动的跨境商品合规检测，覆盖欧盟、美国、东南亚市场',
      })
    }},
    { type: 'separator' },
    { label: '退出', click: () => { isQuitting = true; app.quit() } }
  ])

  tray.setContextMenu(contextMenu)
  tray.on('double-click', () => showWindow())
}

function showWindow(): void {
  if (!mainWindow) {
    createWindow()
  }
  if (mainWindow!.isMinimized()) {
    mainWindow!.restore()
  }
  mainWindow!.show()
  mainWindow!.focus()
}

// ===== IPC 通信 =====
function setupIPC(): void {
  // 窗口控制（无边框窗口）
  ipcMain.on('window:minimize', () => mainWindow?.minimize())
  ipcMain.on('window:maximize', () => {
    if (mainWindow?.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow?.maximize()
    }
  })
  ipcMain.on('window:close', () => mainWindow?.close())
  ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false)

  // 本地文件读写
  ipcMain.handle('file:read', async (_e, filePath: string) => {
    try {
      const content = readFileSync(filePath, 'utf-8')
      return { success: true, data: content }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })

  ipcMain.handle('file:write', async (_e, filePath: string, content: string) => {
    try {
      const dir = resolve(filePath, '..')
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
      writeFileSync(filePath, content, 'utf-8')
      return { success: true }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })

  ipcMain.handle('file:readDir', async (_e, dirPath: string) => {
    try {
      const entries = readdirSync(dirPath).map(name => {
        const fullPath = join(dirPath, name)
        const isDir = statSync(fullPath).isDirectory()
        return { name, path: fullPath, isDir }
      })
      return { success: true, data: entries }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })

  // 文件对话框
  ipcMain.handle('dialog:openFile', async (_e, options: any) => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openFile'],
      filters: options?.filters || [
        { name: 'CSV/Excel', extensions: ['csv', 'xlsx', 'xls'] },
        { name: 'All Files', extensions: ['*'] }
      ],
      ...options
    })
    return result
  })

  ipcMain.handle('dialog:saveFile', async (_e, options: any) => {
    const result = await dialog.showSaveDialog(mainWindow!, options)
    return result
  })

  // 拖拽文件处理
  ipcMain.handle('file:handleDrop', async (_e, filePaths: string[]) => {
    const results = []
    for (const fp of filePaths) {
      try {
        const content = readFileSync(fp, 'utf-8')
        results.push({ path: fp, content, success: true })
      } catch (err: any) {
        results.push({ path: fp, error: err.message, success: false })
      }
    }
    return results
  })

  // 配置读写
  ipcMain.handle('store:get', (_e, key: string) => store.get(key))
  ipcMain.handle('store:set', (_e, key: string, value: any) => { store.set(key, value) })

  // API 基地址
  ipcMain.handle('config:getApiBaseUrl', () => store.get('apiBaseUrl'))
  ipcMain.handle('config:setApiBaseUrl', (_e, url: string) => { store.set('apiBaseUrl', url) })

  // 版本信息
  ipcMain.handle('app:getVersion', () => app.getVersion())

  // 系统通知
  ipcMain.handle('notification:show', async (_e, title: string, body: string) => {
    if (Notification.isSupported()) {
      const notification = new Notification({ title, body, icon: getIcon() })
      notification.show()
      notification.on('click', () => showWindow())
    }
  })
}

// ===== 自动更新 =====
let updateCheckManual = false

function setupAutoUpdater(): void {
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true

  autoUpdater.on('checking-for-update', () => {
    console.log('[AutoUpdater] 正在检查更新...')
  })

  autoUpdater.on('update-available', (info) => {
    console.log('[AutoUpdater] 发现新版本:', info.version)
    if (mainWindow) {
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: '发现新版本',
        message: `新版本 v${info.version} 可用，是否下载？`,
        buttons: ['下载', '稍后'],
        defaultId: 0,
      }).then(({ response }) => {
        if (response === 0) {
          autoUpdater.downloadUpdate()
        }
      })
    }
  })

  autoUpdater.on('update-not-available', () => {
    console.log('[AutoUpdater] 已是最新版本')
    if (updateCheckManual && mainWindow) {
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: '检查更新',
        message: '当前已是最新版本',
      })
    }
    updateCheckManual = false
  })

  autoUpdater.on('download-progress', (progress) => {
    const pct = Math.round(progress.percent)
    console.log(`[AutoUpdater] 下载进度: ${pct}%`)
    mainWindow?.webContents.send('update:download-progress', pct)
  })

  autoUpdater.on('update-downloaded', (info) => {
    console.log('[AutoUpdater] 下载完成:', info.version)
    if (mainWindow) {
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: '更新就绪',
        message: `v${info.version} 已下载完成，是否立即安装？`,
        buttons: ['立即安装', '下次启动'],
        defaultId: 0,
      }).then(({ response }) => {
        if (response === 0) {
          autoUpdater.quitAndInstall(false, true)
        }
      })
    }
  })

  autoUpdater.on('error', (err) => {
    console.error('[AutoUpdater] 错误:', err.message)
    if (updateCheckManual && mainWindow) {
      dialog.showMessageBox(mainWindow, {
        type: 'error',
        title: '检查更新失败',
        message: `更新检查出错: ${err.message}`,
      })
    }
    updateCheckManual = false
  })

  // IPC: 手动检查更新
  ipcMain.handle('app:checkForUpdates', () => {
    updateCheckManual = true
    autoUpdater.checkForUpdates()
  })
}

// ===== 全局快捷键 =====
function setupGlobalShortcuts(): void {
  // Ctrl+Shift+C: 快速打开合规检测
  globalShortcut.register('CommandOrControl+Shift+C', () => {
    showWindow()
    mainWindow?.webContents.send('navigate', '/check')
  })
  // Ctrl+Shift+B: 快速打开批量检测
  globalShortcut.register('CommandOrControl+Shift+B', () => {
    showWindow()
    mainWindow?.webContents.send('navigate', '/batch')
  })
}

// ===== 应用入口 =====
app.whenReady().then(async () => {
  // 判断开发环境
  isDev = !app.isPackaged

  // 单实例运行
  const gotLock = app.requestSingleInstanceLock()
  if (!gotLock) {
    app.quit()
    return
  }

  app.on('second-instance', () => {
    showWindow()
  })

  // Electron 工具包设置
  app.setAppUserModelId('com.crossguard.desktop')

  // 开发环境默认打开 DevTools
  if (isDev) {
    app.on('browser-window-created', (_, window) => {
      window.webContents.openDevTools()
    })
  }

  // 设置开机自启
  if (store.get('autoStart')) {
    app.setLoginItemSettings({ openAtLogin: true })
  }

  // ===== 先启动 Python 后端 =====
  console.log('[CrossGuard] 正在启动后端服务...')
  await startBackend()
  console.log('[CrossGuard] 后端服务已启动（或超时）')

  // 创建窗口和托盘
  createWindow()
  createTray()
  setupIPC()
  setupAutoUpdater()
  setupGlobalShortcuts()

  // 启动后静默检查更新（生产环境）
  if (!isDev) {
    autoUpdater.checkForUpdates()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else {
      showWindow()
    }
  })
})

// 清理
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  isQuitting = true
  stopBackend()
  globalShortcut.unregisterAll()
})

app.on('will-quit', () => {
  stopBackend()
  globalShortcut.unregisterAll()
})
