# WebBrowser Cookie 方法 partition_key 字符串文档与实现不一致

状态：本地 Issue 交接稿，尚未提交到产品仓库。

## 源码快照

只读 worktree `D:\code\desktop`，commit `cb9332d1a04c09e04df54af958e028b2bc45af9b`。
涉及 `WebBrowser.get_cookies`、`remove_cookie`、`clear_cookies`。
本稿限于这三个页面对象方法，不把结果推广到顶层函数。

三个 docstring 都说明 `partition_key` 可以传“顶层站点网址字符串”或字典。
实际均调用 `sdk/src/uiautoma/web/__init__.py:184` 的 `_normalize_cookie_partition_key`：

```python
if not isinstance(partition_key, Mapping):
    raise TypeError("partition_key must be a mapping")
```

后台补充探针对三个方法分别传 `"https://baobaomi900901.github.io"`，均得到上述 TypeError，在进入 Cookie RPC 前拒绝。
因此当前只验证字典分区的正向行为，不能在公开文档中宣称字符串已通过。

## 最小复现

对已获取的 WebBrowser 对象分别调用：

```python
page.get_cookies(partition_key="https://baobaomi900901.github.io")
page.remove_cookie("本次随机名称", partition_key="https://baobaomi900901.github.io")
page.clear_cookies(partition_key="https://baobaomi900901.github.io")
```

当前三个方法均会在规范化处抛 TypeError；不存在真实批量清理副作用。
字典方式在真实第一方 Partitioned Cookie 上已通过，例如：

```python
partition = {
    "top_level_site": "https://baobaomi900901.github.io",
    "has_cross_site_ancestor": False,
}
```

产品侧需决定支持字符串还是修正文档，并统一三个方法合同。测试侧不修改产品源码。

## 材料与范围

- [冻结 docstring、规范化函数与完整源码链路](../../../web/browser_cookie_contracts_20261006.json)
- [行为探针原始输出](../../../web/evidence/artifacts/browser_cookie_probe_20261006.txt)
- [三个方法的后台字符串分区探针](../../../web/evidence/artifacts/browser_cookie_partition_strings_20261006.txt)
- [get_cookies 证据](../../../web/evidence/browser_get_cookies.md)
- [remove_cookie 证据](../../../web/evidence/browser_remove_cookie.md)
- [clear_cookies 证据](../../../web/evidence/browser_clear_cookies.md)

未验证跨站祖先为 True 的正向分区环境；默认未分区与第一方字典分区的三轮结果详见上述证据。
