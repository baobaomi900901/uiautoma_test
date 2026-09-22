# 源码侧文档同步交接包

日期：2026-09-20　被测基线：`uiautoma/desktop` `c101caa9dcd115a461fc71ecaed351b0dea880b8`

## 这个包是干什么的

把 3 个已复验的公开 API 的**产品侧公开文档与验证证据**同步过去：

| API | 本轮结果 |
| --- | --- |
| `uiautoma.web.WebElement.get_html()` | 17/17，连续 3 次退出码 0 |
| `uiautoma.web.WebElement.get_value()` | 17/17，连续 3 次退出码 0 |
| `uiautoma.web.WebElement.set_value()` | 21/21，连续 3 次退出码 0 |

内容已经过产品负责人确认，但**产品仓库为只读**，因此不在源码树内直接修改，改为在此交接，
由产品侧自行应用。本包**不修改任何源码**，只提供目标文件与逐行编辑清单。

## 怎么应用

以下命令在你的 `uiautomata/desktop` 检出根目录执行（把 `$ProductRoot` 换成实际路径）：

```powershell
$ProductRoot = 'D:\code\desktop'
$Handoff = 'D:\code\元素库\sdk测试\issues\docs_sync_20260920_web_element_read_write'

# 1) 整文件替换（7 个）
Copy-Item -Force -LiteralPath "$Handoff\files\sdk\docs\web\get_html.md"  -Destination "$ProductRoot\sdk\docs\web\get_html.md"
Copy-Item -Force -LiteralPath "$Handoff\files\sdk\docs\web\get_value.md" -Destination "$ProductRoot\sdk\docs\web\get_value.md"
Copy-Item -Force -LiteralPath "$Handoff\files\sdk\docs\web\set_value.md" -Destination "$ProductRoot\sdk\docs\web\set_value.md"
Copy-Item -Force -LiteralPath "$Handoff\files\sdk\docs\web\index.md"     -Destination "$ProductRoot\sdk\docs\web\index.md"
Copy-Item -Force -LiteralPath "$Handoff\files\tests\SDK\web\evidence\get_html.md"  -Destination "$ProductRoot\tests\SDK\web\evidence\get_html.md"
Copy-Item -Force -LiteralPath "$Handoff\files\tests\SDK\web\evidence\get_value.md" -Destination "$ProductRoot\tests\SDK\web\evidence\get_value.md"
Copy-Item -Force -LiteralPath "$Handoff\files\tests\SDK\web\evidence\set_value.md" -Destination "$ProductRoot\tests\SDK\web\evidence\set_value.md"

# 2) 逐行编辑：见 edits/tests_SDK_index.md（3 行替换，机械操作）
```

应用后自检：

```powershell
cd $ProductRoot
git diff --stat -- sdk/docs/web tests/SDK
uv run python -m pytest tests/test_uiautoma_documentation_contract.py -q --basetemp .pytest_tmp/docs-sync
```

文档契约测试会校验覆盖矩阵引用的路径必须存在——本包只做**内容替换**，不新增/删除被引用的文件，
因此不会影响该测试。

## 文件清单

| 交接文件 | 目标路径 | 动作 |
| --- | --- | --- |
| `files/sdk/docs/web/get_html.md` | `sdk/docs/web/get_html.md` | 整文件替换 |
| `files/sdk/docs/web/get_value.md` | `sdk/docs/web/get_value.md` | 整文件替换 |
| `files/sdk/docs/web/set_value.md` | `sdk/docs/web/set_value.md` | 整文件替换 |
| `files/sdk/docs/web/index.md` | `sdk/docs/web/index.md` | 整文件替换 |
| `files/tests/SDK/web/evidence/get_html.md` | `tests/SDK/web/evidence/get_html.md` | 整文件替换 |
| `files/tests/SDK/web/evidence/get_value.md` | `tests/SDK/web/evidence/get_value.md` | 整文件替换 |
| `files/tests/SDK/web/evidence/set_value.md` | `tests/SDK/web/evidence/set_value.md` | 整文件替换 |
| `edits/tests_SDK_index.md` | `tests/SDK/index.md` | 逐行替换 3 行 |

## 内容依据

每个结论都来自**本轮当前基线的真实运行**，不是从旧证据推断：

- 运行来源：外部 `sdk测试` 工作区的
  `web/test_web_element_{get_html,get_value,set_value}.py`。
- 原始输出：该工作区 `web/evidence/artifacts/element_{get_html,get_value,set_value}_20260920.txt`。
- 详细证据同目录 `web/evidence/{get_html,get_value,set_value}.md`（含用例表、期望值来源、边界与修订记录）。
- 三个 API 的操作均由产品负责人**亲自复跑确认**（`get_value` 两次、17/17，退出码 0）。

## 本轮要写进公开文档的要点（摘要）

- **`get_html`**：范围是元素自身 `outerHTML`（不是整页）；属性按 **DOM 解析顺序**序列化，
  不是元素库捕获顺序；属性值中的 `&` 在返回串里是 `&amp;`。
- **`get_value`**：读的是 **DOM property**，不是 HTML `value` 内容属性；
  **空字符串 `""` 与 `None` 语义不同**（`""`=内容为空，`None`=没有 `value` property）；
  `input[type=range]` 初始值为 `"0"`；`get_attribute("value")` 不可作内容属性对照。
- **`set_value`**：**只写 property，不聚焦、不触发 `input`/`change` 事件**，因此受控框架
  （React/Ant）状态不更新、页面校验与提交读不到该值——需要页面感知时改用 `input()`；
  **覆盖而非追加**；`<input>` 去换行、`<textarea>` 保留；传 `None` 写入字符串 `"None"`（不是清空）；
  非输入元素上调用不报错，只产生不进入 DOM 的临时属性。

## 需要产品侧知晓的遗留缺口

1. **产品侧持久化脚本本轮未更新**：`tests/SDK/web/test_web_element_{get_html,get_value,set_value}.py`
   仍指向已退役的本机靶场地址（`http://localhost:7199/form-controls`）与旧元素库
   `tests/SDK/web/web测试元素库`，**不能复现本包的结果**。是否把外部工作区的脚本移植进产品仓库
   （涉及元素库归属与仓库相对路径约定）需单独决定；本包不包含脚本。
2. **`get_value` 的旧证据把返回注解记成 `str`**，与源码 `str | None` 不符；本包已在证据第 5 节
   写明订正记录。
3. **只读 / 禁用控件的 `set_value` 行为未实测**：元素库 `260902_web元素` 中没有对应库元素，
   需先采集才能覆盖；证据里如实列为明确排除项。

## 边界

- 本包只含文档与证据文本，**不含任何可执行改动**，不触碰 `sdk/src/`、`runtime/`、`chrome/`。
- 文本内不包含开发机绝对路径；元素库位置以 `--library <目录>` 参数表述。
