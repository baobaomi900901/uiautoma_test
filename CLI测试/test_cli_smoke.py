"""Live smoke tests for the confirmed uia.exe; all Runtime commands are read-only."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import tomllib
import uuid


WORKSPACE = Path(__file__).resolve().parents[1]
PIPE_ENV = "UIAUTOMA_AUTOMATION_PIPE_NAME"
DEFAULT_PIPE = r"\\.\pipe\UIAutoma.Automation.v1"
TOP_COMMANDS = (
    "clipboard", "docs", "screenshot", "package", "app", "capture", "win", "web",
    "observe", "status", "capabilities", "windows", "browser",
)


class Blocked(Exception):
    pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def git_snapshot(source):
    require(source.is_dir(), f"源码目录不存在：{source}")
    values = {}
    for key, args in (
        ("git_root", ("rev-parse", "--show-toplevel")),
        ("branch", ("branch", "--show-current")),
        ("commit", ("rev-parse", "HEAD")),
    ):
        result = subprocess.run(
            ["git", "-C", str(source), *args], capture_output=True, text=True,
            encoding="utf-8", timeout=15, check=True,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
        values[key] = result.stdout.strip()
    values["path"] = str(source)
    values["branch"] = values["branch"] or "detached HEAD"
    return values


def foreground():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    return int(user32.GetForegroundWindow() or 0)


def window_identity(hwnd):
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    pid = wintypes.DWORD()
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    user32.GetClassNameW(hwnd, class_name, len(class_name))
    return {"hwnd": hwnd, "process_id": pid.value, "class_name": class_name.value}


def envelope(result, *, success, command=None, code=None, exit_code=0):
    require(result.returncode == exit_code, f"退出码期望 {exit_code}，实测 {result.returncode}；{result.stdout[:240]}")
    require(len(result.stdout.splitlines()) == 1, "stdout 必须是单行 JSON")
    payload = json.loads(result.stdout)
    require(isinstance(payload, dict), "JSON 外层应为对象")
    require(type(payload.get("schema_version")) is int and payload["schema_version"] == 1, "schema_version 应为整数 1")
    require(payload.get("ok") is success, f"ok 应为 {success}")
    require("command" in payload and payload["command"] == command, f"command 期望 {command!r}，实测 {payload.get('command')!r}")
    if success:
        require(isinstance(payload.get("data"), dict), "成功 data 应为对象")
        require("error" not in payload, "成功输出不应含 error")
    else:
        error = payload.get("error")
        require(isinstance(error, dict), "失败 error 应为对象")
        require(error.get("code") == code, f"error.code 期望 {code}，实测 {error.get('code')}")
        require(isinstance(error.get("message"), str) and error["message"], "错误文案应为非空字符串")
        require("Usage:" not in error["message"], "JSON 错误文案混入终端帮助布局")
    return payload


def list_data(data):
    require(isinstance(data.get("items"), list), "items 应为数组")
    require(type(data.get("count")) is int, "count 应为整数")
    require(data["count"] == len(data["items"]), "count 应等于本次 items 数量")


def identity_only(payload):
    """Preserve browser identities for cleanup without archiving unrelated titles/URLs."""
    copied = json.loads(json.dumps(payload))
    if copied.get("command") == "browser list" and copied.get("ok") is True:
        copied["data"]["items"] = [
            {key: item[key] for key in ("page_ref", "target_browser", "target_tab_id") if key in item}
            for item in copied["data"]["items"]
        ]
    return copied


class Smoke:
    def __init__(self, cli, pipe, desktop, provider, out):
        self.cli, self.pipe, self.desktop = cli, pipe, desktop
        self.provider, self.out = provider, out
        self.missing_pipe = DEFAULT_PIPE + ".smoke-absent-" + uuid.uuid4().hex
        self.marker = "UIA_smoke_unmatched_" + uuid.uuid4().hex
        self.cases, self.calls, self.results, self.lines = [], [], [], []
        self.baseline = None
        self.metadata = {
            "tested_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "provider_source": git_snapshot(provider),
            "desktop_source": git_snapshot(desktop),
            "sdk_test_directory": str(WORKSPACE / "sdk测试"),
            "cli_test_directory": str(Path(__file__).resolve().parent),
            "cli_path": str(cli),
            "cli_sha256": hashlib.sha256(cli.read_bytes()).hexdigest(),
            "cli_size_bytes": cli.stat().st_size,
            "runtime_pipe": pipe,
        }
        cargo = tomllib.loads((desktop / "cli" / "Cargo.toml").read_text(encoding="utf-8"))
        self.version = str(cargo["workspace"]["package"]["version"])

    def invoke(self, args, *, live=False, pipe=None, select_pipe=True, env_extra=None):
        selected = pipe if pipe is not None else (self.pipe if live else self.missing_pipe)
        prefix = ["--pipe", selected] if select_pipe else []
        command = [str(self.cli), *prefix, *args]
        environment = os.environ.copy()
        environment.pop(PIPE_ENV, None)
        environment.update(env_extra or {})
        started = time.monotonic()
        result = subprocess.run(
            command, cwd=WORKSPACE, env=environment, input="", capture_output=True,
            text=True, encoding="utf-8", errors="strict", timeout=8, check=False,
        )
        elapsed = (time.monotonic() - started) * 1000
        archived_stdout = result.stdout
        if "browser" in args and "list" in args and "json" in args:
            try:
                archived_stdout = json.dumps(identity_only(json.loads(result.stdout)), ensure_ascii=False) + "\n"
            except (ValueError, KeyError, TypeError):
                pass
        self.calls.append({
            "argv": command, "environment_override": env_extra or {},
            "exit_code": result.returncode, "elapsed_ms": round(elapsed, 3),
            "stdout": archived_stdout, "stderr": result.stderr,
            "browser_identity_projection": archived_stdout != result.stdout,
        })
        return result

    def add(self, name, expected, function):
        self.cases.append((name, expected, function))

    def json_success(self, args, *, live=False, check=None):
        result = self.invoke([*args, "--format", "json"], live=live)
        if live and result.returncode in (3, 4):
            raise Blocked(f"Runtime 不可用或能力未声明：{result.stdout.strip()}")
        data = envelope(result, success=True, command=" ".join(args[:3] if args[:2] in (["observe", "win"], ["observe", "web"]) else args[:2] if args[0] in ("docs", "package", "windows", "browser") else args[:1]))["data"]
        require(result.stderr == "", "未启用 debug 时 stderr 应为空")
        if check:
            check(data)
        return data

    def invalid(self, args, *, parsed=False, command=None, code="invalid_params", exit_code=2, pipe=None, env_extra=None, select_pipe=True):
        result = self.invoke(args, pipe=pipe, select_pipe=select_pipe, env_extra=env_extra)
        envelope(result, success=False, command=command if parsed else None, code=code, exit_code=exit_code)
        require(result.stderr == "", "未启用 debug 时 stderr 应为空")
        return f"退出码 {exit_code}，{code}，单行 JSON"

    def text_error(self, args, *, exit_code=2, code="invalid_params"):
        result = self.invoke(args)
        require(result.returncode == exit_code, f"期望退出码 {exit_code}，实测 {result.returncode}")
        require(result.stdout.startswith(f"Error [{code}]:"), f"应输出文本错误；实测 {result.stdout[:180]!r}")
        require(result.stderr == "", "无 debug 时 stderr 应为空")
        return f"文本错误 {code}，退出码 {exit_code}"

    def help_case(self, args, *, root=False):
        result = self.invoke(args)
        require(result.returncode == 0 and result.stderr == "", "帮助应成功且无 stderr")
        require("Usage:" in result.stdout, "帮助缺少 Usage")
        require(not result.stdout.startswith("{"), "帮助应保持文本")
        require(not any("\u4e00" <= char <= "\u9fff" for char in result.stdout), "CLI authored help 应使用英文")
        if root:
            require(all(f"  {name}" in result.stdout for name in TOP_COMMANDS), "根帮助缺少公开命令")
            require("does not start Runtime automatically" in result.stdout, "帮助缺少 Runtime 启动边界")
        return "退出码 0，英文文本帮助"

    def version_case(self, flag):
        result = self.invoke([flag])
        require(result.returncode == 0 and result.stderr == "", "版本命令应成功")
        require(result.stdout.strip() == f"uia {self.version}", f"CLI 版本与源码声明不符：{result.stdout!r}")
        self.metadata["cli_version_output"] = result.stdout.strip()
        return result.stdout.strip()

    def read_state(self):
        status = self.json_success(["status"], live=True)
        package = self.json_success(["package", "current"], live=True)
        browser = self.json_success(["browser", "list"], live=True, check=list_data)
        win = self.json_success(["observe", "win", "list"], live=True, check=list_data)
        web = self.json_success(["observe", "web", "list"], live=True, check=list_data)
        return {
            "runtime_pid": status["runtime_pid"], "package": package,
            "browser_refs": sorted(item["page_ref"] for item in browser["items"]),
            "connected_browser_sessions": browser["connected_session_count"],
            "win_sessions": sorted(item["session_id"] for item in win["items"]),
            "web_sessions": sorted(item["session_id"] for item in web["items"]),
        }

    def baseline_case(self):
        self.baseline = self.read_state()
        self.metadata["baseline"] = self.baseline
        return f"Runtime PID {self.baseline['runtime_pid']}，标签 {len(self.baseline['browser_refs'])}，会话 {len(self.baseline['win_sessions'])}/{len(self.baseline['web_sessions'])}"

    def cleanup_case(self):
        if self.baseline is None:
            raise Blocked("环境基线未取得，无法确认收尾状态")
        final = self.read_state()
        self.metadata["final_state"] = final
        if final != self.baseline:
            raise Blocked("环境状态前后变化；本轮仅含只读命令，需核对并发外部操作，不能归为产品缺陷")
        return f"当前库、PID、标签 {len(final['browser_refs'])} 和 Win/Web 会话均一致"

    def discovery_case(self, args, *, browser=False, empty=False):
        before = foreground()
        before_identity = window_identity(before)
        data = self.json_success(args, live=True, check=list_data)
        after = foreground()
        if before != after:
            self.metadata.setdefault("foreground_changes", []).append({
                "query": args, "before": before_identity, "after": window_identity(after),
            })
            raise Blocked(f"发现期间前台窗口变化 {before}→{after}；需排除用户或外部操作")
        if empty:
            require(data["count"] == 0, "随机不存在的标题应无匹配")
        elif not browser:
            require(data["count"] <= 3, "--max-items 3 应限制返回数量")
            for item in data["items"]:
                require(type(item.get("handle")) is int and item["handle"] > 0, "窗口 handle 应为正整数")
        if browser:
            require(type(data.get("connected_session_count")) is int and data["connected_session_count"] >= 0, "已连接环境数应为非负整数")
            require(all(isinstance(item.get("page_ref"), str) and item["page_ref"] for item in data["items"]), "page_ref 应为非空字符串")
        return f"count={data['count']}，前台 HWND {after} 未变化"

    def status_case(self):
        data = self.json_success(["status"], live=True)
        require(type(data.get("runtime_pid")) is int and data["runtime_pid"] > 0, "Runtime PID 应为正整数")
        require(type(data.get("protocol")) is int and data["protocol"] >= 1, "协议应兼容 1")
        require(data.get("min_protocol") == 1, "最小协议期望 1")
        require(data.get("runtime_version") == self.version, "Runtime 版本与本轮源码声明不符")
        require(type(data.get("has_current_package")) is bool, "当前库标志应为布尔值")
        require(data.get("uiautomation_provider_available") is True, "本轮预期 Provider 可用")
        return f"PID {data['runtime_pid']}，协议 {data['protocol']}，Provider=true"

    def debug_case(self):
        result = self.invoke(["status", "--debug", "--format", "json"], live=True)
        data = envelope(result, success=True, command="status")["data"]
        events = [json.loads(line) for line in result.stderr.splitlines()]
        require(events and all(isinstance(item, dict) and isinstance(item.get("event"), str) for item in events), "stderr 应含 JSON 诊断事件")
        require(any(item["event"] == "command" and item.get("command") == "status" for item in events), "缺少 command 诊断")
        require(self.baseline is not None and data["runtime_pid"] == self.baseline["runtime_pid"], "debug 模式应查询同一 Runtime")
        return f"stdout 一行结果，stderr {len(events)} 条 JSON 诊断"

    def text_live(self, args, *, contains):
        result = self.invoke(args, live=True)
        if result.returncode in (3, 4):
            raise Blocked(result.stdout.strip())
        require(result.returncode == 0 and result.stderr == "", "默认文本查询应成功")
        require(contains in result.stdout and not result.stdout.startswith("{"), f"文本输出缺少 {contains!r}")
        return f"退出码 0，文本含 {contains}"

    def unavailable_case(self, *, as_json=True, env_only=False):
        args = ["status", "--connect-timeout-ms", "100"]
        if as_json:
            args += ["--format", "json"]
        start = time.monotonic()
        result = self.invoke(args, select_pipe=not env_only, env_extra={PIPE_ENV: self.missing_pipe} if env_only else None)
        elapsed = (time.monotonic() - start) * 1000
        if as_json:
            envelope(result, success=False, command="status", code="runtime_unavailable", exit_code=3)
        else:
            require(result.returncode == 3 and result.stdout.startswith("Error [runtime_unavailable]:"), "不可用 Runtime 应输出文本错误及退出码 3")
        require(elapsed < 2500, f"100ms 连接预算未有限退出，耗时 {elapsed:.1f}ms")
        return f"runtime_unavailable，退出码 3，{elapsed:.1f}ms"

    def capability_case(self):
        data = self.json_success(["capabilities"], live=True)
        require(isinstance(data.get("supported_methods"), list) and all(isinstance(x, str) for x in data["supported_methods"]), "方法列表应为字符串数组")
        require(isinstance(data.get("capabilities"), dict) and all(type(x) is bool for x in data["capabilities"].values()), "能力表值应为布尔值")
        require("system.ping" in data["supported_methods"], "方法列表缺少握手方法")
        return f"{len(data['supported_methods'])} 个声明方法，{len(data['capabilities'])} 项能力"

    def docs_case(self, args, check):
        data = self.json_success(["docs", "sdk", "--skills-dir", str(self.desktop / "skills"), *args], check=check)
        return "不存在的 Runtime 管道下成功读取显式本地参考"

    def build_cases(self):
        self.add("environment_baseline", "只读获取 Runtime、库、标签和观察会话基线", self.baseline_case)
        for flag in ("--version", "-V"):
            self.add("version_" + flag.lstrip("-"), "退出码 0；与源码声明版本一致", lambda flag=flag: self.version_case(flag))
        for args in (["--help"], ["-h"], ["--format", "json", "--help"]):
            self.add("root_help_" + "_".join(args), "退出码 0；英文文本；公开命令完整", lambda args=args: self.help_case(args, root=True))
        for command in TOP_COMMANDS:
            self.add("help_" + command, "离线帮助退出码 0", lambda command=command: self.help_case([command, "--help"]))
        for commands in (("observe", "win"), ("observe", "web"), ("windows", "list"), ("browser", "list"), ("docs", "sdk")):
            self.add("help_" + "_".join(commands), "嵌套帮助退出码 0", lambda commands=commands: self.help_case([*commands, "--help"]))

        invalid_cases = [
            ("missing_command", ["--format", "json"]),
            ("unknown_command_format_before", ["--format", "json", "stauts"]),
            ("unknown_command_format_after", ["stauts", "--format", "json"]),
            ("unknown_option_equals_before", ["--format=json", "status", "--unexpected"]),
            ("unknown_option_equals_after", ["status", "--unexpected", "--format=json"]),
            ("hwnd_zero", ["windows", "info", "--hwnd", "0", "--format", "json"]),
            ("hwnd_missing", ["windows", "info", "--format", "json"]),
            ("screenshot_out_missing", ["screenshot", "screen", "--format", "json"]),
            ("screenshot_targets_conflict", ["screenshot", "win", "--hwnd", "1", "--session", "dummy", "--snapshot", "1", "--out", "__must_not_create__.png", "--format", "json"]),
            ("clipboard_source_missing", ["clipboard", "set", "--format", "json"]),
            ("clipboard_sources_conflict", ["clipboard", "set", "--text", "smoke", "--stdin", "--format", "json"]),
            ("browser_mode_invalid", ["browser", "list", "--mode", "firefox", "--format", "json"]),
            ("browser_profile_session_conflict", ["browser", "open", "--url", "about:blank", "--profile", "Default", "--session", "dummy", "--format", "json"]),
            ("max_items_zero", ["windows", "list", "--max-items", "0", "--format", "json"]),
            ("max_items_overflow", ["windows", "list", "--max-items", "10001", "--format", "json"]),
            ("snapshot_zero", ["observe", "win", "refresh", "--session", "dummy", "--snapshot", "0", "--format", "json"]),
        ]
        for name, args in invalid_cases:
            self.add(name, "本地拒绝；退出码 2；invalid_params；command=null", lambda args=args: self.invalid(args))
        for name, args in (
            ("missing_command_text", []),
            ("invalid_format_falls_back_text", ["status", "--format", "yaml"]),
            ("missing_format_value_falls_back_text", ["status", "--format"]),
            ("format_in_text_is_not_option", ["clipboard", "set", "--text", "--format=json", "--unexpected"]),
        ):
            self.add(name, "默认/无效格式采用文本错误，退出码 2", lambda args=args: self.text_error(args))
        self.add("explicit_format_after_text_value", "参数值中的 format 不覆盖真正的 JSON 选项", lambda: self.invalid(["clipboard", "set", "--text", "--format=text", "--unexpected", "--format", "json"]))
        self.add("format_after_double_dash_ignored", "-- 后内容不改变输出；连接失败退出码 3", lambda: self.text_error(["app", "launch", "--exe", "__uia_smoke_nonexistent__.exe", "--connect-timeout-ms", "100", "--", "--format=json"], exit_code=3, code="runtime_unavailable"))
        self.add("explicit_format_before_double_dash", "-- 前 JSON 生效；不启动程序", lambda: self.invalid(["--format", "json", "app", "launch", "--exe", "__uia_smoke_nonexistent__.exe", "--connect-timeout-ms", "100", "--", "--format=text"], parsed=True, command="app launch", code="runtime_unavailable", exit_code=3))

        for option, invalid_values, valid_values in (
            ("--connect-timeout-ms", ("0", "300001"), ("1", "300000")),
            ("--timeout-ms", ("0", "300001"), ("1", "300000")),
            ("--max-response-bytes", ("255", "67108865"), ("256", "67108864")),
        ):
            for value in invalid_values:
                self.add(f"range_reject_{option}_{value}", "超出公开范围，解析拒绝，command=null", lambda option=option, value=value: self.invalid([option, value, "status", "--format", "json"]))
            for value in valid_values:
                self.add(f"range_accept_{option}_{value}", "边界值通过解析；无效管道随后本地拒绝，command=status", lambda option=option, value=value: self.invalid([option, value, "status", "--format", "json"], pipe="not-a-local-pipe", parsed=True, command="status"))
        for pipe in ("not-a-local-pipe", r"\\smoke-server\pipe\absent", "\\\\.\\pipe\\"):
            self.add("reject_pipe_" + pipe, "非本地/空名称管道本地拒绝，退出码 2", lambda pipe=pipe: self.invalid(["status", "--format", "json"], pipe=pipe, parsed=True, command="status"))
        self.add("missing_runtime_json", "连接预算 100ms；JSON runtime_unavailable；退出码 3", self.unavailable_case)
        self.add("missing_runtime_text", "连接预算 100ms；文本 runtime_unavailable；退出码 3", lambda: self.unavailable_case(as_json=False))
        self.add("environment_pipe_selected", "无 --pipe 时使用环境变量，而非已运行的默认 Runtime", lambda: self.unavailable_case(env_only=True))
        self.add("explicit_pipe_overrides_environment", "显式 --pipe 覆盖无效环境变量", lambda: self.invalid(["status", "--connect-timeout-ms", "100", "--format", "json"], parsed=True, command="status", code="runtime_unavailable", exit_code=3, env_extra={PIPE_ENV: "not-a-local-pipe"}))

        self.add("docs_topics_offline", "显式本地资源；不连接 Runtime；包含公开主题", lambda: self.docs_case([], lambda data: require(isinstance(data.get("topics"), list) and "web-elements" in data["topics"] and "contracts" in data["topics"], "文档主题列表不完整")))
        self.add("docs_symbol_offline", "精确查询 WebElement.click 签名和指南", lambda: self.docs_case(["--symbol", "WebElement.click"], lambda data: require(data.get("symbol") == "WebElement.click" and str(data.get("signature", "")).startswith("WebElement.click("), "精确符号签名不正确")))
        self.add("docs_contracts_offline", "本地 contracts 主题返回非空内容", lambda: self.docs_case(["--topic", "contracts"], lambda data: require(data.get("topic") == "contracts" and isinstance(data.get("content"), str) and bool(data["content"]), "行为合同内容应非空")))
        self.add("docs_unknown_symbol", "不存在的公共符号退出码 2，documentation_not_found", lambda: self.invalid(["docs", "sdk", "--skills-dir", str(self.desktop / "skills"), "--symbol", "WebElement.__uia_smoke_absent__", "--format", "json"], parsed=True, command="docs sdk", code="documentation_not_found"))
        self.add("docs_missing_resources", "资源目录缺失退出码 2，documentation_unavailable", lambda: self.invalid(["docs", "sdk", "--skills-dir", str(WORKSPACE / ".pytest_tmp" / self.marker), "--format", "json"], parsed=True, command="docs sdk", code="documentation_unavailable"))

        self.add("runtime_status_json", "协议/版本/PID 类型正确，Provider 可用", self.status_case)
        self.add("runtime_status_default_text", "默认输出为文本", lambda: self.text_live(["status"], contains="runtime_pid:"))
        self.add("runtime_status_debug", "debug 不污染 stdout，stderr 为诊断 JSON", self.debug_case)
        self.add("runtime_capabilities", "方法数组、布尔能力表；只验证声明", self.capability_case)
        self.add("runtime_package_current", "当前库只读查询，无库也成功", lambda: self.json_success(["package", "current"], live=True, check=lambda data: require(type(data.get("has_current_package")) is bool, "has_current_package 应为布尔值")))
        self.add("windows_list_limited", "返回数不超过 3，句柄正整数，前台不变", lambda: self.discovery_case(["windows", "list", "--max-items", "3"]))
        self.add("windows_empty_json", "随机标题 count=0/items=[]，前台不变", lambda: self.discovery_case(["windows", "list", "--title", self.marker], empty=True))
        self.add("windows_empty_text", "默认文本与空 JSON 结果一致", lambda: self.text_live(["windows", "list", "--title", self.marker], contains="No windows."))
        self.add("browser_list_json", "items/count 一致，page_ref 为字符串，前台不变", lambda: self.discovery_case(["browser", "list"], browser=True))
        self.add("browser_empty_json", "随机标题 count=0/items=[]，保留连接数", lambda: self.discovery_case(["browser", "list", "--title", self.marker], browser=True, empty=True))
        self.add("browser_empty_text", "默认文本与空 JSON 结果一致", lambda: self.text_live(["browser", "list", "--title", self.marker], contains="No pages."))
        for backend in ("win", "web"):
            self.add("observe_" + backend + "_list", "只读会话列表，items/count 一致", lambda backend=backend: self.json_success(["observe", backend, "list"], live=True, check=list_data))
        self.add("state_cleanup", "PID、库、标签和观察会话保持本轮基线", self.cleanup_case)

    def execute(self):
        self.build_cases()
        self.lines = [
            "UIAutoma CLI 基础冒烟测试",
            f"CLI     : {self.cli}",
            f"SHA-256 : {self.metadata['cli_sha256']}",
            f"Runtime : {self.pipe}",
        ]
        for line in self.lines:
            print(line)
        for index, (name, expected, function) in enumerate(self.cases, 1):
            first_call = len(self.calls)
            started = time.monotonic()
            try:
                actual = function()
                if isinstance(actual, dict):
                    actual = f"只读查询成功，字段 {','.join(sorted(actual))}"
                status = "PASS"
            except Blocked as error:
                status, actual = "BLOCKED", str(error)
            except (OSError, subprocess.TimeoutExpired) as error:
                status, actual = "BLOCKED", str(error)
            except Exception as error:
                status, actual = "FAIL", f"{type(error).__name__}: {error}"
            elapsed = (time.monotonic() - started) * 1000
            record = {"id": name, "status": status, "expected": expected, "actual": str(actual), "elapsed_ms": round(elapsed, 3), "call_indices": list(range(first_call, len(self.calls)))}
            self.results.append(record)
            label = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}[status]
            line = f"{index:02}/{len(self.cases):02} [{label}] {name} | 期望：{expected} | 实测：{actual} | {elapsed:.1f}ms"
            self.lines.append(line)
            print(line, flush=True)
        counts = {status: sum(case["status"] == status for case in self.results) for status in ("PASS", "FAIL", "BLOCKED")}
        exit_code = 1 if counts["FAIL"] else 2 if counts["BLOCKED"] else 0
        summary = f"总计 {len(self.results)}：{counts['PASS']} PASS，{counts['FAIL']} FAIL，{counts['BLOCKED']} BLOCKED；退出码 {exit_code}"
        self.lines.append(summary)
        print(summary)
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.out.write_text(json.dumps({"metadata": self.metadata, "cases": self.results, "calls": self.calls, "summary": {**counts, "total": len(self.results), "exit_code": exit_code}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.out.with_suffix(".txt").write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--provider-source", required=True, type=Path)
    parser.add_argument("--desktop-source", required=True, type=Path)
    parser.add_argument("--pipe", default=DEFAULT_PIPE)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    cli = args.cli.resolve(strict=True)
    out = args.out.resolve()
    require(cli.is_file(), "CLI 路径应为文件")
    require(out.is_relative_to(WORKSPACE), "测试证据必须保存到当前测试工作区")
    return Smoke(cli, args.pipe, args.desktop_source.resolve(strict=True), args.provider_source.resolve(strict=True), out).execute()


if __name__ == "__main__":
    raise SystemExit(main())
