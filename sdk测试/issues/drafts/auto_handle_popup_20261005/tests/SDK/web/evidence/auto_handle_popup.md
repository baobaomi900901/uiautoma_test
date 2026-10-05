# `uiautoma.web.auto_handle_popup()` 验证记录

本记录为 2026-10-05 测试侧真实验收的产品仓库同步稿。

## 快照与结果

- 产品只读 worktree：`D:\code\desktop`；commit `cb9332d1a04c09e04df54af958e028b2bc45af9b`。
- 靶场只读 worktree：`D:\code\xpath`；commit `c886261211541cd48224dda51dc566af4710df16`。
- 环境：dev Runtime、Chrome；页面 `https://baobaomi900901.github.io/xpath/#/keys-click-test`。
- 元素库：`D:\code\元素库\260902_web元素`；只连接本次临时副本。
- 生命周期：**VERIFIED；连续 3 轮，每轮 19/19 PASS，0 FAIL / 0 BLOCKED，退出码 0。**
- 每轮清理 PASS，标签集合恢复到进入时基线 5→5，无新增/移除外部标签，无本次对话框或临时库残留。

## 用例与独立确证

库元素为 `web靶场_打开遮罩弹窗_按钮`、`web靶场_模态弹窗`、`web靶场_模态弹窗_关闭按钮`。现场核对打开节点 ID=`btn-open-occlusion-modal`，Modal 标题为“遮挡测试弹窗”，关闭按钮是同一 Modal 内唯一的 `button.ant-modal-close`。

19 个用例覆盖合同、六个本地参数/不支持分支、库元素、环境、无规则对照、名称注册、重复注册、注册后 get 页面、名称规则重复自动关闭、Selector 注册、注册后 create 页面、Selector 自动关闭、清理。

无规则对照中，弹窗保持打开 3 秒、关闭事件为零；库关闭按钮手动点击一次后隐藏。自动分支只点击打开按钮，记录到一次真正的关闭按钮 click，事件发生时弹窗可见，结束时隐藏。DOM 监听器只记录状态和事件，没有触发关闭，也没有改变 Modal 行为。

本轮未独立验收 `remove_all_auto_handle_popup()` 的移除后行为，未覆盖 Edge、跨 iframe、选择器歧义、多规则并行、连接中途关闭等情况。

## 历史修正

2026-10-04 的 1/2 PASS + 1 KNOWN 是未找到可用关闭按钮时的条件检查。此前“靶场只有原生 JavaScript 弹窗”的判断已撤回：靶场源码已包含 Ant Design DOM Modal。用户随后新增库中 Modal 与关闭按钮，本记录对应补齐元素后的真实验收；旧原始报告保留为历史证据。

## 测试侧材料与复测

测试仓库为 `baobaomi900901/uiautomata_test`；材料路径：

- `sdk测试/web/test_web_auto_handle_popup.py`（该 API 唯一测试脚本，文件名不含日期）。
- `sdk测试/web/evidence/auto_handle_popup_20261005.md`（完整合同、用例和边界）。
- `sdk测试/web/evidence/artifacts/auto_handle_popup_20261005_run{1,2,3}.{json,txt}`。
- `sdk测试/web/evidence/artifacts/auto_handle_popup_20261005_probe.txt`。

上述为本地归档材料，本交接稿不宣称它们已推送或发布。正式脚本复用测试侧公共辅助模块；应在完整测试工作区复测，不单独复制入口文件到产品仓库后直接运行。

在测试工作区 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_auto_handle_popup.py
```

合同检查可加 `--contract-only`，但该模式不能代替真实验收。
