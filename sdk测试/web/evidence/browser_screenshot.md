# `WebBrowser.screenshot()` 初次测试

> 命名说明：本文件是**页面级** `WebBrowser.screenshot()` 的证据；元素级
> `WebElement.screenshot()` 的证据在 [`screenshot.md`](screenshot.md)（状态 `READY_FOR_LIVE`，
> 含已知像素取景缺陷）。两者是不同的公开 API。

## 用途

截取页面图片到文件。

| 参数 | 默认 | 说明 |
|---|---|---|
| `folder_path` | 必填 | 保存目录（位置或关键字） |
| `file_name` | `None` | 文件名；`None` 时自动生成；**扩展名决定图片格式** |
| `full_size` | `True` | `True` 截取完整页面；`False` 仅截取当前视口 |
| `piece_height` | `0` | 整页截图每段高度（CSS 像素）；`0` 自动选择 |
| `height` | `0` | 整页截图最大高度；`0` 使用 25000；视口截图忽略 |

返回 `None`。参数校验全部在 SDK 侧完成（`InvalidParamsError`，实测 0.0s，不发起 RPC）。

## 真实验收结果

**VERIFIED：21/21 通过，退出码 0。**

靶场：维护者的官方靶场 `https://baobaomi900901.github.io/xpath/#/form-controls`
被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

活推导的页面尺寸：**整页 2636×2018**，**视口 2651×1270**。

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`folder_path` 必填；其余四个仅限关键字（默认 `None`/`True`/`0`/`0`）；返回 `None` |
| 页面准备 / 活推导 | 通过，现场读出整页与视口尺寸 |
| **默认整页截图** | 通过，产出 `screenshot_<32hex>.png`，**2636×2018**（= `scrollWidth`×`scrollHeight`） |
| **显式文件名决定格式** | 通过，`file_name="acceptance-shot.jpg"` 产出的确实是 **JPEG**（`FFD8FF` 魔数），尺寸同为 2636×2018 |
| **仅视口（`full_size=False`）** | 通过，产出 2636×1214（小于整页高 2018，且不超过视口高 1270） |
| **`height=600` 限高** | 通过，精确裁到 **2636×600** |
| **`piece_height=500` 分段拼接** | 通过，拼回整页 **2636×2018**（耗时 7.3s，默认仅 2.1s） |
| 多级目录自动创建 | 通过，`deep/nested/folder` 被自动创建并写入文件 |
| 空 / 全空白 / 非字符串目录 | 通过，`InvalidParamsError`（"请提供截图保存目录"） |
| `file_name` 含 `/` / `..` / 控制符 | 通过，`InvalidParamsError`（"截图文件名不能包含目录或非法字符"） |
| `full_size=1`（int 非 bool） | 通过，`InvalidParamsError`（"full_size 必须为布尔值"） |
| `piece_height=-1` / `True` | 通过，`InvalidParamsError`（"piece_height 必须为非负整数"） |
| `height="x"` | 通过，`InvalidParamsError`（"height 必须为非负整数"） |
| 页面关闭复核 | 通过，`web.get_all()` 证实无残留 |
| 资源清理 | 通过，删除本次截图目录（含 6 个产物文件） |

## 独立确证：直接解析产出的图片字节

本 API 返回 `None`，**不能靠返回值判断截图是否成功**，因此脚本直接读文件字节校验：

| 校验项 | 做法 |
|---|---|
| 格式 | PNG 校验 8 字节魔数 `89504E47…`；JPEG 校验 `FFD8FF` |
| 尺寸 | PNG 读 IHDR 的宽高；JPEG 扫描 SOF 段读宽高 |

上表所有尺寸结论均由该方式得出（不依赖第三方图像库，也不依赖产品自述）。

## 三点值得记录的实测行为

1. **扩展名决定格式**：`file_name="x.jpg"` 产出真正的 JPEG，而不是改名的 PNG —— 与「自动命名时产出 PNG」形成对比。
2. **`height` 是硬裁剪**：`height=600` 得到恰好 600 高，不是"最多 600"或等比缩放。
3. **`piece_height` 是分段拼接**：结果与整页高度一致，但耗时约为默认整页截图的 3.5 倍（7.3s vs 2.1s），
   说明确实走了分段采集 + 拼接路径，而不是忽略该参数。

## 复测

脚本：[test_web_browser_screenshot.py](../test_web_browser_screenshot.py)
原始产物：[artifacts/screenshot_20260915.txt](artifacts/screenshot_20260915.txt)

```powershell
uv run .\web\test_web_browser_screenshot.py
uv run .\web\test_web_browser_screenshot.py --json
uv run .\web\test_web_browser_screenshot.py --contract-only
```

产物写入 `sdk测试/.pytest_tmp/<run_id>/`，结束时整目录删除（本次清理了 6 个产物文件）。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **超长页面（>25000 CSS 像素）与 `height` 上限行为**：未构造该场景。
- **同名文件重复截图的覆盖/报错行为**：未验证。
- **页面缩放（zoom）与高 DPI 屏幕下的尺寸换算**：本次为单一缩放比例环境。
- **局部失败/超时**（内部 `timeout_ms` 固定 60s）：未构造慢加载到超时的场景。
- 返回路径与真实文件路径一致性核对（本 API 不返回路径）。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- `screenshot_to_clipboard()`：同族另一 API，属下一个候选。
