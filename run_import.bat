@echo off
chcp 65001 >nul
set PGPASSWORD=postgres
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d knowledge_extraction -f "H:\12-extractor\db_backup.sql"
echo Import completed with exit code: %ERRORLEVEL%
