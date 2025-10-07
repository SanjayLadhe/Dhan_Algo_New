@echo off
REM ASCII Converter - Guaranteed Fix for Windows
REM =============================================

echo.
echo ================================================================================
echo UNICODE ERROR FIX - ASCII CONVERTER
echo ================================================================================
echo.
echo This will convert all files to ASCII-only (no special characters).
echo Guaranteed to work on ANY Windows system!
echo.
echo Original files will be backed up with .backup extension.
echo.
pause

echo.
echo Converting files to ASCII...
echo.

python convert_to_ascii.py

echo.
echo ================================================================================
echo CONVERSION COMPLETE
echo ================================================================================
echo.
echo Now you can run without errors:
echo   - python verify_setup.py
echo   - python test_paper_trading.py
echo   - python single_trade_focus_bot.py
echo.
echo If you need to restore original files:
echo   - Delete the converted file
echo   - Rename .backup file (remove .backup extension)
echo.
pause
