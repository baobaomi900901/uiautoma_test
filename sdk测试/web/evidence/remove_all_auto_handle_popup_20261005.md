# `uiautoma.web.remove_all_auto_handle_popup()` 真实 DOM 弹窗验收（2026-10-05）

## 结果

**VERIFIED：最后连续三轮（第 4、5、6 轮）均为 19/19 PASS、0 FAIL、0 BLOCKED，退出码 0；清理标签均为 4→4。**

共保存六轮正式报告。第 1、2 轮全绿；第 3 轮功能用例通过，但外部新增一个标签导致清理复核失败，原始结果保留为 18/19 PASS、1 FAIL，随后重新完成连续三轮验收。此前 [2026-10-04 条件不足的历史记录](web_remove_all_auto_handle_popup_20261004.md)保留。

| 正式轮次 | 结果 / 退出码 | 清理复核 | 原始报告 |
|---|---|---|---|
| 1 | 19/19 PASS / 0 | PASS，标签 2→2 | [终端](artifacts/remove_all_auto_handle_popup_20261005_run1.txt) / [JSON](artifacts/remove_all_auto_handle_popup_20261005_run1.json) |
| 2 | 19/19 PASS / 0 | PASS，标签 2→2 | [终端](artifacts/remove_all_auto_handle_popup_20261005_run2.txt) / [JSON](artifacts/remove_all_auto_handle_popup_20261005_run2.json) |
| 3 | 18/19 PASS、1 FAIL / 1 | 标签 3→4，外部新增标签；本次页面与临时库已清理 | [纯 JSON 输出](artifacts/remove_all_auto_handle_popup_20261005_run3.txt) / [JSON](artifacts/remove_all_auto_handle_popup_20261005_run3.json) |
| 4 | 19/19 PASS / 0 | PASS，标签 4→4 | [终端](artifacts/remove_all_auto_handle_popup_20261005_run4.txt) / [JSON](artifacts/remove_all_auto_handle_popup_20261005_run4.json) |
| 5 | 19/19 PASS / 0 | PASS，标签 4→4 | [终端](artifacts/remove_all_auto_handle_popup_20261005_run5.txt) / [JSON](artifacts/remove_all_auto_handle_popup_20261005_run5.json) |
| 6 | 19/19 PASS / 0 | PASS，标签 4→4 | [纯 JSON 输出](artifacts/remove_all_auto_handle_popup_20261005_run6.txt) / [JSON](artifacts/remove_all_auto_handle_popup_20261005_run6.json) |

## 用途、合同与源码快照

移除当前 SDK 连接注册的所有网页弹窗自动处理规则。成功返回 None。API 不接收参数，也不负责点击或关闭已经打开的弹窗。

```python
remove_all_auto_handle_popup() -> None
```

| 分支 | 源码合同及失败路径 | 本轮覆盖 |
|---|---|---|
| 无参数、无默认值 | 返回注解为 None | 公开签名自检 |
| 当前连接没有规则 owner | 获取客户端后直接返回 None，不发送移除 RPC | 空规则、重复移除 |
| 当前连接已有规则 owner | 发送 `web.popup.remove_all`，成功后清空 SDK owner，返回 None | 移除生效规则、移除未绑定规则、重新注册后再次移除 |
| 没有默认客户端 | `get_client()` 自动连接本机 Runtime；连接失败可抛 HostUnavailableError | 源码确认，未主动中断 Runtime |
| RPC 私有 owner 无效 | Runtime 对非字符串、空字符串或长度超过 100 返回 `invalid_params`，文案“弹窗规则所属连接无效”；SDK 错误映射可抛 InvalidParamsError | owner 不是公开参数，未伪造此分支的公开 API 用例 |
| 其他连接或 RPC 错误 | `_run_web_browser_value()` 按 Runtime 响应传播 SDK 异常；RPC 失败时不会执行后面的 owner 清空 | 未主动制造通信或协议故障 |

产品只读 worktree **`D:\code\desktop`**，commit **`cb9332d1a04c09e04df54af958e028b2bc45af9b`**：

- `sdk/src/uiautoma/web/__init__.py:488`：SDK 方法与 `web.popup.remove_all` 调用。
- `sdk/src/uiautoma/_context.py:19`：默认客户端获取；`sdk/src/uiautoma/_core/client.py:1158`：RPC 与错误传播。
- `runtime/services/action_service.py:2865`：校验 owner，调用 `PopupRules.remove(owner)`。
- `runtime/web/popup_rules.py:44`：在锁内移除该 owner 的整组规则并唤醒轮询。
- 同文件 `attach():35` 在后续获取/创建页面时绑定规则；`_poll():67` 在点击前检查规则仍存在，并在同一锁内执行 `popup_click`。源码说明移除等待在途点击，但本轮未测试这个并发边界。
- 自动点击的辅助链路最终到 `chrome/engine/engine_packages/page_engine_runtime.js:2623`。完整公开签名、docstring 和 SDK 源码见 [冻结合同](../remaining_web_contracts_20261004.json)。

靶场只读 worktree **`D:\code\xpath`**，commit **`c886261211541cd48224dda51dc566af4710df16`**：`WEB/src/pages/KeysClickTestPage.tsx:420` 为真实 Ant Design Modal，`onCancel` 关闭、`maskClosable=false`，没有自动关闭计时器。结论绑定上述源码快照及本次 dev Runtime / Chrome。

## 靶场、元素库与准备

页面：[keys-click-test](https://baobaomi900901.github.io/xpath/#/keys-click-test)。

元素库：`D:\code\元素库\260902_web元素`；每轮复制到本次 UUID 临时目录，只连接副本。

| 用户提供的元素 | 库 ID | 现场映射 |
|---|---|---|
| `web靶场_打开遮罩弹窗_按钮` | `74ad2a3f-abe5-4436-922e-fa5390ac4360` | `button#btn-open-occlusion-modal` |
| `web靶场_模态弹窗` | `19379329-5c15-41ff-8e6b-b54cd0f1fe54` | DIV，Modal 标题“遮挡测试弹窗” |
| `web靶场_模态弹窗_关闭按钮` | `04504f71-3dc6-44cb-b3a7-d883de5e4f4e` | BUTTON，`button.ant-modal-close`，同一 Modal |

复用唯一的 `test_web_auto_handle_popup.py` 中的场景、库映射与被动观察器辅助代码，不运行该文件的另一套正式用例。本 API 使用唯一的[无日期测试脚本](../test_web_remove_all_auto_handle_popup.py)。

## 19 个正式用例

| 用例 | 期望与确证 |
|---|---|
| `api_contract` | 无参数公开签名与冻结源码一致 |
| `library_targets` | 三个指定 Web 库元素均已保存 |
| `environment` | Runtime、Chrome、靶场、临时库可用；记录标签基线 |
| `empty_rules_remove` | 无规则调用返回 None |
| `control_without_rule` | 三元素映射正确；无规则对照保持打开 1 秒，显式库点击可关闭 |
| `before_remove_auto` | 名称注册并重新获取本次页面；只点击打开按钮，自动关闭一次且隐藏 |
| `remove_registered` | 移除已生效规则，返回 None |
| `same_page_after_remove` | 原页弹窗连续至少 3 秒可见，关闭点击为零 |
| `idempotent_remove_open` | 已打开时再移除两次，返回 None；弹窗继续至少 3 秒可见，点击为零 |
| `manual_close_same_page` | 测试显式点击关闭按钮后才隐藏，关闭事件一次 |
| `reopen_after_remove` | 同页再次打开至少 3 秒不自动关闭，随后显式关闭 |
| `create_after_remove` | 关闭本次旧标签，在无规则状态创建新标签 |
| `new_page_after_remove` | 新页弹窗至少 3 秒可见，关闭点击为零 |
| `remove_registered_before_attach` | 已有弹窗打开时注册未绑定的新规则并移除，返回 None；弹窗继续至少 3 秒可见 |
| `manual_close_new_page` | 显式点击新页关闭按钮，事件一次且隐藏 |
| `reregister_restore_auto` | 以库 Web Selector 重新注册、绑定；自动关闭恢复，事件一次且隐藏 |
| `second_remove` | 再次移除重建规则，返回 None |
| `after_second_remove` | 第二次移除后再次打开至少 3 秒不自动关闭，随后显式关闭 |
| `cleanup` | 移除本连接规则与观察器；关闭本次标签和库；删除本次临时目录；复核外部标签与原生对话框 |

## 独立确证、抖动与失败记录

被动 DOM 观察器只记录关闭按钮 click，并读取 `.ant-modal-wrap` 的布局和 computedStyle 判断可见性，没有注入关闭逻辑。移除后的六段观察按约 0.1 秒间隔持续检查可见且点击为零；对于已经打开的分支不重置事件，避免漏掉迟到的关闭点击。第 4、5、6 轮的 18 段观察实际持续 **3.064–3.083 秒**。

先证明同一库规则能自动关闭，再调用被测 API；移除后仅点击打开按钮进行观察，观察结束才由测试显式点击库关闭按钮。随后以 Web Selector 重新注册验证自动关闭恢复，再验证第二次移除。自动分支都恰有一个关闭事件、事件时可见、最后隐藏；所有目标 API 成功调用均为 None。

保留的异常记录与定性：

- [初次探针](artifacts/remove_all_auto_handle_popup_20261005_probe_initial.txt)：移除效果已确认，后续辅助关闭点击记录了事件但弹窗未及时隐藏，等待超时；cleanup PASS、标签 2→2。该次辅助点击超时的原因未被确定，不能写成产品移除缺陷。
- [诊断探针](artifacts/remove_all_auto_handle_popup_20261005_probe_diagnostic.txt)：完整矩阵通过；第一次辅助关闭前记录 `visibilityState='hidden'`、`focus=False`。用户随后说明曾操作电脑，提供了与失焦一致的环境干扰线索，仍不足以确定初次超时的原因。
- 正式脚本在辅助操作前激活本次标签，辅助点击等待 0.3 秒；保持原有连续观察断言，正式失败不在脚本内重试。
- 第 3 轮：18 个其他用例通过，cleanup 因标签集合变化失败。报告中的新增 ID `fe1ada8e24154c6c` 与该轮本次创建的两个页面 ID 不同；本次页面关闭、临时库删除均完成，无规则/观察器清理错误或新原生弹窗。这是外部标签集合变化造成的环境干扰，本脚本保留外部标签，没有将该轮记为全绿。
- 第 4、5、6 轮未改功能判据，连续全绿；进入时外部标签基线为 4，每轮恢复 4→4。

## 清理与已知覆盖边界

连续验收三轮的 errors、external_added、external_removed、new_dialogs、rule_observer_cleanup_errors 均为空；own_tab_closed 和 temporary_copy_removed 均为 True；归档后复核各轮临时目录已不存在。本次一次性探针源文件在保存日志后删除，进入时已有的临时材料保留。

本轮只有**一个真实关闭按钮规则**，覆盖名称与 Web Selector 两次注册、当前连接移除、空规则、重复调用、原页面及新页面、未绑定规则、重新注册恢复。源码的“移除所有”实现按 owner 删除整组规则，但多规则、其他连接 owner 隔离、并发/在途点击、Edge、跨 iframe、网络/Runtime 中断均未做真实验收。已打开弹窗上的移除用例使用未绑定的新规则，不宣称覆盖正执行自动点击的竞争时刻。结论不扩展到 alert/confirm/prompt。

## 运行方式

保持 dev Runtime 与 Chrome 可用，在 `D:\code\元素库\sdk测试` 运行；期间请保持浏览器标签稳定：

```powershell
uv run .\web\test_web_remove_all_auto_handle_popup.py
```

页面会先自动关闭，移除后反复保持打开 3 秒，再由测试显式关闭。若要人工观察更久：

```powershell
uv run .\web\test_web_remove_all_auto_handle_popup.py --observe-seconds 10
uv run .\web\test_web_remove_all_auto_handle_popup.py --contract-only
uv run .\web\test_web_remove_all_auto_handle_popup.py --json --report-file .\web\evidence\artifacts\remove_all_auto_handle_popup_retest.json
```

CLI 另支持 `--target-url`、`--element-library`、`--open-button`、`--close-button`、`--modal`、`--wait-timeout`。观察时间须为有限数且至少 1 秒，等待时间须为有限正数。退出码 0/1/2 分别为通过/失败/阻塞；合同检查仅为 READY_FOR_LIVE，不连接 Runtime。库元素缺失在创建资源前报告 BLOCKED。

辅助入口核对已单独归档：[唯一脚本合同自检](artifacts/remove_all_auto_handle_popup_20261005_contract_only.json)、[公共入口合同路由](artifacts/remove_all_auto_handle_popup_20261005_common_contract.json)均为 1/1 PASS、READY_FOR_LIVE、退出码 0；[公共入口缺库输出](artifacts/remove_all_auto_handle_popup_20261005_common_blocked.txt)为 1 PASS + 1 BLOCKED、退出码 2，未创建页面或库。公共报告器补充 BLOCKED 标签与计数，使新 API 路由的阻塞结果可正常显示。这些辅助检查不计入三轮真实验收。

[归档复核结果](artifacts/remove_all_auto_handle_popup_20261005_validation.json)核对六轮报告、持续观察、自动恢复、清理、唯一脚本、冻结合同入口、索引计数与本 API 的文档链接；第 3 轮失败没有计入连续通过。

测试侧证据和索引照常更新；公开 API 文档交接稿等待本 API 的用户确认。产品仓库只读，本次没有提交 Issue 或推送远端。
