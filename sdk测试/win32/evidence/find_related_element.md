# `Win32Element.find_related_element()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.find_related_element"
lifecycle: "VERIFIED"
verification_date: "2026-09-09"
verification_summary:
  passed: 16
  total: 16
  elapsed_ms: 1780.7
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  necessary_cleanup: "PASS"
  foreground_restore: "未恢复；non-interactive模式警告，不等待人工"
persistent_script:
  path: "win32/test_win32_find_related_element.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "996d6bc3ff8c78bb104227af0ac97f39cfbc6f0ec7acf3526c28f1ca655a787a"
  command: 'uv run .\win32\test_win32_find_related_element.py --non-interactive'
```

## API 与测试场景

```python
related = element.find_related_element(selector, timeout=20)
```

selector必填，接受元素名称字符串或Win32 Selector，可按位置或关键字传入。
timeout仅限关键字，默认20秒；0为单次查询，正数为有限超时。本轮None和数字字符串
亦成功；负数和非数字值被InvalidParamsError拒绝。

先从当前Package解析唯一的已保存Win32目标，再在调用元素的子树中定位该目标。
成功返回Win32Element；Package不存在目标或目标位于调用元素子树之外时，返回路径表现为
抛出ElementNotFoundError。不是在整棵窗口树中任意搜索，也不接受已有Win32Element作为selector。

前置：UIAutoma dev及Win32靶场运行，启用 `D:\code\元素库\260902_win元素`。
脚本自动激活表单页，以 `win32靶场_表单控件_表单面板` 查找姓名输入框、保存按钮。
再从姓名输入框查找同级保存按钮，以验证子树范围限制。

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_find_related_element.py --non-interactive
```

## 本轮覆盖

| 场景 | 观察 | 结果 |
| --- | --- | --- |
| 合同、Package与来源元素 | 公开签名正确，取得对应Runtime元素 | PASS |
| 名称及默认超时 | 面板下返回姓名输入框 | PASS |
| Selector及零超时 | 返回姓名输入框 | PASS |
| 关键字及timeout=2 | 返回保存按钮 | PASS |
| timeout=None、'0.5' | 返回姓名输入框 | PASS |
| 子树外目标 | 输入框查找同级保存按钮抛ElementNotFoundError | PASS |
| Package缺失目标 | 抛ElementNotFoundError | PASS |
| 非法selector | 列表、整数、字典、None被InvalidParamsError拒绝（脚本分组检查） | PASS |
| Win32Element、Web Selector | 均被InvalidParamsError拒绝 | PASS |
| timeout位置传参 | TypeError | PASS |
| 负数/非数字timeout | InvalidParamsError | PASS |
| 资源清理 | 鼠标恢复、Package释放，靶场保持运行 | PASS |

返回对象具有Runtime元素身份，relation为find_related，source_element_id与目标记录一致：

- 姓名输入框：`df849752-32d7-46a0-9bec-7bcd6d0d7d7d`。
- 保存按钮：`377c3a69-95ec-4c3c-b803-2813d8519569`。

汇总16/16通过，总耗时1780.7ms，退出码0。成功查询用例耗时约56.1–66.6ms。
焦点恢复目标为原终端窗口131974，SetForegroundWindow返回False，前台留在靶场2951616。
按照已同意的自动模式规则，焦点未恢复单独记录警告，不表示自动恢复成功，也不阻塞后续测试。

## 验证范围

名称均唯一，未构造重复项，未验证AmbiguousElementError。
未验证查询过程中销毁控件、跨进程子树或动态出现/消失。正数超时针对已存在目标，
不代表已确认完整超时等待时长。测试只读查询，但准备阶段会切换表单页，结束保留该页。
