# lanzador.ps1 - Ejecución Efímera de ATH1

$TempPath = "$env:TEMP\ATH1_Ejecucion"
$ExeUrl = "AQUI_VA_EL_LINK_DE_TU_RELEASE_ATH1.exe" # El link que generará GitHub Actions
$ExePath = "$TempPath\ATH1.exe"

# 1. Crear entorno aislado y temporal
Write-Host "Iniciando enlace con la red principal de ATH1..." -ForegroundColor Cyan
if (!(Test-Path $TempPath)) { New-Item -ItemType Directory -Force -Path $TempPath | Out-Null }

# 2. Descargar la última versión
Write-Host "Descargando módulos de IA en entorno volátil..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $ExeUrl -OutFile $ExePath

# 3. Ejecutar y esperar a que cierre
Write-Host "Desplegando ATH1..." -ForegroundColor Green
$process = Start-Process -FilePath $ExePath -NoNewWindow -PassThru
$process.WaitForExit()

# 4. Protocolo de Autodestrucción (Borrado de rastro)
Write-Host "Borrando rastro local y cerrando conexión..." -ForegroundColor Red
Remove-Item -Path $TempPath -Recurse -Force
Write-Host "Desconexión limpia completada." -ForegroundColor Green