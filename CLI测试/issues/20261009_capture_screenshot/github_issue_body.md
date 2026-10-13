## 问题与预期行为

`uia capture web` 从 iframe / Open Shadow DOM 中捕获输入框时，截图正确性依赖可选的高亮预览：`--no-highlight` 会截到遮挡浏览器的其它窗口；默认参数虽然能激活浏览器，但返回后不恢复窗口层级。目标已经滚出视口时，默认参数也没有滚动目标，最终没有生成 PNG，却仍返回提交成功和截图路径。

用户期望的完整流程是：**记录原窗口状态 → 临时将正确浏览器窗口置于前台 → 将目标元素及必要的 iframe 置于可见位置 → 等待布局稳定并截图 → 无论成功或失败都恢复浏览器原来的层级**。关闭红框不应影响截图准备。

## 被测版本

- Windows，本机 Chrome；UIAutoma Runtime `0.1.1`，`uia 0.1.1`。
- Desktop main：`7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。
- rust_uia main：`b700f9238134f57da83ab478a5ee55337ade1082`。
- 实际 CLI：`D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe`。
- CLI SHA-256：`C4CC52C93DAC523F354C8BAE6B08DA412E6B16E5FA8D2B14917B233A624FCCB8`。版本号和源码 HEAD 不单独作为二进制构建来源的证明。
- 页面：<https://baobaomi900901.github.io/xpath/#/iframe-shadow-form>。
- 受控目标：右侧原生 HTML 表单的“文本输入框”，`input#form-controls-native-text`，placeholder 为“请输入文本”。原始示例的 ant 和原生截图均出现遮挡，完整受控矩阵针对原生输入框。

## 复现步骤

1. 启动 Runtime，准备一个已初始化的空测试元素库。以下 `PAGE`、`SESSION`、`SNAPSHOT`、`REF`、`OCCLUDER_HWND` 均使用本次 CLI 返回值；不要复用过期观察引用。
2. 用 `browser open --url https://baobaomi900901.github.io/xpath/#/iframe-shadow-form` 打开页面，取得 `PAGE`。
3. 用 `observe web open --page PAGE` 获取语义树和观察身份。树中有两个 `textbox "请输入文本"`；用 `observe web details --session SESSION --snapshot SNAPSHOT --ref REF --no-highlight` 核对 `id=form-controls-native-text`。
4. 用 `package open --path <测试元素库绝对路径>` 打开目标库。
5. 用 `windows list --process-name UIAutoma.exe` 获取遮挡窗口，并执行 `windows activate --hwnd OCCLUDER_HWND`，确保窗口覆盖右侧输入框。
6. 运行下述捕获命令，查看 PNG；再次激活遮挡窗口，只去掉 `--no-highlight` 并换一个名称，观察截图及命令返回后的窗口层级。

```powershell
& $uia capture web --session $session --snapshot $snapshot --ref $ref `
  --package $library --name "原生_无预览" --no-highlight

# 再次激活同一遮挡窗口，然后对比默认参数。
& $uia windows activate --hwnd $occluderHwnd
& $uia capture web --session $session --snapshot $snapshot --ref $ref `
  --package $library --name "原生_默认预览"
```

7. 离屏复现：先通过 `web run-code --page PAGE --file <UTF-8代码文件>` 执行以下函数，把页面各文档滚至底部，然后使用当前有效观察中的原生输入框引用进行默认捕获。此次只是滚动，没有导航或刷新；也可重新观察并再次核对 ID。

```javascript
async page => {
  for (const frame of page.frames()) {
    await frame.evaluate(() => window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: 'instant'
    }));
  }
  return true;
}
```

8. 检查元素是否被滚回视口、返回的 PNG 路径是否真实存在、前台窗口和相对层级是否恢复。完成后关闭本次观察。

每次使用独立名称，避免重复写入或同名冲突。提交结果未知时应先检查目录，不能盲目重放捕获。

## 两轮实测结果

同一页面、同一输入框、同一 UIAutoma 遮挡窗口，每组执行两轮，共六次捕获。原生前台 HWND 和窗口相对层级以约 10 ms 间隔只读采样；控制和捕获使用 CLI。

| 场景 | 实际结果 | 次数 |
| --- | --- | --- |
| 目标可见，`--no-highlight` | 未观察到 Chrome 进入前台；PNG 实际显示 UIAutoma 元素列表，而非网页输入框 | 2/2 |
| 目标可见，默认参数 | PNG 正确显示“文本输入框 / 请输入文本”；前台由 UIAutoma 变为 Chrome，浏览器与遮挡窗口的相对顺序反转，返回后没有恢复 | 2/2 |
| 目标离屏，默认参数 | Chrome 进入前台，但目标仍在视口外；PNG 没有生成；仍返回 `committed=true` 和 PNG 相对路径；窗口层级同样没有恢复 | 2/2 |

可见时顶层视口 CSS 边框为 `{x:1181,y:445,width:1033,height:32}`，视口 `2326×1172`。离屏时 iframe 文档 `scrollY=1080`，目标边框 `y=-635`；捕获前后的滚动值、边框和不可见状态完全相同。

六次 CLI 捕获均退出 0，`committed=true, commit_unknown=false`；定位库中有六项快照，但只生成四张 PNG。四张已生成 PNG 均目视确认，离屏场景的两张 PNG 确认不存在。`committed` 证明定位资产已提交，不能证明截图存在或内容正确。

其中一次离屏响应为：

```json
{
  "command": "capture web",
  "ok": true,
  "data": {
    "committed": true,
    "commit_unknown": false,
    "element_id": "bef4a1a8-308c-40da-98f2-7e08715cae38",
    "element_name": "round-1-offscreen-default",
    "kind": "web",
    "highlighted": true,
    "highlight_count": 1,
    "snapshot_path_rel": "./snapshot/bef4a1a8-308c-40da-98f2-7e08715cae38.json",
    "screenshot_path_rel": "./screenshot/bef4a1a8-308c-40da-98f2-7e08715cae38.png"
  }
}
```

该 `screenshot_path_rel` 对应文件实际不存在。

## 源码链路

- [CLI 参数说明](https://github.com/uiautoma/desktop/blob/7f148f27c0efa8bbba1f18d86c14845ea7d639fa/cli/command/src/main.rs#L188)将 `--no-highlight` 描述为关闭红框；[参数映射](https://github.com/uiautoma/desktop/blob/7f148f27c0efa8bbba1f18d86c14845ea7d639fa/cli/command/src/main.rs#L777)仅传 `highlight=false`。
- [Runtime 入库](https://github.com/uiautoma/desktop/blob/7f148f27c0efa8bbba1f18d86c14845ea7d639fa/runtime/services/pipe_server.py#L649)只在 `highlight=true` 时执行预览；实际捕获和提交没有独立的窗口前置保证，也没有恢复窗口状态的外层守卫。
- [Provider 观察高亮](https://github.com/ha0018/rust_uia/blob/b700f9238134f57da83ab478a5ee55337ade1082/src/main.rs#L6050)调用原生 `activate_window`，而[普通引用捕获](https://github.com/ha0018/rust_uia/blob/b700f9238134f57da83ab478a5ee55337ade1082/src/main.rs#L5897)读取几何和截图上下文，没有独立激活/恢复。
- [浏览器引用捕获](https://github.com/uiautoma/desktop/blob/7f148f27c0efa8bbba1f18d86c14845ea7d639fa/chrome/engine/playwright/observation_sessions.mjs#L272)会 `page.bringToFront()`；本机实测不能把它当成 Windows 原生窗口前台保证。
- [DOM 捕获](https://github.com/uiautoma/desktop/blob/7f148f27c0efa8bbba1f18d86c14845ea7d639fa/chrome/engine/playwright/capture_observation.mjs#L78)读取 `boundingBox()`，未先保证目标滚入视口。
- [PNG 实现](https://github.com/ha0018/rust_uia/blob/b700f9238134f57da83ab478a5ee55337ade1082/src/element_library_store.rs#L3290)使用桌面 `GetDC(NULL)` 和 `BitBlt`，会包含其它窗口遮挡；蓝框是在取得像素后绘制，不能证明底图来自浏览器。
- [截图不可用分支](https://github.com/ha0018/rust_uia/blob/b700f9238134f57da83ab478a5ee55337ade1082/src/element_library_store.rs#L1128)仍保存快照和目录记录，CLI 公共响应没有清楚表达截图缺失。

[现有 README](https://github.com/uiautoma/desktop/blob/7f148f27c0efa8bbba1f18d86c14845ea7d639fa/cli/README.md#L1252)明确把原生激活归为预览，`--no-highlight` 关闭这层预览。当前行为符合这段说明，但不满足上述用户要求的截图合同；去掉参数不能解决离屏和层级恢复问题。

相关验收跟踪：#50。该单已将 Web 屏幕截图包含遮挡物列为既有边界。本单具体记录 CLI 引用捕获的复现结果，并提出本次用户明确要求的截图保障流程，包含窗口层级恢复、离屏滚动和 PNG 可用性。

## 建议与验收

- [ ] 截图准备与红框预览分离；默认及 `--no-highlight` 都能拍到无遮挡的正确目标。
- [ ] 目标及必要 iframe 祖先滚动到可见位置，等待布局稳定，再读取最新几何并截图。
- [ ] 在任何激活前保存窗口状态，成功、失败和超时后均恢复原前台、浏览器层级、topmost/最小化状态；只重新激活原前台窗口不足以保证原层级。
- [ ] 显式表达 PNG 是否生成，避免不存在的截图路径被当成完整截图成功；已提交资产不得自动重放保存。
- [ ] 回归覆盖普通遮挡、离屏、最小化、iframe/Shadow DOM、多个浏览器窗口，以及截图/提交失败和超时后的恢复。

受控测试针对本机 Chrome；未声称已验证 Edge、多显示器或全部窗口组合。产品源码未修改。复现脚本、逐次 CLI 输出、前台/层级采样和截图保存在测试工作区 `CLI测试/issues/20261009_capture_screenshot/`；本 Issue 已包含可独立复现的步骤和关键数据，不依赖访问该本地目录。
