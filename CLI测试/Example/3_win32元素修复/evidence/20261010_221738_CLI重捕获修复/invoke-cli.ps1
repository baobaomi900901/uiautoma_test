param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][string[]]$CliArguments
)
$ErrorActionPreference = 'Stop'
$cliPath = 'D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe'
$outFile = Join-Path $PSScriptRoot ($Label + '.json')
$errFile = Join-Path $PSScriptRoot ($Label + '.stderr.txt')
& $cliPath @CliArguments 1> $outFile 2> $errFile
$exitCode = $LASTEXITCODE
[ordered]@{
    cli_path = $cliPath
    args = $CliArguments
    working_directory = (Get-Location).Path
    exit_code = $exitCode
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot ($Label + '.command.json')) -Encoding utf8
Get-Content -LiteralPath $outFile -Raw
if ($exitCode -ne 0) {
    Get-Content -LiteralPath $errFile -Raw
    throw "CLI command exited with $exitCode; evidence saved as $Label"
}
