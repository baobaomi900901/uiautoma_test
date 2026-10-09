# `uiautoma.web.WebElement.is_enabled()` 验证证据

## 当前结论（2026-10-08）

**READY_FOR_LIVE：连续三轮完整验收，每轮 30/32 PASS、2 FAIL、0 BLOCKED，退出码 1。两项失败是同一产品缺陷在两个按钮上的复现。**

用户指定的原始场景均通过：

| 库元素 | 唯一 DOM 命中 | 浏览器 disabled / :disabled | `is_enabled()` |
|---|---|---|---|
| `web靶场_disabled_按钮` | `BUTTON#btn-disabled-click-target` | True / True | **False，PASS** |
| `web靶场_测试点击_单击触发` | `BUTTON#btn-click-target` | False / False | **True，PASS** |

- 靶场：[keys-click-test](https://baobaomi900901.github.io/xpath/#/keys-click-test)。
- 元素库：`D:\code\元素库\260902_web元素`。每轮连接临时副本，仅清空副本内陈旧 session/BrowserPid；保留原选择器。
- desktop 只读 worktree：`D:\code\desktop`；HEAD commit：`7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。文件 SHA-256 与方法源码另存于合同快照，结论绑定该源码快照及本次实际 dev Runtime/Chrome，未独立确认运行时二进制构建 commit。
- 靶场只读源码：`D:\code\xpath\WEB\src\pages\KeysClickTestPage.tsx:365`、`:396`；React Ant Button 最终渲染为上述两个原生 BUTTON。线上 DOM 是测试参考，本地 TSX 只是辅助来源。
- `silent_running=True`；未调用窗口激活、点击、系统键鼠或剪贴板操作。
- 每轮清理 PASS：标签 **2→2**，无外部增删；自有页面与连接关闭、副本删除；源 elements.json SHA-256 不变。
- 每轮自有页面 click/input/change/keydown 计数均为 0；两个按钮的属性、焦点、滚动恢复到本次初始值。

| 正式轮次 | 完整结果 | 原始 UTF-8 日志 | 完整 JSON |
|---|---|---|---|
| 1 | 30/32 PASS，2 FAIL，退出码 1 | [run1.txt](artifacts/element_is_enabled_20261008_run1.txt) | [run1.json](artifacts/element_is_enabled_20261008_run1.json) |
| 2 | 30/32 PASS，2 FAIL，退出码 1 | [run2.txt](artifacts/element_is_enabled_20261008_run2.txt) | [run2.json](artifacts/element_is_enabled_20261008_run2.json) |
| 3 | 30/32 PASS，2 FAIL，退出码 1 | [run3.txt](artifacts/element_is_enabled_20261008_run3.txt) | [run3.json](artifacts/element_is_enabled_20261008_run3.json) |

原始日志有逐项期望、实际、耗时；JSON 保留每次读取前后的独立 DOM 状态。合同检查另为 **3/3 PASS、SKIPPED**，不计入实际功能验收。[汇总和 SHA-256 清单](artifacts/element_is_enabled_20261008.txt)。

## 用途与合同

判断网页元素是否可用；成功返回 Python `bool`，可用为 True、禁用为 False。只读方法，不接收 timeout 或其他业务参数。

```python
is_enabled(self) -> bool
```

合同冻结：[element_is_enabled_contract_20261008.json](../element_is_enabled_contract_20261008.json)，含公开签名、docstring、方法源码、12 段链路源码和文件哈希，以及靶场辅助源码快照。

上述 desktop worktree/commit 的调用链：

1. `sdk/src/uiautoma/web/element.py:866` → `self._raw.is_enabled()`。
2. `sdk/src/uiautoma/_core/client.py:3585` / `:3595` → `_read_state("is_enabled")`，RPC `web.is_enabled`，内部 timeout 5000ms，`bool(result["value"])`。
3. 实时元素会话 `client.py:2130` 传 `locator_kind="runtime_ref"` → SDK RPC 业务错误映射。
4. `runtime/services/pipe_server.py:2136` → `ActionService.web_is_enabled_element`（`:2591`）→ `_run_web_value`（`:6350`）。Runtime 解析实时元素和 page_ref 后调用 Web bridge。
5. `runtime/web/bridge_client.py:94` → `web.action` → `chrome/engine/engine_packages/page_engine_runtime.js:2780`。快照实现沿父节点检查 disabled、aria-disabled、class；该源码行为不直接充当预期值算法。

| 失败条件 | 预期类型/文案 | 路径与覆盖 |
|---|---|---|
| 多余位置参数或关键字 | `TypeError` | Python 签名校验；raw 调用 0 次，PASS |
| 自有页面关闭后的旧元素对象 | `ActionError`；`网页对象已失效`；trace `stale_page_reference` | Runtime page_ref 解析，PASS |
| 库连接关闭后的旧元素对象 | `HostUnavailableError`；`元素对象所属连接已关闭，请重新获取对象` | SDK 会话关闭检查，PASS |
| 浏览器桥接不可用或元素节点失效 | 按 Runtime/引擎的 error/trace 映射；不应伪造 False | 已查阅失败分支，未注入故障，不宣称该分支实测通过 |

## 期望值来源与独立确证

先用保存的库元素 `page.find_all(name)`，断言命中数量为 1，并核对 SDK 对象的 DOM ID。被测调用始终为该库对象的 `is_enabled()`。

参考通道是页面 JavaScript 读取实际 BUTTON 的原生 `disabled` IDL 和浏览器 `matches(':disabled')`，同时保留属性列表；没有从 SDK `get_attribute('disabled')` 推导预期，也没有复刻引擎的字符串分支。读取前后比较两个按钮属性、焦点、滚动和事件计数，排除本次调用修改状态。

原始 disabled 空串及属性变体按 HTML 布尔属性的存在语义判断；即使属性值为字符串 false，存在的 disabled 仍表示禁用。字符串 true/false 不符合 HTML 布尔属性的编写规则，但浏览器仍将该节点判定为禁用，因此保留为健壮性边界用例。依据：[HTML Standard，Boolean attributes](https://html.spec.whatwg.org/multipage/common-microsyntaxes.html#boolean-attributes)。

ARIA 用例先移除原生 disabled，再分别设置 aria-disabled 为 true、false 或缺失，检查实际属性准备完成。预期采用 ARIA 状态语义和公开“是否可用”合同；这些是已有按钮上的受控状态干预，不代表靶场原始按钮自带 ARIA。ARIA 禁用声明与浏览器原生 disabled 是两种不同状态；本轮没有验证 ARIA 是否阻止实际点击。依据：[WAI-ARIA 1.2，aria-disabled](https://www.w3.org/TR/wai-aria-1.2/#aria-disabled)。

## 用例与实测行为

| 用例组 | 数量 | 三轮每轮结果 |
|---|---:|---|
| 合同、无参数签名校验 | 3 | 3 PASS |
| 环境、两个库元素唯一映射 | 3 | 3 PASS |
| 两个原始按钮状态 | 2 | 2 PASS |
| 两按钮 × disabled 空串/disabled/true/false/False | 10 | 8 PASS、2 FAIL，失败均为小写 false |
| 两按钮 × disabled 属性动态 False→True→False | 2 | 2 PASS，API 顺序 True→False→True |
| 两按钮 × aria-disabled true/false/缺失 | 6 | 6 PASS |
| 两按钮各连读三次，确认只读 | 2 | 2 PASS |
| 状态恢复、页面关闭、连接关闭、资源清理 | 4 | 4 PASS |
| **总计** | **32** | **30 PASS、2 FAIL、0 BLOCKED** |

只在自有测试标签上的现有两个按钮临时改属性；每条干预用例以 finally 恢复，不新建测试控件。所有正式用例无人干预跑完。

### 失败定性与 Issue 交接

**产品缺陷，靶场与库定位正常。** `disabled_false_disabled_button` 和 `disabled_false_click_button` 均出现：

```json
{"disabled_attribute":"false","dom_disabled":true,"pseudo_disabled":true,
 "expected_is_enabled":false,"actual_is_enabled":true,"return_type":"bool","readonly":true}
```

两库元素定位唯一、DOM 原生属性与伪类一致、读取前后状态未变；同一准备流程的其他属性值均通过，三轮稳定复现。源码快照 `page_engine_runtime.js:2787` 使用 `disabled != null ? disabled !== "false"`，与实测误判一致。未修改产品源码。

现有 [Issue #23](https://github.com/uiautoma/desktop/issues/23) 只读核对为 OPEN；经用户授权，[已补充复测评论](https://github.com/uiautoma/desktop/issues/23#issuecomment-6055620980)，同时请求修正文中将 HTML disabled 字符串 false/False 视为可用的旧验收条件。[测试侧交接材料](../../issues/issue_23/is_enabled_retest_20261008.md)。

## 覆盖边界与历史

本轮限于 Chrome、上述两个 Ant Button 渲染出的原生 BUTTON。未验收 fieldset 继承、祖先 disabled/aria-disabled、CSS class 禁用启发式、iframe/Shadow DOM 目标、节点移除/页面刷新、断网或桥接中断等场景。返回 bool 的正常协议路径已测，没有注入畸形 RPC value。没有把缺陷改为 KNOWN/跳过，也没有因原始两个按钮通过而提升到 VERIFIED。

- 2026-08-09 disabled 空串误判记录与旧脚本：[历史归档](../../issues/is_enabled_history_20261008/README.md)。当前两个按钮的空串用例已通过，不应把历史错误当成本次结果。
- 2026-10-04 原生输入框 disabled="false" 8/9、三轮失败：[历史证据](element_is_enabled_20261004.md)，原始日志保持原样。
- 先行探针：[JSON](artifacts/element_is_enabled_20261008_probe.json)、[日志](artifacts/element_is_enabled_20261008_probe.txt)、[探针源码](artifacts/element_is_enabled_20261008_probe.py.txt)。原始两个按钮、属性变体、动态状态、ARIA 和生命周期在写正式脚本前已探明。

## 当前唯一入口

[test_web_element_is_enabled.py](../test_web_element_is_enabled.py)。在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_element_is_enabled.py
```

可用 `--contract-only` 仅核对合同，或 `--report-file .\web\evidence\artifacts\is_enabled_manual.json` 留存本次完整报告。默认后台创建并关闭自有页面，不依赖用户当前选中的网页。退出码 0 全通过、1 存在 FAIL、2 存在 BLOCKED。

本轮 API 状态仍为 READY_FOR_LIVE，未达到公开文档更新门槛；仅更新测试证据与两处状态索引。
