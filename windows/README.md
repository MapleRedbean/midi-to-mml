# Windows 使用

## 方式 A：有 Python（最简单，5 分钟）

1. 安装 Python 3.11+（勾选 "Add to PATH"）：https://www.python.org/downloads/
2. 双击 `run.bat`，或命令行：
   ```
   run.bat 输入.mid -o 输出目录 --zip
   ```
   首次运行会自动 `pip install mido`。

## 方式 B：打包成单个 .exe（给没有 Python 的机器）

1. 在任意 Windows 机上安装 Python + PyInstaller：
   ```
   pip install pyinstaller mido
   ```
2. 运行 `build_exe.ps1`（或 `pyinstaller --onefile scripts\midi2mml.py`）
3. 产物 `dist\midi2mml.exe` 可直接分发，双击或命令行使用：
   ```
   midi2mml.exe 输入.mid -o 输出目录 --zip
   ```

## 注意

- PyInstaller 不能跨平台编译：在 Linux 上打不出 Windows .exe。必须在 Windows 上打，或用 GitHub Actions。
- 若要 CI 自动打 Windows 包，可把 `build_exe.ps1` 放进 GitHub Actions 的 `windows-latest` runner。
