## 来源与关联

关联 #50 的 A5「Win 静态相似元素捕获回归」。测试者于 2026-09-10 提供两组真实失败场景。
本次仅提交缺陷，未修改产品源码或元素库。

## 复现

前置：UIAutoma dev 与 Win32 靶场运行，启用 `D:\code\元素库\260902_win元素`，显示表单页。

1. 分别单独捕获并保存“北京”“上海”复选框，两者均成功。
2. 选中已保存的“北京”，启动“捕获相似元素”，点选“上海”。
3. 提示：`所选元素与当前元素不属于同一类型，无法获取相似元素`。
4. 对“姓名”“密码”两个文字标签重复单独捕获和相似捕获流程，同样失败。

注意：本次新捕获的“姓名”“密码”是 `Text/Static` 标签，不是旁边的 Edit 输入框。

预期：同父级、同控件类型的静态目标可以进入相似规则归纳及有效性校验；合法的纯 wnd
路径不应仅因为没有 UIA/ACC 后缀被一律拒绝。如果拒绝有其他实际原因，应给出准确诊断。

## 四份已保存快照分析

| 名称 | 元素 ID | 目标 tag | class_name | backend |
| --- | --- | --- | --- | --- |
| 北京 | ef5b863e-3a8f-4e52-8fd6-96e1ce78ca71 | CheckBox | Button | wnd |
| 上海 | 38cee73a-9c4a-41a6-93e9-15dadd2e7f84 | CheckBox | Button | wnd |
| 姓名 | e7291e0e-d301-4d94-bf57-91bedcf36b07 | Text | Static | wnd |
| 密码 | 28e06ea7-043e-4845-a5b8-1a350cdd4d8c | Text | Static | wnd |

对应文件为元素库 `snapshot/<元素 ID>.json`。共同路径结构：

```text
wnd Window: process_name=win32-shooting-range-uia.exe
            class_name=XPathWin32ShootingRange, title=Win32 靶场 - UIA
  -> wnd Tab: class_name=SysTabControl32
  -> wnd Pane: class_name=XPathWin32Panel, uia_name=表单控件页
  -> wnd CheckBox/Button 或 wnd Text/Static
```

四份路径均只有四层 `wnd`，没有 UIA/ACC 后缀。每组的祖先层一致，目标 tag 和类名一致，
差别为名称、title 和 index 等字段。因此保存快照不支持“组内控件类型不同”的解释。
这些是单独捕获保存的快照，尚未取得失败那次实时点选的完整 Provider 报告。

## 只读源码线索

Rust Provider 源码检查 HEAD：`e7efb4328727aef1a3b9555ba0b3217a83f6a515`。
该值为提交 Issue 时的源码快照，不是已核实的运行二进制构建版本。

`src/element_library_store.rs::build_similar_win32_snapshot`：

```rust
let reference_wnd_len = wnd_prefix_len(reference_path);
let selected_wnd_len = wnd_prefix_len(selected_path);
let reference_suffix = &reference_path[reference_wnd_len..];
let selected_suffix = &selected_path[selected_wnd_len..];
if reference_suffix.is_empty() || selected_suffix.is_empty() {
    return Err("the selected element does not share the same structure".to_string());
}
```

`wnd_prefix_len()` 统计连续 wnd 层。对上述纯 wnd 参照，前缀长度等于路径总长，
reference_suffix 必为空，按当前源码会在实际类型归纳前直接拒绝。

`src/main.rs::replace_win_similar` 对 `build_similar_win32_snapshot` 的所有错误统一调用
`win_similar_type_mismatch()`，最终将结构/路径限制显示为“不同类型”。

以上可解释已保存参照在当前源码下的确定性拒绝条件；尚未通过运行二进制日志或
直接调用 Rust 函数独立复现，不宣称已完成全部运行时根因验证。

## 验收要求

- 北京→上海、姓名标签→密码标签两组均可完成相似捕获，保存后匹配范围符合预期。
- 对四份纯 wnd 快照增加直接归纳回归，覆盖同类目标及确实不同类型目标。
- 保留不同 backend/结构的必要校验，不通过取消全部类型检查绕过缺陷。
- 保留已有 wnd+UIA、wnd+ACC 等支持路径的回归，避免修复影响原生菜单场景。
- 对拒绝原因保留具体诊断，不把所有结构或归纳失败都误报为类型不同。
- 在真实 App/Provider 链路复跑 A5，两组分别记录结果、实际运行版本和保存后校验结果。

本地结果已记录为 A5 的 `win-static-checkbox=FAIL`、`win-static-text=FAIL`；Web A5 未测。
