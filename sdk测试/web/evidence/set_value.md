# `WebElement.set_value()` 验收证据

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
| RPC 名 | — | **`web.action`**（`action="type_text"`）；不存在 `web.set_value`（`capabilities.py` 中无此项） |
| Runtime 业务 | `runtime/services/action_service.py:2298` | `web_type_text_element`：未开 `input_check` 时直接 `_run_web_dom_action(params, action="type_text")`；**不校验目标是否可编辑**（对比 `mode="cdp"` 分支会检查 `disabled`/`readOnly`） |
| 引擎 | `chrome/engine/engine_packages/page_engine_runtime.js:3632-3636` | `const property = command.mode === "set_value" \|\| tag === "input" \|\| tag === "textarea" ? "value" : "innerText";` → `element[property] = command.mode === "set_value" \|\| command.clear ? text : …` |

要点：

1. 因为 `mode === "set_value"`，`property` **恒为 `"value"`** —— 即使在 `<div>`/`<label>` 上也是写 `element.value`。
2. 因为 `mode === "set_value"`，赋值分支**恒为覆盖**，SDK 也硬编码 `clear=True` → **公开 API 没有追加能力**。
3. 只写 IDL，不派发任何事件、不聚焦。

另注（**源码读得，未作为判据**）：`type_text` 不在同文件 `:3502` 的 `scrollIntoView` 跳过列表里，
所以 `set_value` 会先执行 `element.scrollIntoView({block:"center"})`——即会滚动到元素但不聚焦。
这与 docstring 不矛盾（它只承诺不改焦点、不触发事件）。

## 2. 真实验收结果

**VERIFIED：21/21 通过，退出码 0；连续 3 次完整运行全绿（2026-09-20）。**

- 靶场：<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>（`title` 实测 `iframe + Shadow 表单测试`）。
- 元素库：`D:\code\元素库\260902_web元素`（只用 `.pytest_tmp/` 下**副本**）；主元素
  `web靶场_表单测试_原生_输入框`，另用 `原生_文本域` / `原生_radio_label_男` / `原生_按钮_提交` 对照
  （主元素与三个对照元素均绑定成功）。
- 被测 worktree：`D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`；
  `sdk/`、`runtime/`、`chrome/` 无本地改动。
- Runtime：`UIAutoma Runtime 0.1.0`，protocol 1。
- 脚本：[test_web_element_set_value.py](../test_web_element_set_value.py)。
- 原始输出：[artifacts/element_set_value_20260920.txt](artifacts/element_set_value_20260920.txt)。

| # | 用例 | 检查内容 | 实测结果 |
| --- | --- | --- | --- |
| 01 | `api_contract` | 签名、必填、返回注解 | 通过；`(self, value: 'str') -> 'None'` |
| 02 | `library_prepare` | 元素库副本、Runtime | 通过；协议 1 |
| 03 | `page_prepare` | 靶场页面标题 | 通过 |
| 04 | `dynamic_id_precondition` | 动态 ID 开关地面真值 | 通过；id `form-controls-native-text` |
| 05 | `element_bind` | 主元素 + 3 个对照元素绑定 | 通过；`find_all` 命中 1 个 |
| 06 | `return_none_and_roundtrip` | 返回值 + 回读 + 跨通道 | 通过；返回 `None`，`get_value` 与页面侧 `el.value` 三方一致 |
| 07 | `no_input_event` | **不派发 input/change 事件** | 通过；监听计数保持 **0** |
| 08 | `event_counter_control` | 计数器有效性对照 | 通过；派发真实事件后计数 **1**，证明上一条非空断言 |
| 09 | `no_focus_change` | 不改变焦点 | 通过；`activeElement` 前后均为 `None` |
| 10 | `overwrite_not_append` | 覆盖语义 | 通过；`AAA` → `B` 得 `'B'` |
| 11 | `empty_string` | 空串 | 通过；回读 `''` |
| 12 | `newline_sanitized_text_input` | `<input>` 换行净化 | 通过；`'a\nb'` → `'ab'` |
| 13 | `newline_preserved_textarea` | `<textarea>` 换行保留 | 通过；`'a\nb'` → `'a\nb'` |
| 14 | `non_string_coerced` | 非字符串入参 | 通过；`123`→`'123'`，`None`→`'None'` |
| 15 | `non_form_element_expando_not_serialized` | 非输入元素 | 通过；不报错、可读回，但 `get_html` 中**没有**该 value 属性 → 只是 JS expando |
| 16 | `form_state_not_synced` | 页面表单状态 A/B | 通过；`set_value` 后页面自身快照**不含**该值，对照路径派发事件后**立即包含** |
| 17 | `param_missing` | 缺参 | 通过；`TypeError: missing 1 required positional argument: 'value'` |
| 18 | `param_extra_positional` | 多余位置参数 | 通过；`TypeError: takes 2 positional arguments but 3 were given` |
| 19 | `param_keyword` | 关键字传参 | 通过；`set_value(value=…)` 正确写入 |
| 20 | `stale_page_reference` | 关闭后写入 | 通过；`ActionError` trace=`stale_page_reference` |
| 21 | `cleanup` | 资源清理 | 通过；页面与 Package 关闭、副本已删除 |

## 3. 期望值来源与独立确证

**独立推导（DOM/HTML 规范，不看产品返回）**：

- docstring 承诺「不改变输入焦点或触发输入事件」→ `input`/`change` 监听计数必须为 **0**。
- HTML 规范：`<input type="text">` 的 value sanitization **去除换行**；`<textarea>` **保留换行**。
  同一段 `'a\nb'` 在两个控件上必须得到 `'ab'` 与 `'a\nb'` 的不同结果——这是纯规范推导的对照。
- 覆盖语义来自 SDK 硬编码 `clear=True`（公开签名没有追加开关）。

**独立确证（跨通道）**：页面侧经
`iframe.contentDocument → #form-shadow-host → shadowRoot` 直读 `el.value`，与 SDK 返回对照。

**独立确证（页面自身状态）**：点页面自己的「提交」触发 `handleNativeSubmit()` →
`buildFormSnapshot(nativeForm, …)` → 写 `#native-result`（不经 SDK），用它做 A/B：

| 步骤 | 页面自身快照中的 `text` |
| --- | --- |
| 基线（清空后提交） | `""` |
| `set_value("…-nosync")` 后提交 | 仍为 `""` —— **未同步** |
| 对照路径派发真实 `input` 事件后提交 | 立即变为 `"…-sync"` |

A/B 成立即证明：`set_value` 的写入对「页面自己的表单状态」不可见，而原因正是它不派发事件。

**反向自证（避免空断言）**：`no_input_event` 断言计数为 0，若监听本身没装上，这条会永远通过。
因此紧接一条 `event_counter_control` 用同一监听验证「派发真实事件时计数确实会变」，
两条一起才构成有效判据。

## 4. 实测行为记录 / 已知边界

- **不派发事件（已实测）**：`set_value` 后 `input`/`change` 计数为 0。带来两个用户可见后果：
  1. 受控框架（React/Ant）的**表单状态不会更新**——页面自己的快照与提交值仍是旧值；
  2. 依赖 `input` 事件的页面逻辑（校验、联动、字数统计）不会触发。
  需要页面感知写入时应改用真实输入路径，而不是 `set_value`。
- **不聚焦（已实测）**：写值前后 `shadow root` 的 `activeElement` 不变。
- **覆盖而非追加**：公开签名没有 `append`，连续写入是覆盖。
- **换行按控件类型处理**：`<input>` 去换行，`<textarea>` 保留——这是浏览器 value sanitization，
  不是本 API 的逻辑。
- **非字符串入参被强转**：SDK 侧 `str(value)`，所以 `123` → `'123'`、`None` → `'None'`。
  `None` **不会**被当作清空。
- **非输入元素不报错**：`property` 恒为 `"value"`，所以在 `<label>` 上也直接赋值，产生一个
  **JS expando**：`get_value()` 能读回，`get_html()` 里没有该属性（没进 DOM）。
  又因 `get_attribute()` 的实现是 `getAttribute(name) ?? element[name]`（`page_engine_runtime.js:3688`），
  这个 expando 会通过属性 API 的**回退**被读出来——容易误判成「DOM 上真有这个属性」。
- **Runtime 不校验可编辑性**：`web_type_text_element` 在非 `input_check` 路径下不做
  `disabled`/`readOnly` 检查（引擎 `mode="cdp"` 分支才检查），因此 `set_value` 对只读/禁用控件
  也会直接改 IDL。**本轮未能实测**（元素库里没有只读/禁用控件元素，见下）。
- **会滚动到元素**：源码读得的 `scrollIntoView` 副作用，本轮**未作为判据**断言
  （断言实现细节属反模式）。
- **必须由实时 `find` 取得**元素；页面关闭后写入返回 `stale_page_reference`。
- **前置条件**：靶场「动态 ID」开关默认开启且状态持久化，开启时固定 id 全部失效；
  脚本先读地面真值、只在动态时关闭（与 `get_value` 同一套逻辑）。

**明确排除（未覆盖）**

- Edge；闭合 Shadow DOM。
- **只读 / 禁用控件**：元素库 `260902_web元素` 中**没有**对应库元素（已核对无
  `只读/禁用/readonly/disabled` 命名条目），需先采集才能验证上一条行为。
- **模拟人工路径 / `input()` 之后再用 `set_value`**：沿用旧证据的排除项，本轮未覆盖。
- **追加语义**：公开 API 无追加开关，无从覆盖（已由签名与 `clear=True` 定性）。
- **IDL 与 content attribute 的分歧**：该 fixture 上两者同进同退（上一轮 `get_value` 已确认），
  本 API 也无法证伪这条区分。
- 元素库捕获期会话字段行为。

## 5. 修订记录（相对 2026-08-08 旧结论）

旧版本文件（YAML 风格，`source_commit_at_doc_time: 25055f00…`）记录如下，按「保留原结论」留档：

- 旧验证日期 2026-08-08；靶场 `http://localhost:7199/form-controls`（**本地 dev server**，现不存在）；
  元素 `input元素` / `重置_html`，属 `tests/SDK/web/web测试元素库`（产品仓库路径）。
- 旧流程：对 `input元素` 调 `set_value(随机值)` → 再 `get_value()` 核对；示例值 `sv_070fc4ac6d3c`；
  `set_value_then_get_value` 约 `31.2ms`；清理记为「本次资源 3/3」。
- 旧明确排除包含：Edge/CEF/Auto、**模拟人工路径 / `input()` 后再 `set_value`**、
  **空值、非输入控件、追加语义**、捕获期会话字段。

本次修订与差异：

1. **原排除项「空值、非输入控件、追加语义」已撤销**：本轮分别以 `empty_string`、
   `non_form_element_expando_not_serialized`、`overwrite_not_append` 覆盖，并给出实测结论
   （追加在公开面上不存在；非输入元素只产生 expando）。
2. **新增判据**：不派发事件（含有效性对照）、不改变焦点、换行按控件类型的规范差异、
   非字符串强转、页面表单状态 A/B、参数三态、`stale_page_reference`、动态 ID 前置条件。
3. **靶场与元素更换**：改用标准靶场 `#/iframe-shadow-form` 与库元素
   `web靶场_表单测试_原生_输入框`；旧靶场是不可复现的本机端口。
4. **旧脚本在本工作区不可复现**：默认元素库 `sdk测试/web/web测试元素库` 不存在，
   且无 `--library` 参数。本次已就地重写并新增 `--library` / `--element` / `--target-url`。
5. 旧文件本身在 git 历史中保留，不删除。

## 6. 复测

在 `D:\code\元素库\sdk测试` 目录运行：

```powershell
uv run .\web\test_web_element_set_value.py
```

仅检查合同（不连接 Runtime、不打开浏览器、不复制元素库）：

```powershell
uv run .\web\test_web_element_set_value.py --contract-only
```

归档 JSON 报告：

```powershell
uv run .\web\test_web_element_set_value.py --json
```

退出码约定：`0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED
（靶场结构未就绪、动态 ID 无法关闭、元素绑定失败、页面回显通道不可用均记 2）。
