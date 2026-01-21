@echo off
echo Installing pgvector for PostgreSQL 16...
echo.

REM Set up Visual Studio environment
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

REM Set PostgreSQL root (change 18 to 16)
set "PGROOT=C:\Program Files\PostgreSQL\16"

REM Clone and build pgvector
cd %TEMP%
echo Cloning pgvector repository...
git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
cd pgvector

echo.
echo Building pgvector...
nmake /F Makefile.win

echo.
echo Installing pgvector to PostgreSQL 16...
nmake /F Makefile.win install

echo.
echo pgvector installation complete!
echo.
pause
