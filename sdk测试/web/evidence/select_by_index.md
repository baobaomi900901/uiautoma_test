# `uiautoma.web.WebElement.select_by_index()` 验证证据

## 2026-09-24 iframe / Shadow 表单复验

- **结果**：`VERIFIED`（标准原生 `<select>`）。连续 3 次完整运行，每次 `17/18 PASS`、`1 KNOWN`、`0 FAIL`、`0 BLOCKED`、退出码 `0`；清理每轮 `PASS`。`KNOWN` 为 Ant 自定义 combobox 的能力边界，并非成功选中 Ant 选项。
- **源码快照与环境**：只读产品 worktree `D:\code\desktop`，commit `e08eadd0d6d921ea11579e4acfb894c1c4cee038`；dev Runtime、Chrome、<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>；连接 `D:\code\元素库\260902_web元素` 的临时副本。以下结论只对应此快照与环境。
- **合同与实现链**：`select_by_index(self, index: int, delay_after: float=1) -> None`；`index` 必填且为整数，`delay_after` 可按位置或名称传入。`WebElement.select_by_index` → `RawWebElement.select_by_index` → `web.action.select`（`index=...`）→ `ActionService.web_select_element` → Page Engine `selectOption`。引擎仅接受 `<select>`；负索引以 `options.length + index` 换算，越界不改变原选择；`bool`、浮点数、字符串、`None` 抛 `InvalidParamsError`。
- **元素与期望值来源**：原生库元素 `web靶场_表单测试_原生_select单选` 唯一对应 `select#form-controls-native-city`。从页面 DOM 确认选项依次为索引 0 占位/`''`、1 北京/`beijing`、2 上海/`shanghai`、3 广州/`guangzhou`、4 深圳/`shenzhen`。Ant 库元素 `web靶场_表单测试_ant_select单选` 对应 `input#form-controls-ant-city[role=combobox]`。
- **真实场景与独立确证**：每例从页面「重置」后的稳定状态开始，调用目标 API 后独立读取 DOM `value`，再点页面自己的「提交」并解析新产生的 `#native-result` JSON 中的 `city`，最后再次重置复核空值。索引 `1` 选北京，`2` 选上海，`0` 从预选北京回到占位项，`-1` 选深圳，`-2` 选广州；`99` 和 `-99` 均保留预选北京；关键字 `index=3` 选广州。默认 `delay_after=1` 的调用约 1 秒，显式短延时约 0.1 秒。无效索引类型和缺少 `index` 均无 DOM 状态变化；关闭库连接后抛 `StalePackageError`。
- **Ant 边界**：`select_by_index(1, delay_after=0)` 对 Ant 自定义 combobox 抛 `ActionError`，trace `element_not_selectable`，前后显示和值不变。展开后点击选项属于其他 API，本轮未计为 `select_by_index()` 成功。
- **探针与清理**：初次一次性探针在页面「重置」后复用旧元素引用，触发元素 ID 失效；改为每次重置后重新 `find()`，探针与正式脚本结果一致。正式脚本每轮恢复动态 ID 开关、关闭本次标签和元素库连接、删除临时副本，并用本次标签 ID 独立复核关闭；三轮外部标签数均无变动。
- **复测与报告**：从 `D:\code\元素库\sdk测试` 运行 `uv run .\web\test_web_element_select_by_index.py --json --report-file .\web\evidence\artifacts\select_by_index_20260924_run1.txt`；[第 1 轮](artifacts/select_by_index_20260924_run1.txt)、[第 2 轮](artifacts/select_by_index_20260924_run2.txt)、[第 3 轮](artifacts/select_by_index_20260924_run3.txt)。若 `uv` 默认缓存目录权限不足，可加 `--no-cache`。退出码 `0` 允许 `KNOWN`，`1` 表示失败，`2` 表示环境阻塞。
- **范围**：未覆盖 Edge、CEF、动态 ID 开启时的定位、超大选项列表或 Ant 点击选项流程；产品源码未修改。

下列 2026-08-09 的 `form-controls`、`select_html` 记录保留为旧快照证据；其中对越界索引的说明不能代替本轮实测。对应旧脚本已归档为 [`test_web_element_select_by_index_legacy_20260809.py`](../test_web_element_select_by_index_legacy_20260809.py)。

```yaml
api: "uiautoma.web.WebElement.select_by_index"
lifecycle: "VERIFIED"
verification_summary:
  chrome_select_by_index_beijing_ok: "PASS"
  chrome_select_by_index_shanghai_ok: "PASS"
  chrome_select_by_index_placeholder_ok: "PASS"
  chrome_select_by_index_delay_after_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.select_by_index 的最小 SDK、Runtime 与 DOM select 实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.select_by_index", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.select_by_index"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_select"]
      fingerprint: "23a56351fce260eaccdfa8a4465519e0ffd85a73"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_select_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "select_by_index(index: int, delay_after: float = 1) -> None"
    parameter_order: ["self", "index", "delay_after"]
    defaults:
      delay_after: 1
    index_required: true
    note: "index/delay_after 均为位置或关键字参数；index 从 0 开始"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_select_by_index.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "1147f0a45fce2b95c45b44429b288d0a0b6b0af8"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "ca318ee0b1f358e39b7b061de278aa9200a562ec"
  select_element_name: "select_html"
  submit_element_name: "提交_html"
  reset_element_name: "重置_html"
source_commit_at_doc_time: "39dfab9ce9b6b18ccefdcfdf3e632584d21919ef"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_select_by_index.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select_by_index.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select_by_index.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`；`finally` 中删除该副本。选择步骤日志输出到 stderr。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` / `提交_html` 的 `click()`。
- 目标 API：只对 `select_html` 直接调用 `WebElement.select_by_index(...)`。
- 验收 API：`get_value()` 与剪贴板表单 JSON 的 `city`（非目标合同）。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.select_by_index
  -> RawWebElement.select_by_index
  -> AutomationDispatcher._handle_web_action_select
  -> ActionService.web_select_element (index=...)
  -> page_engine selectOptionByIndex
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `index` 必填；`delay_after` 默认 `1` |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与三库项可用 |
| 页面与库连接 | `PASS` | 绑定成功 |
| index `1` | `PASS` | `value`/`city`=`beijing` |
| index `2` | `PASS` | `value`/`city`=`shanghai` |
| index `0` | `PASS` | `value`/`city`=`""` |
| `delay_after=1` | `PASS` | 耗时 ≥900ms 且选中正确 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`http://localhost:7199/form-controls`
- `select_by_index_beijing`：约 `282.5ms`
- `select_by_index_shanghai`：约 `283.5ms`
- `select_by_index_placeholder`：约 `288.0ms`
- `select_by_index_delay_after`：约 `1026.3ms`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- 越界 index（`option_not_found`）负例矩阵。
- Ant Design / 组件库下拉框。
- Edge、CEF、Auto。
