# is_enabled 历史归档（2026-10-08）

当前唯一测试入口是 [web/test_web_element_is_enabled.py](../../web/test_web_element_is_enabled.py)，不含日期，使用 keys-click-test 的用户指定两个按钮。

- `test_web_element_is_enabled.py`：2026-08-09 的旧版输入框运行器，只留历史源码，不再作为入口。
- `test_web_element_is_enabled_20261004.py`：2026-10-04 通用运行器包装脚本，原始 import/合同对应当时快照，不作为当前运行入口。
- `is_enabled_20260809.md`：迁移前的历史证据原文，内部产品仓库路径和命令只代表当时环境。

2026-10-04 的证据与原始日志继续保留在 web/evidence 中，并加上当前入口提示；合同 JSON 和原始日志中的旧脚本名是历史数据，不进行改写。

[当前验收证据](../../web/evidence/is_enabled.md)：2026-10-08，三轮每轮 30/32 PASS、2 FAIL，READY_FOR_LIVE。
