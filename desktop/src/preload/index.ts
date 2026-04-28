import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

// ===== 自定义 API 暴露给渲染进程 =====
const api = {
  // 窗口控制
  window: {
    minimize: () => ipcRenderer.send('window:minimize'),
    maximize: () => ipcRenderer.send('window:maximize'),
    close: () => ipcRenderer.send('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
    onMaximizeChange: (callback: (maximized: boolean) => void) => {
      ipcRenderer.on('window:maximizeChanged', (_e, val) => callback(val))
    }
  },

  // 文件操作
  file: {
    read: (filePath: string) => ipcRenderer.invoke('file:read', filePath),
    write: (filePath: string, content: string) => ipcRenderer.invoke('file:write', filePath, content),
    readDir: (dirPath: string) => ipcRenderer.invoke('file:readDir', dirPath),
    handleDrop: (filePaths: string[]) => ipcRenderer.invoke('file:handleDrop', filePaths),
  },

  // 文件对话框
  dialog: {
    openFile: (options?: any) => ipcRenderer.invoke('dialog:openFile', options),
    saveFile: (options?: any) => ipcRenderer.invoke('dialog:saveFile', options),
  },

  // 持久化配置
  store: {
    get: (key: string) => ipcRenderer.invoke('store:get', key),
    set: (key: string, value: any) => ipcRenderer.invoke('store:set', key, value),
  },

  // API 配置
  config: {
    getApiBaseUrl: () => ipcRenderer.invoke('config:getApiBaseUrl'),
    setApiBaseUrl: (url: string) => ipcRenderer.invoke('config:setApiBaseUrl', url),
  },

  // 系统通知
  notification: {
    show: (title: string, body: string) => ipcRenderer.invoke('notification:show', title, body),
  },

  // 应用信息
  app: {
    getVersion: () => ipcRenderer.invoke('app:getVersion'),
    checkForUpdates: () => ipcRenderer.invoke('app:checkForUpdates'),
  },

  // 导航（从主进程推送）
  onNavigate: (callback: (path: string) => void) => {
    ipcRenderer.on('navigate', (_e, path) => callback(path))
  },

  // 版本更新
  onCheckUpdate: (callback: () => void) => {
    ipcRenderer.on('check-update', () => callback())
  },
}

// 暴露 electron API + 自定义 API
if (process.contextIsolated) {
  contextBridge.exposeInMainWorld('electron', electronAPI)
  contextBridge.exposeInMainWorld('api', api)
} else {
  ;(window as any).electron = electronAPI
  ;(window as any).api = api
}
