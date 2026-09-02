[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $ObsRoot,
    [Parameter(Mandatory)]
    [string] $PythonPath,
    [Parameter(Mandatory)]
    [string] $OutputDirectory,
    [string] $WindowTitle = 'BlurGo Window Capture QA'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$obsExecutable = Join-Path $ObsRoot 'bin\64bit\obs64.exe'
$targetScript = Join-Path $PSScriptRoot 'show-window-capture-target.ps1'
$obsConfigRoot = Join-Path $ObsRoot 'config\obs-studio'
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)

foreach ($requiredPath in @($obsExecutable, $PythonPath, $targetScript)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required file does not exist: $requiredPath"
    }
}

New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null
$obsStdout = Join-Path $resolvedOutput 'obs-console.log'
$obsStderr = Join-Path $resolvedOutput 'obs-console-error.log'
$targetProcess = $null
$obsProcess = $null
$obsLog = $null

try {
    $targetArguments = @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        ('"{0}"' -f $targetScript),
        '-Title',
        ('"{0}"' -f $WindowTitle)
    )
    $targetProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList $targetArguments -PassThru
    Start-Sleep -Seconds 2
    if ($targetProcess.HasExited) {
        throw 'The Window Capture QA target exited before OBS started.'
    }

    $obsProcess = Start-Process `
        -FilePath $obsExecutable `
        -WorkingDirectory (Split-Path -Parent $obsExecutable) `
        -ArgumentList @('--portable', '--multi', '--websocket_port=4455') `
        -WindowStyle Minimized `
        -RedirectStandardOutput $obsStdout `
        -RedirectStandardError $obsStderr `
        -PassThru

    $websocketReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $tcpClient = $null
        try {
            $tcpClient = [System.Net.Sockets.TcpClient]::new()
            $tcpClient.Connect('127.0.0.1', 4455)
            $tcpClient.Dispose()
            $websocketReady = $true
            break
        }
        catch {
            if ($null -ne $tcpClient) {
                $tcpClient.Dispose()
            }
            if ($obsProcess.HasExited) {
                throw "OBS exited before WebSocket became ready (exit code $($obsProcess.ExitCode))."
            }
            Start-Sleep -Seconds 1
        }
    }
    if (-not $websocketReady) {
        throw 'OBS WebSocket did not become ready within 60 seconds.'
    }

    & $PythonPath (Join-Path $PSScriptRoot 'obs-smoke.py') run `
        --output-dir $resolvedOutput `
        --width 1280 `
        --height 720 `
        --fps 60 `
        --set-video-settings `
        --stats-seconds 3 `
        --scene-switches 20 `
        --test-window-capture $WindowTitle
    if ($LASTEXITCODE -ne 0) {
        throw "OBS runtime harness failed with exit code $LASTEXITCODE."
    }

    $obsLog = Get-ChildItem -LiteralPath (Join-Path $obsConfigRoot 'logs') -File -Filter '*.txt' |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $obsLog) {
        throw 'OBS did not create a runtime log.'
    }
    if (-not (Select-String -LiteralPath $obsLog.FullName -SimpleMatch '[blurgo] loaded successfully' -Quiet)) {
        throw 'OBS did not report a successful BlurGo load.'
    }

    Write-Output 'Windows Window Capture runtime smoke passed.'
}
finally {
    foreach ($process in @($obsProcess, $targetProcess)) {
        if ($null -eq $process -or $process.HasExited) {
            continue
        }
        $null = $process.CloseMainWindow()
        if (-not $process.WaitForExit(10000)) {
            Stop-Process -Id $process.Id -Force
            $process.WaitForExit()
        }
    }
    if ($null -eq $obsLog -and (Test-Path -LiteralPath (Join-Path $obsConfigRoot 'logs'))) {
        $obsLog = Get-ChildItem -LiteralPath (Join-Path $obsConfigRoot 'logs') -File -Filter '*.txt' |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
    }
    if ($null -ne $obsLog -and (Test-Path -LiteralPath $obsLog.FullName -PathType Leaf)) {
        Copy-Item -LiteralPath $obsLog.FullName -Destination $resolvedOutput -Force
    }
}
