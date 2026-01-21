$env:PGPASSWORD = 'postgres'
$psqlPath = 'C:\Program Files\PostgreSQL\16\bin\psql.exe'
$backupFile = 'H:\12-extractor\db_backup.sql'

Write-Host "Starting database import..."
& $psqlPath -U postgres -d knowledge_extraction -f $backupFile

Write-Host "Import completed with exit code: $LASTEXITCODE"
exit $LASTEXITCODE
