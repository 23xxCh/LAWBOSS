!macro customHeader
  !system "echo 'CrossGuard Desktop Installer'"
!macroend

!macro customInstall
  ; 注册自定义协议
  WriteRegStr HKCR "crossguard" "" "URL:CrossGuard Protocol"
  WriteRegStr HKCR "crossguard" "URL Protocol" ""
  WriteRegStr HKCR "crossguard\shell\open\command" "" '"$INSTDIR\${APP_EXECUTABLE_NAME}" "%1"'
!macroend

!macro customUnInstall
  ; 清理注册表
  DeleteRegKey HKCR "crossguard"
!macroend
