param(
    [Parameter(Mandatory=$true)][string]$AssetName,
    [Parameter(Mandatory=$true)][string]$AssetId,
    [Parameter(Mandatory=$true)][int]$Snapshot
)
$ErrorActionPreference = 'Stop'
$session = '3b56cf9d-7e81-47de-8f4a-eae6641c03d8'
$library = 'D:\code\元素库\CLI测试\Example\3_win32元素修复\element'
$script:currentSnapshot = $Snapshot
$script:tree = $null
function Invoke-Recorded([string]$step, [string[]]$arguments) {
    $label = "$AssetId-$step-$script:currentSnapshot"
    & (Join-Path $PSScriptRoot 'invoke-cli.ps1') -Label $label -CliArguments $arguments | Out-Null
    return (Get-Content -LiteralPath (Join-Path $PSScriptRoot "$label.json") -Raw | ConvertFrom-Json)
}
function Refresh-Tree {
    $refresh = Invoke-Recorded 'refresh' @('observe','win','refresh','--session',$session,'--snapshot',"$script:currentSnapshot",'--format','json')
    $script:currentSnapshot = $refresh.data.snapshot_id
    $result = Invoke-Recorded 'tree' @('observe','win','subtree','--session',$session,'--snapshot',"$script:currentSnapshot",'--max-depth','42','--max-nodes','800','--budget-ms','10000','--format','json')
    if ($result.data.truncated) { throw 'App tree truncated; no action taken.' }
    $script:tree = $result.data.root
}
function Find-Nodes($node, [string]$type, [string]$name) {
    if ($node.backend -eq 'acc' -and $node.control_type -eq $type -and $node.name -eq $name) { $node }
    foreach ($child in $node.children) { Find-Nodes $child $type $name }
}
function Click-Node($node, [string]$step) {
    $result = Invoke-Recorded $step @('win','click','--session',$session,'--snapshot',"$script:currentSnapshot",'--ref',$node.ref,'--format','json')
    if (-not $result.ok -or $result.data.status -ne 'completed') { throw "Click did not complete: $step" }
}
function Single-Node([string]$type, [string]$name) {
    $matches = @(Find-Nodes $script:tree $type $name)
    if ($matches.Count -ne 1) { throw "Expected one $type named $name, got $($matches.Count)" }
    return $matches[0]
}
$snapshotFile = Join-Path $library "snapshot\$AssetId.json"
$asset = Get-Content -LiteralPath $snapshotFile -Raw | ConvertFrom-Json
$panes = @($asset.path | Where-Object tag -eq 'Pane')
if ($panes.Count -ne 2) { throw 'Expected two Pane layers.' }
foreach ($pane in $panes) {
    $randomClass = @($pane.required | Where-Object { $_.name -eq 'class_name' -and $_.value -like 'XPathWin32Panel_*' })
    if ($randomClass.Count -ne 1) { throw 'Expected a selected random class; do not toggle blindly.' }
}
Refresh-Tree
Click-Node (Single-Node 'div' "$AssetName 删除元素 $AssetName") 'select-asset'
Refresh-Tree
# The details tab is observed separately from the library's top-level 元素 button.
$tabs = @(Find-Nodes $script:tree 'button' '元素')
if ($tabs.Count -ne 2) { throw 'Expected library and details 元素 buttons.' }
Click-Node $tabs[1] 'details-tab'
Refresh-Tree
for ($index = 0; $index -lt 2; $index++) {
    $rows = @(Find-Nodes $script:tree 'td' 'Pane')
    if ($rows.Count -ne 2) { throw 'Expected two observed Pane label cells.' }
    Click-Node $rows[$index] "select-pane-$index"
    Refresh-Tree
    $values = @(Find-Nodes $script:tree 'td' "$($panes[$index].required | Where-Object name -eq 'class_name' | Select-Object -ExpandProperty value) 为 class_name 选择全局变量")
    if ($values.Count -ne 1) { throw 'Selected layer does not show the captured random class.' }
    Click-Node (Single-Node 'button' 'class_name 启用状态') "class-off-$index"
    Refresh-Tree
}
Click-Node (Single-Node 'button' '保存') 'save'
# App saves asynchronously. Read the asset to confirm the committed result before continuing.
$deadline = [DateTime]::UtcNow.AddSeconds(5)
do {
    $updated = Get-Content -LiteralPath $snapshotFile -Raw | ConvertFrom-Json
    $remaining = @($updated.path | Where-Object tag -eq 'Pane' | ForEach-Object { $_.required } | Where-Object name -eq 'class_name')
    if ($remaining.Count -eq 0) { break }
    Start-Sleep -Milliseconds 100
} while ([DateTime]::UtcNow -lt $deadline)
if ($remaining.Count -ne 0) { throw 'Save outcome not confirmed; do not retry the save blindly.' }
$updatedPanes = @($updated.path | Where-Object tag -eq 'Pane')
if (@($updatedPanes | ForEach-Object { $_.required } | Where-Object name -eq 'uia_name').Count -ne 2) { throw 'Stable Pane names were lost.' }
[ordered]@{asset=$AssetName;id=$AssetId;random_class_required=$false;stable_pane_names_preserved=$true;snapshot=$script:currentSnapshot} | ConvertTo-Json
