# 顶层 `uiautoma.win32.find()` 验证证据

```yaml
api: "uiautoma.win32.find"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  passed: 16
  failed: 1
  total: 17
  elapsed_ms: 1796.0
  exit_code: 1
  full_log_provided: true
  necessary_cleanup: "PASS"
  foreground_restore: "未恢复；自动模式警告"
issue: "https://github.com/uiautoma/desktop/issues/54"
persistent_script:
  path: "win32/test_win32_module_find.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "84eca879f1e3ddc2772eb2ebbacc58878d98adeef2c92acb933db546a320782a"
  command: 'uv run .\win32\test_win32_module_find.py --non-interactive'
```

## 用途与参数

```python
element = win32.find(selector, timeout=20, session=None)
```

直接从当前或指定Package查找唯一的Win32元素，无需先取得窗口。
selector必填，支持名称字符串或Win32 Selector，可位置/关键字传入。
timeout和session仅限关键字。返回Win32Element；未找到抛ElementNotFoundError，
多项命中应抛AmbiguousElementError（本轮未构造该场景）。

timeout=0单次、正数有限等待、None默认20秒，支持数字字符串及-1无限值。
本轮-1仅用于已经存在的目标，不验证无限等待后出现。

session省略或None的路径成功；显式传入current()返回的Package路径失败，
不能把该分支描述为已支持并通过验收。

## 运行场景

dev与Win32靶场运行，启用 `D:\code\元素库\260902_win元素`。
脚本切换表单页，查找姓名输入框及保存按钮，核对返回类型、来源ID、名称和有效实时边界。
在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_module_find.py --non-interactive
```

## 本轮结果

| 场景 | 结果 |
| --- | --- |
| 合同与准备 | PASS，显式session类型为Package |
| 名称默认调用 | PASS，返回姓名输入框 |
| Selector零超时 | PASS，返回姓名输入框 |
| 名称关键字、timeout=2 | PASS，返回保存按钮 |
| 显式session=None | PASS |
| 显式session=package | FAIL，InvalidParamsError |
| None超时、数字字符串、无限值已有目标 | PASS |
| 不存在名称 | PASS，ElementNotFoundError |
| None/整数/列表/字典selector及Web Selector | PASS，InvalidParamsError |
| 无效session对象 | PASS，InvalidParamsError |
| 非法timeout | PASS，InvalidParamsError |
| 缺参、多余位置参数和未知关键字 | PASS，TypeError |
| 必要清理 | PASS，鼠标恢复、Package释放；靶场保留表单页 |

第07/17项错误：

```text
session 必须是由 uiautoma.open() 或 uiautoma.current() 返回的对象
异常: InvalidParamsError
```

传入对象恰为current()返回的公开Package，未使用内部字段。对照调用在默认上下文下成功，
说明本次不是目标元素缺失。姓名输入框来源ID为df849752-32d7-46a0-9bec-7bcd6d0d7d7d，
边界(1547,725,430,30)；保存按钮来源ID为377c3a69-95ec-4c3c-b803-2813d8519569，
边界(1763,1266,92,32)。这些数值仅为当时观察，不是固定测试条件。

汇总16/17通过，总耗时1796.0ms，退出码1，保持READY_FOR_LIVE。
原终端68608未恢复，前台留在靶场331172，按自动模式记录警告，与session入参失败无关。

## 缺陷及验收边界

[Issue #54](https://github.com/uiautoma/desktop/issues/54) 已提交。
`_package_session()` 用win_elements特征校验内部会话，而公开Package不具备该方法，
造成显式公开对象被拒绝。修复应接收公开Package并使用其上下文，不要求用户传私有字段。

未覆盖多项命中、动态销毁/出现、多个Package之间的隔离。find_all使用同一辅助函数，
需要开发检查直接影响，但此文档不将其计作已实测失败。产品源码未修改。
