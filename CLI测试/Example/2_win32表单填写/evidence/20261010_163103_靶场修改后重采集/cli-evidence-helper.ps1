$cliPath='D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe'
function Invoke-TestCli([string]$stepName,[string[]]$cliArguments){
  $outText=@(& $cliPath @cliArguments 2> (Join-Path $evidenceRoot ($stepName+'.stderr.txt'))) -join "`n"
  $exitCode=$LASTEXITCODE
  $outText | Set-Content -LiteralPath (Join-Path $evidenceRoot ($stepName+'.json')) -Encoding utf8
  @{args=$cliArguments;exit_code=$exitCode;recorded_at=(Get-Date -Format o)} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $evidenceRoot ($stepName+'.command.json')) -Encoding utf8
  $reply=$outText|ConvertFrom-Json
  if($exitCode -ne 0){throw $outText}
  return $reply
}
function Get-TreeNodes($node){$node;foreach($child in $node.children){Get-TreeNodes $child}}
