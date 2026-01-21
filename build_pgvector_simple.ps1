# Simple pgvector build script

Write-Host "Starting pgvector build..." -ForegroundColor Cyan

# Define paths
$vsDevShell = "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\Launch-VsDevShell.ps1"
$vsVarsAll = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"

# Set PGROOT
$env:PGROOT = "C:\Program Files\PostgreSQL\16"

# Navigate to pgvector
Set-Location "H:\12-extractor\pgvector"

# Try using cmd with vcvarsall.bat
$buildScript = @"
call "$vsVarsAll" x64
set "PGROOT=C:\Program Files\PostgreSQL\16"
cd /d H:\12-extractor\pgvector
nmake /F Makefile.win clean
nmake /F Makefile.win
nmake /F Makefile.win install
"@

$buildScript | Out-File -FilePath "H:\12-extractor\temp_build.bat" -Encoding ASCII

# Execute the build script
cmd /c "H:\12-extractor\temp_build.bat"

$exitCode = $LASTEXITCODE
Remove-Item "H:\12-extractor\temp_build.bat" -ErrorAction SilentlyContinue

if ($exitCode -eq 0) {
    Write-Host "`nBuild and installation successful!" -ForegroundColor Green
} else {
    Write-Host "`nBuild failed with exit code: $exitCode" -ForegroundColor Red
}

exit $exitCode
