# WebBrowser Cookie API 验收计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 独立验收用户指定的五个 WebBrowser Cookie 方法，区分顶层 API 的历史计数。

**Architecture:** 顺序测试，一个方法一轮。共用临时 Cookie 准备、页面原生观察、合同和清理代码；每个公开方法有唯一无日期入口和独立报告。Cookie 名称随机，清理前保护其他数据。

**Tech Stack:** 当前 dev Runtime、只读 Python SDK、Chrome、已发布 Cookie 靶场、Python 标准库。

## Global Constraints

- 只读 `D:\code\desktop`，不得改产品或靶场源码。
- 靶场 `https://baobaomi900901.github.io/xpath/#/cookie-test`。
- 用户要求五个 WebBrowser 方法；不借用顶层 API 的旧结果。
- 每个 API 连续三轮完整验收；环境不足如实 BLOCKED/KNOWN，不算成功。
- 独立确证优先页面 `document.cookie`、受控 Cookie 属性和时钟；不把本 API 返回当 oracle。
- 不清理用户原有 Cookie。批量清理只在页面范围内不存在外部 Cookie 的前置条件满足时执行。
- 仅关闭本次标签，保留外部标签；异常路径也必须清理测试 Cookie。
- 不自动生成公开 API 文档；完成后按 AGENTS.md 另询问交接稿。

## Task 1: 合同和环境探针

**Files:** `web/browser_cookie_contracts_20261006.json`、`.pytest_tmp/browser_cookie_probe/`。

- [x] 冻结五个方法的签名、默认值、docstring 与只读源码链路。
- [x] 创建本次靶场页，检查 Runtime、原生 Cookie 可见性和标签基线。
- [x] 实测参数错误、路径匹配、Cookie 属性、空结果与同名不同 Path 的语义。
- [x] 决定 HttpOnly/分区的独立确证是否可行；不可行明确列入跳过边界。

## Task 2–6: 分别验收五个方法

**Files:** `web/_web_browser_cookie_common.py`；`web/test_web_browser_<api>.py`；`web/evidence/browser_<api>.md`；`web/evidence/artifacts/browser_<api>_20261006_run<N>.json/.txt`。

**Interfaces:** 共用 `main(api)` 与一次性上下文；入口仅调用当前方法的用例集合。

- [x] `get_cookies`：列表与完整 Cookie 对照、name/domain/path/secure/session 及组合筛选、空结果、只读/引用生命周期、分区参数。
- [x] `get_cookie`：单项、缺失、必须 name、重复只读、当前网页范围、引用生命周期。
- [x] `set_cookie`：None 返回、默认持久 100 秒、会话、空值、覆盖、Path/Secure、HttpOnly（具独立证据时）、有效期与非法参数、失效引用。
- [x] `remove_cookie`：删除单项、保留其他项、重复删除、同名多路径、分区参数与失效引用。
- [x] `clear_cookies`：前置隔离检查、匹配当前 URL 的项清空、其他 Path 保留、重复清理、分区参数与失效引用；环境不足跳过实际清理。
- [x] 每个方法探针充分后再落正式断言，连续三轮完整运行并保留失败尝试。

## Task 7: 证据与索引

**Files:** `web/web api 清单.md`、`index.md`、上述各方法 evidence/artifacts。

- [x] 同步方法身份、状态、计数、覆盖/跳过边界、源码 worktree/commit 和复测命令。
- [x] 复核三轮 JSON 和页面/Cookie 清理、文档链接、无日期唯一入口。
- [x] 清理本次临时目录，保留旧临时材料和用户改动。
- [x] 已询问四项 VERIFIED 的公开 API 文档交接稿；提交技能与推送权限限制已记录，文件保留本地。

## 实际结果与限制

- 最终三轮 run2/run3/run4：get_cookies 29/29、get_cookie 18/18、remove_cookie 16/16、clear_cookies 13/13，VERIFIED。
- set_cookie 三轮各 20/21 PASS + 1 FAIL，READY_FOR_LIVE；异 Path 项实际写入却报 cookie_set_failed，已准备本地缺陷交接稿，尚未向产品仓库提交。
- 所有正式标签 silent_running=True；最终三轮清理均 PASS、外部 Cookie 基线保留、标签 3→3。
- 第一轮 set_cookie 清理脚本 Path 规范化错误已修正，原始失败证据保留。
- 分区字符串 docstring 与 Mapping 实现不符，三方法后台补充探针和本地交接稿已保留；字典第一方分区通过。
- 精确 Path 的清理采用 document.cookie，而不是会规范化尾斜杠的 Cookie Store.delete。
- 公开文档须获确认；未修改产品源码。提交要求的 git-emoji-commit 技能未找到，且此前推送受自动审批拒绝；本轮不再次尝试推送。
- 本次临时目录 browser_cookie_probe 已删除；其他历史临时材料与用户改动保留。
- 四项公开 API 文档交接稿的异步确认问题已发出，尚未收到答复；仅测试侧证据与索引自动更新。
- 用户要求继续确认后，直接用同版本 Chrome 154.0.8037.95 做隔离无窗口原生 callback/Promise 对照，18 项确认成功；不加载产品 Engine 或靶场代码。当前 dev SDK 三对相同 Cookie 参数仅改变网页 URL 绑定，也确认异 Path 已写入却报错。
- 根因已定位为引擎把 Chrome 成功的 undefined 返回误判为 cookie_set_failed；证据和本地 Issue 稿已补充，产品未修复，正式 API 状态与 20/21 计数保持不变。

## Issue 交接（2026-10-06）

按用户明确要求查重，未找到同缺陷；已新建 [desktop #74](https://github.com/uiautoma/desktop/issues/74)，并在[提测总单 #51](https://github.com/uiautoma/desktop/issues/51#issuecomment-6006002391)补充。远端正文和评论均读回一致，本地归档 `issues/issue_74/`。首次完整稿自动审批因披露范围拒绝，改用精简稿成功。set_cookie 状态保持 READY_FOR_LIVE，三轮各 20/21 PASS + 1 FAIL；产品源码未修改。
