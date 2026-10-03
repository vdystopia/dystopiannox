# Drives an already-open editor window for visual QA:
#   1. screenshots the Mini Map tab (whole map overview),
#   2. presses "Go to Center" and screenshots the Large Map view at the map centre.
# The editor's tab headers are not exposed to UI Automation, so tabs are switched with a
# mouse click on the header; the mouse cursor is restored afterwards.
param([Parameter(Mandatory)] [string]$OutDir)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Win2 {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, UIntPtr e);
    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        mouse_event(0x02, 0, 0, 0, UIntPtr.Zero);   // left down
        mouse_event(0x04, 0, 0, 0, UIntPtr.Zero);   // left up
    }
}
'@
$p = Get-Process MapEditor | Where-Object MainWindowHandle -ne 0 | Select-Object -First 1
if (-not $p) { throw 'editor is not running' }
$h = $p.MainWindowHandle
[void][Win2]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 500
$root = [Windows.Automation.AutomationElement]::FromHandle($h)

function Find($prop, $value) {
    $c = New-Object Windows.Automation.PropertyCondition($prop, $value)
    $e = $root.FindFirst([Windows.Automation.TreeScope]::Descendants, $c)
    if (-not $e) { throw "control '$value' not found" }
    $e
}
function Shot($file) {
    $r = New-Object Win2+RECT; [void][Win2]::GetWindowRect($h, [ref]$r)
    $bmp = New-Object Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
    $g = [Drawing.Graphics]::FromImage($bmp); $hdc = $g.GetHdc()
    [void][Win2]::PrintWindow($h, $hdc, 2)
    $g.ReleaseHdc($hdc); $g.Dispose()
    $path = Join-Path $OutDir $file; $bmp.Save($path, [Drawing.Imaging.ImageFormat]::Png); "saved $path"
}

$saved = New-Object Win2+POINT; [void][Win2]::GetCursorPos([ref]$saved)
try {
    # Tab header strip: between the top of the main tab control (automation id 1) and the top
    # of its "Large Map" page. Tabs: Large Map | Mini Map | Map Info | Map Image.
    $tabCtl = Find ([Windows.Automation.AutomationElement]::AutomationIdProperty) '1'
    $tabs = $tabCtl.Current.BoundingRectangle
    # only the currently selected page exists in the tree; any page gives the header bottom
    $page = [Windows.Automation.TreeWalker]::ControlViewWalker.GetFirstChild($tabCtl).Current.BoundingRectangle
    $y = [int](($tabs.Top + $page.Top) / 2)
    $hdrW = ($page.Top - $tabs.Top)                       # header height ~ tab text height
    $largeX = [int]($tabs.Left + 1.6 * $hdrW)
    $miniX = [int]($tabs.Left + 3.9 * $hdrW)
    $infoX = [int]($tabs.Left + 6.0 * $hdrW)

    [Win2]::Click($infoX, $y); Start-Sleep -Seconds 2
    Shot 'qa_mapinfo.png'
    [Win2]::Click($miniX, $y); Start-Sleep -Seconds 2
    Shot 'qa_minimap.png'
    $btn = Find ([Windows.Automation.AutomationElement]::NameProperty) 'Go to Center'
    $b = $btn.Current.BoundingRectangle
    [Win2]::Click([int]($b.Left + $b.Width / 2), [int]($b.Top + $b.Height / 2)); Start-Sleep -Seconds 2
    [Win2]::Click($largeX, $y); Start-Sleep -Seconds 3
    Shot 'qa_largemap.png'
} finally {
    [void][Win2]::SetCursorPos($saved.X, $saved.Y)
}
