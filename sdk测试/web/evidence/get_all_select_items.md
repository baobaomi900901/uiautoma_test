# `uiautoma.web.WebElement.get_all_select_items()` 验证证据

## 2026-10-03 iframe / Shadow 表单复验

- **结果**：`VERIFIED`（标准原生 `<select>`）。连续 3 次完整运行，每轮 `15/17 PASS`、`2 KNOWN`、`0 FAIL`、`0 BLOCKED`、退出码 `0`；每轮清理 `PASS`。两个 `KNOWN` 是 Ant 自定义单选和多选控件的能力边界。
- **源码快照与环境**：只读产品 worktree `D:\code\desktop`，commit `f63c5cfc27a3ff8c4f3a86acc665bcb601d1a0ac`；dev Runtime、Chrome、<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>；连接 `D:\code\元素库\260902_web元素` 的临时副本。以下结论只对应此快照与环境，产品源码未修改。
- **合同与实现链**：`get_all_select_items(self) -> list[str]`，无额外参数。`WebElement.get_all_select_items` 调用 `RawWebElement.get_select_options` → `web.get_select_options` → `ActionService.web_get_select_options` → Page Engine `get_select_options`，从每个返回项取 `name` 并将 U+00A0 不换行空格替换成普通空格。非原生 `SELECT` 抛 `ActionError`，trace `element_options_not_readable`；额外位置参数抛 `TypeError`；库连接关闭后抛 `StalePackageError`。
- **元素与独立确证**：原生单选 `web靶场_表单测试_原生_select单选` 包含占位项、北京、上海、广州、深圳；原生多选 `web靶场_表单测试_原生_select多选_options_面板` 包含四个城市项。每次目标 API 读取前后独立读取页面 DOM 的 `option.text/value/selected`，将 DOM 文本按合同转换后逐项比较返回顺序，并确认读取没有改变 DOM。
- **真实场景**：初始列表分别为 5 项、4 项；选中上海或同时选中北京和广州后，仍返回全部文本。连续读取两次结果相同；页面重置后列表和选中状态回到初始值。临时添加重复北京项时两次出现北京；临时清空全部 option 时返回 `[]`；临时加入文本 `甲 乙`（中间为 U+00A0）时返回 `甲 乙`（中间为普通空格）。三种临时 DOM 变更均已恢复并复核。
- **Ant 边界**：`web靶场_表单测试_ant_select单选` 实际为 `INPUT`，`web靶场_表单测试_ant_select多选` 实际为 `DIV`；两者调用均抛 `ActionError` / `element_options_not_readable`，前后 DOM 不变。该 API 读取标准 HTML `<select>` 的 option 文本，不读取 Ant 自定义面板的候选项。
- **收尾与范围**：三轮均恢复动态 ID 开关，关闭本次标签和库连接，删除临时副本；外部标签变动 `+0/-0`，标签总数 `4→4`。未覆盖 Edge、CEF、动态 ID 开启时的定位或其他自定义下拉框。
- **复测与报告**：在 `D:\code\元素库\sdk测试` 运行 `uv run --no-cache .\web\test_web_element_get_all_select_items.py --json --report-file .\web\evidence\artifacts\get_all_select_items_20261003_run1.txt`；[第 1 轮](artifacts/get_all_select_items_20261003_run1.txt)、[第 2 轮](artifacts/get_all_select_items_20261003_run2.txt)、[第 3 轮](artifacts/get_all_select_items_20261003_run3.txt)。退出码 `0` 允许 `KNOWN`；`1` 表示失败，`2` 表示环境阻塞。

下列 2026-08-09 的 `form-controls`、`select_html` 和 `UnsupportedActionError` 结论属于旧源码快照，不能套用当前版本；旧脚本归档为 [`test_web_element_get_all_select_items_legacy_20260809.py`](../test_web_element_get_all_select_items_legacy_20260809.py)。

```yaml
api: "uiautoma.web.WebElement.get_all_select_items"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_get_all_select_items_after_reset_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defect: "web.element.get_all_select_items unsupported"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_all_select_items 的公开签名与当前 SDK 未实现行为"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_all_select_items"]
      fingerprint: "4b6e99fdafe1c3a18c71761df0b6fe4cc3356f4b"
  verified_contract:
    signature: "get_all_select_items() -> list[str]"
    parameter_order: ["self"]
    defaults: {}
    return_annotation: "list[str]"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web.element.get_all_select_items"
      message: "当前版本暂不支持"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_get_all_select_items.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "c2855b2a6c594c5b4d103ddda32ead15defbf8cd"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "a77c5aaeeee8781799d06fb12237ec84ca2755e7"
  select_element_name: "select_html"
  reset_element_name: "重置_html"
  select_characteristics: "//select[@id='form-controls-native-city']"
  expected_items_after_reset:
    - "请选择城市"
    - "北京"
    - "上海"
    - "广州"
    - "深圳"
source_commit_at_doc_time: "16f2e338b123cbac891ecf5ff7fc9867efe8cac1"
known_issue: "https://github.com/uiautoma/desktop/issues/27"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_all_select_items.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_all_select_items.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_get_all_select_items.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()`。
- 目标 API：对 `select_html` 直接调用 `get_all_select_items()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链（当前缺口）

```text
uiautoma.web.WebElement.get_all_select_items
  -> raise UnsupportedActionError("web.element.get_all_select_items")
```

公开签名存在，但 SDK facade 尚未接到 Runtime / Page Engine 选项读取通道。同批
`get_select_options`（#19）/ `get_selected_item` 亦为显式 unsupported。

## 覆盖矩阵

| 场景 | 结果 | 说明 |
| --- | --- | --- |
| 公开签名 | `PASS` | 无参；`list[str]` |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `select_html` / `重置_html` |
| 重置后读取全部选项文本 | `FAIL` | `UnsupportedActionError` |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`
- 产品源码修改：无

## 明确排除

- 选中态变化对全部选项列表的影响（接通后再验）
- `select_html_多选` / Ant / 组件库下拉
- Edge、CEF、Auto

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/27
