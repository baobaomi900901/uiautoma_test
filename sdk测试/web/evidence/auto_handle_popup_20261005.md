# `uiautoma.web.auto_handle_popup()` 真实 DOM 弹窗验收（2026-10-05）

## 结果

**VERIFIED：连续 3 轮，每轮 19/19 PASS、0 FAIL、0 BLOCKED，退出码 0。**

同日用户运行无日期唯一脚本完成一次复测：**19/19 PASS、退出码 0，清理 PASS，标签 4→4**。该记录单独归为用户复测，不计作 agent 的第四轮连续验收。

此前 2026-10-04 的 1/2 PASS + 1 KNOWN 是条件不足时的历史记录。用户已新增模态弹窗与关闭按钮，真实自动关闭验收现已完成；[旧证据](web_auto_handle_popup_20261004.md)与旧原始输出保留。

| 轮次 | 结果 | 清理 | 报告 |
|---|---|---|---|
| 1 | 19/19 PASS | 标签 5→5，临时库已删除 | [终端](artifacts/auto_handle_popup_20261005_run1.txt) / [JSON](artifacts/auto_handle_popup_20261005_run1.json) |
| 2 | 19/19 PASS | 标签 5→5，临时库已删除 | [终端](artifacts/auto_handle_popup_20261005_run2.txt) / [JSON](artifacts/auto_handle_popup_20261005_run2.json) |
| 3 | 19/19 PASS | 标签 5→5，临时库已删除 | [纯 JSON 输出](artifacts/auto_handle_popup_20261005_run3.txt) / [JSON](artifacts/auto_handle_popup_20261005_run3.json) |
| 用户复测 | 19/19 PASS，退出码 0 | 标签 4→4；cleanup PASS | [用户提供的终端日志](artifacts/auto_handle_popup_20261005_user_retest.txt) |

### 用户复测记录

用户通过 `uv run .\web\test_web_auto_handle_popup.py` 运行同一测试。其日志显示无规则对照、名称规则两次自动关闭、Selector 规则自动关闭、异常参数与重复注册全部通过；cleanup 中 errors、external_added、external_removed、new_dialogs 和 rule_observer_cleanup_errors 均为空，own_tab_closed 与 temporary_copy_removed 为 True。

用户提供的是终端文本，未附独立 JSON 报告或新的源码 commit；本记录保留上述正式验收的源码快照，不推定另一版本已经验收。4→4 与先前三轮的 5→5 是不同的进入时标签基线，各轮均恢复了自己的基线。

## 用途、合同与源码快照

注册点击关闭按钮的规则，对注册后通过 SDK 获取或创建的网页生效。关闭按钮必须是元素库中的 Web 元素名称，或指向该元素的 Web Selector。

```python
auto_handle_popup(handle_method: str, close_button=None,
                  element_selector=None, process: str | None = None,
                  package=None) -> None
```

| 参数/返回 | 本轮合同 |
|---|---|
| `handle_method` | `close_dialog` 支持；非法值抛 `InvalidParamsError`；`execute_process` 抛 `UnsupportedActionError` |
| `close_button` | 元素库名称或 Web Selector，默认 None；缺省、空白名称、错误类型、Win Selector 均抛 `InvalidParamsError` |
| `element_selector` / `process` / `package` | 默认 None；当前 close_dialog 路径不使用，本轮未扩展其语义 |
| 返回 | 成功注册返回 None；真实效果必须另查弹窗与点击事件 |
| 重复规则 | 同一连接重复注册同一关闭按钮抛 `InvalidParamsError`，实测 trace=`invalid_params` |
| 跨 iframe | 源码拒绝跨 iframe 关闭按钮；本轮只测试顶层 DOM Modal，没有执行该异常分支 |

产品只读 worktree `D:\code\desktop`，commit **`cb9332d1a04c09e04df54af958e028b2bc45af9b`**：

- SDK：`sdk/src/uiautoma/web/__init__.py:454` → `web.popup.add`。
- Runtime：`runtime/services/action_service.py:2827`，解析已保存选择器，校验规则。
- 后台：`runtime/web/popup_rules.py`，获取唯一可见关闭按钮并执行 `popup_click`；轮询约 0.5 秒。
- 引擎：`chrome/engine/engine_packages/page_engine_runtime.js:2623`，对可见且启用的节点分派点击。
- 完整签名、默认值、docstring 与 SDK 入口源码：[冻结合同](../remaining_web_contracts_20261004.json)。结论绑定上述快照与本次 dev Runtime / Chrome。

靶场只读 worktree `D:\code\xpath`，commit **`c886261211541cd48224dda51dc566af4710df16`**：`WEB/src/pages/KeysClickTestPage.tsx:420` 的真实 Ant Design Modal，`onCancel` 关闭、`maskClosable=false`，没有自动关闭计时器。

## 场景与设计

页面：[keys-click-test](https://baobaomi900901.github.io/xpath/#/keys-click-test)。

元素库：`D:\code\元素库\260902_web元素`；每轮复制到本次 UUID 临时目录，只连接副本。

| 用户提供的元素 | 库 ID | 本轮现场映射 |
|---|---|---|
| `web靶场_打开遮罩弹窗_按钮` | `74ad2a3f-abe5-4436-922e-fa5390ac4360` | `button#btn-open-occlusion-modal` |
| `web靶场_模态弹窗` | `19379329-5c15-41ff-8e6b-b54cd0f1fe54` | DIV，所属 Modal 标题为“遮挡测试弹窗” |
| `web靶场_模态弹窗_关闭按钮` | `04504f71-3dc6-44cb-b3a7-d883de5e4f4e` | BUTTON，匹配 `button.ant-modal-close`，所属 Modal 标题一致 |

选择库名称和 `Package.selector(..., kind='web')` 两条公开注册路径。先做无规则对照，再注册规则并重新获取页面；第二条路径在注册后创建新标签。没有为本测试自建页面、新增库条目或注入关闭逻辑。

一次性 [探针](artifacts/auto_handle_popup_20261005_probe.txt) 已确认：无规则时保持打开；名称注册连续两次自动关闭；Selector 注册自动关闭；清理标签 5→5。之后再运行正式脚本三轮。

## 19 个正式用例

| 用例 | 期望与确证 |
|---|---|
| `api_contract` | 公开签名与只读快照一致 |
| `invalid_method` | 非法处理方式抛 InvalidParamsError |
| `unsupported_process` | execute_process 抛 UnsupportedActionError |
| `missing_close_button` | 未提供关闭按钮抛 InvalidParamsError |
| `blank_close_button` | 空白名称抛 InvalidParamsError |
| `invalid_close_type` | 整数参数抛 InvalidParamsError |
| `non_web_selector` | Win Selector 抛 InvalidParamsError |
| `library_targets` | 库中存在用户指定的三个 Web 元素 |
| `environment` | Runtime、Chrome、靶场与临时库可用；记录进入时标签基线 |
| `control_without_rule` | 核对三元素映射；无规则时弹窗保持打开 3 秒；库关闭按钮可手动关闭 |
| `register_name` | 使用关闭按钮名称注册返回 None |
| `duplicate_rule` | 同一关闭按钮重复注册抛 InvalidParamsError |
| `acquire_after_name_rule` | 注册后 get() 获取本次标签，复核页面 ID |
| `auto_close_name_1` | 只点击打开按钮，关闭事件恰好一次，事件发生时弹窗可见，结束时隐藏 |
| `auto_close_name_2` | 再次打开同一个弹窗，规则再次生效 |
| `register_selector` | 辅助移除旧规则后，使用 Web Selector 注册返回 None |
| `create_after_selector_rule` | 关闭本次旧标签，在注册后创建新标签 |
| `auto_close_selector` | 新标签中只点击打开按钮，自动关闭事件恰好一次，结束时隐藏 |
| `cleanup` | 移除本连接规则与本页观察器；关闭本次页面/库；删除本次临时目录；复核标签和原生对话框 |

## 独立确证与边界

页面内的被动监听器只记录真实关闭按钮的 click 事件。可见性通过 `.ant-modal-wrap` 的布局矩形和 computedStyle 判断；事件发生时记录可见状态。自动分支没有调用关闭按钮 click，也没有执行关闭弹窗的 JavaScript。若 API 未生效，点击记录为空、弹窗持续可见，断言会超时失败。

无规则对照中，3 秒后弹窗仍可见、关闭事件为零；手动关闭一次后恢复隐藏。自动分支每次都记录一次关闭事件，且该事件发生时弹窗可见，最终隐藏。重复打开前等待 0.8 秒，让后台观察上轮隐藏状态；这不是性能保证。

每轮清理都无错误，标签集合与进入时完全一致，external_added / external_removed / new_dialogs 为空，临时库目录不存在。原始库由用户采集，本脚本没有修改原件；既有 `.pytest_tmp` 材料与用户其他标签保留。

本轮未独立验收 `remove_all_auto_handle_popup()` 的移除后效果；该 API 仅作为本轮辅助清理使用，不能据此更新它的历史状态。未覆盖 Edge、跨 iframe、关闭按钮歧义、多规则并行、用户中途关闭连接等场景。不将本结论延伸到原生 alert/confirm/prompt。

## 运行方式

用户已确认生成公开文档交接稿；[四个同步目标与完整草稿](../../issues/drafts/auto_handle_popup_20261005/README.md)保存在测试仓库，仅供审阅，尚未发布到产品仓库或提交 Issue。

保持 dev Runtime 与 Chrome 可用，在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_auto_handle_popup.py
```

本 API 统一使用唯一的[无日期测试脚本](../test_web_auto_handle_popup.py)。首次弹窗保持打开 3 秒用于对照，后续弹窗会自动快速关闭。历史原始报告中的 script 字段保留运行时记录；当前入口以本节为准。

```powershell
uv run .\web\test_web_auto_handle_popup.py --control-observe-seconds 10
uv run .\web\test_web_auto_handle_popup.py --contract-only
```

CLI 另支持 `--target-url`、`--element-library`、`--open-button`、`--close-button`、`--modal`、`--wait-timeout`、`--json`、`--report-file`。缺少库元素时在创建标签前报告 BLOCKED，退出码 2；合同检查通过不等于完成真实验收。
