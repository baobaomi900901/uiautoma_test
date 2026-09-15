"""reset_user_environment() 当前 SDK 会话环境恢复验收。"""
from __future__ import annotations

import argparse
import inspect
import os
from pathlib import Path

from uiautoma import InvalidParamsError, web

__test__ = False
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id, status, detail, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract():
    signature = inspect.signature(web.reset_user_environment)
    ok = tuple(signature.parameters) == ("mode",) and signature.parameters["mode"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    return result("api_contract", "PASS" if ok else "FAIL",
                  "mode 为唯一位置参数，返回 None" if ok else f"公开签名不符合合同: {signature}")


def run_case(results, case_id, call):
    try:
        detail = call()
        results.append(result(case_id, "PASS", detail or "调用成功，返回 None"))
        return True
    except Exception as exc:  # noqa: BLE001
        trace = str(getattr(exc, "trace_info", "") or "")
        results.append(result(case_id, "FAIL", f"{type(exc).__name__}: {exc}", trace_info=trace))
        return False


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    selected = False
    try:
        run_case(results, "reset_without_selection", lambda: (web.reset_user_environment(args.mode), "无已选环境时重置成功，返回 None")[1])

        def select_then_reset():
            nonlocal selected
            web.set_user_environment(args.mode, args.profile_name)
            selected = True
            web.reset_user_environment(args.mode)
            return f"选择 {args.profile_name} 后重置成功，返回 None"

        run_case(results, "select_then_reset", select_then_reset)
        run_case(results, "reset_auto", lambda: (web.reset_user_environment("auto"), "auto 重置成功，返回 None")[1])

        def invalid_mode():
            try:
                web.reset_user_environment("invalid")
            except InvalidParamsError:
                return "非法浏览器模式被 InvalidParamsError 拒绝"
            raise AssertionError("非法浏览器模式未被拒绝")

        run_case(results, "invalid_mode", invalid_mode)

        def keyword_rules():
            try:
                web.reset_user_environment(args.mode, "extra")
            except TypeError:
                return "多余位置参数被 TypeError 拒绝"
            raise AssertionError("多余位置参数未被拒绝")

        run_case(results, "argument_rules", keyword_rules)
    finally:
        try:
            web.reset_user_environment("auto")
            results.append(result("cleanup", "PASS", "已恢复默认浏览器环境选择"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("cleanup", "FAIL", f"环境恢复失败: {type(exc).__name__}: {exc}"))
    blocked = any(item["status"] == "BLOCKED" for item in results)
    return results, 0 if all(item["status"] == "PASS" for item in results) else (2 if blocked else 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="uiautoma.web.reset_user_environment() API 验收")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--profile-name", default="Default")
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.reset_user_environment")
    print(f" 模式    : {args.mode}\n 环境    : {args.profile_name}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for index, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        print(f"{index:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  {item['case_id']:<22}  {item['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
