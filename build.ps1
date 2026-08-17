# ==============================================================================
# SCRIPT DE COMPILACION: BIO-SONAR NEUROMORFICO (C++17 / MSVC)
# ==============================================================================
param (
    [switch]$NoServer
)

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  COMPILACION BIO-SONAR NEUROMORFICO (C++17 / MSVC)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Localizar vcvarsall.bat de Visual Studio
$vcvarsall = $null
if (Test-Path "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat") {
    $vcvarsall = "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
} elseif (Test-Path "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat") {
    $vcvarsall = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
} else {
    $search = Get-ChildItem -Path "C:\Program Files (x86)\Microsoft Visual Studio", "C:\Program Files\Microsoft Visual Studio" -Recurse -Filter "vcvarsall.bat" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($search) {
        $vcvarsall = $search.FullName
    }
}

if ($null -eq $vcvarsall) {
    Write-Host "[ERROR] No se pudo encontrar vcvarsall.bat de MSVC." -ForegroundColor Red
    exit 1
}

Write-Host "[+] Compilador localizado en: $vcvarsall" -ForegroundColor Green

# 2. Configurar directivas
$defines = ""
if ($NoServer) {
    Write-Host "[!] Compilando sin servidor (-NoServer)..." -ForegroundColor Yellow
    $defines = "/DNO_SERVER"
} else {
    Write-Host "[+] Compilando con servidor HTTP activo..." -ForegroundColor Green
}

# 3. Compilacion
$source_files = "main.cpp cerebro.cpp server.cpp synthetic_signal_adapter.cpp audio_sonar_adapter.cpp"
$compiler_cmd = "cl /EHsc /O2 /std:c++17 $source_files $defines /link ws2_32.lib /out:bio_sonar.exe"

Write-Host "[*] Compilando con MSVC..." -ForegroundColor Cyan
$cmd_args = "call `"$vcvarsall`" x64 && $compiler_cmd"

cmd.exe /c $cmd_args

if ($LASTEXITCODE -eq 0) {
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "  COMPILACION EXITOSA! Ejecutable: bio_sonar.exe" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host "[ERROR] La compilacion fallo." -ForegroundColor Red
    exit 1
}
