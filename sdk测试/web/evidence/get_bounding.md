# `uiautoma.web.WebElement.get_bounding()` 验证证据

```yaml
api: "uiautoma.web.WebElement.get_bounding"
lifecycle: "VERIFIED"
verification_summary:
  chrome_get_bounding_default_ok: "PASS"
  chrome_get_bounding_to96dpi_false_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_bounding 的最小 SDK locate→rect 实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_bounding"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
  verified_contract:
    signature: "get_bounding(to96dpi: bool = True, relative_to: str = 'screen') -> dict[str, int]"
    parameter_order: ["self", "to96dpi", "relative_to"]
    defaults:
      to96dpi: true
      relative_to: "screen"
    keys: ["x", "y", "width", "height", "top", "left", "right", "bottom"]
    note: "to96dpi 为保留参数；relative_to 仅支持 screen"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_get_bounding.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "f7a6d314c4bde77ed82bcd4042777e7b09b5bb57"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "58086849245009d8662dddc5b6a068d019ed74a3"
  select_element_name: "select_html_多选"
  reset_element_name: "重置_html"
  select_characteristics: "//input[@id='form-controls-native-cities']"
  snapshot_path: "tests/SDK/web/web测试元素库/snapshot/localhost_7199_input_20260809_084233_177_20260809_084233_177.json"
  snapshot_fingerprint: "847dc2578fadcb37629dc686ef1f9ad9731eb8d1"
  snapshot_note: "补齐 xpath/machine_xpath/platform，避免 Runtime 报 web element has no xpath"
source_commit_at_doc_time: "01e2c667fd619d3e120a535933bed8eadf378059"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_bounding.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_bounding.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_get_bounding.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API：对 `select_html_多选` 直接调用 `get_bounding(...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.get_bounding
  -> RawWebElement.locate
  -> rect_tuple / screen rect 规范化
  -> dict[str, int]
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `to96dpi`/`relative_to` 默认值与 `dict[str, int]` |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `select_html_多选` |
| 默认 `get_bounding()` | `PASS` | 键齐全、int、宽高>0、几何一致 |
| `to96dpi=False` | `PASS` | 同上 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`http://localhost:7199/form-controls`
- 元素：`select_html_多选`
- 示例返回：`x=1200, y=1127, width=1034, height=26, right=2234, bottom=1153`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无（仅测试库快照补齐 xpath）

## 明确排除

- `relative_to` 非 `screen` 负例。
- 跨 DPI 精确像素对照（`to96dpi` 当前保留）。
- `select_html` 单选 / Ant Design / 组件库控件。
- Edge、CEF、Auto。
