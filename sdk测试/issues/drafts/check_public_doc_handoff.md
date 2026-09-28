## 背景

测试侧于 2026-09-24 对 `uiautoma.web.WebElement.check()` 完成真实复验。被测产品源码 commit 为 `e08eadd0d6d921ea11579e4acfb894c1c4cee038`，环境为 dev Runtime + Chrome，靶场为 <https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>。本单仅交接公开文档与测试索引同步，不要求修改产品实现。

测试侧提交：[uiautoma_test@35b078a](https://github.com/baobaomi900901/uiautoma_test/commit/35b078a)，包含持久化脚本、验证证据、三轮原始报告和修正后的元素库快照。

## 复验结论

- 连续三轮完整运行均为 `61/61 PASS`、`0 FAIL`、`0 BLOCKED`，退出码 `0`；资源清理每轮均为 `PASS`。
- Ant 与原生表单的 radio / checkbox `input`、`label` 均直接调用 `check()`，再通过目标 DOM `checked` 与页面提交 JSON 的 `gender` / `hobbies` 独立确证。checkbox 幂等 `check`、`uncheck`、`toggle`，非法参数及 radio 禁止取消也通过。
- 2026-09-23 的 `60/61` 中，Ant「音乐」input 的旧保存选择器同时命中 Ant 与原生两个节点。用户在 App 中确认双匹配并重新抓取，使 `id=form-controls-ant-hobbyMusic` 成为必需条件；2026-09-24 的正式用例直接调用该 input 的 `check()`，DOM、提交值与重置均通过。
- 未读写系统剪贴板；未覆盖 Edge、CEF、动态 ID 开启或其他靶场。

## 请求同步的产品仓库文件

1. `sdk/docs/web/check.md`：补充当前快照下的真实验收、独立确证方式和适用范围；把“本轮未提升其验收状态”保留为带日期的历史记录。公开签名仍为 `check(mode='check', delay_after=1) -> None`。
2. `sdk/docs/web/index.md`：让 `check()` 条目指向更新后的说明与当前验证状态。
3. `tests/SDK/web/evidence/check.md`：保留 2026-08-08 旧快照失败记录，追加 2026-09-23 定位阻塞和 2026-09-24 三轮通过的测试侧证据链接。
4. `tests/SDK/index.md`：将当前快照下的 `check()` 状态订正为 `VERIFIED`，注明 `61/61`、连续三轮退出码 `0` 和限定环境。

历史 [Issue #12](https://github.com/uiautoma/desktop/issues/12) 对应旧靶场与旧源码快照；本次不同环境的通过结果不自动证明其原场景已复测，也不据此直接关闭该 Issue。

## 完成判据

- 四处文件的日期、被测 commit、结果数字、适用范围和历史结论一致。
- 公开文档只把此次真实通过的场景写成已验证行为，明确列出未测边界。
- 链接到测试侧脚本、证据和原始报告；不把 `click()` 人工演示算作 `check()` 的目标 API 验收。
