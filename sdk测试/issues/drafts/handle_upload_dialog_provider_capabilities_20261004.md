# 上传对话框测试无法唤起窗口：Provider 缺少 Runtime 要求的能力

状态：历史诊断草稿，尚未提交 Issue。2026-10-05 本机 Provider 更新为 `a18ff222a6c237cce0c5b39b93d92aa26f34946b` 后，按用户指定单/多文件元素连续 3 轮 10/10 PASS，此阻塞未再复现；见 [最新证据](../../web/evidence/web_handle_upload_dialog_20261005.md)。以下保留 2026-10-04 的快照与复现记录，当时 `handle_upload_dialog()` 正向功能尚未验收。

## 源码与运行环境快照

- Runtime/SDK worktree：`D:\code\desktop`，commit `cb9332d1a04c09e04df54af958e028b2bc45af9b`。
- Provider 来源 worktree：`D:\code\rust_uia`，commit `e8a7545cdd58d744addf972deebaec4faf67a048`（本机 HEAD 与本机 `origin/main` 均为该 commit；没有查询远端最新提交）。
- Provider 运行路径：`D:\code\desktop\assets\provider\UIAutoma.UIAutomation.Provider.exe`；`asset-manifest.json` 记录 SHA-256 `CF68DF41ACBECC758A5B00470B7B997F35E7041A065CFE88C407623B8A4684ED`。
- 靶场：<https://baobaomi900901.github.io/xpath/#/upload-dialog-test>。
- 原始元素库：`D:\code\元素库\260902_web元素`；脚本打开临时副本。

## 复现方式

在已由 `D:\code\.tools\build-test.py` 启动的 dev 环境运行：

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_handle_upload_dialog_20261004.py
```

最小核心调用：

```python
element = page.find('web靶场_上传对话框测试 _原生_上传组件')
assert element.get_attribute('id') == 'input-upload-single'
element.click(simulative=True, delay_after=.1)  # 此处失败
# 尚未执行 web.handle_upload_dialog(...)
```

## 期望与实测

期望：点击真实上传控件后出现文件选择窗口，再分别调用 `handle_upload_dialog(..., 'ok')` 与 `handle_upload_dialog([], 'cancel')`，确证 DOM FileList。

实测：元素定位成功；点击抛 `ActionError`，trace=`uiautomation_provider_unavailable`。确认和取消两条用例均为 `stage=click_upload_input`、`api_called=False`。

沿异常 `result.raw` 内的嵌套 `raw` 向下读取，第三层保留原始 Provider 失败结果：

```text
missing_capabilities:
  capture_web_from_ref
  win32_observation_actions
  win32_observation_sessions
```

上层动作结果的 `log_lines` 为空，详细原因只在嵌套 `raw` 中，所以此前报告仅显示“元素自动化服务暂不可用”。测试侧现已补充阶段与能力缺失日志。

## 源码依据

以下位置只对应上述 worktree/commit 快照：

- `D:\code\desktop\runtime\services\uiautomation_provider.py`：`REQUIRED_PROVIDER_CAPABILITIES` 包含上述三项；`UiAutomationProvider._ensure_started()` 对 `system.ping` 返回的能力逐项检查，缺少时终止启动并返回 `uiautomation_provider_unavailable`。
- `D:\code\rust_uia\src\main.rs`：`ping()` 的 `capabilities` 不包含上述三项，与现场缺失清单一致。
- `D:\code\desktop\sdk\src\uiautoma\_core\exceptions.py`：`ActionError.result.raw` 保留底层响应；原因可从其中的嵌套 `raw` 获取。

## 结果、资源与交接

最新正式复测：4/6 PASS、0 FAIL、2 KNOWN，生命周期仍为 `SKIPPED`。退出码 0 表示脚本无 FAIL，不表示确认/取消功能已通过。

cleanup PASS：标签数 1→1、本次页面关闭、临时库和文件删除、无遗留本次对话框。

产品侧需对齐 Runtime 与 Provider 的能力合同，再复测真实点击、确认和取消；仅重新编译同一份缺少这些能力声明的 Provider 源码不能解决该校验失败。测试侧未修改产品源码、二进制或启动配置。

证据：[原始输出](../../web/evidence/artifacts/web_handle_upload_dialog_20261004_provider_diagnosis.txt)、[结构化报告](../../web/evidence/artifacts/web_handle_upload_dialog_20261004_provider_diagnosis.json)。
