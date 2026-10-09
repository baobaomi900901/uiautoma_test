# Issue #23：is_enabled 最新复测交接（2026-10-08）

Issue：https://github.com/uiautoma/desktop/issues/23（核对时 OPEN）。

用户明确授权后，复测摘要已补充为 [评论 6055620980](https://github.com/uiautoma/desktop/issues/23#issuecomment-6055620980)。[已发布正文副本](comment_6055620980.md)，[API 验收证据](../../web/evidence/is_enabled.md)，[当前唯一脚本](../../web/test_web_element_is_enabled.py)。

## 复现与结果

```powershell
cd 'D:\code\元素库\sdk测试'
uv run .\web\test_web_element_is_enabled.py
```

默认靶场 keys-click-test，库 260902_web元素；禁用按钮和单击触发按钮均经库唯一定位。三轮每轮 30/32 PASS、2 FAIL、0 BLOCKED，退出码 1；失败是同一缺陷在两个真实按钮上分别出现。

原始禁用按钮 False、原始可用按钮 True，均正确。对任一现有按钮设置 `disabled="false"` 时，浏览器 `disabled=True`、`:disabled=True`，API 返回 True，期望 False。属性随后恢复，三轮清理均 PASS、标签 2→2、无输入或点击事件。

## 源码线索，仅限只读快照

worktree：`D:\code\desktop`；HEAD：`7f148f27c0efa8bbba1f18d86c14845ea7d639fa`；文件 SHA-256 与完整链路摘录见 [合同快照](../../web/element_is_enabled_contract_20261008.json)。

`sdk/src/uiautoma/web/element.py:866` → `_read_state("is_enabled")` → `web.is_enabled` → `ActionService._run_web_value` → `runtime/web/bridge_client.py:web_dom_action` → `chrome/engine/engine_packages/page_engine_runtime.js:2780`。

`:2787` 将 disabled 字符串恰好为 false 的情况当作可用；它与浏览器对 HTML 布尔属性的存在语义不一致。历史 Issue 的 Request 第 1 条也把 false/False 列为可用，应修正验收口径，并将 HTML disabled 和 ARIA true/false 字符串语义分开。测试侧不修改产品源码。

## 产品侧待交接事项

- 修复 HTML disabled 属性判定；保留现有公开签名。
- 针对实际原生控件回归属性缺失、空串、disabled、true、false、False 和 disabled IDL 动态切换；继续验证 ARIA true/false。
- 同步产品侧持久化脚本、验证证据与索引。修复并完成真实复验前维持 READY_FOR_LIVE，不把失败写成公开 API 已验证行为。
- 本测试工作区只更新测试侧材料。未获本 API 公开文档生成授权，且当前未满足 VERIFIED 门槛，因此没有生成公开 API 文档。
