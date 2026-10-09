# SDK Web API 测试情况与关联 Issue（2026-10-09）

本报告汇总现有测试记录，未执行新的 SDK 全量回归。清单状态绑定各自测试日期、源码快照与覆盖范围；102 个 VERIFIED 不等于同一最新构建的全部场景通过。Issue 状态已于 2026-10-09 通过 GitHub REST API 只读核对。

来源：[Web API 清单](../web%20api%20清单.md)、[总索引](../../index.md)、各方法证据；[统计快照](artifacts/web_api_status_20261009_inventory.json)、[Issue 状态快照](artifacts/web_api_status_20261009_issues.json)。

## 1. 清单总览

| 层级 | VERIFIED | READY_FOR_LIVE | DRAFT | SKIPPED | 合计 |
|---|---:|---:|---:|---:|---:|
| 顶层 uiautoma.web | 16 | 0 | 0 | 1 | 17 |
| WebBrowser | 38 | 1 | 0 | 2 | 41 |
| WebElement | 48 | 1 | 1 | 4 | 54 |
| **合计** | **102** | **2** | **1** | **7** | **112** |

112 条包含方法、属性和历史移除项。VERIFIED 表示在记录范围内真实场景与清理通过；部分记录含 KNOWN 能力边界。READY_FOR_LIVE 的两项均有稳定失败。

## 2. 最近完成的重点验收

| API | 每轮结果 | 最近日期与覆盖 |
|---|---|---|
| WebElement.highlight | 8/8 PASS，连续 3 轮 | 10-09；非静默，真实红框；Chrome/96 DPI；完整验收 --close-page。[证据](highlight.md) |
| WebElement.input | 60/60 PASS，连续 3 轮 | 10-08；Ant/原生双输入框，后台范围；系统键盘和实际鼠标锚点未复测。[证据](input.md) |
| WebElement.get_bounding | 38/38 PASS，连续 3 轮 | 10-08；DOM+Win32 独立几何；96 DPI。[证据](get_bounding.md) |
| WebElement.get_anchor_position | 76/76 PASS，连续 3 轮 | 10-08；九锚点/random/偏移/滚动；96 DPI。[证据](get_anchor_position.md) |
| WebBrowser.get_cookies / get_cookie | 29/29、18/18 PASS，各连续 3 轮 | 10-06；后台方法独立验收。[get_cookies](browser_get_cookies.md)、[get_cookie](browser_get_cookie.md) |
| WebBrowser.remove_cookie / clear_cookies | 16/16、13/13 PASS，各连续 3 轮 | 10-06；后台，保留外部 Cookie 基线。[remove_cookie](browser_remove_cookie.md)、[clear_cookies](browser_clear_cookies.md) |
| WebBrowser.stop_load | 18/18 PASS，最后连续 3 轮 | 10-05；慢资源中止及自然完成对照，JS 心跳保留。[证据](browser_stop_load_20261005.md) |
| WebBrowser.is_load_completed | 19/19 PASS，连续 3 轮 | 10-05；加载中/完成/失败/失效引用。[证据](is_load_completed.md) |
| uiautoma.web.handle_upload_dialog | 10/10 PASS，连续 3 轮 | 10-05；用户指定单/多文件按钮，真实文件对话框。[证据](web_handle_upload_dialog_20261005.md) |
| WebBrowser.handle_javascript_dialog | 16/16 PASS，连续 3 轮 | 10-05；指定 alert/confirm/prompt 按钮。[证据](handle_javascript_dialog_20261005.md) |
| uiautoma.web.auto_handle_popup | 19/19 PASS，3 轮及用户复测 | 10-05；Ant DOM Modal；名称/Selector 注册及重复规则。[证据](auto_handle_popup_20261005.md) |
| uiautoma.web.remove_all_auto_handle_popup | 19/19 PASS，最后连续 3 轮 | 10-05；规则移除后弹窗保留，复注册生效。[证据](remove_all_auto_handle_popup_20261005.md) |
| WebElement.check | 61/61 PASS，连续 3 轮 | 09-24；Ant/原生 checkbox/radio，DOM 与提交值核对；音乐选择器重新抓取后解除歧义。[证据](check.md) |

顶层 Cookie API 的旧计数与 WebBrowser 方法的独立计数分别统计，不互相替代。

## 3. 当前未通过 / 未独立验收 / 跳过

| API | 状态 | 原因与关联 Issue |
|---|---|---|
| WebBrowser.set_cookie | READY_FOR_LIVE；三轮各 20/21 PASS+1 FAIL | 写入另一 Path 已成功，却因原生成功的 undefined 被误判为 cookie_set_failed。产品缺陷，[#74](https://github.com/uiautoma/desktop/issues/74) OPEN，已补充 [#51](https://github.com/uiautoma/desktop/issues/51) 跟踪。不是靶场或 Python 脚本错误。[证据](browser_set_cookie.md) |
| WebElement.is_enabled | READY_FOR_LIVE；三轮各 30/32 PASS+2 FAIL | 两个按钮存在 disabled="false" 时 DOM 判为禁用，API 错报 True；原始 disabled/普通按钮通过。两条失败对应同一缺陷；[#23](https://github.com/uiautoma/desktop/issues/23) OPEN，已补充复测。原 Issue 的空串问题本轮已通过。[证据](is_enabled.md) |
| WebElement.id | DRAFT | 尚缺属性本身独立验收证据；不沿用旧 8/8 方法计数。 |
| set_user_environment_fingerprint | SKIPPED | 源码未实现，抛 UnsupportedActionError。 |
| WebBrowser.extract_table / WebElement.extract_table / WebElement.get_basetable_value | SKIPPED（3 项） | 源码未实现，抛 UnsupportedActionError。 |
| WebBrowser.id / WebElement.element_id / WebElement.raw | SKIPPED（3 项） | 已移除或源码不存在；这些是历史清单条目。 |

## 4. 关联 Issue 状态与测试对应

**本报告整理 27 个直接或跨层关联 Issue：22 OPEN、5 CLOSED。这不是 22 个当前仍复现的 SDK 缺陷。**

### 4.1 当前复现的两个缺陷

- [#74](https://github.com/uiautoma/desktop/issues/74)：WebBrowser.set_cookie；20/21×3，清理 PASS，写入成功后误报失败。
- [#23](https://github.com/uiautoma/desktop/issues/23)：WebElement.is_enabled；30/32×3，清理 PASS，目前失败条件为 disabled="false"。

### 4.2 需要补充原始触发条件验收的 OPEN Issue

| Issue | 关联 API | 当前测试与待核对范围 |
|---|---|---|
| [#9](https://github.com/uiautoma/desktop/issues/9) | handle_save_dialog(wait_complete=True) | 保存/取消 7/7 通过，但现证据明确未覆盖 wait_complete=True；不能据此关闭下载等待超时问题。 |
| [#20](https://github.com/uiautoma/desktop/issues/20) | WebElement.screenshot | 当前截图验收通过；dpr=1 未复现历史偏移，高 DPI/页面缩放触发条件仍未复核。[历史范围说明](screenshot.md) |
| [#60](https://github.com/uiautoma/desktop/issues/60) | wait_load_completed | 原问题是连续两次超时后 stale_page_reference/标签泄漏；stop_load 和 is_load_completed 通过不等于该序列通过。 |
| [#57](https://github.com/uiautoma/desktop/issues/57) | handle_save_dialog | Chrome 重启后 7/7 通过，已补充评论；Issue 仍 OPEN，等待原窗口/桥接冲突根治确认。[证据](handle_save_dialog_current.md) |
| [#24](https://github.com/uiautoma/desktop/issues/24) | is_displayed | 7/7 通过 visible/display:none/visibility:hidden 等场景；历史 scrollIntoView 污染可见性的屏外条件不在该矩阵内。 |
| [#29](https://github.com/uiautoma/desktop/issues/29) | download | 5/5×3，下载字节与 HTTP 独立读取一致；历史原生“另存为”及浏览器下载配置组合须单独核对。 |

### 4.3 已有对应 API 通过记录，但 Issue 仍 OPEN

| Issue | API / 最新已记录范围 |
|---|---|
| [#12](https://github.com/uiautoma/desktop/issues/12) | check：61/61×3，Ant 与原生受控状态/提交值通过；旧未可靠更新状态的报告需与该快照对应。 |
| [#14](https://github.com/uiautoma/desktop/issues/14) | set_attribute：7/7×3，实际属性读写通过。 |
| [#17](https://github.com/uiautoma/desktop/issues/17)、[#18](https://github.com/uiautoma/desktop/issues/18) | select_multiple / select_multiple_by_index：20/21、22/23×3；标准原生 select 通过，Ant 自定义控件记 KNOWN。 |
| [#19](https://github.com/uiautoma/desktop/issues/19)、[#27](https://github.com/uiautoma/desktop/issues/27) | get_select_options / get_all_select_items：14/16、15/17×3；原生通过，Ant 为能力边界。 |
| [#28](https://github.com/uiautoma/desktop/issues/28) | get_selected_item：10/12×3；2 KNOWN，不能推广到全部自定义控件。 |
| [#21](https://github.com/uiautoma/desktop/issues/21) | screenshot_to_clipboard：18/18，ctypes 独立读回与取景核对；本次 DPI 范围。 |
| [#22](https://github.com/uiautoma/desktop/issues/22) | is_checked：11/11×3。 |
| [#25](https://github.com/uiautoma/desktop/issues/25)、[#26](https://github.com/uiautoma/desktop/issues/26) | drag_to：6/7×3；simulative=False 真实位移通过，simulative=True 因 Provider 条件记 KNOWN；两个 Issue 标题指向相同现象。 |

这些 Issue 的“暂不支持”或旧失败标题可能已落后于测试记录。应先用原触发条件复测，并把证据补回 Issue，再由维护者决定关闭；本轮未发布评论或更改 Issue 状态。

### 4.4 已 CLOSED 的关联 Issue

| Issue | 关联 API / 当前记录 |
|---|---|
| [#65](https://github.com/uiautoma/desktop/issues/65) | input：后台 60/60×3，原生/Ant 提交状态正常。 |
| [#59](https://github.com/uiautoma/desktop/issues/59) | is_load_completed：19/19×3；失败页当前按加载失败抛异常，不是无限等待。 |
| [#58](https://github.com/uiautoma/desktop/issues/58) | go_back：5/5×3；go_forward 旧记录仍含 #58 预热依赖说明，需后续刷新。 |
| [#64](https://github.com/uiautoma/desktop/issues/64) | 元素级 find_all 作用域：GitHub 已 CLOSED；清单/旧证据仍保留跨 iframe/open Shadow 的 KNOWN，需要修复后专项复测与文档同步。 |
| [#61](https://github.com/uiautoma/desktop/issues/61) | 无响应标签 close/navigate：GitHub 已 CLOSED；当前 stop_load 场景是可响应 JS 的慢资源，不是同步 JS 死循环专项复测。 |

### 4.5 跨层提测跟踪（OPEN）

- [#51](https://github.com/uiautoma/desktop/issues/51)：Web 动作对齐、SDK 与跨层旧路径；set_cookie 结果已补充。
- [#70](https://github.com/uiautoma/desktop/issues/70)：Win32/Web 实时引用与 Package 解耦、生命周期验收。
- [#39](https://github.com/uiautoma/desktop/issues/39)：Web 注入、高亮与元素快照选择器合同；单元素 highlight 验收不替代整个捕获/快照合同验收。

## 5. 复测安排建议

1. 修复并重跑 set_cookie / is_enabled：分别对应 #74 / #23。
2. 补齐 #60 的连续超时序列，以及 #20 的高 DPI/缩放，#9 的 wait_complete=True。
3. 对 #64 原跨 iframe/open Shadow 组合开展修复后回归；同步清单里仍为 KNOWN 的旧说明。
4. 给 WebElement.id 建独立属性验收；未实现的 4 项保留 SKIPPED。
5. 逐个核对历史 OPEN Issue 的原复现条件，再交接更新/关闭；保留 Ant 自定义 select、物理拖拽、其他浏览器/DPI 等覆盖边界。

## 6. 完整清单快照

下表直接保留当前清单的记录口径，不能用历史通过数证明所有当前版本行为。

| 条目 | 状态 | 当前记录 |
|---|---|---|
| `uiautoma.web.create` | VERIFIED | ✅ `VERIFIED`（5/5） |
| `uiautoma.web.get` | VERIFIED | ✅ `VERIFIED`（9/9） |
| `uiautoma.web.get_active` | VERIFIED | ✅ `VERIFIED`（9/9） |
| `uiautoma.web.get_all` | VERIFIED | ✅ `VERIFIED`（9/9） |
| `uiautoma.web.get_cookies` | VERIFIED | ✅ `VERIFIED`（12/12） |
| `uiautoma.web.get_cookie` | VERIFIED | ✅ `VERIFIED`（8/8） |
| `uiautoma.web.set_cookie` | VERIFIED | ✅ `VERIFIED`（10/10） |
| `uiautoma.web.remove_cookie` | VERIFIED | ✅ `VERIFIED`（9/9） |
| `uiautoma.web.clear_cookies` | VERIFIED | ✅ `VERIFIED`（10/10） |
| `uiautoma.web.close_all` | VERIFIED | ✅ `VERIFIED`（9/9） |
| `uiautoma.web.handle_save_dialog` | VERIFIED | ✅ `VERIFIED`（7/7；2026-09-15复测） |
| `uiautoma.web.handle_upload_dialog` | VERIFIED | ✅ `VERIFIED`（2026-10-05；10/10 PASS + 0 FAIL + 0 KNOWN；连续 3 轮；退出码 0；指定单/多文件库元素）；[证据](web_handle_upload_dialog_20261005.md) |
| `uiautoma.web.auto_handle_popup` | VERIFIED | ✅ `VERIFIED`（2026-10-05；19/19 PASS；3 轮正式验收 + 用户复测 1 次；退出码 0；用户清理 4→4）；[证据](auto_handle_popup_20261005.md) |
| `uiautoma.web.remove_all_auto_handle_popup` | VERIFIED | ✅ `VERIFIED`（2026-10-05；19/19 PASS；最后连续 3 轮；退出码 0；清理 4→4）；[证据](remove_all_auto_handle_popup_20261005.md) |
| `uiautoma.web.set_user_environment` | VERIFIED | ✅ `VERIFIED`（6/6；含预期环境状态） |
| `uiautoma.web.set_user_environment_fingerprint` | SKIPPED | ⏭️ `SKIPPED`（2026-10-04；1/2 PASS + 0 FAIL + 1 KNOWN；1 轮；退出码 0）；[证据](web_set_user_environment_fingerprint_20261004.md) |
| `uiautoma.web.reset_user_environment` | VERIFIED | ✅ `VERIFIED`（7/7） |
| `WebBrowser.id` | SKIPPED | ⏭️ `SKIPPED`（公开 API 已移除）；脚本改为「成员收敛 + 替代方式」契约（8/8，`test_web_browser_id.py`） |
| `WebBrowser.get_url` | VERIFIED | ✅ `VERIFIED`（7/7） |
| `WebBrowser.get_title` | VERIFIED | ✅ `VERIFIED`（7/7） |
| `WebBrowser.get_text` | VERIFIED | ✅ `VERIFIED`（7/7） |
| `WebBrowser.get_html` | VERIFIED | ✅ `VERIFIED`（8/8） |
| `WebBrowser.activate` | VERIFIED | ✅ `VERIFIED`（6/6） |
| `WebBrowser.activateTab` | VERIFIED | ✅ `VERIFIED`（6/6；恢复仅尝试） |
| `WebBrowser.navigate` | VERIFIED | ✅ `VERIFIED`（14/14） |
| `WebBrowser.go_back` | VERIFIED | ✅ `VERIFIED`（2026-10-04；5/5 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](browser_go_back_20261004.md) |
| `WebBrowser.go_forward` | VERIFIED | ✅ `VERIFIED`（13/13；前置依赖 #58，仅预热路径） |
| `WebBrowser.reload` | VERIFIED | ✅ `VERIFIED`（12/12） |
| `WebBrowser.stop_load` | VERIFIED | ✅ `VERIFIED`（2026-10-05；最后连续 3 轮 18/18 PASS；退出码 0；准备恢复与首轮 BLOCKED 已记录）；[证据](browser_stop_load_20261005.md) |
| `WebBrowser.is_load_completed` | VERIFIED | ✅ `VERIFIED`（2026-10-05；连续 3 轮 19/19 PASS；True/False、加载失败与失效引用）；[证据](is_load_completed.md) |
| `WebBrowser.wait_load_completed` | VERIFIED | ✅ `VERIFIED`（12/12） |
| `WebBrowser.close` | VERIFIED | ✅ `VERIFIED`（10/10） |
| `WebBrowser.execute_javascript` | VERIFIED | ✅ `VERIFIED`（16/16） |
| `WebBrowser.scroll_to` | VERIFIED | ✅ `VERIFIED`（16/16；`48f5bafb` 起默认值由 instant 改为 smooth） |
| `WebBrowser.handle_javascript_dialog` | VERIFIED | ✅ `VERIFIED`（2026-10-05；16/16 PASS；连续 3 轮；指定库按钮）；[证据](handle_javascript_dialog_20261005.md) |
| `WebBrowser.get_javascript_dialog_text` | VERIFIED | ✅ `VERIFIED`（13/13） |
| `WebBrowser.get_scroll` | VERIFIED | ✅ `VERIFIED`（15/15） |
| `WebBrowser.wait_appear` | VERIFIED | ✅ `VERIFIED`（31/31 + 1 边界；canonical=靶场自计时页 delayed-element.html） |
| `WebBrowser.wait_disappear` | VERIFIED | ✅ `VERIFIED`（32/32；隐藏元素不算消失，自计时页零调度） |
| `WebBrowser.get_cookies` | VERIFIED | ✅ `VERIFIED`（2026-10-06；连续 3 轮 29/29 PASS；后台；清理 3→3；分区限字典，字符串文档差异已记录）；[证据](browser_get_cookies.md) |
| `WebBrowser.get_cookie` | VERIFIED | ✅ `VERIFIED`（2026-10-06；连续 3 轮 18/18 PASS；后台；清理 3→3）；[证据](browser_get_cookie.md) |
| `WebBrowser.set_cookie` | READY_FOR_LIVE | ❌ `READY_FOR_LIVE`（2026-10-06；三轮各 20/21 PASS + 1 FAIL；同版本 Chrome 原生 18 项与 SDK 三对确认：成功的 undefined 被误判 cookie_set_failed；清理 PASS）；[证据](browser_set_cookie.md)；[缺陷 #74](https://github.com/uiautoma/desktop/issues/74) |
| `WebBrowser.remove_cookie` | VERIFIED | ✅ `VERIFIED`（2026-10-06；连续 3 轮 16/16 PASS；后台；清理 3→3；分区限字典，字符串文档差异已记录）；[证据](browser_remove_cookie.md) |
| `WebBrowser.clear_cookies` | VERIFIED | ✅ `VERIFIED`（2026-10-06；连续 3 轮 13/13 PASS；后台；清理 3→3；分区限字典，字符串文档差异已记录）；[证据](browser_clear_cookies.md) |
| `WebBrowser.start_monitor_network` | VERIFIED | ✅ `VERIFIED`（12/12；过滤为存储级） |
| `WebBrowser.get_responses` | VERIFIED | ✅ `VERIFIED`（19/19） |
| `WebBrowser.stop_monitor_network` | VERIFIED | ✅ `VERIFIED`（13/13） |
| `WebBrowser.http_request` | VERIFIED | ✅ `VERIFIED`（41/41；2026-09-18 新基线复跑；地址形态探测删除后 connect_timeout 由回显 `/delay` 覆盖） |
| `WebBrowser.find_all` | VERIFIED | ✅ `VERIFIED`（20/20；超时返回空列表、多命中返回全部；含清理复核修正） |
| `WebBrowser.find` | VERIFIED | ✅ `VERIFIED`（22/22；库=260902_web元素，靶场=#/iframe-shadow-form；含清理复核修正） |
| `WebBrowser.find_all_by_css` | VERIFIED | ✅ `VERIFIED`（22/22；官方靶场+活 DOM 推导） |
| `WebBrowser.find_by_css` | VERIFIED | ✅ `VERIFIED`（22/22；官方靶场+活 DOM 推导） |
| `WebBrowser.find_all_by_xpath` | VERIFIED | ✅ `VERIFIED`（22/22；官方靶场+活 DOM 推导） |
| `WebBrowser.find_by_xpath` | VERIFIED | ✅ `VERIFIED`（22/22；官方靶场+活 DOM 推导） |
| `WebBrowser.is_element_displayed` | VERIFIED | ✅ `VERIFIED`（20/20；库级未命中会抛异常而非 False） |
| `WebBrowser.extract_table` | SKIPPED | ⏭️ `SKIPPED`（2026-10-04；1/2 PASS + 0 FAIL + 1 KNOWN；1 轮；退出码 0）；[证据](browser_extract_table_20261004.md) |
| `WebBrowser.screenshot` | VERIFIED | ✅ `VERIFIED`（21/21；扩展名决定格式） |
| `WebBrowser.screenshot_to_clipboard` | VERIFIED | ✅ `VERIFIED`（23/23；ctypes 独立读 CF_DIB，与文件截图三角像素比对） |
| `WebElement.id` | DRAFT | 📝 `DRAFT`（原 8/8 尚缺属性独立验收证据） |
| `WebElement.element_id` | SKIPPED | ⏭️ `SKIPPED`（源码不存在；源码核对；应使用 `WebElement.id`） |
| `WebElement.name` | VERIFIED | ✅ `VERIFIED`（2026-10-04；6/6 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_name_20261004.md) |
| `WebElement.raw` | SKIPPED | ⏭️ `SKIPPED`（源码不存在；源码核对） |
| `WebElement.find` | VERIFIED | ✅ `VERIFIED`（6/6；连续 3 次；人工复测通过） |
| `WebElement.find_all` | VERIFIED | ✅ `VERIFIED`（30 用例 29/29 + 1 记录；标准靶场同文档路由 `#/anchor-test` 语义正确；跨 iframe/open shadow 的已保存路径返回空，记为不对称边界 KNOWN，已提 [#64](https://github.com/uiautoma/desktop/issues/64)） |
| `WebElement.find_by_css` | VERIFIED | ✅ `VERIFIED`（38/38；已定位的 iframe/open shadow 容器内 CSS 查找） |
| `WebElement.find_all_by_css` | VERIFIED | ✅ `VERIFIED`（39/39；已定位的 iframe/open shadow 容器内 CSS 全量查找） |
| `WebElement.find_by_xpath` | VERIFIED | ✅ `VERIFIED`（40/40；已定位的 iframe/open shadow 容器内相对 XPath） |
| `WebElement.find_all_by_xpath` | VERIFIED | ✅ `VERIFIED`（41/41；已定位的 iframe/open shadow 容器内 XPath 全量查找） |
| `WebElement.parent` | VERIFIED | ✅ `VERIFIED`（23/23；含零预算超时边界，未宣称零超时读取成功） |
| `WebElement.children` | VERIFIED | ✅ `VERIFIED`（25/25；直接子元素；含零预算超时边界） |
| `WebElement.child_at` | VERIFIED | ✅ `VERIFIED`（40/40；0 起始索引；含零预算超时边界） |
| `WebElement.previous_sibling` | VERIFIED | ✅ `VERIFIED`（28/28；前一个兄弟元素；含零预算超时边界） |
| `WebElement.next_sibling` | VERIFIED | ✅ `VERIFIED`（28/28；下一个兄弟元素；含零预算超时边界） |
| `WebElement.click` | VERIFIED | ✅ `VERIFIED`（62/62；含真实 Win 键日志核验） |
| `WebElement.dblclick` | VERIFIED | ✅ `VERIFIED`（41/41；真实/DOM 双击；剪贴板日志核验） |
| `WebElement.input` | VERIFIED | ✅ `VERIFIED`（2026-10-08；后台范围连续 3 轮 60/60 PASS；Ant/原生；清理 2→2；系统键盘/实际鼠标锚点未复测）；[证据](input.md) |
| `WebElement.clipboard_input` | VERIFIED | ✅ `VERIFIED`（双模式44/44；非 iframe/iframe；剪贴板 JSON 核对） |
| `WebElement.focus` | VERIFIED | ✅ `VERIFIED`（15/15；focusin/activeElement/剪贴板日志；实测 isTrusted=True） |
| `WebElement.hover` | VERIFIED | ✅ `VERIFIED`（23/23；真实/脚本悬停；锚点与 delay_after 核验） |
| `WebElement.get_text` | VERIFIED | ✅ `VERIFIED`（35/35 语义矩阵复验：隐藏不计入、不截断、空文本非 None） |
| `WebElement.get_html` | VERIFIED | ✅ `VERIFIED`（17/17；2026-09-20 真实库元素 `web靶场_测试超链接`：独立 DOM 全量比对、HTML/文本通道差异、属性转义、活推导读写） |
| `WebElement.get_value` | VERIFIED | ✅ `VERIFIED`（17/17；2026-09-20 `web靶场_表单测试_原生_输入框`：IDL 语义、`''`/`None` 区分、控件矩阵、动态 ID 前置条件含恢复、页面自身提交回显确证） |
| `WebElement.set_value` | VERIFIED | ✅ `VERIFIED`（21/21；2026-09-20 `web靶场_表单测试_原生_输入框`：不派发事件含有效性对照、不聚焦、覆盖语义、换行按控件类型、非输入元素 expando、页面表单状态 A/B） |
| `WebElement.check` | VERIFIED | ✅ `VERIFIED`（2026-09-24：61/61 PASS，连续 3 次退出码 0；Ant「音乐」input 重新抓取后唯一定位） |
| `WebElement.select` | VERIFIED | ✅ `VERIFIED`（2026-09-24：13/14 PASS + 1 KNOWN，连续 3 次退出码 0；Ant 自定义下拉框是已知边界） |
| `WebElement.select_multiple` | VERIFIED | ✅ `VERIFIED`（2026-09-24：20/21 PASS + 1 KNOWN，连续 3 次退出码 0；Ant 自定义控件是已知边界） |
| `WebElement.select_by_index` | VERIFIED | ✅ `VERIFIED`（2026-09-24：17/18 PASS + 1 KNOWN，连续 3 次退出码 0；Ant 自定义控件是已知边界） |
| `WebElement.select_multiple_by_index` | VERIFIED | ✅ `VERIFIED`（2026-09-24：22/23 PASS + 1 KNOWN，连续 3 次退出码 0；Ant 自定义控件是已知边界） |
| `WebElement.get_select_options` | VERIFIED | ✅ `VERIFIED`（2026-10-03：14/16 PASS + 2 KNOWN，连续 3 次退出码 0；Ant 是已知边界） |
| `WebElement.get_all_select_items` | VERIFIED | ✅ `VERIFIED`（2026-10-03：15/17 PASS + 2 KNOWN，连续 3 次退出码 0；Ant 是已知边界） |
| `WebElement.get_selected_item` | VERIFIED | ✅ `VERIFIED`（2026-10-04；10/12 PASS + 0 FAIL + 2 KNOWN；3 轮；退出码 0）；[证据](element_get_selected_item_20261004.md) |
| `WebElement.set_attribute` | VERIFIED | ✅ `VERIFIED`（2026-10-04；7/7 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_set_attribute_20261004.md) |
| `WebElement.get_attribute` | VERIFIED | ✅ `VERIFIED`（2026-10-04；8/8 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_get_attribute_20261004.md) |
| `WebElement.get_all_attributes` | VERIFIED | ✅ `VERIFIED`（2026-10-04；7/7 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_get_all_attributes_20261004.md) |
| `WebElement.get_bounding` | VERIFIED | ✅ `VERIFIED`（2026-10-08；后台/96 DPI；连续 3 轮各 38/38 PASS；清理 6→6）；[证据](get_bounding.md) |
| `WebElement.get_anchor_position` | VERIFIED | ✅ `VERIFIED`（2026-10-08；后台/96 DPI；连续 3 轮各 76/76 PASS；清理 8→8）；[证据](get_anchor_position.md) |
| `WebElement.get_anchor_viewport_position` | VERIFIED | ✅ `VERIFIED`（2026-10-04；11/11 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_get_anchor_viewport_position_20261004.md) |
| `WebElement.extract_table` | SKIPPED | ⏭️ `SKIPPED`（2026-10-04；1/2 PASS + 0 FAIL + 1 KNOWN；1 轮；退出码 0）；[证据](element_extract_table_20261004.md) |
| `WebElement.get_basetable_value` | SKIPPED | ⏭️ `SKIPPED`（2026-10-04；1/2 PASS + 0 FAIL + 1 KNOWN；1 轮；退出码 0）；[证据](element_get_basetable_value_20261004.md) |
| `WebElement.screenshot` | VERIFIED | ✅ `VERIFIED`（2026-10-04；5/5 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_screenshot_20261004.md) |
| `WebElement.screenshot_to_clipboard` | VERIFIED | ✅ `VERIFIED`（18/18；活矩形裁切偏移扫描验取景，dpr=1 下 Issue #20 未复现） |
| `WebElement.is_checked` | VERIFIED | ✅ `VERIFIED`（2026-10-04；11/11 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_is_checked_20261004.md) |
| `WebElement.is_enabled` | READY_FOR_LIVE | ❌ `READY_FOR_LIVE`（2026-10-08；30/32 PASS + 2 FAIL + 0 BLOCKED；3 轮；退出码 1；原始两按钮通过，disabled="false" 缺陷；[Issue #23 已补充](https://github.com/uiautoma/desktop/issues/23#issuecomment-6055620980)）；[证据](is_enabled.md) |
| `WebElement.is_displayed` | VERIFIED | ✅ `VERIFIED`（2026-10-04；7/7 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_is_displayed_20261004.md) |
| `WebElement.execute_javascript` | VERIFIED | ✅ `VERIFIED`（2026-10-04；10/10 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_execute_javascript_20261004.md) |
| `WebElement.scroll_to` | VERIFIED | ✅ `VERIFIED`（2026-10-04；9/9 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_scroll_to_20261004.md) |
| `WebElement.get_scroll` | VERIFIED | ✅ `VERIFIED`（2026-10-04；10/10 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_get_scroll_20261004.md) |
| `WebElement.drag_to` | VERIFIED | ✅ `VERIFIED`（2026-10-04；6/7 PASS + 0 FAIL + 1 KNOWN；3 轮；退出码 0）；[证据](element_drag_to_20261004.md) |
| `WebElement.drag_to_by_cdp` | VERIFIED | ✅ `VERIFIED`（2026-10-04；5/5 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_drag_to_by_cdp_20261004.md) |
| `WebElement.upload` | VERIFIED | ✅ `VERIFIED`（2026-10-04；6/6 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_upload_20261004.md) |
| `WebElement.download` | VERIFIED | ✅ `VERIFIED`（2026-10-04；5/5 PASS + 0 FAIL + 0 KNOWN；3 轮；退出码 0）；[证据](element_download_20261004.md) |
| `WebElement.highlight` | VERIFIED | ✅ `VERIFIED`（2026-10-09；8/8 PASS，连续 3 轮；Chrome/96 DPI；非静默；完整清理用 --close-page）；[证据](highlight.md) |
