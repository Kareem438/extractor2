@echo off
REM Install pgvector for PostgreSQL 16

echo ========================================
echo Installing pgvector for PostgreSQL 16
echo ========================================
echo.

REM Run this in x64 Native Tools Command Prompt environment
call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64

echo Setting PGROOT...
set "PGROOT=C:\Program Files\PostgreSQL\16"

echo Navigating to pgvector directory...
cd /d H:\12-extractor\pgvector

echo.
echo Cleaning previous build...
nmake /F Makefile.win clean

echo.
echo Building pgvector...
nmake /F Makefile.win

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Installing pgvector to PostgreSQL 16...
nmake /F Makefile.win install

if %ERRORLEVEL% NEQ 0 (
    echo Installation failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo pgvector installation completed successfully!
echo ========================================
echo.
pause
