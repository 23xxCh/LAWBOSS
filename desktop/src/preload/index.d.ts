import { ElectronAPI } from '@electron-toolkit/preload'

interface CustomAPI {
  window: {
    minimize(): void
    maximize(): void
    close(): void
    isMaximized(): Promise<boolean>
    onMaximizeChange(callback: (maximized: boolean) => void): void
  }
  file: {
    read(filePath: string): Promise<{ success: boolean; data?: string; error?: string }>
    write(filePath: string, content: string): Promise<{ success: boolean; error?: string }>
    readDir(dirPath: string): Promise<{ success: boolean; data?: { name: string; path: string; isDir: boolean }[]; error?: string }>
    handleDrop(filePaths: string[]): Promise<{ path: string; content?: string; error?: string; success: boolean }[]>
  }
  dialog: {
    openFile(options?: any): Promise<Electron.OpenDialogReturnValue>
    saveFile(options?: any): Promise<Electron.SaveDialogReturnValue>
  }
  store: {
    get(key: string): Promise<any>
    set(key: string, value: any): Promise<void>
  }
  config: {
    getApiBaseUrl(): Promise<string>
    setApiBaseUrl(url: string): Promise<void>
  }
  app: {
    getVersion(): Promise<string>
    checkForUpdates(): Promise<void>
  }
  notification: {
    show(title: string, body: string): Promise<void>
  }
  onNavigate(callback: (path: string) => void): void
  onCheckUpdate(callback: () => void): void
}

declare global {
  interface Window {
    electron: ElectronAPI
    api: CustomAPI
  }
}
