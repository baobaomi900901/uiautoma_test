# SDK PERSISTENT TESTS

## SCOPE

本文件适用于本测试工作区（`D:\code\元素库\sdk测试`）下的 SDK 实测脚本、验证证据、
复现材料和状态索引。本工作区是被测产品的**测试侧副本**，不是产品源码仓库。
未覆盖事项继续遵循仓库侧 `tests/SDK/AGENTS.md` 与仓库根 `AGENTS.md` 中的测试约定。

## WORKSPACE BOUNDARY

- 本工作区**只允许**：开发与运行测试脚本、编写测试文档与证据、归档复现材料、提交 Issue。
- **禁止修改被测产品源码**，包括 `D:\code\desktop` 的主检出、任何 `.worktree` 和任何分支：
  不得在其中新建、修改或删除文件，不得创建/切换分支，不得提交或推送。
- 被测源码只读。引用源码位置时必须同时标注 worktree 与 commit，作为**快照证据**，
  不得表述为当前分支的结论。
- 源码侧需要同步的内容（`tests/SDK/index.md`、`tests/SDK/<module>/evidence/`、
  `sdk/docs/<module>/`）在本工作区**不直接修改**，统一通过 Issue 交接：
  https://github.com/uiautoma/desktop/issues
- 本工作区内的对应物：`index.md`（状态索引）、`web/evidence/` 与 `win32/evidence/`
  （验证证据）、`issues/issue_<n>/`（复现脚本、原始产物与 Issue 正文归档）。

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
- 上述四个路径位于产品源码仓库，按 WORKSPACE BOUNDARY 在本工作区不直接修改；
  本工作区以 `index.md`、`web/evidence/`、`win32/evidence/` 记录同一结论，
  并把需要源码侧同步的部分通过 Issue 交接。
