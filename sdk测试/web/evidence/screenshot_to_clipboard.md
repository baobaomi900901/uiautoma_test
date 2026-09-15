# `WebBrowser.screenshot_to_clipboard()` 初次测试

> 命名说明：本文件是**页面级** `WebBrowser.screenshot_to_clipboard()` 的证据。
> 与之同名的两个 API 是不同的公开接口，证据在其他文件：
> 元素级 `WebElement.screenshot_to_clipboard()`（尚无证据文件）、
> 页面级 `WebBrowser.screenshot()`（[`browser_screenshot.md`](browser_screenshot.md)）。

## 用途

截取页面图片到 Windows 剪贴板。

| 参数 | 默认 | 说明 |
|---|---|---|
| `full_size` | `True` | `True` 截取完整页面；`False` 仅截取当前视口 |
| `piece_height` | `0` | 整页截图每段高度（CSS 像素）；`0` 自动选择 |
| `height` | `0` | 整页截图最大高度；`0` 使用 25000；**视口截图忽略** |

返回 `None`。**没有目录与文件名参数**（与 `screenshot()` 的关键区别）。
参数校验全部在 SDK 侧完成（`InvalidParamsError`，实测 0.0s，不发起 RPC）。

## 真实验收结果

**VERIFIED：23/23 通过，退出码 0**（连续两次完整运行均 23/23）。

靶场：维护者的官方靶场 `https://baobaomi900901.github.io/xpath/#/form-controls`
被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

活推导的页面尺寸：**整页 2636×2018**；视口宽度 2651；视口高度现场读到 1214（另一次运行读到 1270）。

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`full_size`/`piece_height`/`height` 均为**仅限关键字**（默认 `True`/`0`/`0`），无目录/文件名参数，返回 `None` |
| 剪贴板独立通道可用性 | 通过，`ctypes` 可直接枚举/读写剪贴板 |
| 脚本自身写读自检 | 通过，哨兵文本写入后立即读回一致（保证收尾还原可信） |
| 页面准备 / 活推导 | 通过，现场读出整页与视口尺寸 |
| **哨兵守卫** | 通过，先放哨兵文本，调用后文本消失且出现 `CF_DIB` —— 证明内容确由本次调用改写，而非读到上一次残留 |
| **默认整页** | 通过，`CF_DIB` **2636×2018**、24bpp、**15958384 字节精确吻合**，与同参数文件截图差异 **0 字节**（15958344 字节） |
| **仅视口（`full_size=False`）** | 通过，`CF_DIB` 2636×1214，0 字节差异 |
| **`height=600` 限高** | 通过，`CF_DIB` 恰好 **2636×600**，0 字节差异 |
| **`piece_height=500` 分段拼接** | 通过，`CF_DIB` 拼回 **2636×2018**，0 字节差异（耗时 7.1s，默认仅 1.9s） |
| **视口截图忽略 `height`** | 通过，`full_size=False` 配 `height=600` 仍得 2636×1214，与"仅视口"完全一致 |
| `full_size=1`（int 非 bool） | 通过，`InvalidParamsError`（"full_size 必须为布尔值"） |
| `piece_height=-1` / `True` | 通过，`InvalidParamsError`（"piece_height 必须为非负整数"） |
| `height="x"` / `-1` | 通过，`InvalidParamsError`（"height 必须为非负整数"） |
| 传位置参数 / 未知关键字 | 通过，`TypeError`（"takes 1 positional argument"、"unexpected keyword argument 'folder'"） |
| **参数非法时不碰剪贴板** | 通过，仍为哨兵文本且无 `CF_DIB` —— 校验发生在写出之前 |
| 页面关闭复核 | 通过，`web.get_all()` 证实无残留 |
| **页面失效后调用** | 通过，`ActionError`（"网页对象已失效"，0.0s，SDK 侧拒绝），且剪贴板未被触碰 |
| 资源清理 | 通过，删除本次截图目录（含 10 个产物文件），并还原进入时的剪贴板内容（15958384 字节 `CF_DIB`） |

## 独立确证：不靠产品自述，直接问 Windows 要剪贴板

本 API 返回 `None`，「写进去了」无法由返回值判定。脚本用 `ctypes` 走**与产品无关的通道**
（`OpenClipboard`/`GetClipboardData`/`GlobalLock`/`GlobalSize`）读取剪贴板，做三层校验：

| 层 | 校验内容 | 实测结果 |
|---|---|---|
| 格式层 | 调用后必须出现 `CF_DIB`（格式 8） | 通过；同时可见 `CF_BITMAP`(2)、`CF_DIBV5`(17) |
| 结构层 | 解析 `BITMAPINFOHEADER`：宽/高/位深/压缩方式/朝向，并核对字节数 == `40 + stride × height` | 通过；24bpp、`BI_RGB`、自下而上，字节数与公式精确相等（无 `GlobalSize` 填充） |
| 像素层 | 独立解开 `CF_DIB` 像素，与同参数 `screenshot()` 的 PNG 文件截图逐像素比对 | 通过；五种参数组合**全部 0 字节差异** |

补充两点：
- `CF_BITMAP`/`CF_DIBV5` 是 Windows 在 `CF_DIB` 存在时**自动合成**的格式；产品源码
  `runtime/desktop/screen_capture.py` 的 `copy_dib_to_clipboard()` 只写 `CF_DIB` 一种。
- PNG 由脚本自带的纯标准库解码器解开（`zlib` + 逐行反过滤），不引入第三方依赖，
  与 SDK「零运行时依赖」的定位一致。

## 三角确证：把偶发渲染抖动与系统性偏差区分开

首轮实现要求「剪贴板像素与文件截图 0 字节差异」，**第二次运行时**
`piece_height=500` 用例报出 **3 / 15958344 字节**差异（1 个像素），首轮同用例为 0。

随后专项探针（同一参数连截两张文件图 A、B，再取剪贴板图 C，互相比对）在
`piece_height=500` 与默认整页两组上共 6 次比对**全部 0 像素差异**，
说明这是极低概率的单像素级渲染抖动，而不是稳定的取景/拼接偏差。

据此把用例改为**三角比对**，把抖动变成可测量的量而不是假失败：

1. 同参数连截两张文件图 A、B，测出**当时**的真实抖动 `jitter`；
2. 再取剪贴板图 C；
3. 要求 C 与 A、B 的差异都不超过 `jitter + 64 字节`（64 字节 ≈ 21 像素，
   占最小用例 2636×600 的 0.0014%，不足以掩盖系统性偏差）；
4. 三个数值（与 A 差、与 B 差、jitter）全部写进 JSON 报告。

本轮两次运行的 5 个像素用例均为 `差异 0 字节 / jitter 0 字节`。
若将来某次运行报出差异，报告会同时给出 jitter，可直接判断是环境抖动还是产品偏差。

## 实测行为记录

1. **只写 `CF_DIB`，且先 `EmptyClipboard`**：剪贴板原有内容（包括文本）会被清掉，
   `CF_UNICODETEXT` 消失。这与「截图到剪贴板」的常规语义一致（同 PrtScn），
   但公开文档未声明这一副作用，用户侧需知悉。
2. **`height` 是硬裁剪**：`height=600` 得到恰好 600 高，不是"最多 600"或等比缩放 —— 与
   文件版 `screenshot()` 的行为一致（两者共用同一段参数与截图实现）。
3. **视口截图确实忽略 `height`**：文档声明已实测确认（`full_size=False` + `height=600` 与
   仅视口结果完全相同）。
4. **`piece_height` 是分段拼接**：结果与整页一致，但耗时约 3.7 倍（7.1s vs 1.9s），
   说明确实走了分段采集 + 拼接路径，而不是忽略该参数。
5. **页面失效后立即在 SDK 侧拒绝**：`ActionError: 网页对象已失效`（0.0s），
   不发起 RPC，也不触碰剪贴板。
6. **视口高度随窗口变化**：两次运行分别读到 `innerHeight` 1214 与 1270，
   而 `full_size=False` 产出均为 1214。脚本所有尺寸期望都是活推导，结论不依赖固定数字。
7. **剪贴板会被其他进程短暂占用**：探针早期曾出现 `OpenClipboard` 直接失败，
   脚本因此对 `OpenClipboard` 做重试（20 × 0.25s），仍失败则记 `BLOCKED` 而不是 `FAIL`
   —— 环境占用不构成产品结论。

## 复测

脚本：[test_web_browser_screenshot_to_clipboard.py](../test_web_browser_screenshot_to_clipboard.py)
原始产物：[artifacts/screenshot_to_clipboard_20260915.txt](artifacts/screenshot_to_clipboard_20260915.txt)

```powershell
uv run .\web\test_web_browser_screenshot_to_clipboard.py
uv run .\web\test_web_browser_screenshot_to_clipboard.py --json
uv run .\web\test_web_browser_screenshot_to_clipboard.py --contract-only
```

副作用与收尾：脚本会快照进入时的剪贴板文本/图像，结束时还原；若进入时剪贴板为空，
则保留最后一次验收截图（可直接 `Ctrl+V` 目视确认），并在报告中明确写出。
产物写入 `sdk测试/.pytest_tmp/<run_id>/`，结束时整目录删除（本次 10 个产物文件）。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **剪贴板历史/云同步/剪贴板监视器开启时的行为**：本次环境未开启。
- **剪贴板被其他进程长期占用**导致写出失败的真实路径：只做了读取侧重试，未构造写出失败。
- **超长页面（>25000 CSS 像素）与 `height` 上限行为**：未构造。
- **页面缩放（zoom）与高 DPI 屏幕下的尺寸换算**：单一缩放环境。
- **与剪贴板中其他格式共存**（如同时保留文本、HTML、文件列表）：产品先 `EmptyClipboard`，
  本次只验证了原有文本被清掉，未验证保留策略。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- **元素级** `WebElement.screenshot_to_clipboard()`：同族另一 API，未测。
