# CLI 重抓元素与 SDK 填写验证

测试日期：2026-10-10（Asia/Shanghai）。

## 结果

通过已确认的 uia.exe 重新抓取姓名、城市单选和城市多选，并通过 CLI 操作 App 的公开元素编辑页，取消两层 Pane 随机 class_name 的必选条件，保留 uia_name、窗口和标准控件类型等条件。未手工改写实际元素库的选择器文件。

新资产均保存于 `D:\code\元素库\CLI测试\Example\3_win32元素修复\element`：

| 脚本逻辑字段 | 保存名称 | 元素 ID | CLI 校验数量 |
| --- | --- | --- | --- |
| 姓名 | 姓名_修复 | be4c0721-a09d-4fad-9ce6-8e68e8b3b14f | 1 |
| 城市（单选） | 城市（单选）_修复 | 6f92710c-67f0-4493-9d3b-605f5251c96c | 1 |
| 城市（多选） | 城市（多选）_修复 | c904e218-0412-4dc8-bc92-6a52946272c4 | 5 |

原有六个资产保留，修改前 main.py 与元素库保存在本目录 `main-before.py`、`library-before`。

## 实测步骤与证据

1. CLI 启动抓取实例 PID 141176 / HWND 1189108，观察真实控件后分别执行 capture win。三次 committed=true，commit_unknown=false；多选相似抓取 match_count=5。原始结果见 capture-name.json、capture-single.json、capture-multi.json。
2. CLI 打开元素编辑页，选择两层 Pane，取消随机 class_name，点击保存。只读核对实际保存的文件：Pane 的 required 仅保留相应 uia_name，随机类名转入 optional。每次编辑操作及快照保存在本目录 JSON 中。
3. CLI package validate：姓名和单选数量各 1，多选数量 5，均 passed。
4. 抓取实例在跨启动验证前关闭；随后在示例目录运行 `uv run main.py`，以新的 PID 166884 校验和填写。执行退出码 0，三个保存元素均找到。
5. SDK 回读验证：姓名 moby；单选 [深圳]；多选北京=true、广州=true，其余上海、深圳、杭州=false。详见 main-run.stdout.txt、main-run.stderr.txt、main-run.exitcode.txt。
6. 脚本只断开 SDK 客户端，保留目标程序。CLI 随后 windows list 确认仅一个目标窗口：PID 166884 / HWND 599304，见 final-windows.json。测试观察会话已关闭，未关闭填写后的实例。

main.py 语法检查通过。验证范围为本轮真实抓取实例及一个新启动实例，未声称覆盖所有随机表单布局。

## 本轮被测版本

- 元素抓取器：`D:\code\rust_uia`，Git 根 `D:/code/rust_uia`，分支 main，commit `b700f9238134f57da83ab478a5ee55337ade1082`。
- Desktop：`D:\code\desktop`，Git 根 `D:/code/desktop`，分支 main，commit `7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。
- SDK 源码：`D:\code\desktop\sdk\src`（只读使用，禁用字节码写入）。
- SDK 测试目录：`D:\code\元素库\sdk测试`。
- CLI 测试目录：`D:\code\元素库\CLI测试`。
- CLI：`D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe`。
- CLI SHA-256：`C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8`。
- CLI 版本：`uia 0.1.1`，版本命令退出码 0。源码 commit 和版本号不能单独证明二进制构建来源。
- 靶场 EXE：`D:\code\xpath\WIN32\dist\UIA 版（标准 Win32 控件_随机表单）.exe`。启动工作目录为测试示例目录。

全部脚本、备份和证据写入测试工作区。未修改被测源码或构建产物。
