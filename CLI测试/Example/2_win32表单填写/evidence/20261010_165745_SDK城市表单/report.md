# SDK 城市表单脚本运行结果

脚本：D:\code\元素库\CLI测试\Example\2_win32表单填写\main.py

在此目录执行 `uv run --offline .\main.py`，退出码 0。脚本打印修改前、修改后状态，并验证最终状态。

| 项目 | 修改前 | 修改后 |
| --- | --- | --- |
| 城市（单选）选中项 | 北京 | 深圳 |
| 城市（多选）北京 | true | true |
| 城市（多选）上海 | false | true |
| 城市（多选）广州 | true | false |
| 城市（多选）深圳 | false | false |
| 城市（多选）杭州 | true | false |

## SDK 调用

- `uiautoma.current(required=True)` 借用 App 当前库，校验目录是脚本目录；退出仅释放本地连接。
- `win32.get_list()` 及 `get_detail()` 确认唯一的指定靶场窗口。
- `window.find("城市（单选）")` 获取实际 ComboBox；`get_all_select_items()` 读取五个选项；`get_selected_item()` 读取当前选中项。
- `window.find_all("城市（多选）选项")` 获取相似集合；`get_all_attributes()` 读取实时 `Name`、`IsTogglePatternAvailable` 和 `ToggleToggleState`。本控件的 0/1 分别解释为 false/true；不支持、未知、三态或业务范围错误直接报错。
- `select("深圳", mode="exact", delay_after=0)` 设置单选。
- 对城市集合逐项调用 `check(mode="check"/"uncheck", delay_after=0)`，仅北京和上海设为勾选。
- 修改后重新查找两项保存选择器，并读取实时状态验证。没有用动作返回值推断状态，没有截图视觉判断。

## 实际 SDK 与被测版本

- SDK 源码：D:\code\desktop\sdk，导入 D:\code\desktop\sdk\src\uiautoma；版本 0.1.1。脚本禁止生成 SDK 的 __pycache__，未安装或修改被测源码。
- Desktop 源码：D:\code\desktop；commit 7f148f27c0efa8bbba1f18d86c14845ea7d639fa。
- rust_uia 源码：D:\code\rust_uia；commit b700f9238134f57da83ab478a5ee55337ade1082。
- SDK 测试目录：D:\code\元素库\sdk测试；本次示例位于用户指定的 CLI 示例库目录。
- CLI 既有路径：D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe。
- CLI SHA-256：C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8；--version 为 uia 0.1.1，退出码 0。CLI 未用于本轮状态读取或设置。
- 源码 commit 与版本号不能单独证明该二进制的构建来源。

## 证据

- environment.json：实际路径、commit、版本、CLI 哈希与脚本哈希。
- probe_read_state.py / probe_read_state.stdout.txt：动作前只读 SDK 属性探针。
- main.stdout.txt：脚本修改前、后完整输出。
- main.stderr.txt：为空。
- main.command.json：运行命令与退出码。

复跑：在示例目录执行 `uv run .\main.py`。保持 UIAutoma 和靶场运行，并在 App 打开此示例目录的元素库。
