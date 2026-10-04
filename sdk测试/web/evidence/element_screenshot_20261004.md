# `uiautoma.web.WebElement.screenshot()` 验证证据（2026-10-04）

## 用途与合同

截取元素图片到文件。

```python
screenshot(self, folder_path: str, *, file_name: str | None = None) -> str
```

- 被测 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。结论只绑定该源码快照和本次 dev Runtime。
- SDK 入口：`sdk\src\uiautoma\web\element.py:825`。
- 调用链：web.screenshot.element → ActionService.web_element_screenshot → CDP screenshot/crop → SDK 保存路径。
- 完整签名、默认值、docstring 与入口源码保存在 [合同快照](../remaining_web_contracts_20261004.json)。

## 真实验收结果

**VERIFIED（2026-10-04；5/5 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）**

页面：[靶场](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
元素库：`D:\code\元素库\260902_web元素`；只使用临时副本。

| 轮次 | 结果 | 原始报告 |
|---|---|---|
| 1 | 5/5 PASS + 0 FAIL + 0 KNOWN；退出码 0 | [element_screenshot_20261004_run1.txt](artifacts/element_screenshot_20261004_run1.txt) |
| 2 | 5/5 PASS + 0 FAIL + 0 KNOWN；退出码 0 | [element_screenshot_20261004_run2.txt](artifacts/element_screenshot_20261004_run2.txt) |
| 3 | 5/5 PASS + 0 FAIL + 0 KNOWN；退出码 0 | [element_screenshot_20261004_run3.txt](artifacts/element_screenshot_20261004_run3.txt) |

## 期望值来源与独立确证

独立解析输出 PNG 尺寸，以 DOM 活矩形在视口 PNG 上裁切，扫描 ±1px 并比较像素字节。 参数错误按冻结源码合同检查；具体覆盖见下表和原始报告。

| 用例 | 状态 | 期望/确证方法 |
|---|---|---|
| `api_contract` | PASS | 公开签名与只读源码快照一致 |
| `environment` | PASS | Runtime/Chrome/现有靶场与临时库可用 |
| `file_and_framing` | PASS | PNG 尺寸与 DOM 一致，取景与页面 PNG 对照（±1px 扫描、差异<2.5%） |
| `invalid_filename` | PASS | 非法文件名抛 InvalidParamsError |
| `cleanup` | PASS | 关闭本次页面和库、删除临时目录、复核标签和文件弹窗 |

## 实测行为与边界

PNG 字节独立解析；iframe 边框计入页面矩形，再与视口截图裁切比对。±1px 扫描、像素差异预算 <2.5%，实际差异保存在每轮报告；只覆盖本次 DPI 和当前元素。

闭包连接的生命周期判据采用本次 SDK 的 `HostUnavailableError`（包含“连接已关闭”）；旧快照的错误类型不作为本次期望。

本次仅验收报告列出的场景；未列出的浏览器模式、DPI、参照系、控件种类、超大输入、网络异常或原生交互路径均不宣称通过。SKIPPED 的合同检查通过不等于实际功能通过。

## 资源清理与复测

各轮 cleanup 均 PASS：仅关闭本次标签页和库连接，删除本次 UUID 临时目录；标签数 1→1，未留下本次文件对话框。原始库和用户原页面保留。

脚本：[test_web_element_screenshot_20261004.py](../test_web_element_screenshot_20261004.py)。

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_element_screenshot_20261004.py
```

退出码 0 表示无 FAIL（允许 KNOWN/跳过），1 表示存在 FAIL。通过范围与生命周期必须结合报告读取。
