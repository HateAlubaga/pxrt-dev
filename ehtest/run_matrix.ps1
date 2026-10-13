# Runs every ehtest variant/scenario and prints the process exit code in hex.
# 0xC0000029 = STATUS_INVALID_UNWIND_TARGET (the 2026-10-10 in-game crash).
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
foreach ($v in 'b_sc', 'b_a') {
  foreach ($x in 'old', 'new') {
    foreach ($s in 1, 2, 3) {
      $exe = Join-Path $here "$v\Release\ehtest_$x.exe"
      $out = & $exe $s 2>&1 | Out-String
      $code = '0x{0:X8}' -f $LASTEXITCODE
      $tag = ($out -split "`n" | Where-Object { $_ -match 'RESULT|UNHANDLED|hook caught' }) -join ' | '
      "{0,-5} {1,-4} s{2}  exit={3}  {4}" -f $v, $x, $s, $code, $tag.Trim()
    }
  }
}
