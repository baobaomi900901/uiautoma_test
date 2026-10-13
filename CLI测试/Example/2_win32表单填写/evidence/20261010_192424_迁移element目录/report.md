# 元素库迁移到 element

参考 D:\code\元素库\CLI测试\Example\1_网页表单填写 的组织方式，将 Win32 示例的元素库整体迁至：

D:\code\元素库\CLI测试\Example\2_win32表单填写\element

迁移项目：package.json、elements.json、images.json、icon、images、screenshot、snapshot。

main.py 和 evidence 保留在示例根目录。main.py 的 LIBRARY_DIR 变为脚本所在目录 / element；启动时使用 uiautoma.open() 自动绑定此目录，最后使用 uiautoma.close() 释放 SDK 连接，与网页示例的方式一致。城市读写行为保持原有实现。

## 验证

- 全部 7 个库文件在移动前后的相对路径、长度及 SHA-256 均一致。
- 包 ID d13bd3c5-3e17-40b6-a2f8-ea27676e1632 保持一致。
- 两个资产及其 UUID 保持一致：城市（单选）、城市（多选）选项。
- 两项资产的 snapshot 和 screenshot 文件均存在，清单与快照 JSON 可解析。
- 根目录不再保留元素库清单或资源目录。
- python -W error 导入及语法检查通过，确认 main.LIBRARY_DIR 指向新 element 目录，退出码 0。
- 首次验证探针从 evidence 运行时缺少示例根目录的导入路径；修正探针后通过。初始失败日志单独保留在 verify-initial.*。

本轮为目录迁移及文件、脚本导入验证，没有重新运行城市选择动作。Runtime 当前为其他示例库，因此本轮没有切换其共享库；用户下次运行 main.py 时会自动打开本示例的 element 目录。

此前原始测试证据中的路径对应当时实际运行目录，保留历史原样；当前运行说明已更新为新目录。

## 版本与证据

- 元素抓取器源码：D:\code\rust_uia；commit b700f9238134f57da83ab478a5ee55337ade1082。
- Desktop 源码：D:\code\desktop；commit 7f148f27c0efa8bbba1f18d86c14845ea7d639fa。
- SDK 来源：D:\code\desktop\sdk；SDK 测试目录：D:\code\元素库\sdk测试。
- CLI 测试目录：D:\code\元素库\CLI测试\Example\2_win32表单填写。
- CLI 路径：D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe。
- CLI SHA-256：C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8。
- --version：uia 0.1.1，退出码 0。源码 commit 与版本号不能单独证明二进制构建来源。

move-plan.json 为已核对的绝对移动路径；files-before.json、files-after.json 和 integrity-check.json 为文件完整性证据；verify.stdout.txt、verify.stderr.txt 和 verify.command.json 为导入及资源路径检查结果。

运行方式不变：在示例根目录执行 uv run .\main.py。
