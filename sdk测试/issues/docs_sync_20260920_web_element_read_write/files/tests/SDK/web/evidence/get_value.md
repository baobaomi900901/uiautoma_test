# `uiautoma.web.WebElement.get_value()` 验证证据

## 1. 用途与合同

读取**当前网页元素的 value property（IDL）**——不是 HTML 的 `value` 内容属性。

```python
WebElement.get_value(self) -> str | None
```

公开签名**没有任何参数**。返回原生 `str`；节点没有 `value` property 时返回 `None`
（引擎把 `null` 原样透出，SDK 只把非 `None` 值转 `str`）。

| 层 | 位置 | 事实 |
| --- | --- | --- |
| SDK 公开对象 | `sdk/src/uiautoma/web/element.py:548` | `get_value(self) -> str | None`，无参数 |
| SDK Raw | `sdk/src/uiautoma/_core/client.py:3944` | `get_value(*, timeout: float = 5.0) -> str | None`；`None` 原样返回，其余 `str(...)` |
| RPC 名 | — | `web.get_value` |
| 能力/参数 | `runtime/services/capabilities.py:274,483` | 必填 `package_token` / `element_id` / `timeout_ms`；capability `web_dom_actions_stage5` |
| Runtime 业务 | `runtime/services/action_service.py:2489` → `6102` | `web_get_value_element` → `_run_web_value(op="get_value")`；要求 `locator_kind == "runtime_ref"` |
| 桥接 | `runtime/web/bridge_api.py:343` | `m == "web.get_value"` → `action = "get_value"` |
| 引擎 | `chrome/engine/engine_packages/page_engine_runtime.js:3669` | `element.value`；`null` 原样返回 |

两条容易踩的实现细节：

1. `get_attribute("value")` **不能**当内容属性的对照：引擎（同文件 `:3688`）是
   `element.getAttribute(name) ?? element[name]`，属性缺失时会回退到 IDL 属性，两者被混同。
2. 引擎的 `get_value` 分支还有 `mode === "input_check"` 与 `mode === "cdp_ready"` 两条内部路径，
   但公开 `get_value()` 不发送 `mode`，**公开面无法触达**。

## 2. 真实验收结果

**VERIFIED：17/17 通过，退出码 0；连续 3 次完整运行全绿（2026-09-20）。**

- 靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`。
- 元素库/元素：`260902_web元素` → `web靶场_表单测试_原生_输入框`
  （iframe → open shadow DOM 内的 `input#form-controls-native-text`）。只用副本。
- 被测 worktree 基线：`c101caa9dcd115a461fc71ecaed351b0dea880b8`；`sdk/`、`runtime/`、`chrome/`
  无本地改动。Runtime `0.1.0`，protocol 1。
- 运行脚本：外部 `sdk测试` 工作区 `web/test_web_element_get_value.py`。
- 归档原始输出：该工作区 `web/evidence/artifacts/element_get_value_20260920.txt`。

| # | 用例 | 实测结果 |
| --- | --- | --- |
| 01 | 公开签名 | 通过；`(self) -> 'str \| None'` |
| 02–05 | 元素库副本、靶场页面、动态 ID 前置条件、元素绑定 | 全部通过 |
| 06 | 空值语义 | 通过；空输入框返回 `''`（`str`），**不是 `None`** |
| 07 | 与页面侧 IDL 跨通道一致 | 通过 |
| 08 | 页面侧写入后读回 | 通过；写入值精确读回 |
| 09 | 页面**自身**表单状态确认 | 通过；提交回显 JSON 含该值 |
| 10 | 连续 3 次读取 | 通过；一致 |
| 11 | 还原并复核 | 通过 |
| 12 | `None` 负例 | 通过；radio label 元素返回 `None` |
| 13 | 控件矩阵 | 通过；密码/邮件/数字/文本域/select/提交 = `''`，滑块 = `'0'`，均与页面侧一致 |
| 14–15 | 参数边界 | 通过；`TypeError` |
| 16 | 页面关闭后读取 | 通过；trace=`stale_page_reference` |
| 17 | 资源清理 | 通过 |

## 3. 期望值来源与独立确证

**独立推导**（DOM 规范）：空输入框的 IDL `value` 是空字符串 `""`；`""` 与 `None` 必须可区分，
`None` 只表示「该节点没有 `value` property」。

**独立确证（跨通道）**：页面侧经
`iframe.contentDocument → #form-shadow-host → shadowRoot → getElementById(...)` 直读 `el.value`，
与 SDK 返回逐项对照；主元素与 7 个控件全部一致。

**独立确证（页面自身状态，完全不经过 SDK）**：点页面自己的「提交」触发
`handleNativeSubmit()` → Ant form 实例生成快照 → 写入 `#native-result`（并同时写剪贴板）。
实测回显含写入值，证明该值被**页面自己**认可。

**活推导**：写入走「原生 setter 改 IDL + 派发真实 `input` 事件」，让受控状态同步；
写入回执同时给出 IDL 值与属性存在性，与 `get_value()` 三方对照。

## 4. 实测行为记录 / 已知边界

- **前置条件（会翻转）**：靶场「动态 ID」开关默认开启且状态持久化；开启时元素 id 带随机后缀，
  固定 id 的库元素路径全部失效。脚本先读地面真值（DOM 实际 id），只在动态时关闭开关。
  该分支已**双向实测**：强制开启后固定元素 `find_all` 为 0、开关元素仍可绑定，复跑脚本自动
  关闭并仍 17/17，最终状态还原。
- **`''` 与 `None` 的区分成立**：空输入框 `''`；无 `value` property 的节点（radio label）`None`。
- **滑块初始值是 `'0'` 而不是 `''`**：`input[type=range]` 的 IDL 默认即 `"0"`。
- **本 fixture 无法证伪 IDL 与内容属性的分歧**：页面侧实测该 input 的 `getAttribute('value')`
  初始为 `''`，写入后同步变成写入值——两者同进同退；加上 `get_attribute()` 的回退实现，
  这条区分在本轮**没有可证伪样本**，未作为判据。
- **DOM 值与页面表单状态可能不同源**：空 `number` 控件的 DOM `value` 是 `''`，而页面自己提交的
  快照里是 `null`。这是两个来源的差异，不是本 API 的缺陷。
- **页面失效**：`close()` 之后读取返回 `stale_page_reference`。
- **一次未复现的瞬时现象**：探针阶段，库元素 `web靶场_表单测试_原生_重置` 出现过一次
  `ActionError: 未找到指定ID的元素`；随后专门复核（提交前/提交后/原生点击后）4/4 均能绑定，
  未复现。验收脚本不依赖该元素。
- **明确排除（未覆盖）**：Edge；闭合 Shadow DOM；模拟人工 `input`（`simulative=True`）之后再读；
  只读/禁用控件（元素库中**没有**对应元素，需先采集）；`locator_kind != runtime_ref` 的报错路径
  （公开面无入口构造）。

## 5. 修订记录（相对 2026-08-08 旧结论）

旧记录（`source_commit_at_doc_time: 1b2d10fd…`）：

- 日期 2026-08-08；靶场 `http://localhost:7199/form-controls`（**本地 dev server**，现已不存在）；
  元素 `input元素` / `重置_html`。场景准备用 `input(simulative=False)` 写随机值再读 `get_value()`；
  示例值 `gv_499b74c7c10b`；清理记为「本次资源 3/3」。
- **旧记录把合同写成 `get_value() -> str`，与源码不符**；当前源码为 `str | None`。
- 旧明确排除包含：Edge/CEF/Auto、模拟人工 `input` 后再读、
  **空值、只读控件、非输入控件的 `value` 边界**、捕获期会话字段。

本次修订：

1. **合同订正**：返回注解为 `str | None`，并新增 `None` 负例实测；覆盖原排除项中的
   「非输入控件的 `value` 边界」。
2. **原排除项「空值」已撤销**：实测空输入框返回 `''`（非 `None`），作为独立判据。
3. **靶场与元素更换**：改用标准靶场与库元素 `web靶场_表单测试_原生_输入框`；
   旧靶场是不可复现的本机端口。
4. **新增判据**：动态 ID 前置条件（含双向恢复实测）、页面侧 IDL 跨通道一致、页面自身表单状态
   回显、活写入读回、控件矩阵、零参数合同、`stale_page_reference`。
5. **产品侧 `tests/SDK/web/test_web_element_get_value.py` 本轮未更新**：仍指向已退役的本机靶场
   地址与旧元素库，不能复现本次结果；是否移植外部工作区脚本需单独决定。

## 6. 复测

在外部 `sdk测试` 工作区根目录运行：

```powershell
uv run .\web\test_web_element_get_value.py
```

仅检查合同：

```powershell
uv run .\web\test_web_element_get_value.py --contract-only
```

归档 JSON 报告：

```powershell
uv run .\web\test_web_element_get_value.py --json
```

元素库位置可用 `--library <目录>` 指定（默认使用该工作区约定的 `260902_web元素`）。

退出码约定：`0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED。
