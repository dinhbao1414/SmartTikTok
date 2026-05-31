import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app.paths as paths_module


class PathsTest(unittest.TestCase):
    def tearDown(self):
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        importlib.reload(paths_module)

    def test_source_paths_stay_under_project_root(self):
        module = importlib.reload(paths_module)

        self.assertEqual(module.DATA_DIR, module.ROOT_DIR / "data")
        self.assertEqual(module.PROFILES_PATH, module.DATA_DIR / "profiles.json")
        self.assertEqual(module.APP_DB_PATH, module.DATA_DIR / "app.db")
        self.assertEqual(module.DOWNLOADS_DIR, module.ROOT_DIR / "downloads")

    def test_frozen_paths_use_exe_folder_for_portable_writable_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe_path = Path(tmp) / "SmartTikTok.exe"
            with (
                patch.object(sys, "executable", str(exe_path)),
                patch.object(sys, "argv", [str(exe_path)]),
            ):
                sys.frozen = True
                module = importlib.reload(paths_module)

        expected_root = Path(tmp)
        self.assertEqual(module.DATA_DIR, expected_root / "data")
        self.assertEqual(module.PROFILES_PATH, expected_root / "data" / "profiles.json")
        self.assertEqual(module.APP_DB_PATH, expected_root / "data" / "app.db")
        self.assertEqual(module.DOWNLOADS_DIR, expected_root / "downloads")

    def test_onefile_paths_ignore_nuitka_extraction_cache(self):
        with tempfile.TemporaryDirectory() as outer, tempfile.TemporaryDirectory() as cache:
            outer_exe = Path(outer) / "SmartTikTok.exe"
            extracted_exe = Path(cache) / "SmartTikTok" / "onefile" / "SmartTikTok.exe"
            with (
                patch.object(sys, "executable", str(extracted_exe)),
                patch.object(sys, "argv", [str(outer_exe)]),
            ):
                sys.frozen = True
                module = importlib.reload(paths_module)

        self.assertEqual(module.DATA_DIR, Path(outer) / "data")
        self.assertNotIn("onefile", str(module.DATA_DIR).lower())

    def test_nuitka_onefile_paths_use_original_binary_dir_when_argv_is_cache(self):
        with tempfile.TemporaryDirectory() as outer, tempfile.TemporaryDirectory() as cache:
            outer_dir = Path(outer)
            cache_dir = Path(cache)
            extracted_exe = Path(cache) / "SmartTikTok" / "onefile" / "SmartTikTok.exe"
            compiled = SimpleNamespace(
                onefile=True,
                containing_dir=str(outer_dir),
                original_argv0=str(outer_dir / "SmartTikTok.exe"),
            )
            with (
                patch.object(sys, "executable", str(extracted_exe)),
                patch.object(sys, "argv", [str(extracted_exe)]),
                patch.object(paths_module, "__compiled__", compiled, create=True),
            ):
                sys.frozen = True
                module = importlib.reload(paths_module)

        self.assertEqual(module.APP_STATE_DIR, outer_dir)
        self.assertEqual(module.DATA_DIR, outer_dir / "data")
        self.assertFalse(str(module.DATA_DIR).startswith(str(cache_dir)))
        self.assertNotIn("SmartTikTok\\onefile".lower(), str(module.DATA_DIR).lower())

    def test_nuitka_onefile_paths_use_parent_exe_when_compiled_values_are_cache(self):
        with tempfile.TemporaryDirectory() as outer, tempfile.TemporaryDirectory() as cache:
            outer_dir = Path(outer)
            outer_exe = outer_dir / "SmartTikTok.exe"
            extracted_exe = Path(cache) / "SmartTikTok" / "onefile" / "SmartTikTok.exe"
            compiled = SimpleNamespace(
                onefile=True,
                containing_dir=str(extracted_exe.parent),
                original_argv0=str(extracted_exe),
            )
            fake_psutil = SimpleNamespace(
                Process=lambda pid: SimpleNamespace(exe=lambda: str(outer_exe))
            )
            with (
                patch.object(sys, "executable", str(extracted_exe)),
                patch.object(sys, "argv", [str(extracted_exe)]),
                patch.object(paths_module, "__compiled__", compiled, create=True),
                patch.dict(os.environ, {"NUITKA_ONEFILE_PARENT": "12345"}, clear=False),
                patch.dict(sys.modules, {"psutil": fake_psutil}),
            ):
                sys.frozen = True
                module = importlib.reload(paths_module)

        self.assertEqual(module.APP_STATE_DIR, outer_dir)
        self.assertEqual(module.DATA_DIR, outer_dir / "data")

    def test_nuitka_onefile_paths_use_parent_when_containing_dir_is_runtime_folder(self):
        with tempfile.TemporaryDirectory() as outer:
            outer_dir = Path(outer)
            runtime_dir = outer_dir / "SmartTikTok.runtime"
            runtime_exe = runtime_dir / "SmartTikTok.exe"
            compiled = SimpleNamespace(
                onefile=True,
                containing_dir=str(runtime_dir),
                original_argv0=str(runtime_exe),
            )
            with (
                patch.object(sys, "executable", str(runtime_exe)),
                patch.object(sys, "argv", [str(runtime_exe)]),
                patch.object(paths_module, "__compiled__", compiled, create=True),
            ):
                sys.frozen = True
                module = importlib.reload(paths_module)

        self.assertEqual(module.APP_STATE_DIR, outer_dir)
        self.assertEqual(module.DATA_DIR, outer_dir / "data")

    def test_compiled_paths_do_not_require_sys_frozen_flag(self):
        with tempfile.TemporaryDirectory() as outer:
            outer_dir = Path(outer)
            outer_exe = outer_dir / "SmartTikTok.exe"
            runtime_dir = outer_dir / "SmartTikTok.runtime"
            runtime_exe = runtime_dir / "SmartTikTok.exe"
            compiled = SimpleNamespace(
                onefile=True,
                containing_dir=str(outer_dir),
                original_argv0=str(outer_exe),
            )
            with (
                patch.object(sys, "executable", str(outer_exe)),
                patch.object(sys, "argv", [str(runtime_exe)]),
                patch.object(paths_module, "__compiled__", compiled, create=True),
            ):
                if hasattr(sys, "frozen"):
                    delattr(sys, "frozen")
                module = importlib.reload(paths_module)

        self.assertEqual(module.APP_STATE_DIR, outer_dir)
        self.assertEqual(module.DATA_DIR, outer_dir / "data")
        self.assertNotIn("SmartTikTok.runtime".lower(), str(module.DATA_DIR).lower())

    def test_resolve_app_path_expands_relative_paths_under_app_state_dir(self):
        module = importlib.reload(paths_module)

        self.assertEqual(module.resolve_app_path("downloads"), module.APP_STATE_DIR / "downloads")
        self.assertEqual(module.resolve_app_path("", module.DOWNLOADS_DIR), module.DOWNLOADS_DIR)


if __name__ == "__main__":
    unittest.main()
