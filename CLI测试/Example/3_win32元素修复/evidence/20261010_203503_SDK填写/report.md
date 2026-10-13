# 随机 Win32 表单 SDK 脚本验证

已创建 `D:\code\元素库\CLI测试\Example\3_win32元素修复\main.py`，加载旁边的 `element` 元素库，使用用户保存的“姓名”“城市（单选）”“城市（多选）”三个资产。

本轮使用 `uiautoma-sdk` 指引编写 SDK 示例脚本，不是完整的公开 API 验收矩阵。

## 版本与目录

- rust_uia：`D:\code\rust_uia`，commit `b700f9238134f57da83ab478a5ee55337ade1082`。
- Desktop：`D:\code\desktop`，commit `7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。
- SDK 来源：`D:\code\desktop\sdk\src`，实际导入版本 `0.1.1`。
- SDK 测试目录及实测工作目录：`D:\code\元素库\sdk测试`。
- 元素库：`D:\code\元素库\CLI测试\Example\3_win32元素修复\element`。
- Python：`D:\code\元素库\sdk测试\.venv\Scripts\python.exe`。

## 实际结果

Python 语法检查通过。只读 SDK 探针确认三个保存元素可定位，复选框集合恰好包含北京、上海、广州、深圳、杭州，全部支持 Toggle 状态读取。

脚本使用 `win32.get_by_selector("姓名")` 找到所属窗口，使用 `window.find/find_all` 定位控件。`Win32Element.input(simulative=False, append=False)` 覆盖姓名，`select(mode="exact")` 选择深圳，`check(mode="check"/"uncheck")` 设置五个复选框状态。修改前完成范围检查，修改后重新定位并读取实时值核对，异常不重试操作。

| 目标 | 期望 | 实际 |
| --- | --- | --- |
| 姓名 | moby | moby |
| 城市（单选） | 深圳 | 深圳 |
| 城市（多选） | 仅北京、广州 | 北京和广州为 true，上海、深圳、杭州为 false |

实测命令：`D:\code\元素库\sdk测试\.venv\Scripts\python.exe -B D:\code\元素库\CLI测试\Example\3_win32元素修复\main.py`。退出码 0，标准错误为空。脚本在 `finally` 中调用 `uiautoma.close()` 释放 SDK 连接；靶场和填写结果保留。

用户运行方式：在示例目录执行 `uv run .\main.py`。脚本使用本会话确认的 SDK 源码路径，不安装第三方包；设置 `sys.dont_write_bytecode=True`，实测另加 `-B`，防止写入被测源码目录。该 `uv` 启动命令未单独试跑，本轮使用上述现有 Python 环境完成实际验证。

环境登记见 `environment.json`；探针原始结果见 `probe.json`；实际脚本输出见 `main.stdout.txt`，参数、退出码及脚本哈希见 `main.command.json`。
