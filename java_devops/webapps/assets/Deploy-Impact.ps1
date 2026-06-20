# =============================================================================
# Deploy-Impact.ps1
# Called by the dashboard deploy API or run directly from the assets folder
# Can also be run standalone (uses defaults from the colocated deploy-config.json)
# =============================================================================
param(
    [string]$SftpEnv = "",          # overrides config.activeSftpEnv
    [string]$TargetEnv = "",          # overrides config.defaultTarget
    [ValidateSet("package", "gitbuild")]
    [string]$DeployMode = "package",
    [string]$ConfigPath = (Join-Path $PSScriptRoot 'deploy-config.json')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# =============================================================================
# LOAD CONFIG
# =============================================================================
if (-not (Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
$Cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json

# Apply param overrides
if ($SftpEnv) { $Cfg.activeSftpEnv = $SftpEnv }
if ($TargetEnv) { $Cfg.defaultTarget = $TargetEnv }

# =============================================================================
# LOAD WINSCP
# =============================================================================
Add-Type -Path $Cfg.winscp.dllPath

# =============================================================================
# HELPERS
# =============================================================================
function Get-SftpEnv {
    param([string]$Name)
    $e = $Cfg.sftpEnvs | Where-Object { $_.name -eq $Name }
    if (-not $e) { throw "SFTP env '$Name' not found in config." }
    return $e
}

function Get-DeployTarget {
    param([string]$FileName)
    foreach ($t in $Cfg.deployTargets) {
        if ($FileName -match [regex]::Escape($t.keywordInFilename)) { return $t }
    }
    Write-Host "[WARN] No keyword matched '$FileName'. Using default: $($Cfg.defaultTarget)"
    return Get-DeployTargetByName -Name $Cfg.defaultTarget
}

function Get-DeployTargetByName {
    param([string]$Name)
    $targets = @($Cfg.deployTargets | Where-Object { $_.name -eq $Name })
    if ($targets.Count -eq 0) { throw "Deploy target '$Name' not found in config." }
    if ($targets.Count -gt 1) { throw "Multiple deploy targets named '$Name' found in config." }
    return $targets[0]
}

function New-SftpSession {
    $e = Get-SftpEnv -Name $Cfg.activeSftpEnv
    $opts = New-Object WinSCP.SessionOptions -Property @{
        Protocol                             = [WinSCP.Protocol]::Sftp
        HostName                             = $e.hostName
        UserName                             = $e.userName
        Password                             = $e.password
        GiveUpSecurityAndAcceptAnySshHostKey = [bool]$Cfg.winscp.acceptAnySshKey
    }
    $s = New-Object WinSCP.Session
    $s.ExecutablePath = $Cfg.winscp.exePath
    $s.SessionLogPath = $Cfg.winscp.logPath
    $s.Open($opts)
    return $s
}

function Clear-Dir {
    param([string]$Path)
    Write-StepLog "Clearing: $Path"
    Remove-Item -Path "$Path\*" -Recurse -Force -ErrorAction SilentlyContinue
}

function Write-StepLog {
    param([Parameter(Mandatory = $true)][string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [string]$StepName = $FilePath
    )

    Write-Host "Running $StepName"
    Write-Host "Command: $FilePath $($ArgumentList -join ' ')"
    Write-Host "Working dir: $WorkingDirectory"

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    foreach ($arg in $ArgumentList) {
        [void]$psi.ArgumentList.Add($arg)
    }
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi

    [void]$proc.Start()
    while (-not $proc.StandardOutput.EndOfStream) {
        Write-Host $proc.StandardOutput.ReadLine()
    }
    while (-not $proc.StandardError.EndOfStream) {
        Write-Host $proc.StandardError.ReadLine()
    }
    $proc.WaitForExit()

    if ($proc.ExitCode -ne 0) {
        throw "$StepName failed with exit code $($proc.ExitCode)."
    }
}

function Invoke-ArchiveExistingDeployment {
    param([string]$TargetName)

    $target = Get-DeployTargetByName -Name $TargetName
    $webRoot = $target.webRoot.TrimEnd('\')

    if (-not (Test-Path $webRoot)) {
        Write-StepLog "Archive skipped. Web root not found: $webRoot"
        return
    }

    $versionFile = Join-Path $webRoot "version.txt"
    $currentVersion = ""

    if (Test-Path $versionFile) {
        $currentVersion = (Get-Content $versionFile -Raw).Trim()
    }

    if (-not $currentVersion) {
        $currentVersion = Get-Date -Format "yyyy-MM-ddTHH-mm-ss"
        Write-StepLog "Version not found in version.txt. Using archive folder: $currentVersion"
    }

    $itemsToArchive = @()

    $directPaths = @(
        (Join-Path $webRoot "assets"),
        (Join-Path $webRoot "UI"),
        $versionFile
    )

    foreach ($path in $directPaths) {
        if (Test-Path $path) {
            $itemsToArchive += Get-Item -LiteralPath $path -Force
        }
    }

    $ckeditorItems = @(Get-ChildItem -Path $webRoot -Filter "ckeditor-*" -Force -ErrorAction SilentlyContinue)
    $htmlItems = @(Get-ChildItem -Path $webRoot -Filter "*.html" -File -Force -ErrorAction SilentlyContinue)

    $itemsToArchive += $ckeditorItems
    $itemsToArchive += $htmlItems
    $itemsToArchive = @($itemsToArchive | Sort-Object FullName -Unique)

    if ($itemsToArchive.Count -eq 0) {
        Write-StepLog "Archive skipped. No matching deployment files found in: $webRoot"
        return
    }

    $archiveDir = Join-Path $webRoot "archived\$currentVersion"
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null

    Write-StepLog "Archiving existing deployment items to: $archiveDir"
    foreach ($item in $itemsToArchive) {
        $destinationPath = Join-Path $archiveDir $item.Name
        if (Test-Path $destinationPath) {
            Remove-Item -LiteralPath $destinationPath -Recurse -Force
        }

        Move-Item -LiteralPath $item.FullName -Destination $archiveDir -Force
    }

    Write-StepLog "Archive complete."
}

function Invoke-GitBuild {
    [OutputType([string])]
    param([string]$TargetName)

    if (-not $Cfg.build) { throw "Config missing build section." }
    if (-not $Cfg.build.repoPath) { throw "Config missing build.repoPath." }
    if (-not $Cfg.build.outputDir) { throw "Config missing build.outputDir." }

    $repoPath = $Cfg.build.repoPath
    $buildPath = if ($Cfg.build.buildWorkingDir) { $Cfg.build.buildWorkingDir } else { $repoPath }
    $outputDir = $Cfg.build.outputDir

    if (-not (Test-Path $repoPath)) { throw "Build repo path not found: $repoPath" }
    if (-not (Test-Path $buildPath)) { throw "Build working dir not found: $buildPath" }

    $gitArgs = @("-C", $repoPath, "pull")
    if ($Cfg.build.branch) {
        $gitArgs = @("-C", $repoPath, "pull", "origin", $Cfg.build.branch)
    }
    Invoke-LoggedProcess -FilePath "git" -ArgumentList $gitArgs -WorkingDirectory $repoPath -StepName "git pull"

    $buildCmd = if ($Cfg.build.gulpCommand) { [string]$Cfg.build.gulpCommand } else { "gulp build" }
    Invoke-LoggedProcess -FilePath "cmd.exe" -ArgumentList @("/c", $buildCmd) -WorkingDirectory $buildPath -StepName "gulp build"

    if (-not (Test-Path $outputDir)) {
        throw "Build output dir not found after build: $outputDir"
    }

    Write-StepLog "Build output ready: $outputDir"
    return $outputDir
}

function Invoke-BulkCopy {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$DestinationDir
    )

    $srcRoot = $SourceDir.TrimEnd('\')
    $destRoot = $DestinationDir.TrimEnd('\')

    if (-not (Test-Path $srcRoot)) { throw "Source dir not found: $srcRoot" }
    if (-not (Test-Path $destRoot)) {
        New-Item -ItemType Directory -Path $destRoot -Force | Out-Null
    }

    $roboArgs = @(
        $srcRoot,
        $destRoot,
        "/E",
        "/R:2",
        "/W:1",
        "/MT:8",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP"
    )

    Write-StepLog "Copying files in bulk with robocopy"
    Write-StepLog "Source      : $srcRoot"
    Write-StepLog "Destination : $destRoot"

    & robocopy @roboArgs | ForEach-Object { Write-Host $_ }
    $exitCode = $LASTEXITCODE

    if ($exitCode -gt 7) {
        throw "robocopy failed with exit code $exitCode"
    }

    Write-StepLog "Bulk copy complete."
}

# =============================================================================
# STEP 1 -- DOWNLOAD
# =============================================================================
function Invoke-Download {
    [OutputType([string])]
    param()

    Clear-Dir -Path $Cfg.local.processDir

    $session = New-SftpSession
    try {
        Write-StepLog "Listing: $($Cfg.remote.inDir)"
        $dir = $session.ListDirectory($Cfg.remote.inDir)
        $latest = $dir.Files |
        Where-Object { -not $_.IsDirectory } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

        if (-not $latest) { throw "No files in $($Cfg.remote.inDir)" }

        $remoteLastWriteTime = [DateTime]::SpecifyKind($latest.LastWriteTime, [System.DateTimeKind]::Local)
        $remoteLastWriteTimeIso = $remoteLastWriteTime.ToString("yyyy-MM-ddTHH:mm:sszzz")
        Write-StepLog "Remote file: $($latest.Name)  [$remoteLastWriteTimeIso]"

        $opts = New-Object WinSCP.TransferOptions
        $opts.TransferMode = [WinSCP.TransferMode]::Binary

        $result = $session.GetFiles($Cfg.remote.inDir + $latest.Name, $Cfg.local.inDir, $false, $opts)
        $result.Check()

        Write-StepLog "Downloaded: $($latest.Name)"
        return [System.IO.Path]::Combine($Cfg.local.inDir, $latest.Name)
    }
    finally {
        $session.Dispose()
        Start-Sleep -Seconds $Cfg.delays.afterDownload
    }
}

# =============================================================================
# STEP 2 -- UNZIP
# =============================================================================
function Invoke-Unzip {
    param([string]$ZipPath)
    Write-StepLog "Unzipping: $ZipPath  ->  $($Cfg.local.processDir)"
    Expand-Archive -Path $ZipPath -DestinationPath $Cfg.local.processDir -Force
    Write-StepLog "Unzip complete."
    Write-StepLog "Moving zip to local backup."
    Move-Item -Path $ZipPath -Destination $Cfg.local.backupDir -Force
    Start-Sleep -Seconds $Cfg.delays.afterUnzip
}

# =============================================================================
# STEP 3 -- DEPLOY
# =============================================================================
function Invoke-Deploy {
    param([string]$SourceDir, [string]$ZipName)

    $target = Get-DeployTarget -FileName $ZipName
    $webRoot = $target.webRoot
    Write-StepLog "Deploy target: $($target.name)  ->  $webRoot"

    $version = ($ZipName -split "-" | Where-Object { $_ -match "^v\d" } | Select-Object -First 1) -replace "\.zip$"
    if (-not $version) {
        $versionFile = Join-Path $SourceDir "version.txt"
        if (Test-Path $versionFile) {
            $version = (Get-Content $versionFile -Raw).Trim()
        }
    }
    Write-StepLog "Version: $version"

    Invoke-BulkCopy -SourceDir $SourceDir -DestinationDir $webRoot

    Write-StepLog "Deployment complete -> $webRoot"
}

# =============================================================================
# STEP 4 -- REMOTE BACKUP
# =============================================================================
function Invoke-RemoteBackup {
    param([string]$ZipName)
    Write-StepLog "Moving remote file to backup: $ZipName"
    $session = New-SftpSession
    try {
        $session.MoveFile(
            $Cfg.remote.inDir + $ZipName,
            $Cfg.remote.backupDir + $ZipName
        )
    }
    finally {
        $session.Dispose()
        Write-StepLog "Remote backup complete."
    }
}

# =============================================================================
# MAIN
# =============================================================================
try {
    Write-Host "========== IMPACT Deploy =========="
    Write-Host "Config   : $ConfigPath"
    Write-Host "Mode     : $DeployMode"
    Write-Host "SFTP Env : $($Cfg.activeSftpEnv)"
    Write-Host "Target   : $($Cfg.defaultTarget)"
    Write-Host "==================================="

    if ($DeployMode -eq "gitbuild") {
        Invoke-ArchiveExistingDeployment -TargetName $Cfg.defaultTarget
        $buildOutput = Invoke-GitBuild -TargetName $Cfg.defaultTarget
        $syntheticZipName = "gitbuild-$($Cfg.defaultTarget)-manual.zip"
        Invoke-Deploy -SourceDir $buildOutput -ZipName $syntheticZipName
    }
    else {
        $localZip = Invoke-Download
        $zipName = [System.IO.Path]::GetFileName($localZip)

        Invoke-Unzip   -ZipPath    $localZip
        Invoke-ArchiveExistingDeployment -TargetName $Cfg.defaultTarget
        Invoke-Deploy  -SourceDir  $Cfg.local.processDir -ZipName $zipName
        Invoke-RemoteBackup        -ZipName $zipName
    }

    Write-Host "========== Done =========="
    exit 0
}
catch {
    Write-Error "FATAL: $($_.Exception.Message)"
    exit 1
}
