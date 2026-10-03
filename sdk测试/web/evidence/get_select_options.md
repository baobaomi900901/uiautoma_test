# `uiautoma.web.WebElement.get_select_options()` 验证证据

## 2026-10-03 iframe / Shadow 表单复验

- **结果**：`VERIFIED`（标准原生 `<select>`）。连续 3 次完整运行，每轮 `14/16 PASS`、`2 KNOWN`、`0 FAIL`、`0 BLOCKED`、退出码 `0`；每轮清理 `PASS`。两个 `KNOWN` 是 Ant 自定义单选和多选控件的能力边界。
- **源码快照与环境**：只读产品 worktree `D:\code\desktop`，commit `f63c5cfc27a3ff8c4f3a86acc665bcb601d1a0ac`；dev Runtime、Chrome、<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>；连接 `D:\code\元素库\260902_web元素` 的临时副本。以下结论只对应此快照与环境，产品源码未修改。
- **合同与实现链**：`get_select_options(self) -> list[dict[str, Any]]`，无额外参数。`WebElement.get_select_options` → `RawWebElement.get_select_options` → `web.get_select_options` → `ActionService.web_get_select_options` → Page Engine `get_select_options`。返回项按 DOM 顺序含 `name`（option 文本）、`value`（提交值）、`selected`（布尔）；保留重复项，无选项时返回 `[]`。非原生 `SELECT` 抛 `ActionError`，trace `element_options_not_readable`；额外位置参数抛 `TypeError`；库连接关闭后抛 `StalePackageError`。
- **元素与独立确证**：原生单选 `web靶场_表单测试_原生_select单选` 对应 5 个 option（占位项、北京、上海、广州、深圳）；原生多选 `web靶场_表单测试_原生_select多选_options_面板` 对应 4 个城市 option。每次读取前后独立读取页面 DOM 的 `option.text/value/selected`，逐项核对字段、顺序和状态，并确认读取没有改变 DOM。
- **真实场景**：初始单选占位项 `selected=True`、多选全未选；选择后单选上海 `selected=True`，多选北京和广州 `selected=True`；连续读取两次结果相同。点击页面重置后恢复初始状态。临时添加重复的北京 option 时 SDK 仍返回两项北京；临时清空 option 时返回 `[]`，随后恢复原 DOM 并复核。
- **Ant 边界**：`web靶场_表单测试_ant_select单选` 实际为 `INPUT`，`web靶场_表单测试_ant_select多选` 实际为 `DIV`；两者调用均抛 `ActionError` / `element_options_not_readable`，前后 DOM 不变。该 API 读取标准 HTML `<select>` 的 option，不读取 Ant 自定义面板的候选项。
- **收尾与范围**：三轮均恢复动态 ID 开关，关闭本次标签和库连接，删除临时副本；外部标签变动 `+0/-0`，标签总数 `4→4`。未覆盖 Edge、CEF、动态 ID 开启时的定位或其他自定义下拉框。
- **复测与报告**：在 `D:\code\元素库\sdk测试` 运行 `uv run --no-cache .\web\test_web_element_get_select_options.py --json --report-file .\web\evidence\artifacts\get_select_options_20261003_run1.txt`；[第 1 轮](artifacts/get_select_options_20261003_run1.txt)、[第 2 轮](artifacts/get_select_options_20261003_run2.txt)、[第 3 轮](artifacts/get_select_options_20261003_run3.txt)。退出码 `0` 允许 `KNOWN`；`1` 表示失败，`2` 表示环境阻塞。

下列 2026-08-09 的 `form-controls`、`select_html`、`list[tuple[Any, ...]]` 和 `UnsupportedActionError` 结论属于旧源码快照，不能套用当前版本；旧脚本归档为 [`test_web_element_get_select_options_legacy_20260809.py`](../test_web_element_get_select_options_legacy_20260809.py)。

```yaml
api: "uiautoma.web.WebElement.get_select_options"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_get_select_options_after_reset_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defect: "web.element.get_select_options unsupported"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_select_options 的公开签名与当前 SDK 未实现行为"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_select_options"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
  verified_contract:
    signature: "get_select_options() -> list[tuple[Any, ...]]"
    parameter_order: ["self"]
    defaults: {}
    note: "用户合同 List[Tuple]（选项文本，选项值，被选中状态）；当前实现直接 unsupported"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web.element.get_select_options"
      message: "当前版本暂不支持"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_get_select_options.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "8f7c3a13c8891508e8a3fa43ece8d816d9f4edb4"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "58086849245009d8662dddc5b6a068d019ed74a3"
  select_element_name: "select_html"
  reset_element_name: "重置_html"
  select_characteristics: "//select[@id='form-controls-native-city']"
source_commit_at_doc_time: "c1dbcac3eedd3405f4cd4ff99a3efc13fa9a1111"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_select_options.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_select_options.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_get_select_options.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()`。
- 目标 API：对 `select_html` 直接调用 `get_select_options()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链（当前缺口）

```text
uiautoma.web.WebElement.get_select_options
  -> raise UnsupportedActionError("web.element.get_select_options")
```

公开签名存在，但 SDK facade 尚未接到 Runtime / Page Engine 选项读取通道。同文件
`get_all_select_items` / `get_selected_item` 亦为显式 unsupported。

## 覆盖矩阵

| 场景 | 结果 | 说明 |
| --- | --- | --- |
| 公开签名 | `PASS` | 无参；返回注解为 `list[tuple[Any, ...]]` |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `select_html` / `重置_html` |
| 重置后读取选项 | `FAIL` | `UnsupportedActionError`（`web.element.get_select_options`） |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 靶场：`http://localhost:7199/form-controls`
- 元素：`select_html`（`//select[@id='form-controls-native-city']`）
- `get_select_options_after_reset`：`UnsupportedActionError` / `web.element.get_select_options`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- 选中后选项列表变化（接通后再验）。
- `select_html_多选` / Ant Design / 组件库下拉框。
- Edge、CEF、Auto。

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/19
