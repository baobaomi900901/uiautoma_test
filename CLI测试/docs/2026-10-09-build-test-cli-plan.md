# build-test CLI 构建与路径登记 Implementation Plan

> **For agentic workers:** 按本计划在当前会话逐项执行，使用 test-driven-development 和 verification-before-completion；用户已明确要求修改启动脚本和测试 Agent 指引。

**Goal:** `build-test.py` 在启动测试 App 前编译选定 Desktop worktree 的 `uia.exe`，并输出供测试 Agent 登记的绝对路径。

**Architecture:** 在 `desktop_command_plan()` 末尾增加 Cargo release 构建；固定 Windows x64 target 与 `cli/target` 输出目录。路径由 `cli_executable_path()` 统一计算，启动前由 `notify_cli_test_ready()` 显示。CLI 构建失败沿用现有异常、Provider 恢复与 dev 清理流程。

**Tech Stack:** Python 标准库、unittest、Cargo。

## Global Constraints

- 实际被测源码只读；本任务仅修改用户指定的 `D:\code\.tools\build-test.py` 与测试工作区文件。
- 不运行真实构建、同步、依赖安装或启动流程；Cargo 在回归测试中由现有 runner 隔离。
- 新测试、临时目录及验证日志均保存在 `D:\code\元素库`。
- 保留现有六阶段流程，现有 `.tools/tests/test_build_test.py` 不改写。

## Task 1: 编译和提示

**Files:** 修改 `D:\code\.tools\build-test.py`；新增测试 `D:\code\元素库\CLI测试\test_build_test_cli.py`。

**Interfaces:** 新增 `cli_executable_path(desktop: Path) -> Path` 和 `notify_cli_test_ready(cli: Path, *, write=None) -> None`。

- [x] 写测试，确认命令计划末尾存在以下命令且 cwd 为选定 worktree：

```python
("cargo", "build", "--manifest-path", "cli/Cargo.toml", "--release", "--locked",
 "--target", "x86_64-pc-windows-msvc", "--target-dir", "cli/target")
```

- [x] 运行新增测试，确认原脚本缺少 CLI 命令和路径提示而失败。
- [x] 在测试侧暂存脚本副本实现新增计划、统一路径和就绪通知：

```python
def cli_executable_path(desktop: Path) -> Path:
    return (desktop.resolve() / "cli" / "target" / CLI_TARGET / "release" / "uia.exe")
```

- [x] 测试编译步骤由 `prepare_desktop()` 实际执行；模拟 Cargo 失败确认准备中止；测试提示包含绝对路径和 `--help`/`status`。
- [x] 工作流测试保留真实 `prepare_desktop()`，模拟外部 runner，确认 CLI 成功后才通知并启动 dev；失败时 Provider 恢复且不启动 dev。
- [x] 运行原有测试和新增测试全部通过后，将暂存脚本复制回用户指定的实际路径；再针对实际脚本验证。

## Task 2: Agent 路径登记

**Files:** 修改 `D:\code\元素库\AGENTS.md`。

- [x] 保留所有会话对两个源码目录的确认要求；CLI 任务同次补充确认本次 `uia.exe` 绝对路径。
- [x] 要求使用启动脚本的本次输出，记录可执行文件存在性、SHA-256 和 `--version`，不推断或沿用旧路径。
- [x] 重新启动、更换 worktree 或重编译后重新确认 CLI 路径；缺少产物时由用户运行启动脚本准备环境。
- [x] 指引测试覆盖 CLI 条件确认和登记字段；核对原有源码只读边界保留。

## 验收

- [x] 原有完整 unittest 套件与新增回归均通过。
- [x] 对最终实际脚本运行 `--help`，语法解析成功；不执行工作流。
- [x] 记录测试计数、修改的文件和真实 CLI 冒烟尚未执行的范围。

