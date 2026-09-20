# Issue #64：WebElement.find / find_all 失败原因——详细版

## 结论

本轮失败定位到“**元素作用域中的保存选择器查询，其执行上下文与保存路径起点不一致**”。

`root` 已经位于 iframe 内，但保存的定位路线仍从外层页面的 iframe 节点开始。当前源码根据 `root_ref.frame_id` 把命令直接送进 iframe，却没有同步调整保存路径。引擎随后在这个 iframe 的 document 中，从头寻找属于外层文档的 iframe 节点，得到未命中。

这属于 Runtime／浏览器路由／定位引擎组合层的实现问题。SDK 的两个公开方法共用这条查找链路，因此受到同一问题影响。

证据强度需要区分：**真实输出已证实该组合不能正确命中；源码和实际函数的离线复核已证实上下文错配机制。** 本轮没有为正在运行的 Chrome／Runtime 插桩，不能把离线示例的 frameId 或具体失败层号写成现场抓到的数据。

## 资料与源码范围

- [Issue #64](https://github.com/uiautoma/desktop/issues/64) 及其现有评论；读取时为 OPEN。
- 用户本次附件：`find_all_form.py` 为 **25/32，7 项失败，33974.1ms**；`find_form.py` 为 **11/13，2 项失败**。
- 同一轮协作中已有 CSS/XPath 对照：[CSS 单项 38/38](../../web/evidence/element_find_by_css.md)、[CSS 全量 39/39](../../web/evidence/element_find_all_by_css.md)、[XPath 单项 40/40](../../web/evidence/element_find_by_xpath.md)、[XPath 全量 41/41](../../web/evidence/element_find_all_by_xpath.md)。
- 只读源码检出：`D:\code\desktop`，HEAD `c101caa9dcd115a461fc71ecaed351b0dea880b8`。本报告引用的 SDK、Runtime、桥接及引擎源文件与该 commit 没有工作区差异。
- 日志中 SDK 来自 `D:\code\desktop\sdk\src\uiautoma\__init__.py`。运行中的 Runtime／浏览器载入包版本未由本次日志独立证明。
- 分析日期：2026-09-19。没有修改产品源码、测试脚本或 GitHub Issue。

## 一、日志已经排除了什么

| 证据 | 本轮事实 | 能说明什么 |
| --- | --- | --- |
| 元素库准备 | 四个输入框、开关、相似元素库项都存在 | 不是名称根本不在库里 |
| 动态 ID | aria-checked=false，未点击 | 本轮动态 ID 已关闭 |
| 页面级定位 | 文本、密码、邮箱、数字框都取得正确节点 | 保存选择器从页面级入口可以命中 |
| 密码节点核对 | 命中包装 span，且其中包含正确的密码 input | 已纠正“把包装节点当成 input”的旧测试判据 |
| 共同容器 | 四条父级链都到达 #shadow-form-content | 目标与用于查找的根容器关系成立 |
| 独立 DOM | 四个 input 各 1 项，Ant 单选标签为男／女／其他 | DOM 中确实存在应返回的目标 |
| 直接 CSS／相对 XPath | 四个对应 API 已通过实测 | iframe 内节点、当前根引用和基本子树查询可用 |
| 清理 | 页面和 Package 的 close() 成功，副本删除 | 此轮失败发生在查询阶段；不是清理失败造成的退出码 |

`find_all()` 的七个失败：

| 场景 | 期望 | 实际 | 耗时 |
| --- | --- | --- | --- |
| 文本框名称 | 1 项 | [] | 5002.3ms |
| 密码框名称 | 1 个包装 span | [] | 5001.2ms |
| 邮箱框名称 | 1 项 | [] | 5001.7ms |
| 数字框名称 | 1 项 | [] | 5001.9ms |
| Selector 对象 | 1 项 | [] | 5003.1ms |
| 已存在目标、timeout=0 | 1 项 | [] | 6.9ms |
| 相似单选标签 | 3 项 | [] | 5001.9ms |

其中六项都已经等满约 5 秒。延长等待只会让相同的错误起点查询重复更久，不能修正路径上下文。

25 个通过项也不能证明核心查询可用：如果保存选择器查询总是返回空列表，本来就期望空列表的负向用例仍可能通过。正向用例和独立 DOM 对照才是这次定性的关键。

## 二、保存选择器里存了什么

以文本输入框快照 `ef82d0d4-5b13-481b-ae99-adc203f2417d.json` 为例，当前激活的是结构化 `path`，`xpath.enabled=false`。

对该实际快照调用仓库的真实 `compileSelectorPathPlan()`，得到三段：

```text
iframe:
  //iframe[contains(@src,'/xpath/#/iframe-shadow-form-content')]
shadow_host:
  //div[@id='form-shadow-host']
target:
  //input[@type='text'][@class='ant-input css-mncuj7 ant-input-outlined'][@placeholder='请输入文本']
```

这条路线的第一段属于外层 document，后两段属于 iframe 里的 document／Shadow DOM。它不是一个已经相对于 `#shadow-form-content` 的简单子元素条件。

快照里虽然还记录过带随机后缀的旧 id，但这次真实编译出的目标表达式没有使用该旧 id。不能仅看到快照中的随机值，就把本次错误归因于动态 ID。

## 三、源码调用链中的错配

### 1. 名称和 Selector 都会变成保存选择器查询

名称产生 `{type: "saved", name: ...}`；Selector 对象产生 `{type: "saved", element_id: ...}`。后者只是改用库项 ID 查记录，不会自动把保存路径转换成相对路径。[源码：_saved_query](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/sdk/src/uiautoma/web/element.py#L1145)

元素级调用会携带 `root_element_id`；页面级调用携带 `page_ref`，不带这个 root。两者最终都进入 `web.element.find_all` RPC。[元素级入口](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/sdk/src/uiautoma/web/element.py#L73)、[页面级入口](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/sdk/src/uiautoma/web/browser.py#L608)、[RPC 入口](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/sdk/src/uiautoma/_core/client.py#L2650)

### 2. Runtime 同时保留 root 引用和完整保存路径

`web_element_find_all()` 从 root 的运行时上下文取出 `element_ref` 作为 `root_ref`。对于 saved 查询，它解析库项、生成 descriptor，再设置 `scope_to_root=True`。[源码](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/runtime/services/action_service.py#L2627)

`_web_descriptor()` 复制的是完整的 `snapshot["path"]`。后续选择器参数和桥接命令继续携带这条路径，没有在这些位置按 root 所在框架裁剪已经经过的外层 iframe 前缀。[descriptor](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/runtime/services/action_service.py#L5365)、[桥接参数](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/runtime/web/bridge_state.py#L2344)

这里清除的 `hostname/page_url` 是查询定位参数，不等于把结构化路径改成“相对于 root 的路径”。

### 3. 浏览器路由先把执行位置切到 root 所在框架

`prepareWebDomOperation()` 的关键分支：

```javascript
const liveRef = cmd && (cmd.element_ref || cmd.root_ref);
if (liveRef) {
  options.world = liveRef.world;
  frameId = Number(liveRef.frame_id);
}
```

操作命令随后通过 `Object.assign({}, cmd, ...)` 保留原命令中的完整路径。[选择 frameId](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/plugin_packages/command_legacy_package.js#L4678)、[保留命令](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/plugin_packages/command_legacy_package.js#L4822)

因此形成：

| 调用 | 执行起点 | 查询内容 | 配合情况 |
| --- | --- | --- | --- |
| page.find(库元素) | 顶层 frame 0 | 从外层 iframe 开始的完整路径 | 路径起点一致 |
| root.find / find_all(库元素) | root 所在 iframe | 仍从外层 iframe 开始的完整路径 | 路径起点错配 |
| root.find_by_css 等 | root 所在 iframe | 对当前 root 的直接 CSS 条件 | 可在正确子树中执行 |
| root.find_by_xpath 等 | root 所在 iframe | 从当前 root 开始的相对表达式 | 可在正确上下文中执行 |

### 4. 引擎从当前 document 重新解释保存路径

`resolveSelectorPath()` 使用：

```javascript
let roots = [document];
```

这里的 document 是执行该命令的 iframe 文档。第一段却仍是外层 document 中的 `//iframe[contains(@src,...)]`。那个承载当前页面的 iframe 元素属于父文档，不是子文档内的节点。

该段无匹配时，函数返回 `element_not_found`；尚未走到正确的内部 Shadow host 和目标 input。[路径解析](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/engine_packages/page_engine_runtime.js#L2842)、[未匹配分支](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/engine_packages/page_engine_runtime.js#L2875)

补充纠正 Issue 描述的一点：`root_ref` 不只是最终的后置过滤。源码在 iframe 路由分支也做 `isWithinLiveRoot(frame, liveRoot)` 检查。因此修复不能只删除最后一道过滤。[iframe 分支](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/engine_packages/page_engine_runtime.js#L2886)

### 5. 底层未匹配被规范化为空列表

引擎的 `action === "find_all"` 分支会保留其它错误，但把 `element_not_found` 视为零匹配，最终返回成功结构中的空 `items`。[源码](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/engine_packages/page_engine_runtime.js#L3441)

这解释了为什么 `find_all()` 没有一个明显的跨框架错误 trace：上层收到的是合法空结果，随后在超时范围内继续重查。

## 四、为什么两个 API 的表现不同

两者不是两套独立查找引擎：

| 公开方法 | 内部模式 | 相同底层结果为 0 项时 |
| --- | --- | --- |
| find_all() | many=True，max_results=0 | 返回 [] |
| find() | many=False，max_results=2 | Runtime 返回 element_not_found，SDK 转成 ElementNotFoundError |

`max_results=0` 表示不限制结果，不是要求返回零个。单项方法用 2 是为了识别歧义，而不是允许返回两项。[SDK 参数](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/sdk/src/uiautoma/_core/client.py#L2660)、[Runtime 零匹配处理](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/runtime/services/action_service.py#L2716)、[异常映射](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/sdk/src/uiautoma/_core/client.py#L2025)

所以“返回 []”和“抛 ElementNotFoundError”是同一个错误未命中结果的两种公开表现。需要修复的是前面的定位过程。

## 五、本次额外做的离线复核

使用真实快照、真实编译器和从源文件提取的 `prepareWebDomOperation()`，替换浏览器依赖后运行：

```text
不带 root_ref：
  frameId = 0
  保存路径原样保留
带 root_ref.frame_id = 7：
  frameId = 7
  保存路径仍原样保留
```

7 是离线示例值，不是此次 Chrome 的实际 frameId。本实验没有打开浏览器，证明的是当前源码会组合出“iframe 执行上下文 + 顶层保存路径”。当前运行服务的实际首个失败层号仍需现场诊断才能确认。

## 六、find_form.py 仍需单独注意的脚本问题

`test_web_element_find_form.py` 仍有 `value.name == name` 断言，拿运行时名称和元素库名称比较。当前引擎的运行时名称来自 `innerText / value / tagName`，不保证等于用户保存的库项名称。[引擎名称来源](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/engine_packages/page_engine_runtime.js#L43)、[测试脚本](../../web/test_web_element_find_form.py)

因此：

- `unique_matches` 只给了聚合失败摘要，无法据本次输出逐一确定三个名称调用的具体失败原因。
- 即使产品问题修复，名称等值断言仍可能产生测试误报，应改成适合实际捕获节点的 DOM 身份校验。
- `selector_object` 已明确在调用时抛 ElementNotFoundError，尚未进入名称断言；这条证据不受上述脚本问题影响。
- 改进后的 `find_all_form.py` 给出了四个名称、Selector、零超时和多项查询的明确空列表结果，是本轮更完整的产品缺陷证据。

## 七、开发侧修复方向与验收边界

建议优先修复保存路径与 root 所属框架的协调，而不是改变 []／ElementNotFoundError 的正常含义。可评估两条实现路线：

1. 保存路径仍从顶层执行，定位成功后按稳定的文档／节点／框架引用核对最终目标确实位于指定 root 内。
2. 验证保存路径与 root 框架关系后，构造正确的框架内查询计划，保留必要的 Shadow 边界与作用域限制。

两条路线都需要防止误匹配同名节点、跨出 root 或把跨框架不支持伪装成空结果。不能简单强制 frameId=0：当前 root 引用与其 document 绑定，换文档可能直接失效。[引用有效性](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/engine_packages/page_engine_runtime.js#L49)。现有跨 iframe 继续路由还会删除 `root_ref`，修改起点时必须同时审视作用域约束如何保留。[路由代码](https://github.com/uiautoma/desktop/blob/c101caa9dcd115a461fc71ecaed351b0dea880b8/chrome/engine/plugin_packages/command_legacy_package.js#L4403)

建议回归覆盖：同文档、iframe 内、仅 open shadow、iframe+shadow；名称与 Selector 两种入参；一个／多个／零个真实匹配；root 外同名节点不能混入；直接 CSS／相对 XPath 已通过的行为不得退化。

本次实测是 iframe+open shadow 的组合，不能外推为“所有 Shadow DOM 查找均不支持”。Issue #64 更准确的范围是：**已保存完整路径与 iframe 内元素作用域组合时的定位问题**。

本报告交付分析，不实施修复、不修改测试预期，也不更新或关闭 Issue。
