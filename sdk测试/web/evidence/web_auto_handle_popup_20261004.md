# `uiautoma.web.auto_handle_popup()` 验证证据（2026-10-04）

> 2026-10-05 修正：此前“现有靶场只有 JavaScript 原生弹窗”的判断撤回。只读源码 worktree `D:\code\xpath`、commit `c886261211541cd48224dda51dc566af4710df16` 的 `WEB\src\pages\KeysClickTestPage.tsx:420` 已有 Ant Design DOM Modal。可使用 `#/keys-click-test` → “遮挡点击测试” → “打开遮挡弹窗”；本机库尚未保存该弹窗的关闭按钮，真实验收仍未执行，状态与历史计数保持 SKIPPED。

## 用途与合同

注册自动关闭网页弹窗的规则，对随后获取或打开的网页生效。

```python
auto_handle_popup(handle_method: str, close_button=None, element_selector=None, process: str | None = None, package=None) -> None
```

- 被测 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。结论只绑定该源码快照和本次 dev Runtime。
- SDK 入口：`sdk\src\uiautoma\web\__init__.py:454`。
- 调用链：web.popup.add → ActionService.web_popup_add → PopupRules。
- 完整签名、默认值、docstring 与入口源码保存在 [合同快照](../remaining_web_contracts_20261004.json)。

## 真实验收结果

**SKIPPED（2026-10-04；1/2 PASS + 0 FAIL + 1 KNOWN；1 轮；退出码 0）**

页面：未打开页面（条件不满足，直接跳过）。
元素库：`D:\code\元素库\260902_web元素`；只使用临时副本。

| 轮次 | 结果 | 原始报告 |
|---|---|---|
| 1 | 1/2 PASS + 0 FAIL + 1 KNOWN；退出码 0 | [web_auto_handle_popup_20261004_run1.txt](artifacts/web_auto_handle_popup_20261004_run1.txt) |

## 期望值来源与独立确证

当前条件不满足，没有执行真实正向场景；仅自检公开签名与已读取的源码快照。 参数错误按冻结源码合同检查；具体覆盖见下表和原始报告。

| 用例 | 状态 | 期望/确证方法 |
|---|---|---|
| `api_contract` | PASS | 公开签名与只读源码快照一致 |
| `skip` | KNOWN | 需要真实正向场景 |

## 实测行为与边界

跳过原因：

- 可用 DOM 场景已存在于 `#/keys-click-test`；缺少库中已保存的弹窗关闭按钮。旧原始报告中的跳过文案保留作历史记录，按上述修正理解。

本次仅验收报告列出的场景；未列出的浏览器模式、DPI、参照系、控件种类、超大输入、网络异常或原生交互路径均不宣称通过。SKIPPED 的合同检查通过不等于实际功能通过。

## 资源清理与复测

直接跳过，没有创建页面、库副本或弹窗。

脚本：[test_web_auto_handle_popup_20261004.py](../test_web_auto_handle_popup_20261004.py)。

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_auto_handle_popup_20261004.py
```

退出码 0 表示无 FAIL（允许 KNOWN/跳过），1 表示存在 FAIL。通过范围与生命周期必须结合报告读取。
