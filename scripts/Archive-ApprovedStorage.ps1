# One-time, approval-scoped archive. Never traverses links or removes directories.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-CodeAtlasStorage.ps1') -ExpectedGiB 10

$taskCandidates = @(
 'C:\Users\Sahad\AppData\Local\npm-cache\_cacache',
 'C:\Users\Sahad\AppData\Local\pip\Cache',
 'C:\Users\Sahad\AppData\Roaming\Code\CachedExtensionVSIXs',
 'C:\Users\Sahad\AppData\Roaming\Code\Cache',
 'C:\Users\Sahad\AppData\Roaming\Code\CachedData',
 'C:\Users\Sahad\AppData\Local\Google\Chrome\User Data\Default\Cache',
 'C:\Users\Sahad\AppData\Local\Google\Chrome\User Data\Default\Code Cache',
 'C:\Users\Sahad\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Cache',
 'C:\Users\Sahad\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Code Cache',
 'C:\Users\Sahad\AppData\Local\Microsoft\Edge\User Data\Default\Cache',
 'C:\Users\Sahad\AppData\Local\Microsoft\Edge\User Data\Default\Code Cache',
 'C:\Users\Sahad\AppData\Roaming\discord\Cache',
 'C:\Users\Sahad\AppData\Roaming\discord\Code Cache',
 'C:\Users\Sahad\AppData\Local\JetBrains\PyCharm2026.1\caches',
 'C:\Users\Sahad\AppData\Local\node-gyp\Cache',
 'C:\Users\Sahad\AppData\Local\upscayl-updater\installer.exe',
 'C:\Users\Sahad\Downloads',
 'C:\Users\Sahad\AppData\Local\CrashDumps'
)

function Assert-NoLinkAncestor([string]$Path) {
    $taskAncestor = $Path
    while ($taskAncestor) {
        if (Test-Path -LiteralPath $taskAncestor) {
            $taskItem = Get-Item -LiteralPath $taskAncestor -Force
            if ($taskItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Reparse point in path: $taskAncestor"
            }
        }
        $taskParent = Split-Path -Parent $taskAncestor
        if ($taskParent -eq $taskAncestor) { break }
        $taskAncestor = $taskParent
    }
}

# Hold the exact source handle without write/delete sharing until verification completes.
# Delete disposition acts on that verified handle, avoiding path-replacement races.
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Text;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class ApprovedArchiveNative {
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern SafeFileHandle CreateFileW(string name, uint access, uint share,
     IntPtr security, uint creation, uint flags, IntPtr template);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern uint GetFinalPathNameByHandleW(SafeFileHandle h, StringBuilder name, uint size, uint flags);
 [StructLayout(LayoutKind.Sequential)] public struct Info {
   public uint Attributes; public System.Runtime.InteropServices.ComTypes.FILETIME Creation;
   public System.Runtime.InteropServices.ComTypes.FILETIME Access;
   public System.Runtime.InteropServices.ComTypes.FILETIME Write;
   public uint Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
 }
 [DllImport("kernel32.dll", SetLastError=true)]
 public static extern bool GetFileInformationByHandle(SafeFileHandle h, out Info info);
 [StructLayout(LayoutKind.Sequential)] public struct Disposition { [MarshalAs(UnmanagedType.Bool)] public bool Delete; }
 [DllImport("kernel32.dll", SetLastError=true)]
 public static extern bool SetFileInformationByHandle(SafeFileHandle h, int kind, ref Disposition info, uint size);
}
'@

$taskApps = Get-Process -Name Code,chrome,brave,msedge,Discord,pycharm64,idea64,upscayl -ErrorAction SilentlyContinue
$taskRunning = @($taskApps | Select-Object -ExpandProperty ProcessName -Unique)
$taskCBefore = (Get-PSDrive C).Free
$taskDFree = (Get-PSDrive D).Free
if ($taskDFree -lt 60GB) { throw 'D: has insufficient archive and Docker recovery headroom; stopped.' }
$taskRun = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N')
$taskArchive = "D:\CodeAtlas\storage-review\$taskRun"
Assert-NoLinkAncestor $taskArchive
New-Item -ItemType Directory -Path $taskArchive | Out-Null
$taskAcl = Get-Acl -LiteralPath $taskArchive
$taskAcl.SetAccessRuleProtection($true, $false)
$taskOwner = [Security.Principal.WindowsIdentity]::GetCurrent().User
foreach ($taskSid in @($taskOwner, [Security.Principal.SecurityIdentifier]::new('S-1-5-18'), [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))) {
    $taskRule = [Security.AccessControl.FileSystemAccessRule]::new($taskSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $taskAcl.AddAccessRule($taskRule)
}
Set-Acl -LiteralPath $taskArchive -AclObject $taskAcl
$taskJournalPath = Join-Path $taskArchive 'manifest.jsonl'
$taskWriter = [IO.StreamWriter]::new($taskJournalPath, $false, [Text.UTF8Encoding]::new($false))
$taskWriter.AutoFlush = $true
$taskTotals = @{ archivedFiles=0; removedFiles=0; verifiedBytes=[long]0; skippedFiles=0 }
$taskSkipped = [Collections.Generic.List[object]]::new()
$taskQueue = [Collections.Generic.Queue[IO.FileSystemInfo]]::new()

function Record-ArchiveEvent($Record) {
    $taskWriter.WriteLine(($Record | ConvertTo-Json -Compress -Depth 5))
}
function Record-Skip([string]$Path, [string]$Reason) {
    $taskTotals.skippedFiles++
    $taskRecord = @{ source=$Path; status='skipped'; reason=$Reason }
    $taskSkipped.Add($taskRecord)
    Record-ArchiveEvent $taskRecord
}
Write-Output "Archive: $taskArchive"
try {
    foreach ($taskRoot in $taskCandidates) {
        try {
            $taskOwningApp = switch -Regex ($taskRoot) {
                '\\Roaming\\Code\\' { 'Code'; break }
                '\\Google\\Chrome\\' { 'chrome'; break }
                '\\BraveSoftware\\' { 'brave'; break }
                '\\Microsoft\\Edge\\' { 'msedge'; break }
                '\\Roaming\\discord\\' { 'Discord'; break }
                '\\JetBrains\\PyCharm' { 'pycharm64'; break }
                '\\upscayl-updater\\' { 'upscayl'; break }
                default { '' }
            }
            if ($taskOwningApp -and $taskOwningApp -in $taskRunning) {
                Record-Skip $taskRoot "owning application still running: $taskOwningApp"
                continue
            }
            Assert-NoLinkAncestor $taskRoot
            if (-not (Test-Path -LiteralPath $taskRoot)) { Record-Skip $taskRoot 'missing'; continue }
            $taskQueue.Enqueue((Get-Item -LiteralPath $taskRoot -Force))
        } catch { Record-Skip $taskRoot $_.Exception.Message }
    }
    while ($taskQueue.Count) {
        $taskFile = $taskQueue.Dequeue()
        $taskSource = $taskFile.FullName
        try {
            if ($taskFile.Attributes -band [IO.FileAttributes]::ReparsePoint) { Record-Skip $taskSource 'link excluded'; continue }
            if ($taskFile -is [IO.DirectoryInfo]) {
                Assert-NoLinkAncestor $taskSource
                if ($taskFile.Name -in @('.venv','venv','env','envs','site-packages') -or
                    (Test-Path -LiteralPath (Join-Path $taskSource 'pyvenv.cfg'))) {
                    Record-Skip $taskSource 'environment excluded'; continue
                }
                foreach ($taskChild in (Get-ChildItem -LiteralPath $taskSource -Force -ErrorAction Stop)) {
                    $taskQueue.Enqueue($taskChild)
                }
                continue
            }
            if ($taskFile.Extension -in @('.vhd','.vhdx') -or
                ($taskSource.StartsWith('C:\Users\Sahad\AppData\Local\CrashDumps\') -and $taskFile.Name -match 'docker|wsl|vmmem')) {
                Record-Skip $taskSource 'VHD/Docker evidence excluded'; continue
            }
            $taskAllowed = $false
            foreach ($taskRoot in $taskCandidates) {
                if ($taskSource.Equals($taskRoot, [StringComparison]::OrdinalIgnoreCase) -or
                    $taskSource.StartsWith($taskRoot.TrimEnd('\')+'\', [StringComparison]::OrdinalIgnoreCase)) { $taskAllowed=$true; break }
            }
            if (-not $taskAllowed) { throw 'Outside approved source scope' }
            $taskDestination = Join-Path $taskArchive ('files\' + $taskSource.Substring(3))
            $taskResolvedDestination = [IO.Path]::GetFullPath($taskDestination)
            if (-not $taskResolvedDestination.StartsWith($taskArchive+'\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escaped archive' }
            New-Item -ItemType Directory -Path (Split-Path -Parent $taskDestination) -Force | Out-Null
            $taskHandle = $null; $taskInput = $null; $taskOutput = $null; $taskMarked = $false
            try {
                $taskHandle = [ApprovedArchiveNative]::CreateFileW($taskSource, [uint32]2147549184, 1, [IntPtr]::Zero, 3, 2097152, [IntPtr]::Zero)
                if ($taskHandle.IsInvalid) { throw "locked/access denied (Win32 $([Runtime.InteropServices.Marshal]::GetLastWin32Error()))" }
                $taskInfo = [ApprovedArchiveNative+Info]::new()
                if (-not [ApprovedArchiveNative]::GetFileInformationByHandle($taskHandle,[ref]$taskInfo)) { throw 'Cannot verify source identity' }
                if (($taskInfo.Attributes -band 1024) -or $taskInfo.Links -ne 1) { throw 'Reparse point or multiple hard links excluded' }
                $taskName = [Text.StringBuilder]::new(32768)
                if (-not [ApprovedArchiveNative]::GetFinalPathNameByHandleW($taskHandle,$taskName,32768,0)) { throw 'Cannot verify final source path' }
                if (-not $taskName.ToString().Equals('\\?\'+$taskSource,[StringComparison]::OrdinalIgnoreCase)) { throw 'Final source path changed' }
                $taskLength = ([long]$taskInfo.SizeHigh -shl 32) -bor $taskInfo.SizeLow
                $taskLowTime = [BitConverter]::ToUInt32([BitConverter]::GetBytes($taskInfo.Write.dwLowDateTime),0)
                $taskWriteTime = ([long]$taskInfo.Write.dwHighDateTime -shl 32) -bor $taskLowTime
                if ($taskLength -ne $taskFile.Length -or $taskWriteTime -ne $taskFile.LastWriteTimeUtc.ToFileTimeUtc()) { throw 'Source changed since inventory' }
                $taskInput = [IO.FileStream]::new($taskHandle,[IO.FileAccess]::Read,1048576,$false)
                $taskOutput = [IO.FileStream]::new($taskDestination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None,1048576)
                $taskInput.CopyTo($taskOutput,1048576)
                $taskOutput.Flush($true); $taskOutput.Dispose(); $taskOutput=$null
                $taskInput.Position=0
                $taskHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($taskInput))
                $taskCopyHash = (Get-FileHash -LiteralPath $taskDestination -Algorithm SHA256).Hash
                if ($taskHash -cne $taskCopyHash -or (Get-Item -LiteralPath $taskDestination).Length -ne $taskLength) { throw 'Archive verification failed' }
                Record-ArchiveEvent @{ source=$taskSource; archive=$taskDestination; bytes=$taskLength; sha256=$taskHash; status='copy_verified'; lastWriteTimeUtc=$taskFile.LastWriteTimeUtc.ToString('O') }
                $taskTotals.archivedFiles++; $taskTotals.verifiedBytes += $taskLength
                $taskDisposition = [ApprovedArchiveNative+Disposition]::new(); $taskDisposition.Delete=$true
                if (-not [ApprovedArchiveNative]::SetFileInformationByHandle($taskHandle,4,[ref]$taskDisposition,4)) { throw "Verified archive retained; removal denied (Win32 $([Runtime.InteropServices.Marshal]::GetLastWin32Error()))" }
                $taskMarked=$true
            } finally {
                if ($taskOutput) { $taskOutput.Dispose() }
                if ($taskInput) { $taskInput.Dispose() }
                if ($taskHandle) { $taskHandle.Dispose() }
                if ($taskMarked) {
                    $taskTotals.removedFiles++
                    Record-ArchiveEvent @{ source=$taskSource; archive=$taskDestination; status='verified_original_removed' }
                }
            }
        } catch {
            Record-Skip $taskSource $_.Exception.Message
            if (($_.Exception.HResult -band 65535) -in @(39,112) -or $_.Exception.Message -match 'disk.*full|not enough space') {
                throw 'Archive operation stopped after storage exhaustion; no expansion of cleanup scope.'
            }
        }
        if (($taskTotals.removedFiles + $taskTotals.skippedFiles) % 250 -eq 0) {
            Write-Output "Progress: $($taskTotals.archivedFiles) verified, $($taskTotals.removedFiles) removed, $($taskTotals.skippedFiles) skipped"
        }
    }
} finally {
    $taskWriter.Dispose()
    $taskCAfter = (Get-PSDrive C).Free
    $taskSummary = @{ archive=$taskArchive; cBeforeBytes=$taskCBefore; cAfterBytes=$taskCAfter;
        netRecoveredBytes=($taskCAfter-$taskCBefore); totals=$taskTotals; skipped=@($taskSkipped.ToArray());
        restartMarginMet=($taskCAfter -ge 10GB); dockerOrWslTouched=$false }
    $taskSummary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskArchive 'summary.json') -Encoding utf8
    $taskSummary | ConvertTo-Json -Depth 6
}
