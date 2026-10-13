# 原生 UIA ui-tree 勾选状态核对

结论：本次 uia 0.1.1 的 observe win tree/children/subtree 返回中，没有 checked/is_checked/toggle_state 字段。字段缺失不能解释为 false。之前的五个城市状态来自 CLI screenshot win 输出截图的视觉核对。

## 本次环境

- CLI：D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe
- CLI SHA-256：C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8
- CLI --version：uia 0.1.1；退出码 0。
- Desktop：D:\code\desktop；commit 7f148f27c0efa8bbba1f18d86c14845ea7d639fa。
- rust_uia：D:\code\rust_uia；commit b700f9238134f57da83ab478a5ee55337ade1082。
- SDK 测试目录：D:\code\元素库\sdk测试。
- CLI 测试目录：D:\code\元素库\CLI测试\Example\2_win32表单填写。
- 来源登记见 environment.json。源码 commit 与 CLI 版本不能独立证明二进制构建来源。

## 证据

1. 本次 ui-tree 原始输出：../20261010_101014/ui-tree.json；复选框节点只有类型、名称、path 和 children_state，没有勾选状态字段。
2. D:\code\desktop\cli\README.md:699–703 记录树的字段及可确认状态：is_enabled、is_offscreen、has_keyboard_focus、is_password；未记录勾选状态。
3. D:\code\rust_uia\src\uia_inspector.rs:1309–1347 的 inspect_tree_element 原生属性采集没有读取 ToggleState；此前 observe win details 的实际输出同样没有该字段。
4. D:\code\desktop\cli\command\src\win_actions.rs:63–139 公开 Check/Uncheck 修改命令，没有公开读取勾选状态的命令。

范围：上述结论限于本次原生 Win32/UIA 观察，不泛化到 Web 语义快照或其他后端。

产品侧改进建议：增加可直接读取的勾选状态字段或查询入口，并区分未勾选、已勾选、混合及不支持/读取失败。本测试 Agent 未修改被测源码。
