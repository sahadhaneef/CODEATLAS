# Dot-source in each PowerShell session: . .\scripts\Use-CodeAtlasStorage.ps1
[CmdletBinding()]
param(
    [ValidateRange(0, 100000)] [double]$ExpectedGiB = 0,
    [ValidateRange(1, 100000)] [double]$MinimumFreeGiB = 10
)

$taskProjectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
if ($taskProjectRoot.TrimEnd('\') -ne 'D:\projects\CODEATLAS') {
    throw 'This storage policy requires the checkout at D:\projects\CODEATLAS.'
}

$taskRequiredBytes = ($ExpectedGiB + $MinimumFreeGiB) * 1GB
$taskStorageRoot = $null
foreach ($taskDriveName in @('D', 'E')) {
    $taskDrive = Get-PSDrive -Name $taskDriveName -PSProvider FileSystem -ErrorAction SilentlyContinue
    if ($taskDrive -and $null -ne $taskDrive.Free -and $taskDrive.Free -ge $taskRequiredBytes) {
        if ($taskDriveName -eq 'D') {
            $taskStorageRoot = Join-Path $taskProjectRoot '.storage'
        } else {
            $taskStorageRoot = 'E:\CodeAtlas\CODEATLAS-storage'
        }
        break
    }
}
if (-not $taskStorageRoot) {
    throw "Neither D: nor E: has the required $($ExpectedGiB + $MinimumFreeGiB) GiB free. No C: fallback is permitted."
}

# A new temporary session never reuses/deletes a prior test or interrupted download directory.
$taskRunId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N')
$taskMappings = @{
    CODEATLAS_STORAGE_ROOT = $taskStorageRoot
    TEMP = (Join-Path $taskStorageRoot "temp\$taskRunId")
    TMP = (Join-Path $taskStorageRoot "temp\$taskRunId")
    PIP_CACHE_DIR = (Join-Path $taskStorageRoot 'cache\pip')
    NPM_CONFIG_CACHE = (Join-Path $taskStorageRoot 'cache\npm')
    UV_CACHE_DIR = (Join-Path $taskStorageRoot 'cache\uv')
    RUFF_CACHE_DIR = (Join-Path $taskStorageRoot 'cache\ruff')
    MYPY_CACHE_DIR = (Join-Path $taskStorageRoot 'cache\mypy')
    PYTHONPYCACHEPREFIX = (Join-Path $taskStorageRoot 'cache\python-bytecode')
    XDG_CACHE_HOME = (Join-Path $taskStorageRoot 'cache\xdg')
    HF_HOME = (Join-Path $taskStorageRoot 'models\huggingface')
    HF_HUB_CACHE = (Join-Path $taskStorageRoot 'models\huggingface\hub')
    HF_DATASETS_CACHE = (Join-Path $taskStorageRoot 'datasets\huggingface')
    TORCH_HOME = (Join-Path $taskStorageRoot 'models\torch')
    CODEATLAS_DOWNLOAD_DIR = (Join-Path $taskStorageRoot 'downloads')
    CODEATLAS_BUILD_DIR = (Join-Path $taskStorageRoot 'build')
    CODEATLAS_LOG_DIR = (Join-Path $taskStorageRoot 'logs')
    CODEATLAS_ARTIFACT_DIR = (Join-Path $taskStorageRoot 'artifacts')
}
foreach ($taskDirectory in ($taskMappings.Values | Select-Object -Unique)) {
    try {
        New-Item -ItemType Directory -Path $taskDirectory -Force -ErrorAction Stop | Out-Null
    } catch {
        throw "Cannot create CodeAtlas storage at $taskDirectory. Required filesystem permission or capacity is unavailable; no C: fallback was attempted."
    }
}
foreach ($taskMapping in $taskMappings.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($taskMapping.Key, $taskMapping.Value, 'Process')
}

# Reuse the existing supported environment; no installs, activation, data moves or deletion.
if ($taskStorageRoot.StartsWith('D:')) {
    $env:CODEATLAS_VENV_PATH = Join-Path $taskProjectRoot '.venv312'
} else {
    $env:CODEATLAS_VENV_PATH = Join-Path $taskStorageRoot 'venvs\py312'
}
Write-Output "CodeAtlas process storage: $taskStorageRoot"
Write-Output "Existing/new Python 3.12 environment path: $env:CODEATLAS_VENV_PATH"
Write-Output 'Process scope only. Docker virtual disks, existing application data and global settings were not changed.'
