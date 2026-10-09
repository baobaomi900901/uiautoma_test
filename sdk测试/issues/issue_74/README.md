# desktop Issue #74 复现归档

- 缺陷单：[#74](https://github.com/uiautoma/desktop/issues/74)，OPEN。
- 提测总单关联评论：[#51](https://github.com/uiautoma/desktop/issues/51#issuecomment-6006002391)。
- 2026-10-06 搜索全部状态；`cookie` 命中 #51/#58、`set_cookie` 命中 #51、`cookie_set_failed` 无命中。#51 为总单且要求具体缺陷另建，#58 为无关导航问题；未找到同缺陷后新建 #74。
- 正式验收：run2/run3/run4 每轮 20/21 PASS + 1 FAIL，清理 PASS；状态保持 READY_FOR_LIVE，不表示修复通过。
- 源码快照：只读 worktree `D:\code\desktop`，commit `cb9332d1a04c09e04df54af958e028b2bc45af9b`。

## 材料

- [实际发布正文](issue_body.md)与[远端读回](github_issue_20261006.json)：已核对一致。
- [总单评论正文](tracker_comment.md)与[远端读回](github_tracker_comment_20261006.json)：已核对一致。
- [搜索与发布审核记录](search_audit.json)。自动审批首次拒绝含本地路径、原始产物和源码定位的完整稿；改用精简稿后成功发布。只读确认目标仓库为 PRIVATE。完整稿未对外发布。
- [完整技术证据](technical_evidence.md)、[冻结合同](browser_cookie_contracts_20261006.json)。
- [已执行诊断探针和复现说明](confirmation_probe/README.md)：原生 Chrome 18 项对照、SDK 三对页面绑定对照。探针运行前复制到 `.pytest_tmp`，不能在归档目录生成浏览器配置。
- `artifacts/`：正式三轮完整 JSON/输出、原生与 SDK 对照 JSON/输出、原生探针初次准备错误及确认汇总，共 13 件，保留实际原始数据。
- [正式 API 证据](../../web/evidence/browser_set_cookie.md)，[唯一无日期测试入口](../../web/test_web_browser_set_cookie.py)。
- [本目录 SHA-256](archive_sha256.json)。

所有本地完整材料均未通过本 Issue 上传；远端正文已包含调用参数、失败现象、原生对照、验收计数和修复建议。
