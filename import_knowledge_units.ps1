$env:PGPASSWORD = 'postgres'
$psqlPath = 'C:\Program Files\PostgreSQL\16\bin\psql.exe'
$backupFile = 'H:\12-extractor\db_backup.sql'

Write-Host "Re-importing knowledge_units tables with pgvector support..." -ForegroundColor Cyan

# Import the full backup again - this time pgvector is available
& $psqlPath -U postgres -d knowledge_extraction -f $backupFile -q 2>&1 | Select-String -Pattern "CREATE TABLE.*knowledge_units|COPY.*knowledge_units|ERROR"

Write-Host "`nImport completed with exit code: $LASTEXITCODE" -ForegroundColor Green
