# `uiautoma.web.WebElement.select()` 验证证据

## 2026-09-24 iframe / Shadow 表单复验

- **结果**：`VERIFIED`（标准原生 `<select>`）。完整脚本连续 3 次均为 `13/14 PASS`、`1 KNOWN`、`0 FAIL`、`0 BLOCKED`，退出码 `0`；`cleanup` 每轮 `PASS`。`KNOWN` 是 Ant 自定义 combobox 的明确能力边界，不表示 Ant 选项被成功选中。
- **源码快照与环境**：只读产品 worktree `D:\code\desktop`，commit `e08eadd0d6d921ea11579e4acfb894c1c4cee038`；本次 dev Runtime、Chrome、<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>，元素库 `D:\code\元素库\260902_web元素` 的临时副本。以下结论仅对应此快照与环境。
- **合同**：`select(self, item: str, *, mode: str='fuzzy', delay_after: float=1) -> None`；`item` 必填，`mode` 与 `delay_after` 仅可按名称传入。当前源码接受 `fuzzy`、`exact`、`regex`，不接受旧记录里的 `value`；无效 `mode` 和无效正则抛 `InvalidParamsError`。库连接关闭后再调用抛 `StalePackageError`。
- **实现链**：`WebElement.select` → `RawWebElement.select` → `web.action.select` → `ActionService.web_select_element` → Page Engine `selectOption`。引擎先要求目标标签为 `<select>`，否则返回 `element_not_selectable`。
- **真实场景与独立确证**：原生库元素 `web靶场_表单测试_原生_select单选` 唯一对应 `select#form-controls-native-city`。从靶场 DOM 确认选项为“请选择城市”/空值、北京/`beijing`、上海/`shanghai`、广州/`guangzhou`、深圳/`shenzhen`。调用 `select()` 后独立读取 DOM `value`，再点击页面“提交”并读取新产生的 `native-result` JSON 的 `city`，不以方法返回值代替状态证据。默认模糊匹配“京”得到 `beijing`（调用约 1 秒）；精确“上海”得到 `shanghai`；正则 `^广` 得到 `guangzhou`；不存在的选项保留原来选中的北京；精确小写 `beijing` 不匹配中文选项。每例重置后复核空值；无选择时提交 `city=''`，不是 `null`。
- **Ant 边界**：库元素 `web靶场_表单测试_ant_select单选` 唯一对应 `input#form-controls-ant-city[role=combobox]`，不是 HTML `<select>`。`select('北京', mode='exact')` 抛 `ActionError`，trace `element_not_selectable`，前后显示和值不变。错误文案提示对非标准下拉框先点击控件、再点击目标选项；该点击流程属于其他 API，本轮没有把它算作 `select()` 成功。
- **判据修订**：初次脚本曾在提交前直接改写 React 结果区文本，导致五个用例读不到新 JSON；去掉该探针后页面正常提交。独立探针证实页面“重置”会清空旧结果区，正式脚本只等待结果区从重置后的文本变为新的 JSON。另将未选择时的 `city` 期望从错误的 `null` 改为靶场实测的 `''`。这些都是测试判据修正，不计为产品缺陷。下方 2026-08-09 的 `mode='value'` 结论属于旧源码快照，不能套用当前合同。
- **收尾与排除**：每轮关闭本次标签和元素库连接、删除临时库副本、复核 Chrome 标签数与进入前一致，动态 ID 开关恢复原状态。未覆盖 Edge、CEF、Ant 自定义选项的点击流程、多选 `select_multiple()`、动态 ID 开启或超大选项列表；不读写系统剪贴板。
- **复测**：从 `D:\code\元素库\sdk测试` 运行 `uv run .\web\test_web_element_select.py --json --report-file .\web\evidence\artifacts\select_20260924_run1.txt`。原始报告：[第 1 轮](artifacts/select_20260924_run1.txt)、[第 2 轮](artifacts/select_20260924_run2.txt)、[第 3 轮](artifacts/select_20260924_run3.txt)。退出码 `0` 为全部通过（允许 `KNOWN`），`1` 为失败，`2` 为环境阻塞。

下列 2026-08-09 的 `form-controls` 与 `select_html` 记录保留为历史证据；对应的本地旧脚本已归档为 [`test_web_element_select_legacy_20260809.py`](../test_web_element_select_legacy_20260809.py)。

```yaml
api: "uiautoma.web.WebElement.select"
lifecycle: "VERIFIED"
verification_summary:
  chrome_select_fuzzy_shanghai_ok: "PASS"
  chrome_select_exact_beijing_ok: "PASS"
  chrome_select_value_shanghai_ok: "PASS"
  chrome_select_fuzzy_delay_after_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.select 的最小 SDK、Runtime 与 DOM select 实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.select", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.select"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_select"]
      fingerprint: "23a56351fce260eaccdfa8a4465519e0ffd85a73"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_select_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "select(item: str, *, mode: str = 'fuzzy', delay_after: float = 1) -> None"
    parameter_order: ["self", "item", "mode", "delay_after"]
    defaults:
      mode: "fuzzy"
      delay_after: 1
    item_required: true
    mode_values: ["fuzzy", "exact", "value"]
    note: "mode/delay_after 为仅关键字参数；不支持 regex"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_select.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "ec5ed92375e34da735d77229c5d2398bd5d7c3fa"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "ca318ee0b1f358e39b7b061de278aa9200a562ec"
  select_element_name: "select_html"
  submit_element_name: "提交_html"
  reset_element_name: "重置_html"
source_commit_at_doc_time: "39dfab9ce9b6b18ccefdcfdf3e632584d21919ef"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_select.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`；`finally` 中删除该副本。选择步骤日志输出到 stderr。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` / `提交_html` 的 `click()`。
- 目标 API：只对 `select_html` 直接调用 `WebElement.select(...)`。
- 验收 API：`get_value()` 与剪贴板表单 JSON 的 `city`（非目标合同）。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.select
  -> RawWebElement.select
  -> AutomationDispatcher._handle_web_action_select
  -> ActionService.web_select_element
  -> page_engine selectOption
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `item` 必填；`mode`/`delay_after` 仅关键字与默认值 |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与三库项可用 |
| 页面与库连接 | `PASS` | 绑定成功 |
| fuzzy `上海` | `PASS` | `value`/`city`=`shanghai` |
| exact `北京` | `PASS` | `value`/`city`=`beijing` |
| value `shanghai` | `PASS` | `value`/`city`=`shanghai` |
| fuzzy `delay_after=1` | `PASS` | 耗时 ≥900ms 且选中正确 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`http://localhost:7199/form-controls`
- `select_fuzzy_shanghai`：约 `278.2ms`
- `select_exact_beijing`：约 `282.3ms`
- `select_value_shanghai`：约 `291.2ms`
- `select_fuzzy_delay_after`：约 `1026.7ms`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- `mode="regex"`（公开合同抛 `InvalidParamsError`）。
- Ant Design / 组件库下拉框。
- Edge、CEF、Auto。
