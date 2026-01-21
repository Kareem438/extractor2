# Build and install pgvector for PostgreSQL 16

Write-Host "Setting up Visual Studio environment..." -ForegroundColor Cyan

# Import Visual Studio environment
$vsPath = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cmd /c "`"$vsPath`" && set" | ForEach-Object {
    if ($_ -match "^(.*?)=(.*)$") {
        Set-Item -Path "env:\$($matches[1])" -Value $matches[2]
    }
}

Write-Host "Visual Studio environment loaded" -ForegroundColor Green

# Set PostgreSQL root
$env:PGROOT = "C:\Program Files\PostgreSQL\16"
Write-Host "PGROOT set to: $env:PGROOT" -ForegroundColor Yellow

# Navigate to pgvector directory
Set-Location "H:\12-extractor\pgvector"

Write-Host "`nBuilding pgvector..." -ForegroundColor Cyan
nmake /F Makefile.win

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nBuild successful! Installing to PostgreSQL..." -ForegroundColor Green
    nmake /F Makefile.win install

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`npgvector installation complete!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "`nInstallation failed with exit code: $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "`nBuild failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    exit 1
}
