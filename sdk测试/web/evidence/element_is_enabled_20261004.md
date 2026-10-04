# `uiautoma.web.WebElement.is_enabled()` 验证证据（2026-10-04）

## 用途与合同

判断网页元素是否可用。

```python
is_enabled(self) -> bool
```

- 被测 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。结论只绑定该源码快照和本次 dev Runtime。
- SDK 入口：`sdk\src\uiautoma\web\element.py:866`。
- 调用链：web.is_enabled → ActionService.web_is_enabled_element → Page Engine is_enabled（disabled/aria-disabled/class）。
- 完整签名、默认值、docstring 与入口源码保存在 [合同快照](../remaining_web_contracts_20261004.json)。

## 真实验收结果

**READY_FOR_LIVE（2026-10-04；8/9 PASS + 1 FAIL + 0 KNOWN；3 轮；退出码 1）**

页面：[靶场](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
元素库：`D:\code\元素库\260902_web元素`；只使用临时副本。

| 轮次 | 结果 | 原始报告 |
|---|---|---|
| 1 | 8/9 PASS + 1 FAIL + 0 KNOWN；退出码 1 | [element_is_enabled_20261004_run1.txt](artifacts/element_is_enabled_20261004_run1.txt) |
| 2 | 8/9 PASS + 1 FAIL + 0 KNOWN；退出码 1 | [element_is_enabled_20261004_run2.txt](artifacts/element_is_enabled_20261004_run2.txt) |
| 3 | 8/9 PASS + 1 FAIL + 0 KNOWN；退出码 1 | [element_is_enabled_20261004_run3.txt](artifacts/element_is_enabled_20261004_run3.txt) |

## 期望值来源与独立确证

现场 input.disabled 的反值作为期望；覆盖真实禁用控件、动态禁用/恢复和布尔属性 false 字符串。 参数错误按冻结源码合同检查；具体覆盖见下表和原始报告。

| 用例 | 状态 | 期望/确证方法 |
|---|---|---|
| `api_contract` | PASS | 公开签名与只读源码快照一致 |
| `environment` | PASS | Runtime/Chrome/现有靶场与临时库可用 |
| `form-controls-native-text` | PASS | 真实启用/禁用状态与 DOM disabled 一致 |
| `form-controls-native-disabled` | PASS | 真实启用/禁用状态与 DOM disabled 一致 |
| `form-controls-ant-disabled` | PASS | 真实启用/禁用状态与 DOM disabled 一致 |
| `toggle_disabled` | PASS | 动态禁用 False，恢复 True |
| `boolean_disabled_attribute` | FAIL | HTML 布尔 disabled 属性存在时即禁用，包括值 false |
| `cleanup` | PASS | 关闭本次页面和库、删除临时目录、复核标签和文件弹窗 |
| `closed_package` | PASS | 关闭连接后抛当前版本的 HostUnavailableError |

## 实测行为与边界

三轮均在 boolean_disabled_attribute 失败：disabled="false" 时 DOM disabled=True，API 返回 True。标准布尔属性由是否存在决定，字符串 false 不是移除属性；判据见 [HTML Standard](https://html.spec.whatwg.org/multipage/common-microsyntaxes.html#boolean-attributes)。缺陷草稿与复现入口见 [交接材料](../../issues/drafts/is_enabled_disabled_false_20261004.md)。历史 disabled 空串问题本轮通过，不能据此宣称所有禁用判断已修复。

关闭连接的生命周期判据采用本次 SDK 的 `HostUnavailableError`（包含“连接已关闭”）；旧快照的错误类型不作为本次期望。

本次仅验收报告列出的场景；未列出的浏览器模式、DPI、参照系、控件种类、超大输入、网络异常或原生交互路径均不宣称通过。SKIPPED 的合同检查通过不等于实际功能通过。

## 资源清理与复测

各轮 cleanup 均 PASS：仅关闭本次标签页和库连接，删除本次 UUID 临时目录；标签数 1→1，未留下本次文件对话框。原始库和用户原页面保留。

脚本：[test_web_element_is_enabled_20261004.py](../test_web_element_is_enabled_20261004.py)。

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_element_is_enabled_20261004.py
```

退出码 0 表示无 FAIL（允许 KNOWN/跳过），1 表示存在 FAIL。通过范围与生命周期必须结合报告读取。
