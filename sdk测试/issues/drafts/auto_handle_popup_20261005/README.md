# auto_handle_popup 公开文档与测试索引同步交接稿

建议 Issue 标题：`docs: 同步 auto_handle_popup 的真实 DOM 弹窗验收（3×19/19）`

## 背景与结论

用户已于 2026-10-05 明确批准生成公开文档交接稿。测试侧对 `uiautoma.web.auto_handle_popup()` 在 dev Runtime / Chrome 下完成连续三轮真实验收，每轮 **19/19 PASS**、退出码 0，标签集合恢复到 5→5，临时库与本次页面清理 PASS。

产品只读 worktree `D:\code\desktop`，commit `cb9332d1a04c09e04df54af958e028b2bc45af9b`；靶场只读 worktree `D:\code\xpath`，commit `c886261211541cd48224dda51dc566af4710df16`。本交接不要求改动产品实现。

已覆盖关闭按钮名称/Web Selector、注册后 get/create 页面、重复打开、重复注册与参数校验；通过真实关闭按钮事件与 DOM 可见性确认副作用。未测试边界和历史条件不足记录在证据中。

## 四个同步目标与完整内容

| 产品仓库目标 | 本目录交接稿 | 操作 |
|---|---|---|
| `sdk/docs/web/auto_handle_popup.md` | [API 说明](sdk/docs/web/auto_handle_popup.md) | 新增完整文档 |
| `sdk/docs/web/index.md` | [索引片段](sdk/docs/web/index.fragment.md) | 插入对应 API 行 |
| `tests/SDK/web/evidence/auto_handle_popup.md` | [验证记录](tests/SDK/web/evidence/auto_handle_popup.md) | 新增完整证据 |
| `tests/SDK/index.md` | [状态片段](tests/SDK/index.fragment.md) | 插入当前快照 VERIFIED 行 |

产品快照中前述 API 文档与证据尚不存在，两个索引也无该 API 行；无需删除其他条目。四处日期、快照、结果数字与范围须保持一致。

## 测试侧材料

- [正式脚本](../../../web/test_web_auto_handle_popup_20261005.py)。
- [保留原命令的入口](../../../web/test_web_auto_handle_popup_20261004.py)。
- [完整验证证据](../../../web/evidence/auto_handle_popup_20261005.md)。
- [第一轮原始报告](../../../web/evidence/artifacts/auto_handle_popup_20261005_run1.json)、[第二轮](../../../web/evidence/artifacts/auto_handle_popup_20261005_run2.json)、[第三轮](../../../web/evidence/artifacts/auto_handle_popup_20261005_run3.json)。

测试侧 `index.md` 与 `web/web api 清单.md` 已同步；旧 2026-10-04 产物保持为历史记录。`remove_all_auto_handle_popup()` 不因本轮辅助调用而提升独立验收状态。

## 交接状态与完成判据

这是本地可审阅的 Issue 正文与文件交接稿，尚未发送 Issue、发布文档或推送材料；本工作区没有修改产品源码仓库文件。

完成同步后，应确认四个目标文件中的日期、快照、19/19×3、清理结果与边界一致，内部相对链接可用，示例与公开 SDK 签名一致。保留旧快照结论，不将条件检查或未测场景表述为通过。
