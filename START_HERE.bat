закрытии@echo off
chcp 65001 >nul
echo ========================================
echo   Spam KP Assistant - Запуск
echo ========================================
echo.
echo Запуск приложения...
echo.

cd /d "%~dp0"
python run_simple.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Приложение завершено
) else (
    echo.
    echo Ошибка запуска (код: %ERRORLEVEL%)
)

echo.
echo Нажмите любую клавишу для выхода...
pause >nul
