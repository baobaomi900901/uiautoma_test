# `WebElement.get_value()` 验收证据

## 1. 用途与合同

读取**当前网页元素的 value property（IDL）**——不是 HTML 的 `value` 内容属性。

```python
WebElement.get_value(self) -> str | None
```

公开签名**没有任何参数**（`self` 之外无位置参数、无关键字参数）。返回原生 `str`；
节点没有 `value` property 时返回 `None`（引擎把 `null` 原样透出，SDK 只把非 None 值转 `str`）。

完整链路（检出目录 `D:\code\desktop`，基线 commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`）：

| 层 | 位置 | 事实 |
| --- | --- | --- |
| SDK 公开对象 | `sdk/src/uiautoma/web/element.py:548` | `get_value(self) -> str \| None`，无参数，委托 `self._raw.get_value()` |
| SDK Raw | `sdk/src/uiautoma/_core/client.py:3944` | `get_value(*, timeout: float = 5.0) -> str \| None`；docstring「读取 Web 表单元素当前 value property」；`None` 原样返回，其余 `str(...)` |
| RPC 名 | — | `web.get_value` |
| 能力/参数 | `runtime/services/capabilities.py:274,483` | 必填 `package_token` / `element_id` / `timeout_ms`；capability `web_dom_actions_stage5` |
| Runtime 分发 | `runtime/services/pipe_server.py` | `_handle_web_get_value` → `action_service.web_get_value_element` |
| Runtime 业务 | `runtime/services/action_service.py:2489` → `6102` | `_run_web_value(op="get_value")`；**要求 `locator_kind == "runtime_ref"`**，即元素必须由实时 `find`/`find_all` 取得，否则 `invalid_params`「请先查找当前网页元素」 |
| 桥接 | `runtime/web/bridge_api.py:343` | `m == "web.get_value"` → `action = "get_value"` |
| 引擎 | `chrome/engine/engine_packages/page_engine_runtime.js:3669` | `const value = element.value;` → `value == null ? null : String(value)` |

**两条容易踩的实现细节**：

1. `get_attribute("value")` **不能**当作 content attribute 的对照。引擎（同文件 `:3688`）是
   `element.getAttribute(name) ?? element[name]`，属性缺失时会回退到 IDL 属性，两者被混同。
2. 引擎 `get_value` 分支里还有 `mode === "input_check"` 与 `mode === "cdp_ready"` 两条内部路径
   （分别返回 `input_check_target_invalid` / `element_not_focused`），但公开 `get_value()` 不发送
   `mode`，**公开面无法触达**这两条分支。

## 2. 真实验收结果

**VERIFIED：17/17 通过，退出码 0；连续 3 次完整运行全绿（2026-09-20）。**

- 靶场：<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>（`title` 实测 `iframe + Shadow 表单测试`）。
- 元素库：`D:\code\元素库\260902_web元素`（只用 `.pytest_tmp/` 下**副本**，原件未改动）；
  主元素 `web靶场_表单测试_原生_输入框` —— iframe → **open shadow DOM** 内的
  `<input type="text" id="form-controls-native-text">`。
- 被测 worktree：`D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`；
  该 commit 下 `sdk/`、`runtime/`、`chrome/` 无本地改动。
- Runtime：`UIAutoma Runtime 0.1.0`，protocol 1，`web_dom_actions_stage5` 已声明。
- 脚本：[test_web_element_get_value.py](../test_web_element_get_value.py)。
- 原始输出：[artifacts/element_get_value_20260920.txt](artifacts/element_get_value_20260920.txt)。

| # | 用例 | 检查内容 | 实测结果 |
| --- | --- | --- | --- |
| 01 | `api_contract` | 签名 `(self)`、无参数、注解含 `None` | 通过；`(self) -> 'str \| None'` |
| 02 | `library_prepare` | 元素库副本、Runtime | 通过；协议 1 |
| 03 | `page_prepare` | 靶场页面标题 | 通过；`iframe + Shadow 表单测试` |
| 04 | `dynamic_id_precondition` | 动态 ID 开关地面真值 | 通过；DOM 实际 id `form-controls-native-text` |
| 05 | `element_bind` | 库元素绑定 | 通过；`find_all` 命中 1 个 |
| 06 | `empty_value_is_empty_string` | 空值语义 | 通过；返回 `''`（`str`），**不是 `None`** |
| 07 | `dom_idl_agrees` | 与页面侧直读 IDL 跨通道一致 | 通过；均为 `''` |
| 08 | `live_write_visible` | 页面侧写已知值后读回 | 通过；写入 `uiautoma-get-value-probe`，精确读回 |
| 09 | `page_form_state_agrees` | 页面**自身**表单状态确认 | 通过；提交回显 JSON 含该值 |
| 10 | `repeat_read_stable` | 连续 3 次读取 | 通过；一致且等于写入值 |
| 11 | `restore_verified` | 还原并复核 | 通过；写回空串后返回 `''` |
| 12 | `no_value_property_is_none` | `None` 负例 | 通过；radio label 元素返回 `None` |
| 13 | `control_matrix` | 7 个控件的 `get_value` vs 页面侧 IDL | 通过；全部一致：密码/邮件/数字/文本域/select单选/提交 = `''`，滑块 = `'0'` |
| 14 | `param_positional` | 多余位置参数 | 通过；`TypeError` |
| 15 | `param_keyword` | 未声明关键字 | 通过；`TypeError` |
| 16 | `stale_page_reference` | 页面关闭后读取 | 通过；`ActionError` trace=`stale_page_reference` |
| 17 | `cleanup` | 资源清理 | 通过；页面与 Package 关闭、副本已删除 |

## 3. 期望值来源与独立确证

**独立推导**（依据 DOM 规范，不看产品返回）：

- 空输入框的 IDL `value` 是空字符串 `""`；`""` 与 `None` 必须可区分——`None` 只应表示
  「该节点没有 `value` property」。
- 没有 `value` property 的节点（如 `label`）应返回 `None`。

**独立确证（跨通道）**：页面侧经
`iframe.contentDocument → #form-shadow-host → shadowRoot → getElementById(...)` 直读 `el.value`
（CDP 通道），与 SDK 返回（`chrome.scripting` 通道）逐项对照；主元素与 7 个控件全部一致。

**独立确证（页面自身状态，完全不经过 SDK）**：用页面自己的「提交」按钮触发
`handleNativeSubmit()` → `buildFormSnapshot(nativeForm, …)` → `copyFormJson()`，
把 Ant form 实例生成的快照 JSON 写入 `#native-result` 并同时写剪贴板。实测该回显含
`"text": "uiautoma-get-value-probe"`，证明写入的值被**页面自己**认可，而不只是被 SDK 读回。

**活推导**：写入走「原生 setter 改 IDL + 派发真实 `input` 事件」，让 React 受控状态同步；
写入回执同时给出 `idl` 与 `hasAttr`，与 `get_value()` 三方对照。

## 4. 实测行为记录 / 已知边界

**前置条件：动态 ID 开关（会翻转，必须每次检查）**

靶场 `FormControlsPage.tsx:491` 的 `readDynamicIdsPreference()` **默认返回 true**，状态持久化在
`localStorage['form-controls-dynamic-ids']`。开启时 id 变成 `form-controls-native-text_<随机>`，
而库元素路径**必需**固定 id → 全部本组库元素同时失效。

脚本按 `web/表单元素复测清单.md` 的规则处理：先读地面真值（DOM 实际 id），**只在动态时**点一次
开关关闭。**该分支已双向实测**（强制开启动态 ID 后复跑）：

| 步骤 | 实测 |
| --- | --- |
| 强制 `localStorage=true` + 刷新 | id 变为 `form-controls-native-text_3DCxnclfPt1N` |
| 动态状态下的固定元素 | `find_all` = **0**（确认失效机制） |
| 动态状态下的开关元素 | 仍可绑定：`role=switch aria-checked=true`（其路径只依赖 `span.ant-switch-inner`） |
| 复跑脚本 | 自动关闭开关，**17/17 退出码 0**，用例 04 记为「本轮曾开启并已关闭」 |
| 最终状态 | id 还原 `form-controls-native-text`，`localStorage='false'` |

**其他实测边界**

- **`''` 与 `None` 的区分成立**：空输入框返回 `''`，无 `value` property 的节点返回 `None`。
- **滑块初始值是 `'0'` 而不是 `''`**：`input[type=range]` 的 IDL `value` 默认即 `"0"`。
- **本 fixture 无法证伪 IDL 与 content attribute 的分歧**：页面侧实测该 input 的
  `getAttribute('value')` 初始为 `''`（`hasAttribute` 为 true），写入后**同步变成写入值**——
  两者在本页同进同退。加上 `get_attribute()` 的 `?? element[name]` 回退，这条区分在本轮
  **没有可证伪的样本**，故未作为判据。
- **DOM 值与页面表单状态可能不同源**：空 `number` 控件的 DOM `value` 是 `''`，而页面自己提交的
  快照里是 `null`。这是「DOM IDL」与「Ant form 状态」两个来源的差异，不是本 API 的缺陷。
- **必须由实时 `find` 取得**：`_run_web_value` 要求 `locator_kind == "runtime_ref"`，
  仅从库目录取得的条目不能直接读取。
- **页面失效**：`close()` 之后读取返回 `stale_page_reference`。
- **一次未复现的瞬时现象**：探针 3 中在「写入 → 提交 → 重复读取」之后，
  库元素 `web靶场_表单测试_原生_重置` 出现过一次 `ActionError: 未找到指定ID的元素`；
  随后专门复核（提交前/提交后/原生点击后各测一次）**4/4 均能绑定**，未复现。
  本脚本**不依赖该元素**（还原用页面侧写回空串），故不影响结论；如实记录供后续复测者留意。

**明确排除（未覆盖）**

- Edge；闭合 Shadow DOM。
- **模拟人工 `input`（`simulative=True`）之后再读 `get_value`** —— 本轮走页面侧写入，
  未使用真实键盘输入；这条沿用旧证据的排除项。
- **只读 / 禁用控件的 `value` 边界** —— 元素库 `260902_web元素` 里**没有**对应库元素
  （已核对：无 `只读/禁用/readonly/disabled` 命名的条目），需先采集才能覆盖。
- **IDL 与 content attribute 的分歧**（见上，本 fixture 无样本）。
- `locator_kind != runtime_ref` 的报错路径（公开面没有入口构造该状态）。
- 元素库捕获期会话字段在不清理时的直连行为。

## 5. 修订记录（相对 2026-08-08 旧结论）

旧版本文件（YAML 风格，`source_commit_at_doc_time: 1b2d10fd…`）记录如下，按「保留原结论」留档：

- 旧验证日期 2026-08-08；靶场 `http://localhost:7199/form-controls`（**本地 dev server**，
  现已不存在）；元素 `input元素` / `重置_html`，属 `tests/SDK/web/web测试元素库`（产品仓库路径）。
- 旧场景准备用 `input(simulative=False)` 写入随机值，再读 `get_value()`；示例值 `gv_499b74c7c10b`。
- 旧记录把合同写成 **`get_value() -> str`**；清理记为「本次资源 3/3」。
- 旧明确排除包含：Edge/CEF/Auto、**模拟人工 `input` 后再 `get_value`**、
  **空值、只读控件、非输入控件的 `value` 边界**、捕获期会话字段。

本次修订与差异：

1. **合同订正**：返回注解由 `str` 订正为 **`str | None`**，并新增 `None` 负例实测
   （radio label 元素），覆盖原排除项中的「非输入控件的 `value` 边界」。
2. **原排除项「空值」已撤销**：本轮实测空输入框返回 `''`（非 `None`），并作为独立判据。
3. **靶场与元素更换**：改用标准靶场 `#/iframe-shadow-form` 与库元素
   `web靶场_表单测试_原生_输入框`；旧靶场是不可复现的本机端口。
4. **旧脚本在本工作区不可复现**：其默认元素库 `sdk测试/web/web测试元素库` 不存在，
   且脚本没有 `--library` 参数。本次已就地重写，并新增
   `--library` / `--element` / `--target-url` 参数。
5. **新增判据**：动态 ID 前置条件（含双向恢复实测）、页面侧 IDL 跨通道一致、
   页面自身表单状态回显、活写入读回、控件矩阵、零参数合同、`stale_page_reference`。
6. 旧文件本身在 git 历史中保留，不删除。

## 6. 复测

在 `D:\code\元素库\sdk测试` 目录运行：

```powershell
uv run .\web\test_web_element_get_value.py
```

仅检查合同（不连接 Runtime、不打开浏览器、不复制元素库）：

```powershell
uv run .\web\test_web_element_get_value.py --contract-only
```

归档 JSON 报告：

```powershell
uv run .\web\test_web_element_get_value.py --json
```

退出码约定：`0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED
（靶场结构未就绪、动态 ID 无法关闭、元素绑定失败均记 2）。
