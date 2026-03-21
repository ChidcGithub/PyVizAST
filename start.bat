@echo off
chcp 65001 >nul
echo ========================================
echo   PyVizAST - Python AST Visualizer
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

:: Run installation and startup
python run.py all
pause
