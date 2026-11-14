param([string]$Application = 'dist\Klippy\Klippy.exe', [int]$MemoryGiB = 16)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($MemoryGiB -lt 4 -or $MemoryGiB -gt 64) { throw 'Use a process-tree budget between 4 and 64 GiB' }
# Microsoft JOBOBJECT_EXTENDED_LIMIT_INFORMATION. Children inherit this job.
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class KlippyJob {
  [StructLayout(LayoutKind.Sequential)] public struct Limits {
    public long ProcessTime, JobTime; public uint Flags; public UIntPtr MinWs, MaxWs;
    public uint ActiveLimit; public UIntPtr Affinity; public uint Priority, Scheduling;
  }
  [StructLayout(LayoutKind.Sequential)] public struct Io {
    public ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes;
  }
  [StructLayout(LayoutKind.Sequential)] public struct Extended {
    public Limits Basic; public Io Counters; public UIntPtr ProcessMemory, JobMemory, PeakProcess, PeakJob;
  }
  [StructLayout(LayoutKind.Sequential)] public struct Accounting {
    public long User, Kernel, PeriodUser, PeriodKernel;
    public uint PageFaults, TotalProcesses, ActiveProcesses, Terminated;
  }
  [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr CreateJobObject(IntPtr attrs, string name);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool SetInformationJobObject(IntPtr job, int type, ref Extended info, uint length);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
  [DllImport("kernel32.dll", SetLastError=true, EntryPoint="QueryInformationJobObject")] public static extern bool QueryExtended(IntPtr job, int type, ref Extended info, uint length, IntPtr returned);
  [DllImport("kernel32.dll", SetLastError=true, EntryPoint="QueryInformationJobObject")] public static extern bool QueryAccounting(IntPtr job, int type, ref Accounting info, uint length, IntPtr returned);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr handle);
}
'@
function Assert-Native([bool]$Success) {
    if (-not $Success) { throw [ComponentModel.Win32Exception]::new([Runtime.InteropServices.Marshal]::GetLastWin32Error()) }
}
$taskJob = [KlippyJob]::CreateJobObject([IntPtr]::Zero, $null)
if ($taskJob -eq [IntPtr]::Zero) { throw 'Cannot create memory-budget job' }
$taskLimits = [KlippyJob+Extended]::new()
$taskLimits.Basic.Flags = 0x2200 # JOB_MEMORY | KILL_ON_JOB_CLOSE; no breakaway.
$taskLimits.JobMemory = [UIntPtr]::new([ulong]$MemoryGiB * 1GB)
$taskLimitSize = [Runtime.InteropServices.Marshal]::SizeOf($taskLimits)
$taskAccounting = [KlippyJob+Accounting]::new()
$taskAccountingSize = [Runtime.InteropServices.Marshal]::SizeOf($taskAccounting)
$taskOutput = Join-Path $PWD 'local\performance-voice.json'
$taskStarted = [Diagnostics.Stopwatch]::StartNew()
$taskPeakProcesses = 0
try {
    Assert-Native ([KlippyJob]::SetInformationJobObject($taskJob, 9, [ref]$taskLimits, $taskLimitSize))
    $taskProcess = Start-Process -FilePath (Join-Path $PWD $Application) -WindowStyle Hidden -PassThru -ArgumentList @(
        '--preview-self-test','--smoke-report',('"' + $taskOutput + '"'))
    Assert-Native ([KlippyJob]::AssignProcessToJobObject($taskJob, $taskProcess.Handle))
    do {
        Assert-Native ([KlippyJob]::QueryAccounting($taskJob, 1, [ref]$taskAccounting, $taskAccountingSize, [IntPtr]::Zero))
        $taskPeakProcesses = [Math]::Max($taskPeakProcesses, $taskAccounting.ActiveProcesses)
        if ($taskStarted.Elapsed.TotalSeconds -gt 300) { throw 'Performance probe timed out' }
    } while (-not $taskProcess.WaitForExit(500))
    Assert-Native ([KlippyJob]::QueryExtended($taskJob, 9, [ref]$taskLimits, $taskLimitSize, [IntPtr]::Zero))
    Assert-Native ([KlippyJob]::QueryAccounting($taskJob, 1, [ref]$taskAccounting, $taskAccountingSize, [IntPtr]::Zero))
    $taskVoice = Get-Content -LiteralPath $taskOutput -Raw | ConvertFrom-Json
    $taskPassed = $taskProcess.ExitCode -eq 0 -and $taskVoice.engineering_preview_passed -and $taskPeakProcesses -ge 2
    @{
        passed=$taskPassed; scope='Engineering query/wake-followup preview under process-tree commit budget; full acoustic gates separate; not a 16 GB Windows VM';
        memory_budget_gib=$MemoryGiB; peak_job_commit_bytes=$taskLimits.PeakJob.ToUInt64();
        peak_active_processes=$taskPeakProcesses; wall_seconds=[Math]::Round($taskStarted.Elapsed.TotalSeconds,3);
        cpu_seconds=[Math]::Round(($taskAccounting.User + $taskAccounting.Kernel)/10000000.0,3);
        host_ram_bytes=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;
        cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1).Name;
        os=[Environment]::OSVersion.VersionString;
        limitations=@('Total VM RAM/cache is not controlled by the process-tree commit budget','No human microphone accuracy','No real printer connections')
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath 'local\performance-budget.json' -Encoding utf8
    if (-not $taskPassed) { throw 'Voice integration or child-process accounting failed under budget' }
} finally {
    [KlippyJob]::CloseHandle($taskJob) | Out-Null
}
