# Win32 城市表单入库实测

本轮完成指定目录的元素库初始化，以及城市单选 ComboBox 入库。城市多选采用两个真实样本捕获并保存了相似集合，但实际范围为 10 个复选框，未通过“仅五个城市选项”的业务验收；第三项需求仍未完成。

## 环境与来源

- 测试目录及元素库：D:\code\元素库\CLI测试\Example\2_win32表单填写
- rust_uia 源码：D:\code\rust_uia，commit b700f9238134f57da83ab478a5ee55337ade1082
- Desktop 源码：D:\code\desktop，commit 7f148f27c0efa8bbba1f18d86c14845ea7d639fa
- SDK 来源：D:\code\desktop\sdk；SDK 测试目录：D:\code\元素库\sdk测试
- CLI：D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe
- CLI SHA-256：C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8
- CLI 版本：uia 0.1.1，--version 退出码 0。
- 源码 commit 和版本号不能单独证明该二进制的构建来源。
- 靶场：Win32 靶场 - UIA；HWND 8524180；PID 60380。

## 已完成的资产

1. CLI 的 package open 仅打开已有库，没有初始化命令。本轮通过 CLI 读取和操作 App 的公开目录选择、初始化按钮，在指定目录完成初始化。最终 package current 核对为指定目录。
2. 单选资产：城市（单选），ID 22b21bda-3fd1-4549-b0da-beeae579e166。实际控件类型为 ComboBox，UI 树路径 [0,0,11]；不是文字标签。capture win committed=true、commit_unknown=false；package validate 返回 found=true、count=1、status=passed，退出码 0。

## 城市多选相似集合范围不正确

预期只包含北京、上海、广州、深圳、杭州，共 5 个 CheckBox。

本轮在同一观察会话、同一 snapshot 中选取北京 e28 和杭州 e32，执行：

```powershell
& 'D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe' capture win --session 50ddd049-55b8-47c2-a745-ee1e889b5182 --snapshot 1 --ref e28 --similar-ref e32 --package 'D:\code\元素库\CLI测试\Example\2_win32表单填写' --name '城市（多选）选项' --no-highlight --format json
```

返回资产 ID 0726e92d-8380-49b2-9473-6fe4efcbe139，committed=true、commit_unknown=false、match_count=10，退出码 0。重新执行 package validate 也返回 count=10、status=passed。定位校验通过不能证明业务范围正确。

用 CLI details 的元素几何信息逐一匹配 validate 返回的全部矩形，结果如下：

| 选项 | AutomationId | 是否属于城市多选 |
| --- | --- | --- |
| 北京 | 1962 | 是 |
| 上海 | 1963 | 是 |
| 广州 | 1964 | 是 |
| 深圳 | 1965 | 是 |
| 杭州 | 1966 | 是 |
| 阅读 | 1982 | 否 |
| 运动 | 1983 | 否 |
| 音乐 | 1984 | 否 |
| 旅行 | 1985 | 否 |
| 同意用户协议 | 1993 | 否 |

匹配范围核对只使用 CLI 元素详情及矩形，没有使用截图视觉模型。capture 正常生成的截图资产未用于判断范围或状态。

该相似集合仍保留在库中作为本轮测试产物，未通过业务验收，不应当作五个城市专用集合批量操作。测试期间还观察到一个额外的“北京”资产 be988e89-f5cb-45da-a962-e4b24462d077，本轮两个 CLI capture 的返回均不是该 ID；其创建来源未确认，本轮未修改该资产。

## 源码定位与限制

以下文件仅只读检查，未修改被测项目。

- D:\code\rust_uia\src\element_library_store.rs:2474：generalize_similar_layer 仅保留两个样本相等且已激活的条件；不同的 uia_name/title 转为 optional，index 强制不启用。
- 保存的相似快照是 wnd 路径：Window → Tab → Pane（表单控件页）→ CheckBox，末层 required 仅剩 class_name=Button。城市、兴趣、协议复选框共享父节点与这些属性，因此全部被匹配。
- D:\code\rust_uia\src\wnd_selector.rs:526、664、730：当前 wnd 条件只读取 equal；支持的名称/标题/类名为精确匹配，index 是单个索引。无法用现有条件表达这五个不同名称的集合。
- D:\code\desktop\app\src\WinElementPathPanel.tsx:380、438：Win 编辑面板显示匹配方式并提供已有字段值和启用状态编辑，未提供可将此集合限定到五个城市的运算符/范围编辑入口。

建议交由产品项目处理：支持 wnd 集合的名称集合条件或正则条件，并在 App/CLI 中提供公开编辑入口；或支持其他明确的业务分组范围。回归验收应确认恰好匹配这五个城市，并排除四个兴趣选项和协议复选框，不能只检查 count>=2 或 validated=true。

## 证据

- environment.json：版本、哈希、目录与 commit。
- capture-single.json / validate-single.json：单选入库及定位验证。
- capture-similar.json / validate-similar-wide.json：相似入库及实际 10 个匹配矩形。
- similar-scope-check.json：全部匹配与 CLI 详情的逐项对照，scope_passed=false。
- similar-snapshot-original.json：原始相似选择器快照。
- fixture-tree.json 与 fixture-details-*.json / fixture-checkbox-detail-*.json：控件路径、名称、几何信息。
- final-package-current.json / final-package-items.json：最终库状态。
- *.command.json：命令参数及退出码；*.stderr.txt：命令 stderr。

本轮三个观察会话均已关闭；没有关闭 App 或靶场窗口，没有修改 rust_uia/Desktop 源码或构建产物。
