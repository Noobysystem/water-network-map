@echo off
chcp 65001 > nul
echo ==============================================
echo Сборка автономного приложения "Схема ПВ" (.exe)
echo ==============================================
echo.

echo 1. Проверка и установка зависимостей...
python -m pip install pywebview pyinstaller --quiet

echo 2. Сборка исполняемого файла...
python -m PyInstaller --noconfirm --onedir --windowed ^
  --name "Схема_ПВ" ^
  --add-data "frontend;frontend" ^
  --add-data "data;data" ^
  app_pv.py

echo.
echo ==============================================
echo Сборка успешно завершена!
echo Папка с программой: dist\Схема_ПВ\Схема_ПВ.exe
echo ==============================================
pause
