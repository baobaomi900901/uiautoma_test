# 元素库初始化结果

后续已按用户要求将元素库整体移至 `D:\code\元素库\CLI测试\Example\3_win32元素修复\element`，并通过 CLI 在应用中打开新路径，详见 [目录调整结果](report-relocation.md)。以下记录保留初次初始化时的路径和证据。

已通过用户指定的 CLI 初始化 `D:\code\元素库\CLI测试\Example\3_win32元素修复`。

## 本轮环境

- 元素抓取器源码：`D:\code\rust_uia`，Git 分支 `main`，commit `b700f9238134f57da83ab478a5ee55337ade1082`。
- Desktop 源码：`D:\code\desktop`，Git 分支 `main`，commit `7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。
- SDK 测试目录：`D:\code\元素库\sdk测试`。
- CLI 测试目录：`D:\code\元素库\CLI测试`。
- CLI：`D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe`。
- CLI SHA-256：`C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8`。
- `--version`：`uia 0.1.1`，退出码 0。
- 源码 commit 和 CLI 版本号不能单独证明二进制的构建来源。

## 操作和验收

当前 CLI 没有独立的初始化命令，`package open` 只打开已有库。本轮使用 `windows list`、`observe win open/subtree`、`win input/click` 操作程序公开的目录选择与初始化入口。没有调用电脑控制或浏览器 GUI 工具，没有使用 Python SDK，没有修改被测源码。

第一轮目录选择在确认前已关闭，点击返回 `target_closed`，旧应用观察随后返回 `stale_session`。用户提示可能误关了对话框。已保存实际错误，重新观察并操作当前界面，没有重复执行未知结果的初始化。

验收证据：

- `app-pending-init-tree.json`：初始化前界面明确显示指定目录及“初始化”按钮。
- `initialize-click.json`：CLI 点击初始化成功，退出码 0。
- `package-current-after-init.json`：当前库目录为 `D:\code\元素库\CLI测试\Example\3_win32元素修复`，退出码 0。
- `package-items-after-init.json`：`count=0`、`items=[]`，退出码 0。
- `library-files-verification.json`：`package.json`、`elements.json`、`images.json` 均存在且可解析；`snapshot`、`screenshot`、`icon`、`images` 四个目录存在。

Package 名称为 `3_win32元素修复`，ID 为 `85e0046b-6ee2-477f-95ea-fa57a1b77899`。元素和图像目录均为 `groups=[]`，全局变量为空。

版本登记见 `environment.json`；每条 CLI 命令的完整参数和退出码见对应的 `*.command.json`，输出见 `*.json` 和 `*.stderr.txt`。两个有效观察会话已返回 `closed=true`，两个旧观察会话已失效，返回 `stale_session`；清理证据见 `close-*.json`。程序及当前元素库保持打开。
