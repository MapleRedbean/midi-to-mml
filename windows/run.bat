@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>&1 || (echo 请先安装 Python 3.11: https://www.python.org/downloads/ & pause & exit /b 1)
python -c "import mido" 2>nul || python -m pip install -r scripts\requirements.txt
python scripts\midi2mml.py %*
