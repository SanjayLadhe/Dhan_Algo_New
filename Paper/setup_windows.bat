@echo off
REM Windows Encoding Fix - Quick Setup
REM ====================================

echo.
echo ================================================================================
echo WINDOWS ENCODING FIX - AUTOMATIC SETUP
echo ================================================================================
echo.
echo This will fix Unicode/charmap errors in your paper trading files.
echo.
pause

REM Set console to UTF-8
chcp 65001 > nul

echo.
echo [1/3] Setting console to UTF-8 encoding...
echo.

echo [2/3] Running encoding fix script...
echo.
python fix_windows_encoding.py

echo.
echo [3/3] Running setup verification...
echo.
python verify_setup.py

echo.
echo ================================================================================
echo SETUP COMPLETE
echo ================================================================================
echo.
echo Next steps:
echo   1. Test paper trading: python test_paper_trading.py
echo   2. Run your bot: python single_trade_focus_bot.py
echo.
pause
