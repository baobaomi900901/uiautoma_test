# 顶层 `uiautoma.win32.find_all()` 验证证据

```yaml
api: "uiautoma.win32.find_all"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  passed: 20
  failed: 1
  total: 21
  elapsed_ms: 14820.3
  exit_code: 1
  full_log_provided: true
  necessary_cleanup: "PASS"
  foreground_restored: true
  observed_multi_match_count: 140
issue: "https://github.com/uiautoma/desktop/issues/54"
issue_evidence: "https://github.com/uiautoma/desktop/issues/54#issuecomment-5598792600"
persistent_script:
  path: "win32/test_win32_module_find_all.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "9563e1eeebf2b80e3703ebbb2b1d166024fb007b8a1b8be8727a3b35af8294da"
  command: 'uv run .\win32\test_win32_module_find_all.py --non-interactive'
```

## 用途与参数

```python
elements = win32.find_all(selector, timeout=20, session=None)
```

查找当前或指定Package中匹配的Win32元素，返回list[Win32Element]，未找到返回[]。
selector必填，支持名称字符串或Win32 Selector，支持位置或关键字；timeout/session
仅限关键字。timeout默认20秒，0单次、正数有限等待、None默认值、数字字符串可转换，
-1无限等待。本轮-1只用于已存在目标。

显式session=公开Package本轮失败，不能视为该分支已通过；默认上下文和None成功。

## 运行场景

在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_module_find_all.py --non-interactive
```

dev及Win32靶场运行，启用 `D:\code\元素库\260902_win元素`。
先切换表单页，使用姓名输入框和保存按钮测试单项列表、参数规则及上下文。
随后切换表格页，要求第1页含“1”和“用户1”，使用：

- win32靶场_表格数据_list首个单元格
- win32靶场_表格数据_list普通单元格
- win32靶场_表格数据_list普通单元格_相似元素

前两个唯一定位作为参照，相似选择器通过名称和Selector分别查找多项，检查RuntimeId
不重复且包含两个参照元素。逐项读取文本供诊断，不固定结果总数。

## 本轮结果

| 场景 | 结果 |
| --- | --- |
| 合同、当前Package、Selector准备 | PASS |
| 名称默认、Selector零超时、名称关键字 | PASS，单项列表身份与边界正确 |
| 显式None上下文 | PASS |
| 显式Package上下文 | FAIL，InvalidParamsError |
| None、数字字符串、-1超时 | PASS，已有目标定位成功 |
| 不存在名称，timeout=0和0.3 | PASS，均返回[]；有限等待400.8ms |
| 非法selector/Web Selector/session/timeout/传参 | PASS |
| 表格页参照 | PASS，“1”和“用户1”分别定位到不同单元格 |
| 名称多项命中 | PASS，140项，RuntimeId互异且含参照元素 |
| Selector多项命中 | PASS，140项，RuntimeId互异且含参照元素 |
| 清理 | PASS，鼠标恢复、Package释放、靶场保留表格页 |

第07/21项实际错误：

```text
session 必须是由 uiautoma.open() 或 uiautoma.current() 返回的对象
异常: InvalidParamsError
```

传入对象确为current()返回的Package。默认上下文对同一Selector能成功，符合Issue #54
记录的公共对象与内部会话校验不匹配问题。整体20/21通过、14820.3ms、退出码1，保持
READY_FOR_LIVE，不以其他场景通过抵消该失败。

多项结果前10项文本均为：1、用户1、产品部、上海、离职、user1@example.com、
2024-02-02、2、用户2、市场部。两项耗时6634.4ms及6338.1ms包含逐项读取RuntimeId和
文本，不能用来宣称find_all本身耗时6秒。140是本轮观察值，不固定为API合同。

原终端68608恢复前前台为靶场331172，SetForegroundWindow返回True，约20.9ms后核验
切回原终端。清理通过，未关闭靶场。

## 缺陷与覆盖边界

已将该API实际失败追加到 [Issue #54](https://github.com/uiautoma/desktop/issues/54#issuecomment-5598792600)。
修复后需复测显式公开Package，同时保留单项、空列表和多项场景。
目前未通过独立原生表格枚举证明140项是所有应返回项，也未逐项断言全部文本顺序；
已经验证的是多项、不重复及指定参照包含关系。未覆盖跨页、动态出现/销毁、多Package隔离。
本次产品代码未修改。
