# 元素库目录调整

参考 `D:\code\元素库\CLI测试\Example\1_网页表单填写`，已将本轮元素库的 3 个 JSON 文件和 4 个资源目录整体移入 `D:\code\元素库\CLI测试\Example\3_win32元素修复\element`。

## 实际环境

- rust_uia：`D:\code\rust_uia`，commit `b700f9238134f57da83ab478a5ee55337ade1082`。
- Desktop：`D:\code\desktop`，commit `7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。
- SDK 测试目录：`D:\code\元素库\sdk测试`。
- CLI 测试目录：`D:\code\元素库\CLI测试`。
- CLI：`D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe`。
- SHA-256：`C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8`。
- 版本：`uia 0.1.1`，`--version` 退出码 0。
- 源码 commit 和版本号不能单独证明二进制的构建来源。

## 调整与验证

1. CLI `package current` 确认旧目录后，`package close` 释放旧路径的当前库引用。
2. 确认源目录、目标目录均处于测试工作区，并且目标尚不存在；使用 PowerShell `Move-Item -LiteralPath` 移动 `package.json`、`elements.json`、`images.json`、`snapshot`、`screenshot`、`icon`、`images` 七项。
3. 核对移动前后全部文件的 SHA-256 相同；旧根目录只保留 `element` 子目录。Package ID 保持 `85e0046b-6ee2-477f-95ea-fa57a1b77899`，名称保持 `3_win32元素修复`。
4. CLI `package open --path 'D:\code\元素库\CLI测试\Example\3_win32元素修复\element' --in-app` 返回 `opened=true`、`app_opened=true`、`item_count=0`。
5. `package current` 返回新路径；`package items` 返回 `count=0`。本轮 CLI 操作退出码均为 0。

本轮只移动测试侧元素库文件，没有修改被测源码。版本登记见 `environment-relocation.json`，文件校验见 `relocation-files-before.json` 和 `relocation-files-after.json`，CLI 操作证据见 `relocation-*.json` 及对应命令记录。
