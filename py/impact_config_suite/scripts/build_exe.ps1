param(
    [ValidateSet("common")]
    [string]$Target = "common",
    [switch]$Clean,
    [switch]$NoConsole,
    [switch]$LegacyRefs
)

$ErrorActionPreference = "Stop"

# Get the scripts folder path, then navigate to parent (project root)
$scriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptsDir
Set-Location $projectRoot

$metadataPath = Join-Path $projectRoot "config" "build_metadata.json"
$metadata = $null
if (Test-Path $metadataPath) {
    try {
        $metadata = Get-Content $metadataPath -Raw | ConvertFrom-Json
    } catch {
        Write-Host "Warning: unable to read build_metadata.json, using defaults."
    }
}

$targetKey = "common"
$targetMetadata = $null
if ($metadata -and $metadata.PSObject -and ($metadata.PSObject.Properties.Name -contains $targetKey)) {
    $targetMetadata = $metadata.$targetKey
}

if (Test-Path ".\\.venv\\Scripts\\python.exe") {
    $python = ".\\.venv\\Scripts\\python.exe"
} elseif (Test-Path "..\\..\\..\\.venv\\Scripts\\python.exe") {
    $python = "..\\..\\..\\.venv\\Scripts\\python.exe"
} else {
    $python = "python"
}

if ($null -ne $targetMetadata) {
    $productName = [string]$targetMetadata.product_name
    $version = [string]$targetMetadata.version
    $displayName = [string]$targetMetadata.display_name
} else {
    $productName = "IMPACT_ConfigSuite"
    $version = "5.1.0"
    $displayName = "IMPACT_ConfigSuite"
}

$appName = "${productName}_v${version}"
$entry = "main.py"

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
    "--collect-submodules", "pymongo",
    "--collect-submodules", "bson",
    "--collect-submodules", "uvicorn",
    "--add-data", "cjk_checker\\config.json;cjk_checker",
    "--add-data", "cjk_checker\\templates\\report_template.html;cjk_checker\\templates",
    "--add-data", "config\\impact_to_ceg.json;.",
    "--add-data", "config\\build_metadata.json;.",
    "--add-data", "config\\tools_navigation.json;.",
    "--add-data", "search_service\\app\\templates;search_service\\app\\templates",
    "--add-data", "search_service\\app\\static;search_service\\app\\static",
    $entry
)

if ($Clean) {
    $args = @("-m", "PyInstaller", "--clean") + $args[2..($args.Length - 1)]
    
    # Clear existing cache files
    $cacheFiles = @(
        "impact_to_ceg_cache.json",
        "pgm_processor_cache.json",
        "analyses\\analyzer_cache.json"
    )
    
    Write-Host "Clearing cache files..."
    foreach ($cacheFile in $cacheFiles) {
        $cachePath = Join-Path $projectRoot $cacheFile
        if (Test-Path $cachePath) {
            Remove-Item -Force $cachePath
            Write-Host "  [REMOVED] $cacheFile"
        }
    }
}

Write-Host "Building EXE target: $Target"
Write-Host "Using Python: $python"
Write-Host "Entry file: $entry"
Write-Host "Display name: $displayName"
Write-Host "Version: $version"
Write-Host "Legacy refs mode: $LegacyRefs"

& $python @args

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

$exePath = Join-Path $projectRoot "dist\\$appName.exe"
Write-Host "Build completed: $exePath"

$navConfig = Join-Path $projectRoot "config" "tools_navigation.json"
if (Test-Path $navConfig) {
    Copy-Item -Force $navConfig (Join-Path $projectRoot "dist" "tools_navigation.json")
    Write-Host "Navigation config copied to dist\tools_navigation.json"
}

if (Test-Path $metadataPath) {
    Copy-Item -Force $metadataPath (Join-Path $projectRoot "dist" "build_metadata.json")
    Write-Host "Build metadata copied to dist\build_metadata.json"
}

if ($LegacyRefs) {
    $legacyBuildPath = Join-Path $projectRoot "build\impact_suite"
    $legacyExe = Join-Path $projectRoot "dist\IMPACT_ConfigSuite_v3.0.exe"

    $currentBuildPath = Join-Path $projectRoot "build\$appName"

    if (Test-Path $legacyBuildPath) {
        Remove-Item -Recurse -Force $legacyBuildPath
    }
    New-Item -ItemType Directory -Path $legacyBuildPath | Out-Null

    if (Test-Path $currentBuildPath) {
        Copy-Item -Recurse -Force "$currentBuildPath\*" $legacyBuildPath
        Write-Host "Legacy build reference updated: $legacyBuildPath"
    }

    if (Test-Path $exePath) {
        Copy-Item -Force $exePath $legacyExe
        Write-Host "Legacy EXE alias updated: $legacyExe"
    }
}


