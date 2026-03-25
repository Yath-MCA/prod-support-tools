# auto_sftp_upload.ps1
param(
    [string]$client,
    [string]$uploadPath,
    [string]$zipPath,
    [string]$domain = "UAT"
)

# Load WinSCP .NET assembly
Add-Type -Path "C:\Program Files (x86)\WinSCP\WinSCPnet.dll"

# Get Employee ID for logs
$emp_id = (whoami).Split("\")[1]

# Load credentials from config.json
$config = Get-Content (Join-Path $PSScriptRoot "config.json") | ConvertFrom-Json

# Get options for the selected domain
$current = $config.domains.$domain
if ($null -eq $current) {
    Write-Error "Domain '$domain' not found in config.json"
    exit 1
}

# Setup session options
$sessionOptions = New-Object WinSCP.SessionOptions -Property @{
    Protocol                             = [WinSCP.Protocol]::Sftp
    HostName                             = $current.sftp_host
    UserName                             = $config.sftp_credentials.username
    Password                             = $config.sftp_credentials.password
    GiveUpSecurityAndAcceptAnySshHostKey = $true
}

$session = New-Object WinSCP.Session
$session.ExecutablePath = "C:\Program Files (x86)\WinSCP\WinSCP.exe"
$session.SessionLogPath = "C:\Users\$emp_id\Documents\winscp_xml_config.log"

function uploadSFTP {
    try {
        Write-Host "========== transfer starting =========="
        Write-Host "Connecting to $($current.sftp_host) [$domain]"
        
        # Get latest file
        if (-not (Test-Path $zipPath)) {
            Write-Error "Zip path not found: $zipPath"
            return
        }

        $latest = Get-ChildItem -Path $zipPath -Filter "*.zip" | Sort-Object LastAccessTime -Descending | Select-Object -First 1
        
        if ($null -ne $latest) {
            Write-Output "======= FILE FOUND: $($latest.Name) ======"
            $session.Open($sessionOptions)
            
            Write-Host "Uploading to $uploadPath"
            $transferResult = $session.PutFiles($latest.FullName, $uploadPath)
            $transferResult.Check()
            
            foreach ($transfer in $transferResult.Transfers) {
                Write-Host ("Upload of {0} succeeded" -f $transfer.FileName)
            }
        }
        else {
            Write-Output "FILE NOT FOUND in $zipPath"
        }
    }
    finally {
        $session.Dispose()
        Write-Host "========== transfer end =========="
    }
}

uploadSFTP
