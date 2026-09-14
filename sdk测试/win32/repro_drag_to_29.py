r"""单独复测 drag_to 的第 29 项：bottomRight 锚点向右拖动 30 物理像素。

被测调用：element.drag_to(left=30, anchor="bottomRight", delay_after=0)
其余 API 参数使用默认值：simulative=None、behavior="smooth"、top=0、move_speed="middle"。
脚本参数：无。先复制一段普通文本；dev 和靶场应已启动，并启用指定元素库。
拖拽后停留 1 秒，复制 JSON 校验；结束时重置位置并恢复普通剪贴板文本、鼠标和前台。
依赖同目录 test_win32_drag_to.py 的辅助函数，导入不会运行其 38 项测试。
"""

import json
import time
import uuid

import test_win32_drag_to as helpers


def main():
    package = reset_button = copy_button = None
    touched = False
    errors = []
    available, original_text = helpers.read_clipboard_text()
    if not available:
        print("[失败] 请先复制一段普通文本，再运行脚本")
        return 1
    mouse, foreground = helpers.current_cursor(), helpers.current_foreground()

    def read_state():
        nonlocal touched
        touched = True
        helpers.write_clipboard_text("repro-29-" + uuid.uuid4().hex)
        copy_button.click(delay_after=0.1)
        return helpers.parse_state(helpers.read_clipboard_text()[1])

    try:
        package = helpers.uiautoma.current(required=True, refresh=True, timeout=5)
        if helpers.Path(package.package_dir).resolve() != helpers.LIBRARY.resolve():
            raise RuntimeError("当前启用的不是指定测试元素库")
        window = helpers.win32.get(title="Win32 靶场 - UIA",
                                   process_name="win32-shooting-range-uia.exe", timeout=5)

        def find(name):
            return window.find(package.selector(name, kind="win"), timeout=5)

        find(helpers.TAB).click(delay_after=0.2)
        reset_button, copy_button = find(helpers.RESET), find(helpers.COPY)
        reset_button.click(delay_after=0.1)
        element = find(helpers.TARGET)
        before_state = read_state()
        before = element.get_bounding(to96dpi=False, relative_to="screen")
        print("第 29 项：bottomRight 右下角锚点")
        print('调用: element.drag_to(left=30, anchor="bottomRight", delay_after=0)')
        started = time.perf_counter()
        returned = element.drag_to(left=30, anchor="bottomRight", delay_after=0)
        elapsed = (time.perf_counter() - started) * 1000
        time.sleep(1)  # 留出人工观察时间，不计入 API 调用耗时。
        after = element.get_bounding(to96dpi=False, relative_to="screen")
        state = read_state()
        print("靶场结果:", json.dumps(state, ensure_ascii=False, indent=2))
        actual = (after[0] - before[0], after[1] - before[1])
        sx, sy = before[2] / 120, before[3] / 80
        reported = ((state['left'] - before_state['left']) * sx,
                    (state['top'] - before_state['top']) * sy)
        print(f"预期位移: (30, 0)；实际边界位移: {actual}；JSON折算位移: {reported}")
        print(f"实际锚点: {state['anchor']}；返回值: {returned!r}；调用耗时: {elapsed:.1f}ms")
        tolerance = max(2, sx, sy)
        if returned is not None or state['anchor']['sudokuPart'] != 'bottomRight':
            raise AssertionError("返回值或右下角锚点不符合预期")
        if state['dragging'] or state['moveCount'] <= 0:
            raise AssertionError("拖拽未完成或未产生移动")
        for delta in (actual, reported):
            if abs(delta[0] - 30) > tolerance or abs(delta[1]) > tolerance:
                raise AssertionError("拖拽位移不符合预期")
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        def reset():
            reset_button.click(delay_after=0.1)
            state = read_state()
            if state['deltaLeft'] or state['deltaTop'] or state['dragging']:
                raise RuntimeError("位置未重置")

        actions = []
        if reset_button is not None and copy_button is not None:
            actions.append(("重置位置", reset))
        # reset/read_state 也会改写剪贴板，因此在执行清理动作时再检查 touched。
        def restore_text():
            if touched:
                helpers.write_clipboard_text(original_text)
                if helpers.read_clipboard_text() != (True, original_text):
                    raise RuntimeError("剪贴板文本恢复不一致")
        actions.extend([("剪贴板", restore_text), ("鼠标", lambda: helpers.restore_cursor(mouse)),
                        ("前台", lambda: helpers.restore_foreground(foreground))])
        if package is not None:
            actions.append(("Package", package.close))
        for name, action in actions:
            try:
                action()
            except Exception as exc:
                errors.append(f"清理{name}失败: {exc}")
    for error in errors:
        print(error)
    print(helpers.colored("[失败] 第 29 项或资源清理失败" if errors else "[通过] 第 29 项及资源清理通过",
                          helpers.ANSI_RED if errors else helpers.ANSI_GREEN))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
