# CLI 基础冒烟实测

2026-10-09 完成真实 Windows CLI + Runtime 基础冒烟。最后连续三轮各 **85/85 PASS**，退出码均为 **0**；基础冒烟范围内未发现产品 FAIL。首轮为 84 PASS + 1 BLOCKED，原始记录保留，不计为全通过。

## 本轮版本和环境

| 项目 | 实际路径/版本 |
| --- | --- |
| 元素抓取器源码 | `D:\code\rust_uia`，`main@b700f9238134f57da83ab478a5ee55337ade1082` |
| Desktop 源码 | `D:\code\desktop`，`main@7f148f27c0efa8bbba1f18d86c14845ea7d639fa` |
| SDK 测试目录 | `D:\code\元素库\sdk测试` |
| CLI 测试目录 | `D:\code\元素库\CLI测试` |
| CLI 可执行文件 | `D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe` |
| CLI SHA-256 | `C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8` |
| CLI 版本输出 | `uia 0.1.1` |
| Runtime | `UIAutoma Runtime 0.1.1`，PID `95580`，协议/min_protocol `1/1` |
| 实际管道 | `\\.\pipe\UIAutoma.Automation.v1` |
| 当前元素库 | `D:\code\元素库\260902_web元素`，有库状态 |
| 浏览器/会话基线 | 1 个已连接浏览器环境、8 个页面；Win/Web 观察会话均为 0 |

用户在本次重新运行启动脚本后再次确认两份源码目录和 CLI 绝对路径。每轮重新记录 Git 根目录、分支、commit 与 CLI 文件哈希。测试后只读复核，源码 commit 与 CLI 哈希均未变化。commit 和版本号不单独证明二进制构建来源。

## 实测结果

| 轮次（上海时间） | PASS | FAIL | BLOCKED | 退出码 | 标签收尾 | 原始产物 |
| --- | --- | --- | --- | --- | --- | --- |
| 1，11:21:57 | 84/85 | 0 | 1 | 2 | 8→8 | [JSON](artifacts/cli_smoke_20261009_round1.json)、[文本](artifacts/cli_smoke_20261009_round1.txt) |
| 2，11:23:50 | 85/85 | 0 | 0 | 0 | 8→8 | [JSON](artifacts/cli_smoke_20261009_round2.json)、[文本](artifacts/cli_smoke_20261009_round2.txt) |
| 3，11:23:54 | 85/85 | 0 | 0 | 0 | 8→8 | [JSON](artifacts/cli_smoke_20261009_round3.json)、[文本](artifacts/cli_smoke_20261009_round3.txt) |
| 4，11:23:57 | 85/85 | 0 | 0 | 0 | 8→8 | [JSON](artifacts/cli_smoke_20261009_round4.json)、[文本](artifacts/cli_smoke_20261009_round4.txt) |

最后三轮每轮均确认当前库、Runtime PID、页面引用集合、浏览器连接数与 Win/Web 观察会话集合保持本轮基线。窗口与页面发现的前后台核对全部通过。

## 覆盖、合同与期望值来源

| 类别 | 用例数 | 实测合同 |
| --- | --- | --- |
| 版本和帮助 | 23 | 长/短版本选项；根帮助及 JSON 帮助保持文本；13 个顶层命令和 5 个嵌套帮助；英文帮助与 Runtime 前置说明 |
| 参数和格式 | 38 | 必填项、非法命令/选项、参数冲突、句柄及快照边界、预算/响应大小解析范围；JSON 前后位置和等号写法；缺失/非法格式回退文本；参数值与 `--` 后内容不被误认成格式选项；拒绝非本地或空名称管道 |
| 不可用连接与管道选择 | 4 | 100ms 连接预算有限退出；text/JSON 的 `runtime_unavailable` 与退出码 3；环境变量选择及显式管道优先 |
| 离线文档 | 5 | 显式本地 Skills 下主题目录、精确符号及 contracts；不存在符号和缺失资源的公开错误；随机不存在的管道下可运行 |
| Runtime 只读查询 | 13 | 状态、默认 text、debug 的 stdout/stderr 分离、能力声明、当前库、窗口/页面发现及过滤、观察会话列表 |
| 环境基线和收尾 | 2 | 前后 PID、库、标签引用及观察会话一致 |
| 合计 | 85 | 真实执行并记录返回码、stdout/stderr、期望、实际和耗时 |

以上合同均来自 **`D:\code\desktop`，commit `7f148f27c0efa8bbba1f18d86c14845ea7d639fa`** 的只读快照：

- `cli/AGENTS.md`、`cli/Cargo.toml`：英文帮助、输出格式、退出码与版本声明。
- `cli/command/src/main.rs`：命令和参数范围、格式识别、参数错误及退出码映射。
- `cli/client/src/lib.rs`：本地管道配置、连接期限、握手及公开发现结果。
- `cli/command/src/public_output.rs`、`text_output.rs`、`debug_output.rs`：公共 JSON、列表计数、文本与诊断通道。
- `cli/command/src/docs.rs`、`packages.rs`、`screenshots.rs`、`text_input.rs`：离线参考、当前库、必填项和参数冲突。

参数/冲突测试一律使用随机不存在的管道，即使判据有误也无法向当前 Runtime 发送业务动作。预算合法边界使用无效管道，在本地配置拒绝前确认解析已接受；这不代表真实 RPC 超时或响应大小上限已经验收。

## 独立核对和首轮阻塞

- 版本输出与源码 Cargo 声明核对；执行文件单独计算 SHA-256。
- JSON 成功/错误外层类型、单行输出和真实进程退出码分别校验。debug 的 stderr 每行单独解析，不只检查命令返回成功。
- 发现前后使用 Win32 `GetForegroundWindow` 独立核对；Runtime 的库、页面引用与观察会话在整轮前后分别读取并比较。
- 原始 JSON 保存实际参数和输出；浏览器列表只归档页面身份、浏览器类型、tab ID 及计数，省略与验收无关的标题、URL 和连接标识。
- 首轮 `browser_empty_json` 检测到前台 HWND `1581584→992074`，因此标为 `BLOCKED`。同期 API 返回符合合同，整轮收尾一致；现有证据无法确认窗口变化与 CLI 的因果关系，未报为产品缺陷。
- 增加窗口所属进程/类名的诊断记录后，保持断言不变，后续连续三轮全部通过。没有关闭前台检查、重试单条用例掩盖阻塞或删除首轮记录。
- 执行工具的沙箱初次连接 Runtime 返回 OS error 5；解除该测试进程限制后正常连接。手工 `status` 和真实复测均连通，同一 Runtime PID 为 95580；该访问限制未计为产品失败。

## 覆盖边界

`VERIFIED` 仅表示本次基础冒烟范围。当前库查询只实测了已有库状态。未改变元素库，也未验收无库状态、切库、资源捕获、截图、点击、输入、窗口控制、浏览器创建/导航或元素观察内容。

本轮实测退出码 0、2、3；未注入 RPC/协议故障（1）或协议/能力不支持（4）。离线文档使用显式源码 Skills 目录，不代表安装版资源、PATH 或 Setup 验收。能力表仅是声明，Provider 的 available 标志不等于所有 UIA/ACC 动作均已通过。

## 复测入口

先按根 `AGENTS.md` 重新确认本次两份源码目录和 CLI 路径，然后从 `D:\code\元素库` 执行：

```powershell
& .\sdk测试\.venv\Scripts\python.exe -B .\CLI测试\test_cli_smoke.py `
  --cli 'D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe' `
  --provider-source 'D:\code\rust_uia' `
  --desktop-source 'D:\code\desktop' `
  --out '.\CLI测试\evidence\artifacts\cli_smoke_retest.json'
```

路径为本轮示例，不是后续会话的默认值。脚本退出码 0 表示全通过，1 表示存在 FAIL，2 表示存在 BLOCKED。一次运行同时保存同名 JSON 和 TXT。只有得到本轮真实结果后才更新状态与计数。

唯一持久化入口为 `CLI测试/test_cli_smoke.py`；本轮脚本 SHA-256 为 `FAA3249E8B6820EC5F79125A09E7309659B8D69998B1628D2F8C60E56BD8B43C`。[环境登记](smoke_environment_20261009.json)保存当前确认路径和四轮计数。
