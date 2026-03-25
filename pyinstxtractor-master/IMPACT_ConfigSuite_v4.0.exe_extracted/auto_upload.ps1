param(
    [string]$client,
    [string]$filePath
)

# Load WinSCP .NET assembly
Add-Type -Path "C:\Program Files (x86)\WinSCP\WinSCPnet.dll"

# Get Config from JSON file in same directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$configPath = Join-Path $scriptPath "sftp_config.json"

if (-not (Test-Path $configPath)) {
    Write-Host "Error: sftp_config.json not found at $configPath"
    exit 1
}

$jsonContent = Get-Content -Raw -Path $configPath
$x = $jsonContent | ConvertFrom-Json
$current = $x.Stuffs | Where-Object { $_.Name -eq "UAT" }

if ($null -eq $current) {
    Write-Host "Error: UAT configuration not found in JSON."
    exit 1
}

# Session options
$sessionOptions = New-Object WinSCP.SessionOptions -Property @{
    Protocol                             = [WinSCP.Protocol]::Sftp
    HostName                             = $current.hostname
    UserName                             = $current.username
    Password                             = $current.password
    GiveUpSecurityAndAcceptAnySshHostKey = $true
}

$session = New-Object WinSCP.Session
$session.ExecutablePath = "C:\Program Files (x86)\WinSCP\WinSCP.exe"

# Remote paths
$uploadPaths = @(
    "/home/SFTP_DATA/impact-uat/IMPACT_Config/{0}_IMPACT/Cover/" -f $client
)

function Upload-ToSFTP {
    param(
        [string]$localFile,
        [string[]]$remotePaths
    )
    try {
        $session.Open($sessionOptions)
        if (Test-Path $localFile) {
            foreach ($remotePath in $remotePaths) {
                # Upload only PNG files
                $sourcePath = Join-Path $localFile "*.png"
                
                # Check if file/folder exists remotely, create if needed? 
                # WinSCP PutFiles creates structure if needed usually, but let's be safe
                
                $transferResult = $session.PutFiles($sourcePath, $remotePath)
                $transferResult.Check()
                foreach ($transfer in $transferResult.Transfers) {
                    Write-Host ("Upload of {0} succeeded to {1}" -f $transfer.FileName, $remotePath)
                }
            }
        } else {
            Write-Host "FILE NOT FOUND: $localFile"
        }
    }
    catch {
        Write-Host "Error: $($_.Exception.Message)"
    }
    finally {
        $session.Dispose()
    }
}

Upload-ToSFTP -localFile $filePath -remotePaths $uploadPaths