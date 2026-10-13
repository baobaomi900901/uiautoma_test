# Win32 靶场修改后重新采集

已在 D:\code\元素库\CLI测试\Example\2_win32表单填写 重新保存两个资产，并通过 CLI 的持久资产重新定位和业务范围核对。

| 资产 | 类型 | ID | 重新定位结果 |
| --- | --- | --- | --- |
| 城市（单选） | 单个 ComboBox | 11e97a62-472a-47f2-bbcc-e0df7a42937d | 1 个；passed |
| 城市（多选）选项 | CheckBox 相似集合 | 2f3403c2-5c9a-495d-8d72-c1307f80f800 | 北京、上海、广州、深圳、杭州，共 5 个；passed |

## 采集与验证

用户已修改 Win32 靶场，并手动清空库元素。本轮 package items 开始时返回 count=0，结束时返回 count=2。

本轮选取标题完全匹配“Win32 靶场 - UIA”、进程 win32-shooting-range-uia.exe 的窗口，HWND 2428888，PID 101744。旁边的“Win32 靶场 - UIA (表单item 无 Pane)”是另一窗口，没有参与本轮采集。

新的 CLI 元素树未截断、未耗尽预算。单选实际 ComboBox 路径为 [0,0,5,1]。多选有独立的“城市（多选）”Pane，路径 [0,0,6]，五个城市复选框均为其子节点；兴趣和协议位于其他 Pane。

单选通过 capture win 保存实际 ComboBox。多选在同一观察会话、同一 snapshot 下，以北京 e43 和杭州 e47 为两个样本，使用 --similar-ref 保存一个集合资产，返回 match_count=5。两次采集均 committed=true、commit_unknown=false，退出码 0。

随后关闭临时观察，通过两个保存资产的 UUID 执行 package validate。单选 count=1，多选 count=5，两者 validated=true、status=passed，退出码 0。

将全部验证匹配矩形与 CLI details 的名称和几何信息逐一对应，多选匹配只有北京、上海、广州、深圳、杭州；阅读、运动、音乐、旅行和同意用户协议均未包含。scope-check.json 中 single_scope_passed=true、similar_scope_passed=true。

保存的相似选择器保留“城市（多选）”父 Pane 的 class_name 和 uia_name 条件，所以集合限制在该 Pane 内。未手工修改快照或目录清单。

本轮控件识别和范围验证只使用 CLI 元素树、详情及验证输出；capture 正常生成的截图未用于视觉判断。未修改 rust_uia 或 Desktop 源码、配置和构建产物。

## 本轮被测版本

- rust_uia：D:\code\rust_uia；main；commit b700f9238134f57da83ab478a5ee55337ade1082。
- Desktop：D:\code\desktop；main；commit 7f148f27c0efa8bbba1f18d86c14845ea7d639fa。
- SDK 来源：D:\code\desktop\sdk；SDK 测试目录：D:\code\元素库\sdk测试。
- CLI：D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe。
- SHA-256：C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8。
- --version：uia 0.1.1；退出码 0。Runtime PID 58500，版本 0.1.1。
- 源码 commit 与版本号不能单独证明该二进制的构建来源。

## 证据文件

- environment.json：源码目录、commit、CLI 路径、哈希及版本。
- catalog-before.json、items-before.json：开始时元素库为空。
- fixture-tree.json、detail-e*.json：新控件层级和详情。
- capture-single.json、capture-similar.json：两次已确认入库结果。
- fixture-close.json：临时观察已关闭。
- validate-single.json、validate-similar.json、scope-check.json：保存后重新定位与准确范围核对。
- items-after.json、catalog-after.json：最终只包含两个资产。
- single-snapshot.json、similar-snapshot.json：本轮选择器证据副本。
- *.command.json：命令参数、退出码、记录时间；*.stderr.txt：stderr。

此前 10 项相似集合的测试报告属于旧版靶场测试，本轮已重新采集且准确匹配五个城市。
