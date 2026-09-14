# SDK PERSISTENT TESTS

## SCOPE

本文件适用于 `tests/SDK/` 下的 SDK 持久化测试脚本、验证证据和状态索引。
未覆盖事项继续遵循上级 `tests/AGENTS.md` 和仓库根 `AGENTS.md`。

## PUBLIC DOCUMENTATION GATE

- 每次只验证一个公开 SDK API，并使用 `DRAFT`、`READY_FOR_LIVE`、`VERIFIED`
  表示持久化测试生命周期。
- 只有真实场景与本次资源清理均为 `PASS` 时，API 才能进入 `VERIFIED`。
- API 达到 `VERIFIED` 后，agent 必须主动提示用户是否生成或更新对应的公开 API
  文档、验证证据和索引。
- 获得用户明确确认前，不得自动生成、修改、提交或推送公开 API 文档。
- 用户确认后，在同一任务内同步更新：
  - `sdk/docs/<module>/<api>.md`
  - `sdk/docs/<module>/index.md`
  - `tests/SDK/<module>/evidence/<api>.md`
  - `tests/SDK/index.md`
- `FAIL` 或 `BLOCKED` 结果不得写成公开文档中的已验证行为；应先报告失败或环境阻塞。
