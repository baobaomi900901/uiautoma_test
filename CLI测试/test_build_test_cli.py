"""Regression tests for CLI build integration; external build commands are isolated.

Run with python -B -m unittest discover -s CLI测试 -p test_build_test_cli.py -v.
BUILD_TEST_SCRIPT can select the test-side candidate before installing it.
"""
from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import subprocess
import unittest
from unittest import mock


SCRIPT = Path(os.environ.get("BUILD_TEST_SCRIPT", r"D:\code\.tools\build-test.py"))
SPEC = importlib.util.spec_from_file_location("build_test_cli_regression", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
build_test = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_test)

CLI_COMMAND = (
    "cargo", "build", "--manifest-path", "cli/Cargo.toml", "--release", "--locked",
    "--target", "x86_64-pc-windows-msvc", "--target-dir", "cli/target",
)
WORKSPACE = Path(__file__).resolve().parents[1]


class CliBuildTests(unittest.TestCase):
    def test_plan_builds_locked_release_cli_for_selected_worktree(self) -> None:
        desktop = WORKSPACE / ".pytest_tmp" / "Desktop worktree 中文"
        plan = build_test.desktop_command_plan(desktop, "pwsh.exe")
        cli_steps = [step for step in plan if step.args[:2] == ("cargo", "build")]
        self.assertEqual(len(cli_steps), 1, "Desktop plan must build uia.exe once")
        self.assertEqual(cli_steps[0].args, CLI_COMMAND)
        self.assertEqual(cli_steps[0].cwd, desktop)
        self.assertEqual(cli_steps[0].status.label, "CLI")

    def test_prepare_desktop_executes_cli_without_repeating_cleanup(self) -> None:
        desktop = WORKSPACE / ".pytest_tmp" / "Desktop worktree 中文"
        calls = []

        def runner(args, *, cwd, **kwargs):
            calls.append((tuple(args), cwd, kwargs))
            return subprocess.CompletedProcess(args, 0, "", "")

        build_test.prepare_desktop(desktop, "pwsh.exe", runner, include_cleanup=False)
        self.assertEqual(sum(args == CLI_COMMAND for args, _, _ in calls), 1)
        self.assertTrue(all(cwd == desktop for _, cwd, _ in calls))
        self.assertTrue(all("-CleanupOnly" not in args for args, _, _ in calls))

    def test_cli_build_failure_aborts_desktop_preparation(self) -> None:
        desktop = WORKSPACE / ".pytest_tmp" / "Desktop worktree 中文"
        calls = []

        def runner(args, *, cwd, **kwargs):
            calls.append(tuple(args))
            if tuple(args) == CLI_COMMAND:
                raise build_test.CommandError(args, cwd, 101, "compile failure")
            return subprocess.CompletedProcess(args, 0, "", "")

        with self.assertRaises(build_test.CommandError) as raised:
            build_test.prepare_desktop(desktop, "pwsh.exe", runner)
        self.assertEqual(raised.exception.returncode, 101)
        self.assertEqual(calls[-1], CLI_COMMAND)

    def test_cli_path_is_absolute_and_belongs_to_selected_worktree(self) -> None:
        desktop = WORKSPACE / ".pytest_tmp" / "Desktop worktree 中文"
        self.assertTrue(hasattr(build_test, "cli_executable_path"), "CLI path helper is missing")
        artifact = build_test.cli_executable_path(desktop)
        self.assertEqual(artifact, desktop.resolve() / "cli/target/x86_64-pc-windows-msvc/release/uia.exe")
        self.assertTrue(artifact.is_absolute())

    def test_ready_notice_prints_copyable_absolute_cli_commands(self) -> None:
        cli = (WORKSPACE / ".pytest_tmp" / "Desktop worktree 中文" / "uia.exe").resolve()
        self.assertTrue(hasattr(build_test, "notify_cli_test_ready"), "CLI ready notice is missing")
        messages = []
        build_test.notify_cli_test_ready(cli, write=messages.append)
        self.assertEqual(len(messages), 1)
        self.assertIn(str(cli), messages[0])
        self.assertIn(f'& "{cli}" --help', messages[0])
        self.assertIn(f'& "{cli}" status', messages[0])
        self.assertIn("本次", messages[0])


class WorkflowIntegrationTests(unittest.TestCase):
    def run_selected_workflow(self, *, fail_cli: bool):
        rust = WORKSPACE / ".pytest_tmp" / "rust-worktree"
        desktop = WORKSPACE / ".pytest_tmp" / "Desktop worktree 中文"
        sdk_test = WORKSPACE / "sdk测试"
        output = io.StringIO()
        console = build_test.ConsoleReporter(stdout=output, stderr=io.StringIO(), interactive=False, color=False)
        events = []
        calls = []
        provider_patch = mock.MagicMock()
        provider_patch.restored = True
        provider_patch.__enter__.return_value = provider_patch
        provider_patch.__exit__.return_value = False
        config = build_test.default_config()
        config["repositories"] = {
            "rust_uia": {"selection": {"remote_ref": "origin/main"}},
            "desktop": {"selection": {"remote_ref": "origin/main"}},
        }

        def runner(args, *, cwd, **kwargs):
            calls.append((tuple(args), cwd))
            if tuple(args) == CLI_COMMAND:
                events.append("cli_build")
                if fail_cli:
                    raise build_test.CommandError(args, cwd, 101, "compile failure")
            return subprocess.CompletedProcess(args, 0, "", "")

        original_prepare = build_test.prepare_desktop
        original_notice = getattr(build_test, "notify_cli_test_ready", None)

        def prepare(selected, powershell, **kwargs):
            original_prepare(selected, powershell, runner, **kwargs)

        def notice(*args, **kwargs):
            events.append("cli_notice")
            original_notice(*args, **kwargs)

        patches = dict(
            _CONSOLE=console,
            missing_tools=mock.Mock(return_value=[]),
            find_powershell=mock.Mock(return_value="pwsh.exe"),
            load_config=mock.Mock(return_value=config),
            recover_provider_if_needed=mock.Mock(),
            prompt_repository_path=mock.Mock(side_effect=[rust, desktop]),
            prompt_sdk_test_path=mock.Mock(return_value=sdk_test),
            ensure_local_excludes=mock.Mock(),
            confirm=mock.Mock(return_value=False),
            select_repository_worktree=mock.Mock(side_effect=[rust, desktop]),
            sync_remote_worktree=mock.Mock(side_effect=[build_test.SyncResult("a" * 40, "origin/main"), build_test.SyncResult("b" * 40, "origin/main")]),
            prepare_sdk_test_environment=mock.Mock(return_value=build_test.SdkEnvironment(sdk_test / ".venv/Scripts/python.exe", desktop / "sdk")),
            cleanup_desktop=mock.Mock(),
            build_provider=mock.Mock(return_value=rust / "provider.exe"),
            collect_provider_manifest=mock.Mock(return_value={}),
            validate_helpers=mock.Mock(),
            install_provider_temporarily=mock.Mock(return_value=provider_patch),
            prepare_desktop=prepare,
            notify_extension_reload=mock.Mock(),
            ensure_dev_port_available=mock.Mock(),
            run_dev=mock.Mock(side_effect=lambda *args: events.append("dev")),
        )
        if original_notice is not None:
            patches["notify_cli_test_ready"] = notice
        with mock.patch.multiple(build_test, **patches):
            error = None
            try:
                result = build_test.run_workflow(WORKSPACE / ".pytest_tmp" / "workflow-config.json")
            except build_test.CommandError as caught:
                error = caught
                result = None
        return result, error, events, calls, output.getvalue(), provider_patch, patches["cleanup_desktop"]

    def test_workflow_builds_and_announces_cli_before_dev(self) -> None:
        result, error, events, calls, output, _, _ = self.run_selected_workflow(fail_cli=False)
        self.assertIsNone(error)
        self.assertEqual(result, 0)
        self.assertEqual(events, ["cli_build", "cli_notice", "dev"])
        self.assertIn("Desktop worktree 中文", output)
        self.assertIn("uia.exe", output)
        self.assertEqual(sum(args == CLI_COMMAND for args, _ in calls), 1)
        for stage in range(1, 7):
            self.assertEqual(output.count(f"[{stage}/6]"), 1)

    def test_workflow_restores_provider_and_never_starts_dev_on_cli_failure(self) -> None:
        result, error, events, _, output, provider_patch, cleanup = self.run_selected_workflow(fail_cli=True)
        self.assertIsNone(result)
        self.assertIsNotNone(error, "CLI compilation failure must stop startup")
        self.assertEqual(error.returncode, 101)
        self.assertEqual(events, ["cli_build"])
        provider_patch.__exit__.assert_called_once()
        self.assertEqual(cleanup.call_count, 2)
        self.assertIn("已恢复", output)
        self.assertNotIn("CLI 测试环境已就绪", output)


if __name__ == "__main__":
    (WORKSPACE / ".pytest_tmp").mkdir(exist_ok=True)
    unittest.main()
