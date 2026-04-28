import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// Electron 桌面端：监听主进程推送的导航事件
if (window.api) {
  window.api.onNavigate((path: string) => {
    window.location.hash = '#' + path
    // 如果使用 BrowserRouter，需要用 history.push
    // 这里用 hash 方式兼容两种 Router
  })
}
