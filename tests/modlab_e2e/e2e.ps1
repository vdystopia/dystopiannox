# Runs the installed opennox-hd.exe in OpenNox's e2e mode (scripted input from $Yaml) on the private data dir $Shadow
# (tests/modlab_e2e/lab.py play). stderr (the game's log) -> $Out. Kills the game after $Max seconds and checks the game
# folder's nox.cfg is unchanged.
param([string]$Yaml, [int]$Max = 200, [string]$Out, [string]$Shadow, [string]$Config)
$nox = 'C:\GOG Games\Nox'
$env:NOX_E2E = $Yaml
$env:NOX_DEV = 'true'   # the "load" cheat in autoexec.rul
$cfgHash = (Get-FileHash "$nox\nox.cfg").Hash
$proc = $null
try {
  $proc = Start-Process -FilePath "$nox\opennox-hd.exe" -ArgumentList @('-swindow', '-data', "`"$Shadow`"", '-config', "`"$Config`"",
      '-port', '18659', '-pprof', '127.0.0.1:6079') -WorkingDirectory $Shadow -PassThru `
      -RedirectStandardOutput "$Out.stdout" -RedirectStandardError $Out
  $t = 0
  while ($t -lt $Max) {
    Start-Sleep -Seconds 1; $t++; $proc.Refresh()
    if ($proc.HasExited) { "exited at ${t}s code $($proc.ExitCode)"; break }
  }
  if (-not $proc.HasExited) { "stopped after ${Max}s" }
} finally {
  if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force; Start-Sleep -Seconds 2 }
  Remove-Item Env:\NOX_E2E -ErrorAction SilentlyContinue
  Remove-Item Env:\NOX_DEV -ErrorAction SilentlyContinue
  "nox.cfg unchanged: $((Get-FileHash "$nox\nox.cfg").Hash -eq $cfgHash)"
}
