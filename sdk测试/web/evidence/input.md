# `uiautoma.web.WebElement.input()` 验证证据

## 当前结论（2026-10-08）

**VERIFIED（后台范围）：连续三次正式完整运行，每轮 60/60 PASS，退出码均为 0。**

- 只读 worktree：`D:\code\desktop`；源码快照 commit：`7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。结论限于该 SDK 源码快照和本次实际 dev Runtime/Chrome 行为。
- 靶场：[iframe/open Shadow 表单](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：`D:\code\元素库\260902_web元素`。
- Ant 输入框：`web靶场_表单测试_ant_输入框`；原生输入框：`web靶场_表单测试_原生_输入框`。两项库选择器各唯一命中一个对应 input。
- 默认后台运行：`silent_running=True`；没有系统鼠标、键盘、剪贴板读写操作。系统模拟键盘、实际鼠标锚点、英文输入法切换不在本次 VERIFIED 范围。
- 每轮清理 PASS：标签 **2→2**，无外部增删；自有页面/库关闭、临时库副本删除、源 elements.json 不变，并恢复动态 ID 开关及原 localStorage 值。
- 日期使用本对话 2026-10-08；原始输出和 JSON 保留实际计数。

## 用途、参数与返回

填写网页输入框；`append=False` 覆盖、`append=True` 追加。成功返回 `None`。本轮同时验收真实表单提交状态，不能只以 DOM value 正确判断通过。

```python
input(self, text: str, *, simulative: bool=True, cdp_input: bool=False,
      append: bool=False, contains_hotkey: bool=False, force_ime_eng: bool=False,
      send_key_delay: int=50, focus_timeout: int=1000, delay_after: float=1,
      click_before_input: bool=True, anchor: object | None=None,
      input_check: bool=False, retry_times: int=3, check_value: str='') -> None
```

| 参数/组合 | 当前合同与本次覆盖 |
|---|---|
| text / append | 中文、emoji、字面快捷键符号、覆盖、追加、空文本清空；两侧 DOM 与提交值都核对 |
| simulative=False | 普通 DOM 输入；覆盖两输入框受控表单状态 |
| 默认 simulative=True、静默页面 | Runtime 转为 DOM 填写；**不是系统模拟键盘验收** |
| cdp_input=True | 优先使用 CDP；含 simulative=True 同时开启的组合、中文/emoji、追加、快捷键 |
| contains_hotkey | CDP 的 `^a新值` 替换；DOM 快捷键拒绝；静默普通快捷键支持边界见下文 |
| click_before_input=False | DOM 不主动聚焦仍成功；CDP 已聚焦成功、未聚焦抛 ActionError / element_not_focused |
| input_check / check_value | 默认按 text 比较、显式值成功、错误预期值失败；追加/快捷键校验必须提供完整预期值 |
| retry_times | 0 次重试只输入 1 次；2 次重试共输入 3 次；首次人为不匹配后恢复成功；追加失败仅输入一次、不重试 |
| delay_after | None、0、1 秒；1 秒场景用 input 调用自身耗时 ≥0.95 秒验收 |
| force_ime_eng / send_key_delay / focus_timeout / anchor | 静默默认输入同时传入这些参数成功；仅证明静默分支接收并按 DOM 填写，未验证系统键盘/鼠标效果 |

## 期望值来源与独立确证

1. 每个场景先点击**真实表单重置按钮**，等待空值和结果占位文字恢复；重置后重新从元素库获取 input，避免旧节点引用。
2. 只对用户指定两个库元素调用被测 `input()`；准备/提交通过后台 DOM 点击现有按钮。没有按 CSS 替换被测输入元素或自造靶场。
3. 直接读取 ShadowRoot 中对应 input.value，与手写预期文本比较。目标 SDK 的 get_value() 不是正确性的唯一来源。
4. 点击真实提交按钮，等待 `ant-result` / `native-result` 的 JSON；读取实际表单状态的 text，再与独立预期比较。
5. 在自有页面 MAIN 环境仅截获 navigator.clipboard.writeText，把真实提交处理器传给它的 JSON 留在该标签内，并核对它与页面渲染结果完全一致。表单输入处理器、校验和提交取值逻辑保持原状；不读写用户系统剪贴板。
6. 在既有 ShadowRoot 捕获 input 事件；据事件数确认重试次数。恢复重试场景只在首次 input 事件后人为造成一次不匹配，下一次恢复；这项有明确测试干预，不当作无干预普通输入场景。

## 源码合同与链路

[冻结合同](../element_input_contract_20261008.json) 保存签名、docstring、源码、位置和文件 SHA-256；以下均相对于上述 worktree/commit：

| 层 | 快照位置 |
|---|---|
| SDK | `sdk/src/uiautoma/web/element.py:322`；验证选项 helper :24；成功后 _finish 调用 sleep_after |
| Client/RPC | `sdk/src/uiautoma/_core/client.py:3737` → `web.action.type_text` |
| Pipe | `runtime/services/pipe_server.py:2085` |
| Runtime | `runtime/services/action_service.py:2378` 输入校验/重试；:6008 静默普通快捷键拒绝；:6239 静默 keyboard 改为 dom |
| DOM Engine | `chrome/engine/engine_packages/page_engine_runtime.js:2106` 输入事件；:2112 原生 setter；:2667 CDP 聚焦；:2701 普通 DOM 写入和事件同步 |
| CDP Engine | `chrome/engine/plugin_packages/command_legacy_package.js:5180`；:5220 发送编译后的输入/快捷键 |

SDK/Runtime 合同：simulative 必须 bool；启用校验时 retry_times 必须非负整数且不是 bool；追加/快捷键校验缺少 check_value 拒绝。默认静默普通输入不支持 contains_hotkey，需显式用 CDP。检查失败抛 ActionError / input_check_failed；CDP 未聚焦抛 ActionError / element_not_focused。输入校验失败时写入已发生，不能解释为“完全没有写入”。

## 正式矩阵与结果

12 项合同/参数验证 + 1 项环境 + 2 项库映射 + 每侧 22 个场景（共 44） + 1 项清理 = **60 项**。

| 每侧场景 | 判据 | 三轮结果 |
|---|---|---|
| dom_unicode / dom_literal_symbols | 中文/emoji/特殊符号原样写入并提交 | PASS |
| dom_overwrite / dom_append / dom_empty_clear | 覆盖、追加、空文本语义与提交一致 | PASS |
| silent_default / silent_ignored_keyboard_options | 静默默认及键盘参数组合采用 DOM，提交正确 | PASS |
| dom_no_click | 不聚焦仍正确填写和提交 | PASS |
| delay_none / delay_one_second | 不等待/一秒等待和提交正确 | PASS |
| check_default / check_explicit | 默认/显式预期值校验成功 | PASS |
| check_fail_zero / check_fail_two | 错误预期值按次数后抛 input_check_failed，事件数为 1 / 3 | PASS |
| check_recovery | 首次受控不匹配，第二次恢复成功，事件数为 2 | PASS |
| check_append_no_retry | 追加后校验失败只写一次，已追加文本仍正确提交 | PASS |
| cdp_unicode / cdp_append / cdp_priority | CDP 输入、追加及优先组合正确 | PASS |
| cdp_no_click_focused / cdp_no_click_unfocused | 已聚焦成功；未聚焦按合同报错、空值保留 | PASS |
| cdp_hotkey_replace | ^a 选择全部后输入，最终提交“新值” | PASS |

| 正式运行 | 结果 | 退出码 | 清理 |
|---|---|---|---|
| run1 | 60/60 PASS | 0 | PASS，2→2 |
| run2 | 60/60 PASS | 0 | PASS，2→2 |
| run3 | 60/60 PASS | 0 | PASS，2→2 |

## 历史缺陷、准备修正与边界

- [历史 #65](https://github.com/uiautoma/desktop/issues/65) 已 CLOSED；开发者记录修复 commit fd7d610，本轮快照包含该提交。2026-09-20 的两模式各 18/25 失败记录仍保存在[历史证据](element_input_native_form.md)。
- 本轮双输入框 DOM 提交状态均通过，证明指定 iframe/open Shadow 场景当前行为恢复；没有声称本轮复测过非 iframe 页面、Edge 或历史所有场景。
- 准备阶段 uv 默认缓存目录受沙箱权限限制，改用工作区临时缓存；默认沙箱 IPC 连接失败，而同一探针在获得本机 Named Pipe 访问权限后成功。此为执行环境权限，未误报产品故障。
- [六项先行探针](artifacts/element_input_20261008_six_mode_probe.json) 与 [60 项矩阵探针](artifacts/element_input_20261008_probe_matrix.json)均为正式化前准备，不混入正式三轮计数。
- 系统模拟键盘分支、IME 切换、实际鼠标锚点及物理按键间隔/焦点等待尚未复测。`--foreground` 是该分支的手工补验入口，会占用电脑，未计入本轮 60 项结果。
- 本次未生成或修改公开 API 文档；按 AGENTS.md 文档门槛单独征询用户。

## 唯一脚本与复测方式

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_element_input.py
```

默认后台同时测试 Ant 与原生输入框。记录 JSON 可加：

```powershell
uv run .\web\test_web_element_input.py --report-file .\web\evidence\artifacts\element_input_manual.json
```

旧 runner、表单包装器和原生表单 runner 已[归档](../../issues/input_history_20261008/README.md)，不再作为活动入口。产品源码未修改。

## 原始材料

- [run1 JSON](artifacts/element_input_20261008_run1.json) / [输出](artifacts/element_input_20261008_run1.txt)。
- [run2 JSON](artifacts/element_input_20261008_run2.json) / [输出](artifacts/element_input_20261008_run2.txt)。
- [run3 JSON](artifacts/element_input_20261008_run3.json) / [输出](artifacts/element_input_20261008_run3.txt)。
- [本轮汇总与 SHA-256](artifacts/element_input_20261008.txt)。
- [已执行诊断源码和准备说明](../../issues/input_history_20261008/diagnostics/README.md)。
