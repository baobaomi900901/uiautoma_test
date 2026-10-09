# WebBrowser.set_cookie() 写入成功后误报失败

关联提测总单：#51（第九批 Cookie 组）。未查到同一缺陷，按总单约定单独建缺陷并关联。

## 复现条件与调用

Windows / Chrome 154.0.8037.95 / 当前 dev SDK。
页面为公开 Cookie 靶场：<https://baobaomi900901.github.io/xpath/#/cookie-test>，实际 URL Path 为 `/xpath/`。

对该页面的 WebBrowser 对象调用（name 每次替换为随机唯一名称）：

```python
page.set_cookie(
    name="unique_cookie_path_probe",
    value="other-path",
    path="/xpath/stop-load-test/",
    sessionCookie=True,
)
```

在匹配该 Path 的另一真实同源文档中，用原生 Cookie Store 独立观察写入值；每轮只清理本次随机 Cookie。

## 期望与实际

- 期望：合法的显式 Path 写入成功，返回 `None`；当前页面不可见，匹配 Path 的页面可读取正确值。
- 实际：抛 `ActionError: 浏览器操作失败，请重试`，`trace_info="cookie_set_failed"`，但原生观察确认该 Cookie **已经写入**，值和 Path 正确。
- 独立正式验收连续三轮均为 **20/21 PASS + 1 FAIL**；唯一失败为此场景，三轮清理均 PASS。
- 影响：调用方收到失败异常时已经产生写入副作用，可能错误重试或误判状态。尚未修复，验收状态保持 `READY_FOR_LIVE`。

## 排除靶场与测试脚本因素

使用同一 Chrome 可执行文件、独立配置和无窗口模式，直接调用原生 `chrome.cookies.set`，不加载 UIAutoma Engine 或靶场代码。三轮、三个 URL/Path 情形、callback/Promise 两种调用，共 18 项对照：

| URL 与显式 Path | 原生返回 | 实际存储 |
|---|---|---|
| 匹配 | Cookie 对象 | 写入成功 |
| 不匹配 | undefined；callback lastError 为空；Promise 不拒绝 | 写入成功，独立 CDP 确认 |

随后在 dev SDK 中，三对调用保持同一 name/value/path/sessionCookie，仅改变 WebBrowser 绑定 URL：不匹配时均抛上述异常，匹配时均返回 `None`。其中一对反转调用顺序，结果相同。所有测试均后台进行，精确清理本次 Cookie 并关闭自有页面。

Chrome [官方 cookies.set 合同](https://developer.chrome.com/docs/extensions/reference/api/cookies#method-set) 允许返回 `Cookie | undefined`。产品对成功的空返回值做了失败判定，是此次误报的原因。

## 修复与验收建议

- 以原生 Promise 的成功/拒绝结果判断写入，避免仅因返回 undefined 就报 cookie_set_failed；保留真正的写入错误。
- 覆盖 URL/Path 匹配与不匹配、新建与同键覆盖；使用原生存储独立确认写入。
- 连续三轮独立正式验收全部通过，且每轮精确 Path 清理 PASS 后，再更新为 VERIFIED。

完整测试证据、原始产物与源码快照保存在测试侧归档中，本报告未披露本地路径、原始产物或具体源码定位。
