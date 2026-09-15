# `uiautoma.web.reset_user_environment()` 初次测试

## 用途

取消指定浏览器的用户环境选择，恢复后续网页获取和打开操作的默认环境；不关闭已打开网页，也不删除 Profile 数据。

## 真实验收结果

**VERIFIED：7/7 通过，退出码 0。**

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`mode` 为唯一位置参数，返回 `None` |
| 无已选环境 | 通过，重置安全返回 `None` |
| 选择后重置 | 通过，选择 `Default` 后成功恢复 |
| `auto` 重置 | 通过 |
| 非法模式 | 通过，`InvalidParamsError` 正确拒绝 |
| 参数边界 | 通过，多余位置参数被 `TypeError` 拒绝 |
| 资源恢复 | 通过，默认浏览器环境选择已恢复 |

测试脚本：`web/test_web_reset_user_environment.py`
