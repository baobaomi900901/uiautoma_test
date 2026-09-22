# `uiautoma.web.WebElement.set_value()` 验证证据

## 1. 用途与合同

设置当前网页元素的 **value property（IDL）**；按 docstring，**不改变输入焦点、不触发输入事件**。

```python
WebElement.set_value(self, value: str) -> None
```

`value` 是**唯一一个**参数，**必填、无默认值**，位置或关键字皆可。返回 `None`。

**它没有自己的 RPC** —— 实现复用 `type_text`：

| 层 | 位置 | 事实 |
| --- | --- | --- |
| SDK 公开对象 | `sdk/src/uiautoma/web/element.py:557` | `set_value(self, value: str) -> None` → `self._raw.type_text(str(value), clear=True, focus=False, mode="set_value")`，随后 `_finish(result, 0)` |
| SDK Raw | `sdk/src/uiautoma/_core/client.py:3681` | `type_text(text, *, clear=False, focus=True, mode=None, …)`；组装 `text` / `clear` / `focus` / `mode` |
| RPC 名 | — | **`web.action`**（`action="type_text"`）；不存在 `web.set_value` |
| Runtime 业务 | `runtime/services/action_service.py:2298` | `web_type_text_element`：未开 `input_check` 时直接 `_run_web_dom_action(params, action="type_text")`；**不校验目标是否可编辑**（对比 `mode="cdp"` 分支会检查 `disabled`/`readOnly`） |
| 引擎 | `chrome/engine/engine_packages/page_engine_runtime.js:3632-3636` | `property = mode === "set_value" \|\| tag === "input" \|\| tag === "textarea" ? "value" : "innerText"` → `element[property] = mode === "set_value" \|\| clear ? text : …` |

要点：

1. 因为 `mode === "set_value"`，`property` **恒为 `"value"`** —— 即使在 `<div>`/`<label>` 上也是写
   `element.value`。
2. 因为 `mode === "set_value"`，赋值分支**恒为覆盖**，SDK 也硬编码 `clear=True` → **公开 API
   没有追加能力**。
3. 只写 IDL，不派发任何事件、不聚焦。

另注（**源码读得，未作为判据**）：`type_text` 不在同文件 `:3502` 的 `scrollIntoView` 跳过列表里，
所以 `set_value` 会先执行 `element.scrollIntoView({block:"center"})`——即会滚动到元素但不聚焦。
这与 docstring 不矛盾（它只承诺不改焦点、不触发事件）。

## 2. 真实验收结果

**VERIFIED：21/21 通过，退出码 0；连续 3 次完整运行全绿（2026-09-20）。**

- 靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`。
- 元素库/元素：`260902_web元素`（只用副本）；主元素 `web靶场_表单测试_原生_输入框`，
  另用 `原生_文本域` / `原生_radio_label_男` / `原生_按钮_提交` 对照（主元素与三个对照元素均绑定成功）。
- 被测 worktree 基线：`c101caa9dcd115a461fc71ecaed351b0dea880b8`；`sdk/`、`runtime/`、`chrome/`
  无本地改动。Runtime `0.1.0`，protocol 1。
- 运行脚本：外部 `sdk测试` 工作区 `web/test_web_element_set_value.py`。
- 归档原始输出：该工作区 `web/evidence/artifacts/element_set_value_20260920.txt`。

| # | 用例 | 实测结果 |
| --- | --- | --- |
| 01 | 公开签名 | 通过；`(self, value: 'str') -> 'None'` |
| 02–05 | 元素库副本、靶场页面、动态 ID 前置条件、元素绑定 | 全部通过 |
| 06 | 返回值 + 回读 + 跨通道 | 通过；返回 `None`，`get_value` 与页面侧 `el.value` 三方一致 |
| 07 | **不派发 input/change 事件** | 通过；监听计数保持 **0** |
| 08 | 计数器有效性对照 | 通过；派发真实事件后计数 **1**，证明上一条非空断言 |
| 09 | 不改变焦点 | 通过；`activeElement` 前后均为 `None` |
| 10 | 覆盖语义 | 通过；`AAA` → `B` 得 `'B'` |
| 11 | 空串 | 通过；回读 `''` |
| 12 | `<input>` 换行净化 | 通过；`'a\nb'` → `'ab'` |
| 13 | `<textarea>` 换行保留 | 通过；`'a\nb'` → `'a\nb'` |
| 14 | 非字符串入参 | 通过；`123`→`'123'`，`None`→`'None'` |
| 15 | 非输入元素 | 通过；不报错、可读回，但 `get_html` 中**没有**该 value 属性 → 只是 JS 临时属性 |
| 16 | 页面表单状态 A/B | 通过；`set_value` 后页面自身快照**不含**该值，对照路径派发事件后**立即包含** |
| 17–19 | 参数三态 | 通过；缺参/多余位置参数被 `TypeError` 拒绝，关键字传参可用 |
| 20 | 页面关闭后写入 | 通过；trace=`stale_page_reference` |
| 21 | 资源清理 | 通过 |

## 3. 期望值来源与独立确证

**独立推导（DOM/HTML 规范，不看产品返回）**：

- docstring 承诺「不改变输入焦点或触发输入事件」→ `input`/`change` 监听计数必须为 **0**。
- HTML 规范：`<input type="text">` 的 value sanitization **去除换行**；`<textarea>` **保留换行**。
  同一段 `'a\nb'` 在两个控件上必须得到 `'ab'` 与 `'a\nb'` 的不同结果——纯规范推导的对照。
- 覆盖语义来自 SDK 硬编码 `clear=True`（公开签名没有追加开关）。

**独立确证（跨通道）**：页面侧经
`iframe.contentDocument → #form-shadow-host → shadowRoot` 直读 `el.value`，与 SDK 返回对照。

**独立确证（页面自身状态）**：点页面自己的「提交」触发 `handleNativeSubmit()` →
Ant form 实例生成快照 → 写入 `#native-result`（不经 SDK），用它做 A/B：

| 步骤 | 页面自身快照中的 `text` |
| --- | --- |
| 基线（清空后提交） | `""` |
| `set_value("…-nosync")` 后提交 | 仍为 `""` —— **未同步** |
| 对照路径派发真实 `input` 事件后提交 | 立即变为 `"…-sync"` |

**反向自证（避免空断言）**：`no_input_event` 断言计数为 0，若监听本身没装上，这条会永远通过。
因此紧接一条 `event_counter_control` 用同一监听验证「派发真实事件时计数确实会变」，
两条一起才构成有效判据。

## 4. 实测行为记录 / 已知边界

- **不派发事件（已实测）**：带来两个用户可见后果：受控框架（React/Ant）的**表单状态不会更新**，
  依赖 `input` 事件的页面逻辑（校验、联动、字数统计）不会触发。需要页面感知写入时应改用
  真实输入路径。
- **不聚焦（已实测）**：写值前后 `shadow root` 的 `activeElement` 不变。
- **覆盖而非追加**：公开签名没有 `append`，连续写入是覆盖。
- **换行按控件类型处理**：`<input>` 去换行，`<textarea>` 保留——这是浏览器 value sanitization，
  不是本 API 的逻辑。
- **非字符串入参被强转**：SDK 侧 `str(value)`，所以 `123` → `'123'`、`None` → `'None'`。
  `None` **不会**被当作清空。
- **非输入元素不报错**：`property` 恒为 `"value"`，在 `<label>` 上直接赋值产生一个 **JS 临时属性**：
  `get_value()` 能读回，`get_html()` 里没有该属性（没进 DOM）。又因 `get_attribute()` 的实现是
  `getAttribute(name) ?? element[name]`（`page_engine_runtime.js:3688`），这个临时属性会通过属性
  API 的**回退**被读出来——容易误判成「DOM 上真有这个属性」。
- **Runtime 不校验可编辑性**：非 `input_check` 路径不做 `disabled`/`readOnly` 检查，因此
  `set_value` 对只读/禁用控件也会直接改 IDL。**本轮未能实测**（元素库中没有对应元素）。
- **前置条件**：靶场「动态 ID」开关默认开启且状态持久化，开启时固定 id 全部失效；
  脚本先读地面真值、只在动态时关闭。
- **明确排除（未覆盖）**：Edge；闭合 Shadow DOM；只读/禁用控件（元素库中**没有**对应元素，
  需先采集）；模拟人工路径 / `input()` 之后再用 `set_value`；IDL 与内容属性的分歧
  （该 fixture 上两者同进同退，无可证伪样本）。

## 5. 修订记录（相对 2026-08-08 旧结论）

旧记录（`source_commit_at_doc_time: 25055f00…`）：

- 日期 2026-08-08；靶场 `http://localhost:7199/form-controls`（**本地 dev server**，现不存在）；
  元素 `input元素` / `重置_html`。流程为对 `input元素` 调 `set_value(随机值)` → 再 `get_value()`
  核对；示例值 `sv_070fc4ac6d3c`；清理记为「本次资源 3/3」。
- 旧明确排除包含：Edge/CEF/Auto、**模拟人工路径 / `input()` 后再 `set_value`**、
  **空值、非输入控件、追加语义**、捕获期会话字段。

本次修订：

1. **原排除项「空值、非输入控件、追加语义」已撤销**：本轮分别以 `empty_string`、
   `non_form_element_expando_not_serialized`、`overwrite_not_append` 覆盖，并给出实测结论
   （追加在公开面上不存在；非输入元素只产生不进入 DOM 的临时属性）。
2. **新增判据**：不派发事件（含有效性对照）、不改变焦点、换行按控件类型的规范差异、
   非字符串强转、页面表单状态 A/B、参数三态、`stale_page_reference`、动态 ID 前置条件。
3. **靶场与元素更换**：改用标准靶场与库元素 `web靶场_表单测试_原生_输入框`；
   旧靶场是不可复现的本机端口。
4. **产品侧 `tests/SDK/web/test_web_element_set_value.py` 本轮未更新**：仍指向已退役的本机靶场
   地址与旧元素库，不能复现本次结果；是否移植外部工作区脚本需单独决定。

## 6. 复测

在外部 `sdk测试` 工作区根目录运行：

```powershell
uv run .\web\test_web_element_set_value.py
```

仅检查合同：

```powershell
uv run .\web\test_web_element_set_value.py --contract-only
```

归档 JSON 报告：

```powershell
uv run .\web\test_web_element_set_value.py --json
```

元素库位置可用 `--library <目录>` 指定（默认使用该工作区约定的 `260902_web元素`）。

退出码约定：`0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED。
