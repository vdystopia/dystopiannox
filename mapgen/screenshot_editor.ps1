# Opens a map in the built editor and saves a screenshot of the editor window, for visual QA.
# The editor is left open.
param(
    [Parameter(Mandatory)] [string]$MapPath,
    [Parameter(Mandatory)] [string]$OutPng,
    [int]$WaitSeconds = 12
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Win {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@
$exe = Join-Path (Split-Path $PSScriptRoot -Parent) 'MapEditor\bin\Release\MapEditor.exe'
$p = Start-Process -FilePath $exe -ArgumentList "`"$MapPath`"" -PassThru
$deadline = (Get-Date).AddSeconds(60)
do { Start-Sleep -Milliseconds 500; $p.Refresh() } until ($p.HasExited -or ($p.MainWindowHandle -ne 0 -and $p.MainWindowTitle -notmatch '^$|Splash') -or (Get-Date) -gt $deadline)
if ($p.HasExited) { throw "editor exited with code $($p.ExitCode)" }
Start-Sleep -Seconds $WaitSeconds            # let the map load and render
$p.Refresh()
$h = $p.MainWindowHandle
[void][Win]::ShowWindow($h, 3)               # maximize
[void][Win]::SetForegroundWindow($h)
Start-Sleep -Seconds 3
$r = New-Object Win+RECT
[void][Win]::GetWindowRect($h, [ref]$r)
$bmp = New-Object Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
$g = [Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[void][Win]::PrintWindow($h, $hdc, 2)        # PW_RENDERFULLCONTENT
$g.ReleaseHdc($hdc); $g.Dispose()
$bmp.Save($OutPng, [Drawing.Imaging.ImageFormat]::Png)
"title: $($p.MainWindowTitle)"
"saved: $OutPng ($($bmp.Width)x$($bmp.Height))"
