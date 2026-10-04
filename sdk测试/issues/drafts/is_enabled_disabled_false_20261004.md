# Issue 草稿：WebElement.is_enabled 将 disabled="false" 的原生输入框误判为启用

状态：本地草稿，尚未发布。

## 环境与结果

- worktree：`D:\code\desktop`
- commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`；Chrome / dev Runtime
- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)
- 元素库：`D:\code\元素库\260902_web元素`
- 元素：`web靶场_表单测试_原生_输入框`，DOM ID `form-controls-native-text`
- 正式验收连续三轮，每轮 8 PASS / 1 FAIL，资源清理均 PASS。

## 最小复现

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\issues\drafts\repro_is_enabled_disabled_false_20261004.py
```

脚本打开现有靶场的新标签页，连接元素库副本，定位原生输入框，通过 DOM 设置 `disabled="false"`，读取 DOM IDL 与 `is_enabled()`，最后恢复属性、关闭测试标签页与连接、删除副本。

实测：

```json
{"attribute":"false","dom_disabled":true,"expected_is_enabled":false,"actual_is_enabled":true}
```

期望：`is_enabled()` 返回 False。HTML 布尔属性由是否存在决定，false 字符串不是关闭属性；应移除属性才能表达 False。依据：[HTML Standard，Boolean attributes](https://html.spec.whatwg.org/multipage/common-microsyntaxes.html#boolean-attributes)。

## 源码线索（仅限上述快照）

`sdk/src/uiautoma/web/element.py:866` → `RawWebElement._read_state("is_enabled")` → `web.is_enabled` → Page Engine。

`chrome/engine/engine_packages/page_engine_runtime.js:2787` 使用：

```javascript
const unavailable = disabled != null ? disabled !== "false"
```

因此属性字符串恰好为 false 被当成可用。本次旧问题 disabled 空串已通过，剩余失败不能被记作全部修复。历史相关 Issue：[23](https://github.com/uiautoma/desktop/issues/23)，本草稿未查询其最新状态。

## 回归建议与证据

分别验证原生 disabled 属性缺失、空串、disabled、false，以及动态设置/移除属性；同时保留 aria-disabled 的字符串语义。不要把两类属性共用同一布尔解析规则。

[正式证据](../../web/evidence/element_is_enabled_20261004.md)；[第 1 轮](../../web/evidence/artifacts/element_is_enabled_20261004_run1.txt)、[第 2 轮](../../web/evidence/artifacts/element_is_enabled_20261004_run2.txt)、[第 3 轮](../../web/evidence/artifacts/element_is_enabled_20261004_run3.txt)。

本测试工作区只归档复现和证据，没有修改产品源码。
