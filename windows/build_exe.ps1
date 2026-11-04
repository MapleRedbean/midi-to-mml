# 用 PyInstaller 打包成单个 Windows 可执行文件 midi2mml.exe
# 需要先: pip install pyinstaller
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python -m PyInstaller `
  --onefile --noconsole --name midi2mml `
  --add-data "scripts\requirements.txt;." `
  scripts\midi2mml.py
Write-Host "输出: dist\midi2mml.exe"
