param(
    [ValidateSet("common", "cjk")]
    [string]$Target = "common",
    [switch]$Clean,
    [switch]$NoConsole,
    [switch]$LegacyRefs
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

if (Test-Path ".\\.venv\\Scripts\\python.exe") {
    $python = ".\\.venv\\Scripts\\python.exe"
} elseif (Test-Path "..\\..\\..\\.venv\\Scripts\\python.exe") {
    $python = "..\\..\\..\\.venv\\Scripts\\python.exe"
} else {
    $python = "python"
}

$appName = "IMPACT_ConfigSuite_v5.0"
$entry = "main.py"
if ($Target -eq "cjk") {
    $appName = "IMPACT_CJK_Integrity_Checker"
    $entry = "cjk_checker\\main.py"
}

$windowedFlag = "--windowed"
if ($NoConsole) {
    $windowedFlag = "--noconsole"
}

$args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    $windowedFlag,
    "--name", $appName,
    "--add-data", "cjk_checker\\config.json;cjk_checker",
    "--add-data", "cjk_checker\\templates\\report_template.html;cjk_checker\\templates",
    $entry
)

if ($Clean) {
    $args = @("-m", "PyInstaller", "--clean") + $args[2..($args.Length - 1)]
}

Write-Host "Building EXE target: $Target"
Write-Host "Using Python: $python"
Write-Host "Entry file: $entry"
Write-Host "Legacy refs mode: $LegacyRefs"

& $python @args

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

$exePath = Join-Path $scriptRoot "dist\\$appName.exe"
Write-Host "Build completed: $exePath"

if ($LegacyRefs) {
    $legacyBuildPath = ""
    $legacyExe = ""

    if ($Target -eq "common") {
        $legacyBuildPath = Join-Path $scriptRoot "build\impact_suite"
        $legacyExe = Join-Path $scriptRoot "dist\IMPACT_ConfigSuite_v3.0.exe"
    }
    if ($Target -eq "cjk") {
        $legacyBuildPath = Join-Path $scriptRoot "build\impact_cjk_suite"
        $legacyExe = Join-Path $scriptRoot "dist\IMPACT_CJK_Integrity_Checker_v1.0.exe"
    }

    $currentBuildPath = Join-Path $scriptRoot "build\$appName"

    if ($legacyBuildPath -ne "") {
        if (Test-Path $legacyBuildPath) {
            Remove-Item -Recurse -Force $legacyBuildPath
        }
        New-Item -ItemType Directory -Path $legacyBuildPath | Out-Null

        if (Test-Path $currentBuildPath) {
            Copy-Item -Recurse -Force "$currentBuildPath\*" $legacyBuildPath
            Write-Host "Legacy build reference updated: $legacyBuildPath"
        }
    }

    if ($legacyExe -ne "") {
        Copy-Item -Force $exePath $legacyExe
        Write-Host "Legacy EXE alias updated: $legacyExe"
    }
}
