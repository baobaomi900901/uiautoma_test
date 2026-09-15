# SDK PERSISTENT TESTS

## SCOPE

本文件适用于本测试工作区（`D:\code\元素库\sdk测试`）下的 SDK 实测脚本、验证证据、
复现材料和状态索引。本工作区是被测产品的**测试侧副本**，不是产品源码仓库。
未覆盖事项继续遵循仓库侧 `tests/SDK/AGENTS.md` 与仓库根 `AGENTS.md` 中的测试约定。

## WORKSPACE BOUNDARY

- **仓库映射**：本工作区（`D:\code\元素库`）的远端是
  https://github.com/baobaomi900901/uiautomata_test （`origin`，分支 `main`），只存放
  元素库、SDK 实测脚本与测试文档。
  https://github.com/baobaomi900901/xpath 是**靶场站点源码仓库**（即
  `https://baobaomi900901.github.io/xpath/` 的源码），不是测试脚本与元素库的存放位置；
  两者不要混用。
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

## TEST WORKFLOW

每轮**只验证一个**公开 API，按下面 7 步走，每步都有完成判据。判据细则是
[`web/web api 实测手册.md`](web/web%20api%20实测手册.md)（状态模型、期望值来源、独立确证手法、
抖动治理、脚本与证据骨架、反模式清单）；本节的步骤是每轮都要执行的，手册按需查阅。

**前置**：测试环境由 `D:\code\.tools\build-test.py` 拉起（选定的被测 worktree + Runtime + Chrome），
脚本一律在 `D:\code\元素库\sdk测试` 下用 `uv run .\web\<脚本>.py` 运行。

1. **定合同**：从被测 worktree 读该 API 的完整链路——SDK 方法（签名/默认值/返回注解/docstring）
   → RPC 名 → Runtime 的参数校验与业务分支 → 引擎实现；把 worktree 与 commit 记为快照证据。
   *完成判据*：能列出「参数、默认值、返回类型、每种失败的错误类型与文案、失败路径」对照表，
   并据此决定每条断言该期望什么。
2. **摸行为**：先在 `.pytest_tmp/` 写一次性探针，把「文档没说清、可能截断、可能抖动」的语义实测一遍。
   *完成判据*：每条待断言的行为都有实测依据；意外行为已记录，而不是留给正式脚本去发现。
3. **写脚本**：`web/test_web_<browser|element>_<api>.py`，含合同自检、环境基线、准备、正向路径、
   语义矩阵、参数校验、生命周期、收尾复核。
   *完成判据*：脚本无人干预可跑完，并对每条用例自报「期望什么、实测什么、耗时多少」。
4. **试跑加固**：先自己跑；任何 FAIL 必须定性为「产品缺陷 / 我的判据错 / 环境抖动」三者之一并给出依据。
   *完成判据*：连续 3 次完整运行全绿；或缺陷已按 Issue 交接并在脚本与证据里如实标注。
5. **出证据**：`web/evidence/<api>.md` + `web/evidence/artifacts/<api>_<yyyymmdd>.txt`（UTF-8）。
   *完成判据*：用途与合同、真实验收结果、期望值来源与独立确证、实测行为与已知边界、复测命令，五要素齐全。
6. **更索引**：同步 `index.md` 与 `web/web api 清单.md` 中该 API 的状态与计数。
   *完成判据*：两处数字一致，且与本次实际运行结果一致。
7. **定点提交**：`git add` 逐条写显式路径 → 中文提交（含结果数字）→ 推送 → 汇报。
   *完成判据*：仓库干净、`.pytest_tmp` 为空、浏览器标签数与进入时一致。

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
