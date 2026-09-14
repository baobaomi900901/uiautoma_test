r"""Win32Element.drag_to() 实时测试，使用靶场复制出的 JSON 独立校验。

API 参数（全部支持位置或关键字）：
    simulative: bool | None = None  None 使用 SDK 默认配置；False 请求瞬时拖拽。
    behavior: str = "smooth"        smooth / instant，区分大小写。
    top: int = 0                    相对垂直物理像素偏移，正数向下；实现调用 int()。
    left: int = 0                   相对水平物理像素偏移，正数向右；实现调用 int()。
    delay_after: float = 1          动作后等待秒数，None/0 不等待；非法值在动作后拒绝。
    anchor: object | None = None    中心默认；九宫格、random、三元组和字典偏移。
    move_speed: str = "middle"      slow / middle / fast / instant。
返回 None，更新 last_result。API 没有公开 timeout 或 button 参数。

脚本参数：无。命令：uv run .\win32\test_win32_drag_to.py
前置：dev 运行；当前库 D:\code\元素库\260902_win元素；已打开 Win32 靶场。
运行前请复制一段普通文本。脚本仅保存恢复 Unicode 文本，不保存富文本等其他格式。
每例重置到靶场默认中心；结束时再次重置，保留拖拽页，恢复鼠标、前台和剪贴板文本。
复用同目录 get_value 的 DPI/日志/鼠标辅助及 clipboard_input 的剪贴板辅助函数。
靶场源码定义拖拽块内部尺寸 120×80，JSON 使用靶场客户区坐标；与物理边界比值换算 DPI。
真实 UI 运行由测试者执行；本脚本只测试当前靶场，不测试跨窗口或跨显示器拖放。
正数/None 延时与同参数 delay_after=0 作配对比较；速度检查靶场耗时和事件数。
完整 UTF-8 日志自动保存在 sdk测试/.logs/drag_to/，不会覆盖旧日志。
"""

from __future__ import annotations

import inspect
import json
import time
import uuid
import sys
import re
from datetime import datetime
from pathlib import Path

from test_win32_get_value import (
    DPI_AWARENESS_MODE, current_cursor, current_foreground, restore_cursor,
    restore_foreground, run_case, render_results, colored, ANSI_GREEN, ANSI_RED,
)
from test_win32_clipboard_input import read_clipboard_text, write_clipboard_text
import uiautoma
from uiautoma import InvalidParamsError, win32
from uiautoma.win32 import Win32Element

LIBRARY = Path(r"D:\code\元素库\260902_win元素")
TAB = "win32靶场_tab_item拖拽测试"
TARGET = "win32靶场_拖拽测试_可拖拽元素"
COPY = "win32靶场_拖拽测试_复制拖拽元素当前结果到剪切板"
RESET = "win32靶场_拖拽测试_重置位置"
ANCHORS = ["topLeft", "topCenter", "topRight", "middleLeft", "middleCenter",
           "middleRight", "bottomLeft", "bottomCenter", "bottomRight"]


def parse_state(text):
    state = json.loads(text)
    for key in ("left", "top", "initialLeft", "initialTop", "deltaLeft", "deltaTop",
                "startLeft", "startTop", "sessionDeltaLeft", "sessionDeltaTop",
                "moveCount", "durationMs"):
        if type(state.get(key)) is not int:
            raise ValueError(f"靶场 JSON 缺少整数字段 {key}")
    if type(state.get("dragging")) is not bool:
        raise ValueError("靶场 JSON 缺少 dragging 布尔值")
    anchor = state.get("anchor", {})
    if not all(type(anchor.get(k)) is int for k in ("x", "y")):
        raise ValueError("靶场 JSON 缺少 anchor.x/y")
    if anchor.get("sudokuPart") not in ANCHORS:
        raise ValueError("靶场 JSON 锚点区域无效")
    return state


def contract():
    sig = inspect.signature(Win32Element.drag_to)
    expected = {"simulative": None, "behavior": "smooth", "top": 0, "left": 0,
                "delay_after": 1, "anchor": None, "move_speed": "middle"}
    assert list(sig.parameters) == ["self", *expected], str(sig)
    for name, default in expected.items():
        p = sig.parameters[name]
        assert p.default == default and p.kind == p.POSITIONAL_OR_KEYWORD, str(sig)
    assert sig.return_annotation in (None, "None", type(None)), str(sig)
    return "七个公开参数、默认值与位置/关键字调用规则符合合同"


def check_timing(params, state, elapsed, baseline=None):
    """靶场耗时用于速度判断；配对调用差值用于动作后延时判断。"""
    instant = (params['simulative'] is False or params['behavior'] == 'instant'
               or params['move_speed'] == 'instant')
    speed = 'instant' if instant else params['move_speed']
    limits = {'instant': (0, 80), 'fast': (50, 180),
              'middle': (175, 420), 'slow': (450, 1000)}
    low, high = limits[speed]
    duration = state['durationMs']
    assert low <= duration <= high, f"速度 {speed}: 靶场耗时 {duration}ms，验收区间 {low}–{high}ms"
    if int(params['left']) or int(params['top']):
        count = state['moveCount']
        assert count == 1 if instant else count >= 2, f"速度 {speed}: 移动事件数 {count} 不符合预期"
    detail = f"速度校验: {speed}，{duration}ms 在 {low}–{high}ms 内"
    if baseline is not None:
        expected = float(params['delay_after'] or 0) * 1000
        delta = elapsed - baseline
        tolerance = max(80, expected * 0.2)
        assert abs(delta - expected) <= tolerance, (
            f"延时差值不符: 无延时 {baseline:.1f}ms，本次 {elapsed:.1f}ms，"
            f"差值 {delta:.1f}ms，预期 {expected:.0f}±{tolerance:.0f}ms；系统忙时请复测")
        detail += f"；延时校验: 基线 {baseline:.1f}ms，差值 {delta:.1f}ms，预期 {expected:.0f}ms"
    return detail


def main():
    print("UIAutoma Win32 Element API 测试\n")
    print("  API     : uiautoma.win32.Win32Element.drag_to")
    print(f"  元素库  : {LIBRARY}\n  拖拽元素: {TARGET}\n  DPI 模式: {DPI_AWARENESS_MODE}")
    print("  校验方式: 靶场 JSON 位移、锚点及物理边界交叉核对")
    print("  状态恢复: 每例重置位置；结束后恢复普通剪贴板文本、鼠标和前台")
    results = [run_case("API 合同", contract)]
    package = None
    copy_button = reset_button = target = None
    original_text = original_mouse = original_foreground = None
    clipboard_touched = False
    started = time.perf_counter()

    def read_state():
        nonlocal clipboard_touched
        # 唯一标记防止复制按钮失败时误读上一轮的 JSON。
        clipboard_touched = True
        write_clipboard_text("drag-test-" + uuid.uuid4().hex)
        copy_button.click(simulative=True, delay_after=0.05)
        deadline = time.monotonic() + 2
        last = ""
        while time.monotonic() < deadline:
            try:
                available, last = read_clipboard_text()
                if available and last.startswith("{"):
                    return parse_state(last)
            except OSError:
                pass
            time.sleep(0.05)
        raise RuntimeError(f"复制按钮未产生新的靶场 JSON：{last[:160]!r}")

    def reset():
        reset_button.click(simulative=True, delay_after=0.05)
        state = read_state()
        assert state["deltaLeft"] == state["deltaTop"] == 0 and not state["dragging"], state
        return state

    def rect():
        return target.get_bounding(to96dpi=False, relative_to="screen")

    def prepare():
        nonlocal package, target, copy_button, reset_button
        nonlocal original_text, original_mouse, original_foreground
        available, original_text = read_clipboard_text()
        if not available:
            raise RuntimeError("请先复制一段普通文本，再运行脚本，以便保存和恢复剪贴板文本")
        original_mouse, original_foreground = current_cursor(), current_foreground()
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        if package is None or Path(package.package_dir).resolve() != LIBRARY.resolve():
            raise RuntimeError("请在 UIAutoma 中启用指定元素库")
        window = win32.get(title="Win32 靶场 - UIA", process_name="win32-shooting-range-uia.exe", timeout=5)
        window.find(package.selector(TAB, kind="win"), timeout=5).click(delay_after=0.2)
        target = window.find(package.selector(TARGET, kind="win"), timeout=5)
        copy_button = window.find(package.selector(COPY, kind="win"), timeout=5)
        reset_button = window.find(package.selector(RESET, kind="win"), timeout=5)
        state = reset()
        bounds = rect()
        assert bounds[2] > 0 and bounds[3] > 0, bounds
        return "拖拽页与四个元素已就绪，已读取重置后的 JSON", [f"边界: {bounds}", f"初始位置: ({state['left']}, {state['top']})"]

    def exercise(args=(), kwargs=None, expected_error=None, action_expected=True,
                 sample=None, is_baseline=False):
        kwargs = kwargs or {}
        bound = inspect.signature(Win32Element.drag_to).bind(target, *args, **kwargs)
        bound.apply_defaults()
        params = bound.arguments
        baseline = None
        if not expected_error and not is_baseline and params['delay_after'] != 0:
            comparison = {k: v for k, v in params.items() if k != 'self'}
            comparison['delay_after'] = 0
            baseline_sample = {}
            exercise(kwargs=comparison, sample=baseline_sample, is_baseline=True)
            baseline = baseline_sample['elapsed']
        before = reset()
        bounds = rect()
        sx, sy = bounds[2] / 120, bounds[3] / 80
        returned = None
        caught = None
        old_result = target.last_result
        begin = time.perf_counter()
        try:
            returned = target.drag_to(*args, **kwargs)
        except Exception as exc:
            caught = exc
        elapsed = (time.perf_counter() - begin) * 1000
        after_bounds = rect()
        state = read_state()
        if expected_error:
            assert isinstance(caught, expected_error), f"预期 {expected_error}，实际 {caught!r}"
        elif caught:
            raise caught
        else:
            assert returned is None, returned
        assert not state["dragging"], "鼠标仍处于拖拽状态"
        if not action_expected:
            assert (state["left"], state["top"]) == (before["left"], before["top"]), state
            assert state["moveCount"] == 0 and target.last_result is old_result, state
            return "非法参数在拖拽前被拒绝，位置与动作结果未改变"
        dx, dy = int(params["left"]), int(params["top"])
        json_delta = ((state["left"] - before["left"]) * sx, (state["top"] - before["top"]) * sy)
        physical_delta = (after_bounds[0] - bounds[0], after_bounds[1] - bounds[1])
        tolerance = max(2, sx, sy)
        for observed in (json_delta, physical_delta):
            assert abs(observed[0] - dx) <= tolerance and abs(observed[1] - dy) <= tolerance, f"预期物理位移 {(dx, dy)}，JSON折算 {json_delta}，边界位移 {physical_delta}"
        assert target.last_result is not old_result, "last_result 未更新"
        if dx or dy:
            assert state["moveCount"] > 0, "靶场未接收到有效移动事件"
        anchor = params["anchor"]
        name = anchor or "middleCenter"
        ox = oy = 0
        if isinstance(anchor, (tuple, list)):
            name, ox, oy = anchor
        elif isinstance(anchor, dict):
            name, ox, oy = anchor["anchor"], anchor.get("offset_x", 0), anchor.get("offset_y", 0)
        point = state["anchor"]
        if name == "random":
            assert 0 <= point["x"] < 120 and 0 <= point["y"] < 80, point
        else:
            assert point["sudokuPart"] == name, f"预期锚点 {name}，实际 {point}"
            if ox or oy:
                assert abs((point["x"] - 60) * sx - ox) <= tolerance, point
                assert abs((point["y"] - 40) * sy - oy) <= tolerance, point
        timing = check_timing(params, state, elapsed, baseline)
        if sample is not None:
            sample['elapsed'] = elapsed
        return "位移、锚点及返回结果符合预期", [
            f"调用: drag_to{args!r} {kwargs!r}",
            f"位移: 预期 {(dx, dy)}，边界 {physical_delta}，JSON折算 {json_delta}",
            f"锚点: {point}；移动 {state['moveCount']} 次；靶场 {state['durationMs']}ms；调用 {elapsed:.1f}ms",
            timing,
        ]

    try:
        preparation = run_case("页面与测试目标", prepare)
        results.append(preparation)
        if not preparation.passed or not results[0].passed:
            return 1
        cases = [("全部默认参数", (), {}),
                 ("全位置参数", (True, "smooth", 20, 30, 0, "middleCenter", "middle"), {}),
                 ("正向位移", (), dict(top=20, left=30, delay_after=0)),
                 ("负向位移", (), dict(top=-20, left=-30, delay_after=0)),
                 ("仅垂直位移", (), dict(top=20, delay_after=0)),
                 ("仅水平位移", (), dict(left=30, delay_after=0)),
                 ("非模拟模式", (), dict(simulative=False, left=30, delay_after=0)),
                 ("瞬时轨迹", (), dict(simulative=True, behavior="instant", left=30, delay_after=0)),
                 ("三元组锚点", (), dict(left=30, anchor=("middleCenter", 6, 4), delay_after=0)),
                 ("字典锚点", (), dict(left=30, anchor=dict(anchor="middleCenter", offset_x=-6, offset_y=-4), delay_after=0)),
                 ("随机锚点", (), dict(left=30, anchor="random", delay_after=0)),
                 ("None延时", (), dict(left=30, delay_after=None)),
                 ("正数延时", (), dict(left=30, delay_after=0.2)),
                 ("坐标转换", (), dict(left="30", top=20.9, delay_after=0))]
        cases += [("速度 " + speed, (), dict(simulative=True, left=30, move_speed=speed, delay_after=0)) for speed in ("instant", "fast", "middle", "slow")]
        cases += [("锚点 " + anchor, (), dict(left=30, anchor=anchor, delay_after=0)) for anchor in ANCHORS]
        for name, args, kwargs in cases:
            results.append(run_case(name, lambda a=args, k=kwargs: exercise(a, k)))
            reset()  # 清理失败时停止后续动作。
        for name, kwargs, error, acted in [
            ("非法轨迹", dict(behavior="invalid"), InvalidParamsError, False),
            ("非法速度", dict(move_speed="medium"), InvalidParamsError, False),
            ("非法锚点", dict(anchor="invalid"), InvalidParamsError, False),
            ("非法锚点类型", dict(anchor=123), InvalidParamsError, False),
            ("非法横坐标", dict(left="invalid"), ValueError, False),
            ("非法纵坐标", dict(top=None), TypeError, False),
            ("负数延时", dict(left=30, delay_after=-1), InvalidParamsError, True),
            ("非数字延时", dict(left=30, delay_after="invalid"), InvalidParamsError, True),
        ]:
            results.append(run_case(name, lambda k=kwargs, e=error, a=acted: exercise(kwargs=k, expected_error=e, action_expected=a)))
            reset()
    except Exception as exc:
        def failure():
            raise RuntimeError(f"场景准备或重置失败，已停止后续动作：{exc}")
        results.append(run_case("执行中断", failure))
    finally:
        def cleanup():
            errors = []
            actions = []
            if reset_button is not None and copy_button is not None:
                actions.append(("重置位置", reset))
            if clipboard_touched:
                def restore_text():
                    write_clipboard_text(original_text)
                    assert read_clipboard_text() == (True, original_text)
                actions.append(("剪贴板文本", restore_text))
            if original_mouse is not None:
                actions.append(("鼠标", lambda: restore_cursor(original_mouse)))
            if original_foreground:
                actions.append(("前台", lambda: restore_foreground(original_foreground)))
            if package is not None:
                actions.append(("Package", package.close))
            for name, action in actions:
                try:
                    action()
                except Exception as error:
                    errors.append(f"{name}: {error}")
            if errors:
                raise RuntimeError("；".join(errors))
            return "已清理本次取得的资源；拖拽位置已重置（如已准备），靶场保持运行"
        results.append(run_case("资源清理", cleanup))
        render_results(results)
        passed = sum(item.passed for item in results)
        ok = passed == len(results)
        print(colored("\n测试通过" if ok else "\n测试失败", ANSI_GREEN if ok else ANSI_RED))
        print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果    : {passed}/{len(results)} 通过")
        print(f"  总耗时  : {(time.perf_counter() - started) * 1000:.1f}ms\n  退出码  : {0 if ok else 1}")
    return 0 if all(item.passed for item in results) else 1


class LogTee:
    def __init__(self, terminal, log):
        self.terminal, self.log = terminal, log

    def write(self, text):
        self.log.write(re.sub(r'\x1b\[[0-9;]*m', '', text))
        self.log.flush()
        return self.terminal.write(text)

    def flush(self):
        self.log.flush()
        self.terminal.flush()

    def isatty(self):
        return self.terminal.isatty()


def run_logged(directory=None):
    directory = directory or Path(__file__).resolve().parents[1] / '.logs' / 'drag_to'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.txt')
    stdout, stderr = sys.stdout, sys.stderr
    with path.open('x', encoding='utf-8') as log:
        try:
            sys.stdout, sys.stderr = LogTee(stdout, log), LogTee(stderr, log)
            print(f'完整日志: {path}', flush=True)
            return main()
        except BaseException:
            import traceback
            traceback.print_exc()
            raise
        finally:
            sys.stdout, sys.stderr = stdout, stderr


if __name__ == "__main__":
    raise SystemExit(run_logged())
