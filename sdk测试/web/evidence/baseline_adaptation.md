# 测试侧基线适配记录：`dbe9e015` → `main@c101caa9`

## 背景

本工作区此前的全部实测证据都绑在 worktree `codex/stage6-sdk-runtime` 的 `dbe9e015` 上。
产品侧 `main` 已合并该分支（PR #62，合并提交 `ba6edab9`）并继续前进到 `c101caa9`。
按产品负责人决定（**以 `main@c101caa9` 为新基线，先适配再继续**），本轮把外部 `sdk测试`
工作区的 Web API 验收套件适配到新基线，并如实登记适配过程中发现的每一处漂移。

- 新基线：`D:\code\desktop`（主检出）`main` @ `c101caa9 🐳 chore: 完成 Chrome 插件商店提交准备`
- 旧基线：`dbe9e015`（worktree `codex/stage6-sdk-runtime`）
- 环境：`D:\code\.tools\build-test.py` + `build-test.config.json`（`desktop.worktree_path = D:\code\desktop`、
  `active_provider_patch.baseline_head = c101caa9…`）；`sdk测试` 的 venv 以可编辑方式指向 `D:\code\desktop\sdk\src`。

## 一、两个基线之间的公开面差异（`git log dbe9e015..main`，10 个提交）

只有两个提交触及 `sdk/src/uiautoma/web/`：

| 提交 | 对 Web 公开面的影响 | 是否影响本工作区脚本 |
|---|---|---|
| `44c8e91f` 🦄 refactor: 收敛 SDK 独有公开接口与内部状态 | 移除 `WebBrowser.id`；`WebElement` 移除 `element_id`、`raw`；`handle_upload_dialog` 的公开参数 `file_paths` → `file_names` | **是**（见二、三） |
| `48f5bafb` 🐞 fix: 完成 6D-4 鼠标模拟与拖动位移修正 | `WebBrowser.scroll_to` 的 `behavior` 默认值 `instant` → `smooth`（文档同步改为 smooth） | **是** |

其余提交（`6a692944`、`eacfb246`、`b1c16d43`、`61b0aac2`、`6c4329df`、`7e10fac7`、`750b6258`、`c101caa9`、`ba6edab9`）
不触碰 `sdk/src/uiautoma/web/`。

当前基线的公开身份面（`sdk/src/uiautoma/web/browser.py`）：

```python
@dataclass
class WebBrowser:
    _page_ref: dict[str, str] = field(repr=False)   # 私有；__str__ 里仍会打印其中的 id
    url: str | None = None                          # 数据字段，非 property
    title: str | None = None
    mode: str = "auto"
    _client: Any | None = field(default=None, repr=False)
```

即：**`id` 属性已不存在，公开面上没有任何「标签身份」访问器**；
`WebElement.id` 仍然存在（`element.py:54`），所以元素级脚本不受影响。

## 二、适配总账

| 类别 | 文件数 | 处置 |
|---|---|---|
| 机械迁移 `page_id = page.id` → `page_key(page)` | 21 | 迁移脚本 `.pytest_tmp/migrate_page_identity.py`（正则 + ast 校验，不改写未命中文件） |
| 语义改写（`page.id` 不在 `page_id = ` 模式内） | 6 | 补丁脚本 `.pytest_tmp/patch_baseline_semantics.py` |
| 套件内其余 `page.id` 引用 | 9 | 补丁脚本 `.pytest_tmp/patch_suite_identity.py` |
| 契约漂移修正 | 3 | 补丁脚本 `.pytest_tmp/patch_contract_drift.py` |
| 因成员移除而重写的脚本 | 1 | `test_web_browser_id.py` 改为「成员收敛 + 替代方式」契约 |
| 历史漂移（与本次基线切换无关） | 2 | `test_web_get_cookies.py`、`test_web_delete_cookie.py`，随本轮一并修正 |

### 2.1 「同一个页面对象」的替代判据（必须区分两种情况）

`WebBrowser.id` 是原先断言「导航/刷新后仍是同一个标签页」的唯一手段，移除后没有等价公开替代物。
适配时按「组合键（url|title）在操作前后是否必然变化」分两类：

| 类型 | 适用 API | 替代判据 | 强度 |
|---|---|---|---|
| 键不变型 | `reload()`、`reload(load_timeout=0)` | `page_key(page) == page_id`（url、title 都不变，等价断言） | 等价 |
| 键变化型 | `navigate()`、`go_forward()`、`go_back()` | `page_alive(page)`（`get_url`/`get_title`/`execute_javascript` 三次真实调用均成功）+ `tab_count()` 前后一致 | **弱于原断言**：只能证明「对象仍可驱动该标签且未新开标签」，不能证明「就是同一个标签」 |

`_web_page_identity.py` 因此补齐了 `tab_keys()`、`tab_count()`、`page_alive()`，
并在模块 docstring 里写明这一强度差异。

### 2.2 判据错误的自查与修正（如实记录）

第一轮实测 `go_forward` 10/13、`navigate` 13/14 失败。失败明细显示
`return=None`、URL 正确、`alive=对象仍可用`、`tabs_added=0` —— 说明失败不在被测产品，
而在**我新写的判据**：我最初用「标签组合键列表相等」判断未新开标签，
但同标签导航后该标签自身的组合键必然改变，键列表恒不相等，断言恒为假。

修正：改用 `tab_count()`（标签**数量**不变）。修正后 `go_forward` 13/13、`navigate` 14/14。
教训已写入实测手册的抖动/判据章节：**组合键只能标识「一个 URL+标题」，不能标识「一个标签」**。

## 三、逐脚本漂移处置明细

| 脚本 | 漂移原因 | 处置 |
|---|---|---|
| `test_web_browser_id.py` | `44c8e91f` 移除 `WebBrowser.id` | 重写为收敛契约（`id` 不存在、公开字段仍为 url/title/mode、组合键稳定、同 URL 双标签不可区分的能力缺口） |
| `test_web_browser_reload.py` | 同上 | 键不变型判据；`id_changed` 表述改为 `key_changed` |
| `test_web_browser_is_load_completed.py` | 同上 | 刷新分支用键、导航分支用 `page_alive` |
| `test_web_browser_wait_load_completed.py` | 同上 | 导航分支用 `page_alive` |
| `test_web_browser_go_forward.py` | 同上 | 键变化型判据（`page_alive` + `tab_count`） |
| `test_web_browser_navigate.py` | 同上 | 键变化型判据 |
| `test_web_browser_go_back.py` | 同上 | 键变化型判据（缺陷 #58 复现脚本） |
| `test_web_browser_activate.py` / `activate_tab.py` / `get_html_baidu.py` / `test_web_get_active.py` | 同上 | `active.id == page.id` → `page_key(active) == page_key(page)`（同一标签，两值都取当前读数，等价） |
| `test_web_get_all.py` | 同上 | 列表包含性判定改组合键 |
| `test_web_get.py` / `test_web_create.py` | 同上 | 报告字段 `page_id` → `page_key` |
| `test_web_browser_execute_javascript.py` | 同上 | 临时标题不再借 `page_id[:8]`，改用 `time.time_ns()` |
| `test_web_browser_stop_load.py` | 同上 | 标签差分由 id 集合改为组合键集合；新标签识别额外限定 `slow-load-30s` 地址，避免其它标签标题抖动误判 |
| `test_web_browser_scroll_to.py` | `48f5bafb` 默认值 `instant` → `smooth` | 契约期望值与用例描述同步为 `smooth` |
| `test_web_handle_upload_dialog_current.py` | `44c8e91f` 参数改名 | 公开签名期望 `file_paths` → `file_names`（RPC 层仍是 `file_paths`，脚本未改 RPC 断言） |
| `test_web_get_cookies.py` | **历史漂移**：`dbe9e015` 起 `get_cookies` 已是 url-first，脚本写作时用的是更早的 `mode`-first 形态 | 契约改为 `(url, mode, *, name, domain, path, partition_key, secure, session)`；调用点改 url-first；「位置传参被拒」用例改为第三个及以后参数，并新增「url/mode 可位置传入」正例 |
| `test_web_delete_cookie.py` | **历史漂移**：`delete_cookie` 在 `dbe9e015` 中也不存在（只有 `remove_cookie`） | 重写为收敛契约：旧名不存在 + 替代函数 `remove_cookie(url, name, mode='auto', *, partition_key=None)` 已公开导出 |
| `test_web_set_cookie_get_cookie.py` | **历史漂移**：期望 `mode` 默认值 `cef`，现为 `auto` | 默认值期望改为 `auto` |

## 四、验证结果（新基线 `c101caa9`）

### 4.1 契约面：套件全量 `--contract-only`

非历史模板的 61 个脚本全部退出码 0（`61/61`）。明细见 `.pytest_tmp/contract_smoke.json`，
运行器 `.pytest_tmp/run_contract_smoke.py`（对要求 `--mode` 的脚本自动补 `--mode chrome`）。

适配过程中该冒烟先暴露 6 个失败项，全部定位并处置后归零：

| 失败脚本 | 根因 | 处置 |
|---|---|---|
| `test_web_browser_scroll_to.py` | `48f5bafb` 默认值改动 | 期望值改 `smooth` |
| `test_web_handle_upload_dialog_current.py` | `44c8e91f` 参数改名（`KeyError: 'file_paths'`） | 期望值改 `file_names` |
| `test_web_get_cookies.py` | 历史漂移（url-first） | 契约与调用点修正 |
| `test_web_delete_cookie.py` | 历史漂移（函数已不存在） | 重写为收敛契约 |
| `test_web_set_cookie_get_cookie.py` | 历史漂移（`mode` 默认 `cef` → `auto`） | 期望值改 `auto` |
| `test_web_close_all.py` | 非产品问题：脚本要求 `--mode` | 运行器补参数 |

### 4.2 行为面：受影响最重的脚本真机复跑

| 脚本 | 结果 | 复跑日期 |
|---|---|---|
| `test_web_browser_reload.py` | 12/12 · 退出码 0 | 2026-09-18 |
| `test_web_browser_go_forward.py` | 13/13 · 退出码 0（判据修正后） | 2026-09-18 |
| `test_web_browser_navigate.py` | 14/14 · 退出码 0（判据修正后） | 2026-09-18 |
| `test_web_browser_id.py`（重写后） | 8/8 · 退出码 0 | 2026-09-18 |
| `test_web_get_all.py` | 9/9 · 退出码 0 | 2026-09-18 |
| `test_web_browser_activate.py` | 6/6 · 退出码 0 | 2026-09-18 |

日志：`.pytest_tmp/live_smoke_baseline.log`（第一轮，含两个失败）、`.pytest_tmp/live_smoke_round2.log`（修正后）。

## 五、新基线暴露的产品侧观察（供产品负责人决策）

1. **`WebBrowser` 失去标签身份访问器**。`id` 被移除后，公开面无法区分「同一 URL、同一标题的两个标签」，
   测试侧只能用组合键近似。`test_web_browser_id.py` 新增用例 `same_url_tabs_not_distinguishable`
   把这一缺口固化为可复跑的契约记录（当前 PASS = 缺口确实存在）。
   若产品希望保留可区分的标签身份，需要一个新的公开访问器（例如只读 `page_ref`/`tab_key`）。
2. **页级与元素级 `scroll_to` 默认 `behavior` 不一致**：`WebBrowser.scroll_to` 默认 `smooth`（`48f5bafb` 改），
   `WebElement.scroll_to` 仍默认 `instant`。是否属有意区分（页面看滚动动画、元素求快），需产品确认。
3. **`__str__` 仍打印私有 `_page_ref['id']`**：`WebBrowser.__str__` 输出
   `WebBrowser(id='…', title=…, url=…, mode=…)`。也就是说 `id` 仍是「公开字符串形态」的一部分，
   移除的是属性访问。若希望彻底不暴露，需要一并调整 `__str__`。

## 六、测试侧边界裁定：删除全部「地址形态探测」（2026-09-18，产品负责人）

产品负责人裁定：**一律不使用非靶场地址形态探测**，全部删除。据此本轮删除了 4 个脚本里的
6 处自造地址/路径名，页面材料一律来自标准靶场 `https://baobaomi900901.github.io/xpath/`：

| 脚本 | 删除内容 | 处置 |
|---|---|---|
| `test_web_browser_stop_load.py` | `HANG_URLS`（不可路由保留地址 `10.255.255.1` / `192.0.2.1`）、`REFUSED_URL`（`127.0.0.1:9`） | 三个用例改写：待处理导航中止 → `BLOCKED`（请求靶场提供「加载永不完成」页面）；create 超时后标签状态 → `BLOCKED`；Chrome 错误页 `is_load_completed()` 恒 False → `KNOWN`（仅保留历史发现，不再现场复现） |
| `test_web_browser_http_request.py` | `HANG_URL`（不可路由保留地址）及其 `connect_timeout` 用例；`MISSING_PATH` 自造文件名 | `connect_timeout` 语义由回显服务 `/delay` 用例覆盖；404 用例改为**随机不存在路径**（标准靶场宿主上的真实 404） |
| `test_web_get_all.py` | `https://example.invalid/` 保留域名 | 改用哨兵标题过滤（只做标签匹配，不打开任何页面） |
| `test_web_get.py` | 同上 | 同上 |

删除后真机复跑：`stop_load` 10/12 通过 + 2 `BLOCKED` + 1 `KNOWN`（退出码 2）、
`http_request` 41/41（退出码 0）、`get_all` 9/9、`get` 9/9。

**因此产生的缺口（需靶场页面才能补齐）**：

> 产品负责人已确认：**会**在靶场增加一个「加载永不完成」的页面/路由。页面到位后，
> `stop_load` 的中止待处理导航用例与 `create(load_timeout=…)` 超时用例即可恢复实测。

1. `stop_load()` 的**正向路径**（中止「待处理导航」）在静态托管靶场上无法构造——GitHub Pages 总会应答，
   不存在网络级「服务端永不响应」。需要靶场提供一个「加载永不完成」的页面/路由（例如页面内嵌一个
   服务端永不响应的子资源请求）。在该页面到位前，本项保持 `BLOCKED`。
2. `is_load_completed()` 在 Chrome **网络错误页**上恒为 `False`（Issue #59）无法在靶场上复现
   （404 是正常文档，不产生 `chrome-error` 页）。该发现仅保留旧基线证据，标记为 `KNOWN`。
3. `create(load_timeout=…)` 超时后标签状态与 `stop_if_timeout` 的作用，同样依赖第 1 项页面。

## 七、本轮未纳入的范围

- **35 个历史元素库模板脚本**（`test_web_element_*.py`、`test_web_handle_save/upload_dialog.py` 等，
  特征：内含 `profile_launch_recovery` 所有权模板）全部读取 `page.raw` / `element.raw`
  做标签身份与所有权核对，而 `WebElement.raw` 已被 `44c8e91f` 移除、`WebBrowser` 上也不存在 `raw`。
  这批脚本在新基线上**无法运行**，需要产品负责人先决定处置口径（改写为组合键/`_page_ref`，
  或标记为历史证据不再复跑）。本轮按「不改历史证据」原则未改动它们。
- 已交付但未在本轮真机复跑的脚本（如 `http_request`、`wait_appear`、`get_text` 等）：
  契约面已随套件 61/61 通过，行为面待各自下一轮复验时确认。

## 复现命令

```powershell
cd "D:\code\元素库\sdk测试"
uv run python .\.pytest_tmp\run_contract_smoke.py          # 契约面 61/61
uv run .\web\test_web_browser_reload.py --mode chrome      # 键不变型
uv run .\web\test_web_browser_go_forward.py --mode chrome  # 键变化型
uv run .\web\test_web_browser_id.py --mode chrome          # 成员收敛契约
```
