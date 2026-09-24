# `uiautoma.web.WebElement.select_multiple()` 验证证据

## 2026-09-24 iframe / Shadow 表单复验

- **结果**：`VERIFIED`（标准原生 `<select multiple>`）。连续 3 次完整运行，每次 `20/21 PASS`、`1 KNOWN`、`0 FAIL`、`0 BLOCKED`、退出码 `0`；`cleanup` 每轮 `PASS`。`KNOWN` 是 Ant 自定义多选控件的能力边界，并不表示已通过 `select_multiple()` 选中 Ant 选项。
- **源码快照与环境**：只读产品 worktree `D:\code\desktop`，commit `e08eadd0d6d921ea11579e4acfb894c1c4cee038`；dev Runtime、Chrome、<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>；连接 `D:\code\元素库\260902_web元素` 的临时副本。以下结论只对应此快照与环境。
- **合同与实现链**：`select_multiple(self, items: list[str], *, mode: str='fuzzy', append: bool=False, delay_after: float=1) -> None`。`items` 必填，后续参数仅限关键字；当前 `mode` 接受 `fuzzy`、`exact`、`regex`。`WebElement.select_multiple` → `RawWebElement.select_multiple` → `web.action.select`（`multiple=true`）→ `ActionService.web_select_element` → Page Engine `selectOption`。引擎只接受 `<select>`，原生层检查 `items` 为纯文本列表并校验模式；无效列表/模式/正则抛 `InvalidParamsError`，关闭库连接后抛 `StalePackageError`。
- **选项及独立确证**：原生库元素 `web靶场_表单测试_原生_select多选_options_面板` 唯一对应 `select#form-controls-native-cities[multiple]`；页面 DOM 选项依次为北京/`beijing`、上海/`shanghai`、广州/`guangzhou`、深圳/`shenzhen`。每例调用后独立读取各 option 的 `selected`，再点页面自己的「提交」并解析新产生的 `#native-result` JSON 中 `cities`；最后点「重置」复核空列表。默认模糊 `['京','海']`、精确 `['北京','上海']` 均选中北京和上海；正则 `['^广','^深']` 选中广州和深圳。默认调用约 1.0 秒，满足 `delay_after=1`；显式短延时约 0.1 秒。
- **追加与边界**：预选北京后，`append=True` 加选上海得到两项，`append=False` 选深圳只剩深圳；空列表在覆盖模式清空、追加模式保留北京；无匹配列表同理。精确模式的英文 `beijing` 不匹配中文“北京”。这些状态均经 DOM 和页面提交 JSON 双重确证。
- **Ant 边界**：库元素 `web靶场_表单测试_ant_select多选` 对应 `div.ant-select-selection-overflow`，不是 `<select>`；调用 `select_multiple(['北京','上海'], mode='exact')` 抛 `ActionError`，trace 为 `element_not_selectable`，前后显示与原生选中状态不变。展开后点击选项属于其他 API，本轮未计作成功。
- **试跑修订与清理**：初次正式脚本在页面重置后立刻开始下一例，React 状态尚未稳定，导致选择和提交判据失真；等待重置稳定后完整用例通过。一次后续试跑期间用户的百度地图标签加入 Chrome，总标签数由 5 变 6；只读标签清单确认本轮测试页已关闭。正式脚本改为追踪本轮创建的标签 ID，同时记录外部标签增减。最终三轮均复核本轮标签已关闭、元素库连接关闭、临时副本删除、动态 ID 开关恢复。
- **复测与原始报告**：从 `D:\code\元素库\sdk测试` 运行 `uv run .\web\test_web_element_select_multiple.py --json --report-file .\web\evidence\artifacts\select_multiple_20260924_run1.txt`；记录：[第 1 轮](artifacts/select_multiple_20260924_run1.txt)、[第 2 轮](artifacts/select_multiple_20260924_run2.txt)、[第 3 轮](artifacts/select_multiple_20260924_run3.txt)。若本机 `uv` 默认缓存目录权限不足，可加 `--no-cache`。退出码 `0` 允许 `KNOWN`，`1` 表示失败，`2` 表示环境阻塞。
- **范围**：本轮未覆盖 Edge、CEF、动态 ID 开启时的定位、超大选项列表、Ant 点击选项流程或 `select_multiple_by_index()`；产品源码未修改。

下列 2026-08-09 的 `form-controls`、`select_html_多选` 和 `UnsupportedActionError` 结论保留为历史证据，不能套用到本轮源码快照；对应旧脚本已归档为 [`test_web_element_select_multiple_legacy_20260809.py`](../test_web_element_select_multiple_legacy_20260809.py)。

```yaml
api: "uiautoma.web.WebElement.select_multiple"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_select_multiple_fuzzy_items_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defect: "web.element.select_multiple unsupported"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.select_multiple 的公开签名与当前 SDK 未实现行为"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.select_multiple"]
  verified_contract:
    signature: "select_multiple(items: list[str], *, mode: str = 'fuzzy', append: bool = False, delay_after: float = 1) -> None"
    parameter_order: ["self", "items", "mode", "append", "delay_after"]
    defaults:
      mode: "fuzzy"
      append: false
      delay_after: 1
    items_required: true
    note: "mode/append/delay_after 为仅关键字参数；当前实现直接 unsupported"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web.element.select_multiple"
      message: "当前版本暂不支持"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_select_multiple.py"
  fingerprint_kind: "Git blob of current working-tree content"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  select_element_name: "select_html_多选"
  reset_element_name: "重置_html"
  select_characteristics: "//input[@id='form-controls-native-cities']"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_select_multiple.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select_multiple.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_select_multiple.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()`。
- 目标 API：对 `select_html_多选` 直接调用
  `select_multiple(items, mode=..., append=..., delay_after=...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链（当前缺口）

```text
uiautoma.web.WebElement.select_multiple
  -> raise UnsupportedActionError("web.element.select_multiple")
```

## 覆盖矩阵

| 场景 | 结果 | 说明 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序/默认值/仅关键字种类符合合同 |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `select_html_多选` / `重置_html` |
| fuzzy 多选探测 | `FAIL` | `UnsupportedActionError`（`web.element.select_multiple`） |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 靶场：`http://localhost:7199/form-controls`
- 元素：`select_html_多选`（`//input[@id='form-controls-native-cities']`，带 input 的原生城市多选）
- `select_multiple(["上海","北京"], mode="fuzzy")`：`UnsupportedActionError` / `web.element.select_multiple`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- `mode=exact` / `mode=value` / `append=True` / `delay_after` 计时（实现接通后再验）。
- `mode=regex`（用户文案提及；当前未形成可验证合同）。
- 原生 `<select multiple>`（当前控件为带 input 的多选 UI）。
- Ant Design / 组件库下拉框。
- Edge、CEF、Auto。

## 跟踪 Issue

- https://github.com/uiautoma/desktop/issues/17（`select_multiple`）
- https://github.com/uiautoma/desktop/issues/18（`select_multiple_by_index`，同批 stub）
