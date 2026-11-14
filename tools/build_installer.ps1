# Собирает OptiPlayer.exe (PyInstaller) и установщик (Inno Setup).
# Запуск: powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'

if (-not (Test-Path $Python)) {
    throw "Не найдено окружение .venv. Создайте его: python -m venv .venv"
}

$candidates = @(
    $env:ISCC,
    (Join-Path $Root '..\Tools\InnoSetup\ISCC.exe'),
    (Join-Path $Root '..\..\Tools\InnoSetup\ISCC.exe'),
    'C:\Program Files\Inno Setup 7\ISCC.exe',
    'C:\Program Files (x86)\Inno Setup 7\ISCC.exe',
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
) | Where-Object { $_ -and (Test-Path $_) }

$iscc = $candidates | Select-Object -First 1
if (-not $iscc) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { $iscc = $command.Source }
}
if (-not $iscc) {
    throw "Не найден ISCC.exe. Установите Inno Setup 7 или задайте путь в переменной ISCC."
}

Write-Host '==> PyInstaller' -ForegroundColor Cyan
& $Python -m PyInstaller --noconfirm --clean `
    --distpath (Join-Path $Root 'dist') `
    --workpath (Join-Path $Root 'build') `
    (Join-Path $Root 'packaging\OptiPlayer.spec')
if ($LASTEXITCODE -ne 0) { throw "PyInstaller завершился с кодом $LASTEXITCODE" }

Write-Host '==> Inno Setup' -ForegroundColor Cyan
& $iscc (Join-Path $Root 'packaging\OptiPlayer.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup завершился с кодом $LASTEXITCODE" }

$setup = Get-ChildItem (Join-Path $Root 'release') -Filter 'OptiPlayer-Setup-*.exe' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host ''
Write-Host "Готово: $($setup.FullName)" -ForegroundColor Green
Write-Host ("Размер: {0:N1} МБ" -f ($setup.Length / 1MB))
