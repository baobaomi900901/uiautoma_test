# `WebElement.screenshot_to_clipboard()` 初次测试

> 命名说明：本文件是**元素级** `WebElement.screenshot_to_clipboard()` 的证据。
> 与之同名的另外两个 API 证据在其他文件：页面级
> `WebBrowser.screenshot_to_clipboard()`（[`screenshot_to_clipboard.md`](screenshot_to_clipboard.md)）、
> 元素级文件版 `WebElement.screenshot()`（[`screenshot.md`](screenshot.md)，状态 `READY_FOR_LIVE`）。

## 用途

截取**单个元素**的图片到 Windows 剪贴板。

| 参数 | 说明 |
|---|---|
| （无） | **没有任何参数**，也没有目录/文件名参数，与文件版 `WebElement.screenshot(folder_path, ...)` 的关键区别 |

返回 `None`。元素失效时在 SDK 侧立即抛 `ActionError`（实测 0.0s~0.02s，不发起 RPC）。

## 真实验收结果

**VERIFIED：18/18 通过，退出码 0**（连续两次完整运行均 18/18）。

靶场：维护者的官方靶场（测试侧不自建页面）
被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）
元素库：`D:\code\元素库\260902_web元素`（Schema2，web 元素 70 个；脚本复制副本后打开，不碰原件）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，公开签名只有 `self`（无参数），返回注解 `None` |
| 剪贴板独立通道 / 自身写读自检 | 通过，`ctypes` 通道可信后才继续 |
| 元素库准备 | 通过，`web_count=70` 与列举一致 |
| 库元素绑定 | 通过，`web靶场_表单测试_ant_输入框`（标签 `INPUT`，活矩形 1196×32） |
| **哨兵守卫** | 通过，先放哨兵文本，调用后文本消失且出现 `CF_DIB` —— 排除读到上一次残留的假通过 |
| **库元素（iframe 内）写入剪贴板** | 通过，`CF_DIB` **1196×32**、24bpp、**114856 字节精确吻合**，与元素文件截图差异 **0 字节**（114816 字节）；尺寸与 `get_bounding()` 完全一致 |
| **连续两次调用一致** | 通过，两次产出完全相同的 `CF_DIB`（114856 字节） |
| **第二个元素尺寸跟随** | 通过，`web靶场_表单测试_ant_数字输入框` → 1194×30，与其活矩形一致且与第一个元素不同 |
| **取景独立验证（Issue #20 判据）** | 通过，见下节；主框架元素活矩形 `63.84375×32` CSS × dpr 1 → 元素截图与剪贴板均为 **64×32**，偏移扫描最小值在 **(0, 0)** |
| 主框架元素剪贴板 vs 文件截图 | 通过，`CF_DIB` 64×32、6184 字节精确吻合、**0 字节差异**（6144 字节） |
| **导航后旧元素句柄** | 通过，`ActionError`（"未找到指定ID的元素"，0.018s） |
| 页面关闭复核 | 通过，`web.get_all()` 证实无残留 |
| **页面关闭后旧元素句柄** | 通过，`ActionError`（"网页对象已失效"，0.001s） |
| Package 关闭 | 通过 |
| 资源清理 | 通过，删除临时目录（含 233 个文件，含元素库副本）；还原进入时的剪贴板图像（114856 字节 `CF_DIB`） |

## 独立确证：四层校验，不靠产品自述

本 API 返回 `None`，「写进去了」无法由返回值判定。脚本用 `ctypes` 走**与产品无关的通道**
（`OpenClipboard`/`GetClipboardData`/`GlobalLock`/`GlobalSize`）读剪贴板：

| 层 | 校验内容 | 实测结果 |
|---|---|---|
| 格式层 | 调用后必须出现 `CF_DIB`（格式 8） | 通过；同时可见 `CF_BITMAP`(2)、`CF_DIBV5`(17)（Windows 自动合成） |
| 结构层 | `BITMAPINFOHEADER`：宽/高/位深/压缩方式/朝向，字节数 == `40 + stride × height` | 通过；24bpp、`BI_RGB`、自下而上、字节数精确相等 |
| 像素层 | 独立解 `CF_DIB` 像素，与元素文件截图 PNG 逐像素比对（纯标准库解码器） | 通过；两个元素、两种尺寸均 **0 字节差异** |
| 取景层 | 活推导元素页面矩形 → 整页截图裁切 → 与元素截图做偏移扫描 | 通过；最小区块差异在偏移 **(0, 0)** |

像素比对沿用页面级同族脚本的**三角比对**：同参数连截 A、B 两张文件图测出当时抖动，
再与剪贴板图 C 比，许可差异 = `实测抖动 + 64 字节`。本轮 4 次比对全部 `差异 0 / 抖动 0`。

## 取景验证：历史缺陷 Issue #20 在当前基线**未复现**（dpr=1 环境）

`WebElement.screenshot()` 的历史证据（[`screenshot.md`](screenshot.md)，2026-08-09）记录像素取景
缺陷（"偏左上，仅左列"，414×414 的元素截成 303×303），并跟踪
[Issue #20](https://github.com/uiautoma/desktop/issues/20)。

本次用**独立于产品自述**的方式重新验证取景：

1. 在主框架页 `#/form-controls` 上取一个可控元素（`#form-controls-ant-submit`）；
2. 用 `execute_javascript()` 读出它的 `getBoundingClientRect()` 与 `devicePixelRatio`：
   `63.84375×32` CSS、dpr = 1、`scrollX/Y = 0`、页面 2636×2018；
3. 期望尺寸 = `round(63.84375 × 1) × round(32 × 1)` = **64×32**；
4. 元素截图与剪贴板图**都**是 64×32；
5. 把**整页截图**按活矩形裁切（`x=49, y=1823`），与元素截图做 **±6 像素偏移扫描**，
   最小区块差异出现在偏移 **(0, 0)** —— 位置精确对准，没有任何偏移。

结论：**在 dpr=1 的本次环境下，元素级截图的尺寸与位置都与页面实际渲染精确一致，
Issue #20 描述的取景偏移未复现**。但这不等于该缺陷已被修复：

- 原缺陷证据来自 `dpr ≠ 1`（元素 414×414 却截成 303×303，比例约 0.73）或页面缩放环境，
  本次环境 dpr = 1，**没有覆盖缺陷的原始触发条件**；
- 因此本次只能记录"当前环境下未复现"，Issue #20 的关闭与否应由维护者用高 DPI/缩放环境复核决定。

## 实测行为记录

1. **元素截图与剪贴板共用同一段实现**：`ActionService._web_screenshot()` 对元素与页面、
   文件与剪贴板只切换命令名与输出方式（`save_image` / `copy_image`），
   所以剪贴板图与同元素文件截图**必然同源**；本次实测两者像素 0 差异，与该源码结构一致。
2. **只写 `CF_DIB` 且先 `EmptyClipboard`**：剪贴板原有内容（含文本）会被清掉，与原页面级 API 行为一致。
3. **尺寸随元素变化且与 `get_bounding()` 一致**：1196×32 与 1194×30 两个元素各自吻合。
4. **元素失效立即在 SDK 侧拒绝**：导航到别的路由后 → `ActionError：未找到指定ID的元素`（0.018s）；
   页面关闭后 → `ActionError：网页对象已失效`（0.001s）。
5. **附带核实的 `execute_javascript()` 调用约定**（本轮排查时实测）：
   脚本形参是 `function (element, args)` —— **第一个形参恒为 `element` 且为 `null`，
   输入参数在第二个形参**（`argument=` 传字符串/数字/列表/字典都能收到；不传时 `args === undefined`）。
   写成单形参 `function (a)` 会拿到 `element`（即 `null`），看起来像"参数没送达"，实际是形参位置错误。
6. **靶场 `#/form-controls` 的动态 ID**：`FormControlsPage.tsx` 的 `readDynamicIdsPreference()`
   在 `localStorage['form-controls-dynamic-ids'] !== 'false'` 时**默认开启动态 ID**，
   此时元素 id 变成 `form-controls-ant-submit_<随机>`，固定选择器会失效。
   本次环境该键已是 `'false'`（静态 id），脚本据此选用 `#form-controls-ant-submit`；
   若他人运行时该键为默认值，取景用例会因选择器不匹配而报错——这是靶场设计使然，不是产品缺陷。

## 复测

脚本：[test_web_element_screenshot_to_clipboard.py](../test_web_element_screenshot_to_clipboard.py)
原始产物：[artifacts/element_screenshot_to_clipboard_20260915.txt](artifacts/element_screenshot_to_clipboard_20260915.txt)

```powershell
uv run .\web\test_web_element_screenshot_to_clipboard.py
uv run .\web\test_web_element_screenshot_to_clipboard.py --json
uv run .\web\test_web_element_screenshot_to_clipboard.py --contract-only
```

副作用与收尾：脚本快照进入时的剪贴板文本/图像并在结束时还原；进入时为空则保留最后一次验收截图
（可直接 `Ctrl+V` 目视确认）。元素库副本与截图产物写入 `sdk测试/.pytest_tmp/<run_id>/`，结束时整目录删除。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **高 DPI / 页面缩放（dpr ≠ 1）环境**：本次 dpr = 1，**没有覆盖 Issue #20 的原始触发条件**。
- **iframe 内元素的取景独立验证**：库元素在 iframe 内，其跨 frame 页面坐标未做活推导，
  取景只按 `get_bounding()` 尺寸核对，未做整页裁切比对（主框架元素已做）。
- **超大元素 / 超出视口的元素**：仅覆盖 64×32 与 1196×32 两种量级。
- **剪贴板历史/云同步/监视器开启时的行为**：本次环境未开启。
- **剪贴板被其他进程长期占用**导致写出失败：只做了读取侧重试。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- **元素截图写入剪贴板的耗时上限**：内部 `timeout_ms` 固定 60s，未构造超时场景。
