/**
 * 图标生成脚本
 * 运行: node resources/generate-icons.js
 * 需要先安装: npm install --save-dev sharp png-to-ico
 * 
 * 如果没有源图标，此脚本会生成一个默认的蓝色盾牌图标
 */
const fs = require('fs')
const path = require('path')

// 简单的 SVG 盾牌图标
const shieldSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1890ff"/>
      <stop offset="100%" stop-color="#096dd9"/>
    </linearGradient>
  </defs>
  <path d="M256 32 L448 112 L448 272 C448 384 352 448 256 480 C160 448 64 384 64 272 L64 112 Z" fill="url(#g)"/>
  <path d="M256 80 L400 144 L400 264 C400 352 320 408 256 432 C192 408 112 352 112 264 L112 144 Z" fill="#e6f7ff" opacity="0.3"/>
  <text x="256" y="300" text-anchor="middle" fill="white" font-size="180" font-weight="bold" font-family="Arial">CG</text>
</svg>`

const resourcesDir = __dirname

// 写入 SVG
fs.writeFileSync(path.join(resourcesDir, 'icon.svg'), shieldSvg)
console.log('icon.svg created')

// 提示用户如何生成 ICO/ICNS
console.log(`
===========================================
图标文件生成说明：
===========================================

1. 将你的应用图标（512x512 PNG）保存为: resources/icon.png

2. 安装图标转换工具:
   npm install --save-dev electron-icon-builder

3. 一键生成所有平台图标:
   npx electron-icon-builder --input=resources/icon.png --output=resources

   这将自动生成:
   - resources/icon.ico     (Windows)
   - resources/icon.icns    (macOS)  
   - resources/icon.png     (Linux/通用)
   - resources/16x16.png ~ 512x512.png (各尺寸)

4. 或者手动在线转换:
   - https://cloudconvert.com/png-to-ico
   - https://cloudconvert.com/png-to-icns

===========================================
`)
