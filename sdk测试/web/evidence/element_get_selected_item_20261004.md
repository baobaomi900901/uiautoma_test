# `uiautoma.web.WebElement.get_selected_item()` 验证证据（2026-10-04）

## 用途与合同

获取网页下拉框当前选中项的文本。

```python
get_selected_item(self) -> list[str]
```

- 被测 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。结论只绑定该源码快照和本次 dev Runtime。
- SDK 入口：`sdk\src\uiautoma\web\element.py:697`。
- 调用链：RawWebElement.get_select_options → web.get_select_options → ActionService.web_get_select_options → Page Engine get_select_options → selected 文本筛选。
- 完整签名、默认值、docstring 与入口源码保存在 [合同快照](../remaining_web_contracts_20261004.json)。

## 真实验收结果

**VERIFIED（2026-10-04；10/12 PASS + 0 FAIL + 2 KNOWN；3 轮；退出码 0）**

页面：[靶场](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
元素库：`D:\code\元素库\260902_web元素`；只使用临时副本。

| 轮次 | 结果 | 原始报告 |
|---|---|---|
| 1 | 10/12 PASS + 0 FAIL + 2 KNOWN；退出码 0 | [element_get_selected_item_20261004_run1.txt](artifacts/element_get_selected_item_20261004_run1.txt) |
| 2 | 10/12 PASS + 0 FAIL + 2 KNOWN；退出码 0 | [element_get_selected_item_20261004_run2.txt](artifacts/element_get_selected_item_20261004_run2.txt) |
| 3 | 10/12 PASS + 0 FAIL + 2 KNOWN；退出码 0 | [element_get_selected_item_20261004_run3.txt](artifacts/element_get_selected_item_20261004_run3.txt) |

## 期望值来源与独立确证

现场 SELECT.options 的 text/selected 与返回列表逐项对照；读取前后 DOM 不变；选择与重置后重新获取独立 DOM 状态。 参数错误按冻结源码合同检查；具体覆盖见下表和原始报告。

| 用例 | 状态 | 期望/确证方法 |
|---|---|---|
| `api_contract` | PASS | 公开签名与只读源码快照一致 |
| `environment` | PASS | Runtime/Chrome/现有靶场与临时库可用 |
| `initial_form-controls-native-city` | PASS | 读取当前选中项目，DOM 前后不变 |
| `initial_form-controls-native-cities` | PASS | 读取当前选中项目，DOM 前后不变 |
| `single_changed` | PASS | 单选上海返回 [上海] |
| `multi_changed` | PASS | 多选返回北京、广州，按 DOM 顺序 |
| `reset` | PASS | 重置后多选返回空列表 |
| `ant_web靶场_表单测试_ant_select单选` | KNOWN | 非 SELECT 抛 ActionError/element_options_not_readable |
| `ant_web靶场_表单测试_ant_select多选` | KNOWN | 非 SELECT 抛 ActionError/element_options_not_readable |
| `no_extra_parameter` | PASS | 多余位置参数抛 TypeError |
| `cleanup` | PASS | 关闭本次页面和库、删除临时目录、复核标签和文件弹窗 |
| `closed_package` | PASS | 关闭连接后抛当前版本的 HostUnavailableError |

## 实测行为与边界

覆盖原生单选、多选、状态切换和重置；Ant 的 input/div 目标不是标准 SELECT，按 element_options_not_readable 拒绝，记录为 KNOWN。

闭包连接的生命周期判据采用本次 SDK 的 `HostUnavailableError`（包含“连接已关闭”）；旧快照的错误类型不作为本次期望。

本次仅验收报告列出的场景；未列出的浏览器模式、DPI、参照系、控件种类、超大输入、网络异常或原生交互路径均不宣称通过。SKIPPED 的合同检查通过不等于实际功能通过。

## 资源清理与复测

各轮 cleanup 均 PASS：仅关闭本次标签页和库连接，删除本次 UUID 临时目录；标签数 1→1，未留下本次文件对话框。原始库和用户原页面保留。

脚本：[test_web_element_get_selected_item_20261004.py](../test_web_element_get_selected_item_20261004.py)。

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_element_get_selected_item_20261004.py
```

退出码 0 表示无 FAIL（允许 KNOWN/跳过），1 表示存在 FAIL。通过范围与生命周期必须结合报告读取。
