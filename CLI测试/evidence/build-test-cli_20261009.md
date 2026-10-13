# build-test CLI 编译接入验证（2026-10-09）

两项修改已完成：用户指定的 `D:\code\.tools\build-test.py` 增加 CLI 构建和路径提示；测试项目根 `D:\code\元素库\AGENTS.md` 增加 CLI 实测的路径确认和二进制登记要求。

## 最终行为

- 现有第 5/6 阶段末尾在用户选定的 Desktop worktree 执行：

```text
cargo build --manifest-path cli/Cargo.toml --release --locked --target x86_64-pc-windows-msvc --target-dir cli/target
```

- 显式 target 和 target-dir 固定构建位置；产物为该 worktree 下 `cli/target/x86_64-pc-windows-msvc/release/uia.exe`。
- 编译成功后，在启动 dev 前显示该文件的绝对路径，以及 PowerShell 的 `--help` 和 `status` 调用示例。
- 编译失败沿用现有异常流程：停止启动，退出 Provider 临时安装上下文并执行 dev 清理。
- CLI 实测会话补充询问本次 `uia.exe` 路径；证据登记 CLI 测试目录、文件路径、SHA-256、`--version` 输出/退出码，以及两份源码的路径与 commit。
- `.tools/tests/test_build_test.py` 保持原样；新增回归保存在测试工作区。

## 验证结果

针对写回后的实际脚本：

| 验证 | 结果 | 原始输出 |
| --- | --- | --- |
| 原有完整 unittest 套件 | 76/76 PASS，退出码 0 | [原有套件](build-test-existing-tests_20261009.txt) |
| 新增 CLI 构建与流程回归 | 7/7 PASS，退出码 0 | [新增回归](build-test-cli-tests_20261009.txt) |
| `build-test.py --help` | 正常显示帮助，退出码 0 | 在本轮命令输出中核对 |

新增回归在修改前先运行，确认缺少编译、路径提示和失败拦截；实现后转绿。覆盖中文/空格路径、选定 worktree、显式编译命令、清理步骤不重复、路径输出、成功后通知并启动、失败后恢复且不启动。

原有套件的受限运行曾发生 28 个临时目录访问错误；解除该测试进程的沙箱限制后，暂存脚本与实际脚本的两次完整运行均 76/76 PASS。这是本地测试目录权限问题，未放宽断言或修改既有测试。

## 复测命令

从 `D:\code\元素库` 执行，临时目录与日志放在测试工作区：

```powershell
$env:TEMP = 'D:\code\元素库\.pytest_tmp\build-test-cli\temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\sdk测试\.venv\Scripts\python.exe -B D:\code\.tools\tests\test_build_test.py -v
& .\sdk测试\.venv\Scripts\python.exe -B -m unittest discover -s CLI测试 -p test_build_test_cli.py -v
& .\sdk测试\.venv\Scripts\python.exe -B D:\code\.tools\build-test.py --help
```

## 文件证据与范围

- 修改前脚本 SHA-256：`39CEF19EBB8973B6D9CC3F0732B2C6614610D429B31F418CBD9F935ED918F500`。
- 写回后脚本 SHA-256：`242FEEC8E1E8547B4DB36296FA2CF0B6FD82E8044F74F26EB3E3E3D1A6941D38`。
- [脚本差异](build-test-cli_20261009.patch)；写回前检查原文件哈希未变，写回后核对与已通过验证的暂存脚本一致。
- 新增测试通过 runner 隔离真实外部命令；既有套件只使用测试夹具。未执行真实 Cargo 构建、产品同步、安装、启动或 CLI 冒烟。
- `D:\code\rust_uia` 与 `D:\code\desktop` 未被本任务写入。
