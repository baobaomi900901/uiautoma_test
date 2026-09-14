# `uiautoma.web.clear_cookies()` 初次测试

## 用途与当前合同

清除符合 URL、域名和分区筛选条件的 Cookie，成功返回 `None`。

```python
clear_cookies(url="", mode="auto", *, domain=None, partition_key=None) -> None
```

源码依据：本测试环境 `uv run` 实际导入的 `sdk/src/uiautoma/web/__init__.py`，
以及 `chrome/engine/plugin_packages/browser_command_package.js` 的 `cookie_clear` 分支。
脚本启动时打印实际 SDK 文件位置，避免把其他工作副本当作本次运行版本。

`partition_key` 本轮按实现检查：`None` 表示非分区 Cookie；非空值必须是映射，
含 `top_level_site`，可含布尔 `has_cross_site_ancestor`。字符串形式虽出现在当前 docstring 中，
但当前归一化代码不接受字符串，本轮不将它作为成功用例。

## 测试对象与安全范围

打开用户靶场：[cookie-test](https://baobaomi900901.github.io/xpath/#/cookie-test)。
本 API 操作 Cookie 存储，不依赖网页元素库、动态 ID、Ant/原生表单提交或重置按钮。

为避免清理该站点的既有 Cookie，测试通过 SDK 在本次随机生成的 `.test` 域名准备数据，
不导航到这些域名，不依赖其网络服务。主域名、子域名和对照域名均由脚本生成；
开始时先确认它们没有既有 Cookie，再创建五个 Cookie，并逐一读回核验。

所有 `clear_cookies` 成功场景都传入明确的 URL 或随机域名筛选。
不调用不带筛选的全浏览器清理，不用 `clear_cookies` 执行兜底清理。
退出时仅逐项删除本次登记的 Cookie，并用 `get_cookie` 核验不存在，然后关闭本次标签页。
清理失败会报告异常，不吞掉异常后宣称清理完成。

## 场景

| 测试项 | 验收标准 |
| --- | --- |
| API 合同 | 四个参数的顺序、默认值、位置/关键字规则、返回注解正确 |
| 页面准备 | Chrome 打开靶场并返回 WebBrowser |
| Cookie 准备 | 根路径两项、其他路径、子域名、对照域名，共五项均能读回 |
| 按 URL 批量清理 | 根路径两项删除；其他路径、子域名及对照域名三项仍存在 |
| 重复清理空结果 | 返回 None；不影响三项对照数据 |
| URL 与域名不相交 | 不删除任何应保留的 Cookie |
| 域名及子域清理 | 省略 url，仅传主域名，清除其余路径及子域 Cookie，对照域名保留 |
| 显式非分区清理 | partition_key=None 配合对照 URL，删除最后一项，返回 None |
| 参数边界 | domain 位置传入、timeout 关键字、非法分区类型/缺少站点/祖先类型按指定异常拒绝 |
| 资源清理 | 本次 Cookie 均已删除并读回确认，测试标签页关闭 |

辅助 API：`create`、`set_cookie`、`get_cookie`、`get_cookies`、`remove_cookie`、`WebBrowser.close`。
准备或前置状态检查失败时停止后续删除场景，仍执行必要清理；检查异常不能视为 PASS。
Cookie 真实删除结果由读回检查判定，不能只因 `clear_cookies` 返回 None 就算通过。

## 运行

在 `sdk测试` 目录执行：

```powershell
uv run .\web\test_web_clear_cookies.py
```

只检查合同（不启动浏览器、不改 Cookie）：

```powershell
uv run .\web\test_web_clear_cookies.py --contract-only
```

离线脚本回归：

```powershell
uv run python -m unittest discover -s web -p test_clear_cookies_runner_regression.py -v
```

终端采用中文测试项、彩色状态、逐项耗时和完整失败原因，不生成额外运行日志。
请将完整输出反馈用于初次验收记录。

## 未覆盖与当前状态

- 未执行无筛选的全浏览器清理；仅静态检查其参数默认值。
- 未准备真实分区 Cookie（CHIPS），不宣称分区删除功能通过。
- 默认只做 Chrome 验收；Edge 可显式选择 `--mode edge`，须单独运行后记录。
- `.test` Cookie 写入若被环境拒绝，属于测试准备未通过，不能因此判定 clear_cookies 缺陷。

生命周期：`VERIFIED`。真实浏览器验收结果：10/10 通过，退出码 0。

本轮实测覆盖：API 合同、测试页准备、5 个随机 `.test` 域名 Cookie 准备、URL 批量清理、重复清理、URL/域名不相交保护、主域及子域清理、显式非分区清理、参数边界和资源清理。
