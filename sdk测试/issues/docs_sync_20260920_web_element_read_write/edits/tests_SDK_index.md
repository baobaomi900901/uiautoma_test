# `tests/SDK/index.md` 逐行编辑清单

目标文件：`tests/SDK/index.md`（产品仓库，共 216 行，仅 `## Win32` 与 `## Web` 两节）

动作：**替换下面 3 行**，其余内容一律不动。三行都在 `## Web` 表中连续相邻
（当前位于第 46–48 行）。

## 替换 1 —— `get_html`

原文（整行）：

```markdown
| `uiautoma.web.WebElement.get_html()` | `VERIFIED` | [`web/test_web_element_get_html.py`](web/test_web_element_get_html.py) | [`web/evidence/get_html.md`](web/evidence/get_html.md) | [`sdk/docs/web/get_html.md`](../../sdk/docs/web/get_html.md) |
```

改为：

```markdown
| `uiautoma.web.WebElement.get_html()` | `VERIFIED`（17/17；2026-09-20 当前基线复验，连续 3 次退出码 0） | [`web/test_web_element_get_html.py`](web/test_web_element_get_html.py) | [`web/evidence/get_html.md`](web/evidence/get_html.md) | [`sdk/docs/web/get_html.md`](../../sdk/docs/web/get_html.md) |
```

## 替换 2 —— `get_value`

原文（整行）：

```markdown
| `uiautoma.web.WebElement.get_value()` | `VERIFIED` | [`web/test_web_element_get_value.py`](web/test_web_element_get_value.py) | [`web/evidence/get_value.md`](web/evidence/get_value.md) | [`sdk/docs/web/get_value.md`](../../sdk/docs/web/get_value.md) |
```

改为：

```markdown
| `uiautoma.web.WebElement.get_value()` | `VERIFIED`（17/17；2026-09-20 当前基线复验，连续 3 次退出码 0） | [`web/test_web_element_get_value.py`](web/test_web_element_get_value.py) | [`web/evidence/get_value.md`](web/evidence/get_value.md) | [`sdk/docs/web/get_value.md`](../../sdk/docs/web/get_value.md) |
```

## 替换 3 —— `set_value`

原文（整行）：

```markdown
| `uiautoma.web.WebElement.set_value()` | `VERIFIED` | [`web/test_web_element_set_value.py`](web/test_web_element_set_value.py) | [`web/evidence/set_value.md`](web/evidence/set_value.md) | [`sdk/docs/web/set_value.md`](../../sdk/docs/web/set_value.md) |
```

改为：

```markdown
| `uiautoma.web.WebElement.set_value()` | `VERIFIED`（21/21；2026-09-20 当前基线复验，连续 3 次退出码 0） | [`web/test_web_element_set_value.py`](web/test_web_element_set_value.py) | [`web/evidence/set_value.md`](web/evidence/set_value.md) | [`sdk/docs/web/set_value.md`](../../sdk/docs/web/set_value.md) |
```

## 应用后自检

```powershell
cd $ProductRoot
git diff -- tests/SDK/index.md     # 应恰好 3 行被改动
uv run python -m pytest tests/test_uiautoma_documentation_contract.py -q --basetemp .pytest_tmp/docs-sync
```

## 说明

- 三行的「持久化脚本」列仍指向产品仓库内的 `web/test_web_element_*.py`。本轮的运行实际由外部
  `sdk测试` 工作区的同名脚本产生，**产品侧脚本尚未移植**（见交接包 README「遗留缺口」）。
  如果决定移植脚本，这三列需要在同一批里改指新脚本，并同时更新对应证据文件第 6 节。
- 本文件只描述编辑内容，不修改任何文件。
