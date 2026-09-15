# `uiautoma.web.WebElement.screenshot()` 验证证据

```yaml
api: "uiautoma.web.WebElement.screenshot"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_screenshot_explicit_filename_file_ok: "PASS"
  chrome_screenshot_auto_filename_file_ok: "PASS"
  chrome_screenshot_pixel_framing_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 0
  note: "脚本按文件存在记 PASS；人工像素验收取景偏移，阻塞 VERIFIED"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.screenshot 的最小 SDK→web.screenshot.element→CDP 截图链"
source_review:
  status: "reviewed_with_known_defect"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.screenshot"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "chrome/engine/plugin_packages/browser_command_package.js"
      symbols: ["elementScreenshot"]
      note: "DOM.getBoxModel border → Page.captureScreenshot clip 未做 CSS→DIP 换算"
  verified_contract:
    signature: "screenshot(folder_path: str, *, filename: str | None = None) -> str"
    parameter_order: ["self", "folder_path", "filename"]
    defaults:
      filename: null
    filename_kind: "KEYWORD_ONLY"
    return_annotation: "str"
    note: "用户文案曾写返回无；公开合同返回保存路径"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_screenshot.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "f5c177d15512ff8b21110931200655b8be779400"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "58086849245009d8662dddc5b6a068d019ed74a3"
  target_element_name: "按钮_九宫格"
  target_characteristics: "//div[@id='position-grid-panel']"
  snapshot_path: "tests/SDK/web/web测试元素库/snapshot/localhost_7199_div_20260727_160503_061_20260727_160503_061.json"
  snapshot_fingerprint: "56aedeadb765c431c6c647f51eaee75766cb6f75"
  reference_snapshot_image: "tests/SDK/web/web测试元素库/assets/localhost_7199_div_20260727_160503_061_20260727_160503_061.png"
  reference_snapshot_image_note: "414×414 完整九宫格；采集路径非本 API CDP clip"
source_commit_at_doc_time: "152ab053c7a6c733df8adfc3259c9294552a180e"
known_issue: "https://github.com/uiautoma/desktop/issues/20"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_screenshot.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_screenshot.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_screenshot.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API：对 `按钮_九宫格` 直接调用 `WebElement.screenshot(...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本；**桌面截图文件按验收要求保留、不删除**。

## 最小实现链

```text
uiautoma.web.WebElement.screenshot
  -> RawWebElement.screenshot
  -> web.screenshot.element
  -> ActionService.web_screenshot_element
  -> browser_command screenshot_element
  -> elementScreenshot (DOM.getBoxModel + Page.captureScreenshot clip)
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `folder_path`/`filename` 种类与 `str` 返回注解 |
| 靶场/Runtime/元素库/桌面预检 | `PASS` | keys-click-test 与库项、桌面目录可用 |
| 页面与库连接 | `PASS` | 绑定 `按钮_九宫格` |
| 显式 filename → 桌面 | `PASS` | 文件存在、非空、位于桌面（约 4.6KB / 303×303） |
| 自动 filename → 桌面 | `PASS` | 同上 |
| 像素取景对准元素 | `FAIL` | 人工对照：偏左上，仅左列；见 Issue #20 |
| 精确清理 | `PASS` | 库连接/页面/临时库清理；截图文件 `retained=true` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 脚本总状态：`PASS`（仅文件层断言）
- 退出码：`0`
- 生命周期提示：`READY_FOR_LIVE`（像素取景阻塞 `VERIFIED`）
- 靶场：`http://localhost:7199/keys-click-test`
- 元素：`按钮_九宫格`
- 示例路径：
  - `%USERPROFILE%\Desktop\uiautoma_web_screenshot_<uuid>.png`
  - `%USERPROFILE%\Desktop\e_bG9jYWxob3N0OjcxOTk_0_<ts>.png`
- 清理结果：`PASS`；截图文件保留
- 产品源码修改：无（本轮仅记录缺口与文档）

## 明确排除

- Edge、CEF、Auto。
- `screenshot_to_clipboard()`。
- 非法目录 / 无写权限负例。
- Ant/组件库控件截图。
- 自动化像素 diff（当前依赖人工对照参考 SnapshotImage）。

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/20

## 补充实测（2026-09-15，dpr=1 环境）

元素级 `WebElement.screenshot_to_clipboard()` 验收时，顺带用**独立于产品自述**的方式
重新验证了本 API 的取景：主框架元素 `#form-controls-ant-submit` 活矩形
`63.84375×32` CSS、`devicePixelRatio = 1` → 元素截图 **64×32**（= 四舍五入后的活矩形尺寸）；
把整页截图按活矩形裁切后做 **±6 像素偏移扫描**，最小区块差异出现在偏移 **(0, 0)**，
即**取景精确对准、无偏移**。

也就是说：本文件记录的像素取景偏移缺陷（Issue #20）在 **dpr = 1 的当前基线（HEAD `dbe9e015`）上未复现**。

**但本文件的生命周期状态维持 `READY_FOR_LIVE` 不变**：原缺陷证据来自 `dpr ≠ 1` /
页面缩放环境（414×414 的元素截成 303×303，比例约 0.73），本次环境未覆盖该触发条件，
Issue #20 是否可关闭需维护者用高 DPI / 缩放环境复核。

证据：[element_screenshot_to_clipboard.md](element_screenshot_to_clipboard.md)。
