@echo off
REM 域名分析系统 - 启动调度器
REM 设置编码为UTF-8
chcp 65001 >nul

echo ========================================
echo 域名分析系统 - 定时任务调度器
echo ========================================
echo.
echo [说明] 启动后将立即执行一次任务
echo [说明] 然后每天 09:00 自动执行
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查Python是否可用
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到Python，请确保Python已安装并添加到PATH环境变量
    pause
    exit /b 1
)

REM 启动调度器
echo [信息] 正在启动调度器...
echo [信息] 按 Ctrl+C 可以停止调度器
echo.

python scheduler.py

pause

