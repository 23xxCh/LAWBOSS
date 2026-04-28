import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'

// 全局错误捕获，防止黑屏
window.addEventListener('error', (e) => {
  const root = document.getElementById('root')
  if (root) {
    root.innerHTML = `<div style="padding:40px;max-width:600px;margin:80px auto;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.15)">
      <h2 style="color:#ff4d4f">应用运行时错误</h2>
      <p style="color:#666">${e.message}</p>
      ${e.filename ? `<p style="font-size:12px;color:#999">${e.filename}:${e.lineno}:${e.colno}</p>` : ''}
      <button onclick="location.reload()" style="margin-top:16px;padding:8px 24px;background:#1890ff;color:#fff;border:none;border-radius:4px;cursor:pointer">刷新页面</button>
    </div>`
  }
  e.preventDefault()
})
window.addEventListener('unhandledrejection', (e) => {
  console.error('[Unhandled Rejection]', e.reason)
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// Electron 桌面端：监听主进程推送的导航事件
if (window.api) {
  window.api.onNavigate((path: string) => {
    window.location.hash = '#' + path
  })
}
