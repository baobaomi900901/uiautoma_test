# get_bounding 公开文档与测试索引交接稿

## 授权与状态

用户于本对话明确选择“生成文档交接稿”。本稿及公开文档替换稿已在测试工作区生成；**尚未提交到 GitHub Issue、未修改产品仓库、未提交或推送 Git**。

交接目标仓库：`uiautoma/desktop`。本稿仅交接已验证范围内的文档与测试证据，不要求修改产品实现。

## 本次结论

- 2026-10-08，Chrome 后台自有标签，指定 iframe/open Shadow 表单靶场及 `web靶场_表单测试_ant_输入框`。
- 最后连续三轮各 **38/38 PASS、0 FAIL、0 BLOCKED，退出码 0**；清理均 PASS，标签 6→6。
- DOM 原生矩形 + 独立 ctypes/Win32 客户区/viewport 原点和 DPI 核对，每轮 22 次坐标测量、四字段差值全部为 0。
- 原生窗口 DPI=96、devicePixelRatio=1；**高 DPI 实际换算未验收**。window 参照是原生浏览器客户区，不是网页 viewport。
- 五场景为原始、顶层滚动、iframe 内滚动、小数平移/改尺寸、负 viewport 坐标。后四项含对自有现有节点的受控测试干预，准备状态已恢复。
- 前两轮几何测量 22/22 次前台不变，第三轮 21/22 次不变，一次从测试 Chrome 切到其他窗口。没有把后台窗口切到测试 Chrome 的测量记录；不推断切换的具体原因。
- desktop 只读 worktree：`D:\code\desktop`，commit `7f148f27c0efa8bbba1f18d86c14845ea7d639fa`；Provider 只读 worktree：`D:\code\rust_uia`，commit `b700f9238134f57da83ab478a5ee55337ade1082`。结论限于快照和实际 dev 运行环境；未独立确认 Provider 二进制构建 commit。

## 请求同步的四个产品仓库文件

| 产品目标 | 本地交接内容 | 应执行的更新 |
|---|---|---|
| sdk/docs/web/get_bounding.md | [公开文档替换稿](get_bounding_public_doc_20261008.md) | 采用当前四字段、screen/window/96 DPI 合同，补充真实验收、异常与覆盖范围 |
| sdk/docs/web/index.md | 下方文档索引行 | 仅替换 get_bounding 条目，保留其他 API |
| tests/SDK/web/evidence/get_bounding.md | [最新验证证据](../../web/evidence/get_bounding.md) | 同步五要素完整证据和相应原始产物；归档旧八字段证据，保留 10-04 SKIPPED 记录 |
| tests/SDK/index.md | 下方测试索引行 | 更新当前快照的 VERIFIED / 38/38 × 3 / 96 DPI 范围及无日期脚本入口 |

文档索引替换行：

```markdown
| [`WebElement.get_bounding()`](get_bounding.md) | 获取网页元素的位置和尺寸；Chrome/96 DPI，2026-10-08 连续三轮 38/38 PASS。 |
```

测试索引替换行：

```markdown
| `uiautoma.web.WebElement.get_bounding()` | `VERIFIED`（2026-10-08；后台/96 DPI；连续 3 轮各 38/38 PASS；清理 6→6） | [`web/test_web_element_get_bounding.py`](web/test_web_element_get_bounding.py) | [`web/evidence/get_bounding.md`](web/evidence/get_bounding.md) | [`sdk/docs/web/get_bounding.md`](../../sdk/docs/web/get_bounding.md) |
```

## 附件与复测入口

- 唯一正式脚本：[test_web_element_get_bounding.py](../../web/test_web_element_get_bounding.py)。
- 冻结合同：[element_get_bounding_contract_20261008.json](../../web/element_get_bounding_contract_20261008.json)。
- [原始输出与 SHA-256 清单](../../web/evidence/artifacts/element_get_bounding_20261008.txt)列出三轮 JSON/文本、探针和只读源码快照。
- [历史归档](../get_bounding_history_20261008/README.md)保留更新前的两个脚本及旧证据；归档脚本不作为活动入口。
- 正式脚本依赖已有 `test_web_element_get_select_options.py` 的库副本和动态 ID 准备 helper；迁移脚本时复核 helper 可用，不改动被测选择器的 XPath。

在测试侧工作区运行：

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_element_get_bounding.py
```

## 同步验收条件

1. 四处文件日期、commit、计数和覆盖范围相同，不将高 DPI 未测路径写成 VERIFIED。
2. 原始探针 1 的准备失败及历史 SKIPPED 不改写为通过；旧八字段/仅 screen 的说明明确归为历史。
3. 证据相对链接、脚本依赖和原始产物在目标工作区可访问；公开文档的四字段返回结构与当前 SDK 一致。
4. 只同步 get_bounding 相关内容，不覆盖索引中的其他 API；不用本轮通过结论关闭未复测的其他历史问题。

本稿不包含已发布 Issue URL。
