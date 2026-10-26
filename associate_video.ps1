param(
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}
$Root = $PSScriptRoot
if (-not $Root) {
    $Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
}
$Python = Join-Path $Root '.venv\Scripts\pythonw.exe'
$App = Join-Path $Root 'app.py'
$Icon = Join-Path $Root 'assets\optiplayer.ico'
$ProgId = 'OptiPlayer.Video'
$AppName = 'OptiPlayer'
$Classes = 'HKCU:\Software\Classes'
$Command = '"' + $Python + '" "' + $App + '" "%1"'
$Extensions = @(
    '.mp4', '.m4v', '.mov', '.mkv', '.webm', '.avi', '.wmv',
    '.mpg', '.mpeg', '.m2ts', '.mts', '.ts', '.flv', '.3gp', '.ogv'
)

function Ensure-Key([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }
}

function Set-Default([string]$Path, [string]$Value) {
    Ensure-Key $Path
    Set-ItemProperty -Path $Path -Name '(Default)' -Value $Value
}

if ($Remove) {
    foreach ($ext in $Extensions) {
        $context = "$Classes\SystemFileAssociations\$ext\shell\$AppName"
        if (Test-Path -LiteralPath $context) {
            Remove-Item -LiteralPath $context -Recurse -Force
        }
        $openWith = "$Classes\$ext\OpenWithProgids"
        if (Test-Path -LiteralPath $openWith) {
            Remove-ItemProperty -Path $openWith -Name $ProgId -ErrorAction SilentlyContinue
        }
    }
    foreach ($path in @("$Classes\$ProgId", 'HKCU:\Software\OptiPlayer')) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }
    $registered = 'HKCU:\Software\RegisteredApplications'
    if (Test-Path -LiteralPath $registered) {
        Remove-ItemProperty -Path $registered -Name $AppName -ErrorAction SilentlyContinue
    }
    Write-Host ''
    Write-Host 'OptiPlayer удалён из списка программ для видеофайлов.' -ForegroundColor Yellow
    Write-Host 'Если он уже был выбран по умолчанию для каких-то расширений,'
    Write-Host 'назначьте другое приложение в Параметрах Windows.'
    exit 0
}

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "Не найден файл: $Python" -ForegroundColor Red
    Write-Host 'Запустите этот скрипт из папки S:\OptiPlayer.' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath $App)) {
    Write-Host "Не найден файл: $App" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath $Icon)) {
    $Icon = ''
}

# ProgID: как Windows будет запускать плеер
$progKey = "$Classes\$ProgId"
Set-Default $progKey $AppName
Set-ItemProperty -Path $progKey -Name 'FriendlyTypeName' -Value 'Видеофайл OptiPlayer'
if ($Icon) {
    $iconKey = "$progKey\DefaultIcon"
    Set-Default $iconKey "$Icon,0"
}
$commandKey = "$progKey\shell\open\command"
Set-Default $commandKey $Command

# Возможности приложения для страницы «Приложения по умолчанию»
$capabilities = 'HKCU:\Software\OptiPlayer\Capabilities'
Ensure-Key $capabilities
Set-ItemProperty -Path $capabilities -Name 'ApplicationName' -Value $AppName
Set-ItemProperty -Path $capabilities -Name 'ApplicationDescription' -Value 'Быстрый и современный видеоплеер'
if ($Icon) {
    Set-ItemProperty -Path $capabilities -Name 'ApplicationIcon' -Value "$Icon,0"
}
$fileAssociations = "$capabilities\FileAssociations"
Ensure-Key $fileAssociations

$registry = [Microsoft.Win32.Registry]::CurrentUser
foreach ($ext in $Extensions) {
    # Пункт «Открыть в OptiPlayer» в контекстном меню любого видео
    $context = "$Classes\SystemFileAssociations\$ext\shell\$AppName"
    Set-Default $context 'Открыть в OptiPlayer'
    if ($Icon) {
        Set-ItemProperty -Path $context -Name 'Icon' -Value "$Icon,0"
    }
    Set-Default "$context\command" $Command

    # Плеер в списке «Открыть с помощью»
    $openWith = $registry.CreateSubKey("Software\Classes\$ext\OpenWithProgids")
    $openWith.SetValue($ProgId, [byte[]]@(), [Microsoft.Win32.RegistryValueKind]::None)
    $openWith.Close()

    Set-ItemProperty -Path $fileAssociations -Name $ext -Value $ProgId
}

# Регистрация приложения в «Приложения по умолчанию»
$registered = 'HKCU:\Software\RegisteredApplications'
Ensure-Key $registered
Set-ItemProperty -Path $registered -Name $AppName -Value 'Software\OptiPlayer\Capabilities'

Write-Host ''
Write-Host 'Готово: OptiPlayer зарегистрирован для видеофайлов.' -ForegroundColor Green
Write-Host ''
Write-Host 'Чтобы назначить его программой по умолчанию:'
Write-Host '  1. Правый клик по видеофайлу -> Открыть с помощью -> Выбрать другое приложение'
Write-Host '     -> OptiPlayer -> «Всегда использовать для .mp4» (и для других типов).'
Write-Host ''
Write-Host '  Или: Параметры -> Приложения -> Приложения по умолчанию -> OptiPlayer'
Write-Host '       -> отметить нужные расширения.'
Write-Host ''
Write-Host 'Windows не позволяет менять ассоциации полностью без подтверждения пользователя.'
Write-Host 'Для одного файла можно просто выбрать «Открыть в OptiPlayer» в его контекстном меню.'
Write-Host ''
