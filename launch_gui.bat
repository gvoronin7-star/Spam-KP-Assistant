@echo off
chcp 65001 >nul
echo ========================================
echo   Spam KP Assistant - Запуск GUI
echo ========================================
echo.
echo Запуск приложения...
echo.

cd /d "%~dp0"
python run.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Приложение завершено нормально
) else (
    echo.
    echo [ERROR] Произошла ошибка (код: %ERRORLEVEL%)
    echo.
    echo Нажмите любую клавишу для выхода...
    pause >nul
)
