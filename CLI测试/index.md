# CLI 测试状态

| 项目 | 状态和覆盖 | 入口 | 证据 |
| --- | --- | --- | --- |
| 独立 Rust CLI 基础冒烟 | `VERIFIED`：2026-10-09 最后连续三轮各 85/85 PASS；首轮 84 PASS + 1 BLOCKED 保留；仅帮助、参数和只读查询范围 | [test_cli_smoke.py](test_cli_smoke.py) | [实测](evidence/smoke.md) |
| build-test CLI 编译接入 | 原有 76 + 新增 7 项模拟回归通过；未由 Agent 执行真实构建；用户随后启动日志显示 CLI 构建完成 | [test_build_test_cli.py](test_build_test_cli.py) | [流程验证](evidence/build-test-cli_20261009.md) |

每次实测遵循根 `AGENTS.md`，重新确认两份源码目录和本次 CLI 文件路径；登记 commit、CLI 哈希/版本和实际输出。上表的基础冒烟通过不代表全部 CLI 动作已验收。
