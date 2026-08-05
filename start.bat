@echo off
REM VIIMK 一键启动脚本（Windows）
REM 功能：启动 venv 内 Flask 后端 + uniapp Vite 前端
setlocal

cd /d "%~dp0"

REM 1) venv 初始化
if not exist .venv\Scripts\python.exe (
  echo [viimk] 首次启动，创建 Python venv...
  py -3 -m venv .venv
)
if not exist .venv\Scripts\flask.exe (
  echo [viimk] 安装 Python 依赖...
  .venv\Scripts\pip install -q -r requirements.txt
)

REM 2) 端口
if "%PY_PORT%"=="" set PY_PORT=3001

REM 3) 杀可能残留的后端进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PY_PORT%" ^| findstr LISTENING') do (
  taskkill /F /PID %%a >nul 2>&1
)

REM 4) 启动 Flask 后端（后台）
set PY_LOG=.python.log
echo [viimk] 启动 Python 后端 (port=%PY_PORT%)，日志: %PY_LOG%
start /B .venv\Scripts\python.exe server.py > "%PY_LOG%" 2>&1

REM 5) 等待后端就绪
for /L %%i in (1,1,30) do (
  curl -sf "http://127.0.0.1:%PY_PORT%/api/health" >nul 2>&1 && goto ready
  timeout /t 1 /nobreak >nul
)
:ready
echo [viimk] Python 后端就绪

REM 6) 启动前端
set TARGET=%1
if "%TARGET%"=="" set TARGET=h5
echo [viimk] 启动前端 Vite dev server (%TARGET%)
npm run dev:%TARGET%

endlocal
