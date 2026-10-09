# WebElement.input() 双输入框后台测试设计

日期 2026-10-08；唯一入口 [test_web_element_input.py](test_web_element_input.py)，完整合同、矩阵与结果见 [证据](evidence/input.md)。

- 使用用户给定 iframe/open Shadow 表单与元素库，分别核对 Ant/原生库选择器唯一命中。
- 默认 silent_running=True：DOM 输入、默认静默输入、CDP、参数边界、校验成功/失败/重试；手写文本预期由原生 DOM 与真实提交结果双重确认。
- 提交/重置通过现有按钮的 DOM 点击，真实表单处理器保持；仅在自有标签截获剪贴板写入，避免干扰用户电脑。
- 12 项合同/参数 + 环境 1 + 库映射 2 + 两侧各 22 场景 + 清理 1 = 60。
- 清理自有标签与库副本，核对用户标签和源元素库，恢复动态 ID 与 localStorage 基线。
- 系统模拟键盘、IME 和实际鼠标锚点单独等待用户选择；本轮不计入 VERIFIED 范围。
- 旧设计与多入口脚本保留在[历史归档](../issues/input_history_20261008/README.md)，当前只保留一个正式测试脚本。
