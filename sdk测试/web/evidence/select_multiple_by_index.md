# `uiautoma.web.WebElement.select_multiple_by_index()` 验证证据

## 2026-09-24 iframe / Shadow 表单复验

- **结果**：`VERIFIED`（标准原生 `<select multiple>`）。连续 3 次完整运行，每次 `22/23 PASS`、`1 KNOWN`、`0 FAIL`、`0 BLOCKED`、退出码 `0`；清理每轮 `PASS`。`KNOWN` 为 Ant 自定义多选控件的能力边界，并非成功选中 Ant 选项。
- **源码快照与环境**：只读产品 worktree `D:\code\desktop`，commit `e08eadd0d6d921ea11579e4acfb894c1c4cee038`；dev Runtime、Chrome、<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>；连接 `D:\code\元素库\260902_web元素` 的临时副本。以下结论只对应此快照与环境。
- **合同与实现链**：`select_multiple_by_index(self, indexes: list[int], *, append: bool=False, delay_after: float=1) -> None`。`indexes` 必填，`append` 与 `delay_after` 仅限关键字。`WebElement.select_multiple_by_index` → `RawWebElement.select_multiple_by_index` → `web.action.select`（`indexes=...`、`multiple=true`）→ `ActionService.web_select_element` → Page Engine `selectOption`。原生层要求纯整数列表且拒绝 `bool`；引擎将负索引换算为 `options.length + index`，超出范围的索引忽略；`append=False` 先清空旧选中项，`append=True` 保留旧项。
- **元素与期望值来源**：原生库元素 `web靶场_表单测试_原生_select多选_options_面板` 唯一对应 `select#form-controls-native-cities[multiple]`，页面 DOM 选项依次为索引 0 北京/`beijing`、1 上海/`shanghai`、2 广州/`guangzhou`、3 深圳/`shenzhen`。Ant 库元素 `web靶场_表单测试_ant_select多选` 对应 `div.ant-select-selection-overflow`，不是 `<select>`。
- **真实场景与独立确证**：每例从页面「重置」后的稳定状态开始，调用目标 API 后独立读取各 option 的 `selected`，再点页面自己的「提交」并解析新产生的 `#native-result` JSON 中 `cities`，最后重置复核空列表。`[0,2]` 选北京和广州，`[-1,-2]` 选广州和深圳；传入 `[2,0]` 的回显仍按 DOM 顺序排列，重复索引 `[1,1]` 只选上海一次。默认调用约 1 秒，满足 `delay_after=1`。
- **追加、空列表和越界**：预选北京后，`append=True` 加入索引 2 得北京和广州，`append=False` 只剩广州；空列表在覆盖模式清空、追加模式保留北京；纯越界列表 `[99,-99]` 同理。混合 `[99,3,-99]` 只选深圳。无效列表类型、混合类型、布尔和浮点索引抛 `InvalidParamsError` 且 DOM 不变；缺少索引列表和位置传入 `append` 抛 `TypeError`；关闭库连接后抛 `StalePackageError`。
- **Ant 边界**：调用 `select_multiple_by_index([0,1], delay_after=0)` 抛 `ActionError`，trace `element_not_selectable`；Ant 显示和原生选中状态均不变。展开后点击选项属于其他 API，本轮未计作成功。
- **收尾与范围**：三轮均恢复动态 ID 开关、关闭本次标签和元素库连接、删除临时副本，并追踪本次标签 ID 确认关闭。未覆盖 Edge、CEF、动态 ID 开启时的定位、超大选项列表或 Ant 点击选项流程；产品源码未修改。
- **复测与报告**：从 `D:\code\元素库\sdk测试` 运行 `uv run .\web\test_web_element_select_multiple_by_index.py --json --report-file .\web\evidence\artifacts\select_multiple_by_index_20260924_run1.txt`；[第 1 轮](artifacts/select_multiple_by_index_20260924_run1.txt)、[第 2 轮](artifacts/select_multiple_by_index_20260924_run2.txt)、[第 3 轮](artifacts/select_multiple_by_index_20260924_run3.txt)。若 `uv` 默认缓存目录权限不足，可加 `--no-cache`。退出码 `0` 允许 `KNOWN`，`1` 表示失败，`2` 表示环境阻塞。

下列 2026-08-09 的 `form-controls`、`select_html_多选` 和 `UnsupportedActionError` 结论保留为旧源码快照的历史证据，不能套用当前版本；对应旧脚本已归档为 [`test_web_element_select_multiple_by_index_legacy_20260809.py`](../test_web_element_select_multiple_by_index_legacy_20260809.py)。

```yaml
api: "uiautoma.web.WebElement.select_multiple_by_index"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_select_multiple_by_index_items_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defect: "web.element.select_multiple_by_index unsupported"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.select_multiple_by_index 的公开签名与当前 SDK 未实现行为"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.select_multiple_by_index"]
  verified_contract:
    signature: "select_multiple_by_index(indexes: list[int], *, append: bool = False, delay_after: float = 1) -> None"
    parameter_order: ["self", "indexes", "append", "delay_after"]
    defaults:
      append: false
      delay_after: 1
    indexes_required: true
    note: "append/delay_after 为仅关键字参数；当前实现直接 unsupported"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web.element.select_multiple_by_index"
      message: "当前版本暂不支持"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_select_multiple_by_index.py"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  select_element_name: "select_html_多选"
  reset_element_name: "重置_html"
  select_characteristics: "//input[@id='form-controls-native-cities']"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_select_multiple_by_index.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select_multiple_by_index.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_select_multiple_by_index.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()`。
- 目标 API：对 `select_html_多选` 直接调用
  `select_multiple_by_index(indexes, append=..., delay_after=...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链（当前缺口）

```text
uiautoma.web.WebElement.select_multiple_by_index
  -> raise UnsupportedActionError("web.element.select_multiple_by_index")
```

## 覆盖矩阵

| 场景 | 结果 | 说明 |
| --- | --- | --- |
| 公开签名 | `PASS` | `indexes` 必填；`append`/`delay_after` 仅关键字 |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `select_html_多选` / `重置_html` |
| 索引多选探测 | `FAIL` | `UnsupportedActionError`（`web.element.select_multiple_by_index`） |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 靶场：`http://localhost:7199/form-controls`
- 元素：`select_html_多选`（`//input[@id='form-controls-native-cities']`）
- `select_multiple_by_index([1, 0], append=False)`：`UnsupportedActionError` /
  `web.element.select_multiple_by_index`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- `append=True` / `delay_after` 计时（实现接通后再验）。
- 原生 `<select multiple>`（当前控件为带 input 的多选 UI）。
- Ant Design / 组件库下拉框。
- Edge、CEF、Auto。

## 跟踪 Issue

- https://github.com/uiautoma/desktop/issues/18（`select_multiple_by_index`）
- https://github.com/uiautoma/desktop/issues/17（`select_multiple`，同批 stub）
