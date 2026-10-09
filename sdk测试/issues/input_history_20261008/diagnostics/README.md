# 已执行探针

`six_modes_probe.py` 为六项定位/输入/提交对照，`matrix_probe.py` 为正式化之前的 60 项语义探针，均后台执行且清理标签 2→2。当前正式 runner 在 `web/test_web_element_input.py`。

若阅读或复现，请先复制到忽略的 `.pytest_tmp` 目录；六项探针以自身目录生成库副本，不能在归档目录直接运行。矩阵探针使用测试工作区绝对路径和本轮冻结合同，不是额外公开 API 测试入口。

准备诊断：第一次 uv 因默认缓存目录无写入权限停止；改用工作区临时缓存。随后默认沙箱内 SDK Named Pipe 连接失败（HostUnavailableError），而同一探针在获得本机 IPC 访问权限后成功，排除 UIAutoma 未启动。失败准备阶段未创建测试页面或修改表单；六项成功 JSON 和矩阵完整输出保存在 web/evidence/artifacts。
