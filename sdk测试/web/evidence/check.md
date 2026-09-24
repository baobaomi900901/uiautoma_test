# `uiautoma.web.WebElement.check()` 验证证据

## 2026-09-24 Ant「音乐」input 重新抓取后复验

- **结论**：`VERIFIED`。Chrome 的 iframe / Shadow 表单完整脚本连续 3 次均为 `61/61 PASS`、`0 FAIL`、`0 BLOCKED`，退出码均为 `0`；每轮 `cleanup` 也为 `PASS`。
- **源码快照与环境**：只读产品 worktree `D:\code\desktop`，commit `e08eadd0d6d921ea11579e4acfb894c1c4cee038`；本次 dev Runtime、Chrome、<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>，元素库 `D:\code\元素库\260902_web元素` 的临时副本。结论只对应此快照与环境。
- **合同与目标**：`check(self, mode: str='check', delay_after: float=1) -> None`；对 Ant / 原生的 radio、checkbox 的 `input` 与 `label` 验证 `check`，对 checkbox 追加幂等、`uncheck`、`toggle`，并验证非法参数和 radio 禁止取消。目标调用直接使用 `WebElement.check(...)`。
- **阻塞解除**：用户在 App 里确认旧库项曾高亮 Ant 与原生两个 input，重新抓取后只高亮一个。当前 [`Ant「音乐」input 快照`](../../../260902_web元素/snapshot/02eab3e4-f9e8-4f6b-99f4-47aaa70020d8.json) 把 `id=form-controls-ant-hobbyMusic` 列为必需条件。原第 8 项三轮均通过：`check(mode='check', delay_after=0.05)` 返回 `None`，目标 DOM `checked=True`，Ant 表单提交 `hobbies=['音乐']`，重置后 `checked=False`。这是保存选择器修正后的新结论；下节 2026-09-23 的双匹配阻塞为历史记录。
- **期望值与独立确证**：期望来自页面复选框/单选框和表单语义；脚本在 `check()` 后独立读取目标 DOM 的 `checked`，并点击页面提交按钮读取表单 JSON，不把 `check()` 的返回值当作状态证明。用户另用单独的 `click()` 示例目视确认 Ant「音乐」在重置后取消勾选；该人工观察不计作 `check()` 的自动化用例。
- **收尾与范围**：每轮复核重置、关闭本次页面与元素库连接、删除临时库副本、Chrome 标签数恢复；不验证系统剪贴板。Edge、CEF、动态 ID 开启、其他靶场及更大输入规模未在本轮覆盖。
- **复测**：从 `D:\code\元素库\sdk测试` 运行 `uv run .\web\test_web_element_check_iframe_shadow_form.py --json --report-file .\web\evidence\artifacts\check_20260924.txt`。三份原始报告：[第 1 轮](artifacts/check_20260924.txt)、[第 2 轮](artifacts/check_20260924_run2.txt)、[第 3 轮](artifacts/check_20260924_run3.txt)。退出码 `0` 为全通过，`1` 为失败，`2` 为环境阻塞。

## 2026-09-23 iframe / Shadow 表单复测

- 被测源码快照：`D:\code\desktop`，`main`，commit `31b5b714a6c2ab1e88a5dfc39d1a5cfba2ada098`。以下结论仅对这个 worktree 快照和本次 dev Runtime 有效。
- 靶场：<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>；元素库：`D:\code\元素库\260902_web元素` 的本次临时副本。
- 脚本：[`../test_web_element_check_iframe_shadow_form.py`](../test_web_element_check_iframe_shadow_form.py)；[完整原始报告](artifacts/check_20260923.txt)。运行 `uv run .\web\test_web_element_check_iframe_shadow_form.py --json --report-file .\web\evidence\artifacts\check_20260923.txt`，报告退出码 `2`。
- 结果：按用户要求移除两项剪贴板基线及全部剪贴板读写/断言后，61 项中 `PASS 60 / FAIL 0 / BLOCKED 1 / KNOWN 0`。仍有 Ant「音乐」input 的元素库定位阻塞，状态维持 `READY_FOR_LIVE`，不提升为 `VERIFIED`。
- 合同：`check(self, mode: str='check', delay_after: float=1) -> None`；`mode` 接受 `check`、`uncheck`、`toggle`，非法值抛 `InvalidParamsError`；radio 的 `uncheck`/`toggle` 抛 `ActionError`，trace 为 `radio_cannot_uncheck`。这些合同与异常项通过。默认 `delay_after=1` 的实测调用耗时约 1.0 秒，自定义 `0.05` 秒约 0.06 秒。
- 核心行为：除未能唯一定位的 Ant「音乐」input 外，Ant 与原生表单的 radio / checkbox `input` 与 `label` 调用 `check()` 均使目标 `input.checked` 变为 `true`，提交后 `gender` / `hobbies` 与期望一致；checkbox 的 `check` 幂等、`uncheck`、`toggle` 状态转移也通过。Ant「音乐」label 已单独通过：返回 `None`、DOM checked 为 `true`、提交 `hobbies=['音乐']`、重置回到 `false`。判据来自目标 DOM 与表单提交 JSON，未把方法返回值当成状态证明。
- 21/63 初次结果的原因：脚本在重置后立即查找和操作元素，撞上 React 重渲染，产生 `stale_element_reference`；同时过早读取异步勾选状态和上一轮提交 JSON，造成假失败。修正脚本时序后，这些失败消失。测试未证明当前 SDK 的 `check()` 有功能缺陷；异步事件完成时间仍需由调用方按目标状态等待。
- 剪贴板已排除：脚本仍点击提交以核对表单 JSON，但不检查也不修改系统剪贴板。后台页面的 `navigator.clipboard.writeText` 曾报 `NotAllowedError: Document is not focused.`；靶场会显示“复制失败, 请检查浏览器剪贴板权限”。这属于本轮已放过的靶场副作用，弹窗仍可能出现，不影响 DOM 与提交 JSON 判定。
- 元素库边界：[`snapshot/02eab3e4-f9e8-4f6b-99f4-47aaa70020d8.json`](../../../260902_web元素/snapshot/02eab3e4-f9e8-4f6b-99f4-47aaa70020d8.json) 对 Ant「音乐」input 只要求 `type=checkbox` 与 `value=音乐`；Ant 专属 class 和带随机后缀的旧 ID 是可选条件。实测 `find_all` 返回 `form-controls-ant-hobbyMusic` 与 `form-controls-native-hobbyMusic` 两个节点，SDK 的 `page.find()` 按其唯一匹配合同抛 `AmbiguousElementError`，正式用例尚未执行到 `check()`。单独探针从两个匹配中明确选取 Ant 节点后，`check(mode='check')` 返回 `None`、DOM checked 从 `false` 变 `true`、提交 `hobbies=['音乐']`。因此该阻塞是当前保存选择器不唯一，并非 `check()` 对该 input 无效。同一元素库其他 Ant checkbox input 将稳定的 Ant ID 设为必需条件，未出现该歧义；现有证据不能进一步断言抓取生成算法本身有缺陷。
- 测试脚本问题与修正：旧脚本对 label 用例还额外 `page.find()` 同名 input 以取得 ID，致使本来唯一的 Ant「音乐」label 也被阻塞。现用 label 自身的 `control.id` / 子 input ID 取得关联控件，保留对抓取 label 的 `check()` 调用；本轮已通过。
- 收尾：对应重置按钮逐项调用并检查目标 checked 回到 `false`；关闭本次标签和元素库连接，删除本次临时副本，标签数恢复到运行前基线；收尾项 `PASS`。原动态 ID 开关为 `false`，未改变。

下列 2026-08-08 记录是旧靶场、旧元素库和旧源码快照的历史证据，保留原文以便比较。

```yaml
api: "uiautoma.web.WebElement.check"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_html_label_check_ok: "FAIL"
  chrome_ant_label_check_ok: "FAIL"
  chrome_html_input_form_state_ok: "FAIL"
  chrome_ant_input_ui_state_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defects:
    - "element_not_checkable on label targets"
    - "check() DOM property write does not update React/Ant controlled checkbox state"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.check 的最小 SDK、Runtime 与 Page Engine 勾选实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.check", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.check"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_check"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_check_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
    - path: "chrome/engine/engine_packages/page_engine_runtime.js"
      symbols: ["setCheckedState", "setNativeElementProperty"]
      fingerprint: "74f92c170d1d67adae3adae8136eac273d445d82"
  verified_contract:
    signature: "check(mode='check', delay_after=1) -> None"
    parameter_order: ["self", "mode", "delay_after"]
    defaults:
      mode: "check"
      delay_after: 1
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "element_not_checkable"
      affected: "label 目标（checkbox_html_input / checkbox_组件_label）"
      product_source_modified: false
    - trace_info: "controlled_checkbox_state_not_updated"
      affected: "React/Ant 受控复选框真实表单或 UI 状态"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_check.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "621dc0893cbdd3d4c5eb2a6c340faee88f2295a6"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "45299a1c5e4afa2bbfeb55cd24c424cff05dfbba"
  html_label_name: "checkbox_html_input"
  ant_label_name: "checkbox_组件_label"
  ant_input_name: "checkbox_组件_input"
  submit_element_name: "提交_html"
  reset_element_name: "重置_html"
source_commit_at_doc_time: "8a44c023de66eea2a140f7a2fb536a9ff25a7ae8"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_check.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_check.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_check.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`；`finally` 中删除该副本。诊断输出到 stderr，stdout 为 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` / `提交_html` 的 `click()`；HTML 路径下通过 `children()` 取 label 内
  input（仅用于逼近可勾选目标，不是公开合同的一部分）。
- 目标 API：直接调用 `WebElement.check(...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.check
  -> RawWebElement.check
  -> AutomationDispatcher._handle_web_action_check
  -> ActionService.web_check_element
  -> page_engine setCheckedState / setNativeElementProperty
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `mode`/`delay_after` 默认值与 `None` 返回注解 |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与五库项可用 |
| 页面与库连接 | `PASS` | 绑定成功 |
| HTML label 直接 check | `FAIL` | `element_not_checkable` |
| Ant label 直接 check | `FAIL` | `element_not_checkable` |
| HTML 子 input check + 提交 | `FAIL` | `raw.checked=True` 但 `hobbies is null` |
| Ant input check + class | `FAIL` | `raw.checked=True` 但无 `ant-checkbox-wrapper-checked` |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`（阻塞 `VERIFIED`）
- 靶场：`http://localhost:7199/form-controls`
- 对照：同目标 `click()` 可更新 HTML 表单 `hobbies=['旅行']`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无（本轮仅记录缺口）

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- `mode=uncheck` / `mode=toggle` 完整矩阵。
- `delay_after=1` 耗时验收。
- 以 `click()` 代替 `check()` 作为目标 API 验收。

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/12
