# `win32.get_real_resolution()` 验证证据

```yaml
api: "uiautoma.win32.get_real_resolution"
lifecycle: "VERIFIED"
verification_date: "2026-09-10"
verification_summary:
  passed: 7
  total: 7
  elapsed_ms: 2.3
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  virtual_desktop_size: [6000, 1600]
  virtual_desktop_rect: [-2560, 0, 6000, 1600]
persistent_script:
  path: "win32/test_win32_get_real_resolution.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "ced2811d9acf1ab38af15e43fc2b3f2e86b27192597d23d61763e83298d3db6a"
  command: 'uv run .\win32\test_win32_get_real_resolution.py --non-interactive'
```

## 用途与运行

```python
width, height = win32.get_real_resolution()
```

读取当前多显示器虚拟桌面的整体包围宽高，返回正整数元组，无公开参数。
它不是某台显示器支持的最高硬件分辨率，也不返回虚拟桌面的原点。
当前实现直接读取原生虚拟桌面系统指标；测试无需dev、靶场或元素库。

在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_get_real_resolution.py --non-interactive
```

脚本启用Per-Monitor v2，原生枚举显示器并计算包围矩形，与GetSystemMetrics虚拟桌面
指标及SDK返回交叉核验。只读，不调整显示设置。测试期间保持显示配置不变。

## 本轮结果

| 项目 | 实际结果 | 结论 |
| --- | --- | --- |
| API合同 | 无公开参数 | PASS |
| 原生参照 | 各显示器包围矩形与系统虚拟桌面指标一致 | PASS |
| 返回类型 | 正整数元组(6000,1600) | PASS |
| 尺寸一致 | SDK与独立计算的包围宽高一致 | PASS |
| 重复读取 | 连续三次均为(6000,1600) | PASS |
| 参数限制 | 多余位置参数与timeout均TypeError | PASS |
| 清理 | 只读，无新增窗口/文件或待恢复显示设置 | PASS |

副屏边界(-2560,0,2560,1600)，主屏边界(0,0,3440,1440)，整体包围矩形为
(-2560,0,6000,1600)。SDK实际返回(6000,1600)，没有误返回主屏尺寸(3440,1440)。

完整日志及测试者确认：7/7通过，总耗时2.3ms，退出码0。

## 验证范围

本轮验证双屏横向排列、左侧副屏起点为负的配置。不外推为所有DPI感知模式、旋转、
垂直布局或显示配置动态变化均已实测；静态算法检查不等于这些环境的真实验收。
未触发系统虚拟桌面指标异常时的主屏回退分支。
6000×1600仅为本轮观察值，后续按实际显示器布局计算，不固定为验收常量。
