@echo off
chcp 65001 >nul
echo ============================================
echo   RaR 实验项目 — 环境配置
echo ============================================
echo.

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 已找到

REM 安装依赖
echo [*] 安装依赖...
pip install openai python-dotenv -q
if %errorlevel% neq 0 (
    echo [警告] pip install 失败，请手动执行: pip install openai python-dotenv
)
echo [OK] 依赖安装完成

REM 检查 .env 文件
if not exist .env (
    echo [*] 未找到 .env 文件，从 .env.example 复制...
    copy .env.example .env
    echo [重要] 请编辑 .env 文件，填入你的 API Key！
    notepad .env
)

echo.
echo ============================================
echo   配置完成！下一步:
echo   1. 编辑 .env 文件，填入 API Key
echo   2. 运行: python run_experiment.py
echo   3. 运行: python evaluate.py results_*.json
echo ============================================
pause
