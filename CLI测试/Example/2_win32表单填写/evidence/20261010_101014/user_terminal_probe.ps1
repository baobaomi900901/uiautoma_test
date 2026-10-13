$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$evidenceRoot = 'D:\code\元素库\CLI测试\Example\2_win32表单填写\evidence\20261010_101014'
Set-Location -LiteralPath 'D:\code\元素库\CLI测试\Example\2_win32表单填写'
& "D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe" --help | Tee-Object -FilePath (Join-Path $evidenceRoot 'new-terminal-help.stdout.txt')
$helpExit = $LASTEXITCODE
& "D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe" status | Tee-Object -FilePath (Join-Path $evidenceRoot 'new-terminal-status.stdout.txt')
$statusExit = $LASTEXITCODE
[ordered]@{ powershell_pid = $PID; cli_path = 'D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe'; help_exit_code = $helpExit; status_exit_code = $statusExit; finished_at = [DateTimeOffset]::Now.ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'new-terminal-result.json') -Encoding utf8
