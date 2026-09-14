"""uiautoma.web.set_user_environment() 会话环境配置验收。"""
from __future__ import annotations

import argparse
import inspect
import os
from pathlib import Path

import uiautoma
from uiautoma import web

__test__ = False
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def case(case_id, call):
    try:
        detail, status = call()
    except Exception as exc:  # noqa: BLE001
        trace = str(getattr(exc, "trace_info", "") or "")
        detail = f"{type(exc).__name__}: {exc}" + (f" [trace={trace}]" if trace else "")
        status = "FAIL"
    return {"case_id": case_id, "status": status, "detail": detail}


def contract():
    sig = inspect.signature(web.set_user_environment)
    expected = ("mode", "profile_name", "specifield_userdata", "user_data_dir")
    if tuple(sig.parameters) != expected:
        raise AssertionError(f"签名不符: {sig}")
    kinds = (inspect.Parameter.POSITIONAL_OR_KEYWORD,) * 4
    if tuple(p.kind for p in sig.parameters.values()) != kinds:
        raise AssertionError(f"参数位置规则不符: {sig}")
    defaults = (inspect.Parameter.empty, None, False, None)
    if tuple(p.default for p in sig.parameters.values()) != defaults:
        raise AssertionError(f"默认值不符: {sig}")
    return "四个参数均支持位置传入，默认值符合源码", "PASS"


def run(args):
    results = [case("api_contract", contract)]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results
    environment_selected = False
    try:
        def valid_default():
            nonlocal environment_selected
            returned = web.set_user_environment(args.mode, args.profile_name)
            environment_selected = True
            if returned is not None:
                raise AssertionError(f"返回值应为 None，实际 {returned!r}")
            return "选择现有浏览器用户环境成功，返回 None", "PASS"

        results.append(case("select_default_profile", valid_default))
        if environment_selected:
            local = os.environ.get("LOCALAPPDATA", "")
            root = Path(local) / (Path("Google") / "Chrome" / "User Data" if args.mode == "chrome" else Path("Microsoft") / "Edge" / "User Data")
            if root.is_dir():
                def valid_explicit():
                    returned = web.set_user_environment(args.mode, args.profile_name, True, str(root))
                    if returned is not None:
                        raise AssertionError("显式目录调用返回值应为 None")
                    return "指定 user_data_dir 选择环境成功", "PASS"
                results.append(case("select_explicit_directory", valid_explicit))
            else:
                results.append({"case_id": "select_explicit_directory", "status": "BLOCKED", "detail": "默认用户数据目录不存在，跳过显式目录场景"})
        def invalid_values():
            checks = (("", args.profile_name, False, None), (args.mode, "", False, None),
                      (args.mode, args.profile_name, True, None), (args.mode, args.profile_name, "true", None))
            for values in checks:
                try:
                    web.set_user_environment(*values)
                except (ValueError, TypeError, uiautoma.InvalidParamsError):
                    continue
                raise AssertionError(f"非法参数未拒绝: {values!r}")
            return "非法浏览器、空环境名、缺目录和非布尔参数均被拒绝", "PASS"
        results.append(case("invalid_values", invalid_values))
        def argument_rules():
            try:
                web.set_user_environment(args.mode, args.profile_name, False, None, "extra")
            except TypeError:
                return "多余位置参数被 TypeError 拒绝", "PASS"
            return "多余位置参数未被拒绝", "FAIL"
        results.append(case("argument_rules", argument_rules))
    finally:
        if environment_selected:
            try:
                web.reset_user_environment(args.mode)
                results.append({"case_id": "cleanup", "status": "PASS", "detail": "已恢复原浏览器环境选择"})
            except Exception as exc:  # noqa: BLE001
                results.append({"case_id": "cleanup", "status": "FAIL", "detail": f"环境恢复失败: {type(exc).__name__}: {exc}"})
        else:
            results.append({"case_id": "cleanup", "status": "PASS", "detail": "未选择环境，无需恢复"})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="uiautoma.web.set_user_environment() Web API 验收")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--profile-name", default="Default")
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.set_user_environment")
    print(f" 模式    : {args.mode}\n 环境    : {args.profile_name}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for i, item in enumerate(results, 1):
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(item["status"], RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(item["status"], "失败")
        print(f"{i:02d}/{len(results):02d}    {color}[{label}]{RESET}  {item['case_id']:<22}  {item['detail']}")
    blocked = any(i["status"] == "BLOCKED" for i in results)
    code = 0 if all(i["status"] == "PASS" for i in results) else (2 if blocked else 1)
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else ('测试阻塞' if code == 2 else '测试失败')} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
