import unittest
from unittest.mock import Mock, patch

from app.auth import Auth, check_active_key, get_expiry_info
from app.launcher import run
import app.launcher as launcher_module


class AuthLauncherTest(unittest.TestCase):
    def test_auth_uses_current_product_name_and_stable_machine_key(self):
        auth = Auth(machine_id_provider=lambda: "MACHINE", fingerprint_provider=lambda: "12345678")

        self.assertEqual(auth.job_name, "SmartTikTok")
        self.assertTrue(auth.machine_id.startswith("MACHINE"))
        self.assertTrue(auth.machine_id.endswith("12345678"))
        self.assertEqual(
            auth.payload,
            {"machine_id": auth.machine_id, "job_name": "SmartTikTok"},
        )

    def test_check_active_key_returns_false_when_response_missing_user(self):
        response = Mock()
        response.json.return_value = {"detail": "not found"}

        self.assertFalse(
            check_active_key(
                auth=Auth(machine_id_provider=lambda: "MACHINE", fingerprint_provider=lambda: "12345678"),
                request_get=lambda *args, **kwargs: response,
            )
        )

    def test_get_expiry_info_returns_failure_without_valid_response(self):
        response = Mock()
        response.json.return_value = {"detail": "not found"}

        result = get_expiry_info(
            auth=Auth(machine_id_provider=lambda: "MACHINE", fingerprint_provider=lambda: "12345678"),
            request_get=lambda *args, **kwargs: response,
        )

        self.assertEqual(result["success"], False)
        self.assertEqual(result["days_remaining"], 0)

    def test_launcher_shows_main_window_when_key_active(self):
        app = Mock()
        app.exec.return_value = 0
        main_window = Mock()
        login_form = Mock()

        with patch.object(launcher_module, "_create_app_icon", return_value=None):
            result = run(
                app_factory=lambda argv: app,
                main_window_factory=lambda: main_window,
                login_form_factory=lambda: login_form,
                active_key_checker=lambda: True,
                argv=[],
            )

        self.assertEqual(result, 0)
        main_window.show.assert_called_once_with()
        login_form.show.assert_not_called()

    def test_launcher_shows_registration_form_when_key_inactive(self):
        app = Mock()
        app.exec.return_value = 0
        main_window = Mock()
        login_form = Mock()

        with patch.object(launcher_module, "_create_app_icon", return_value=None):
            result = run(
                app_factory=lambda argv: app,
                main_window_factory=lambda: main_window,
                login_form_factory=lambda: login_form,
                active_key_checker=lambda: False,
                argv=[],
            )

        self.assertEqual(result, 0)
        login_form.show.assert_called_once_with()
        main_window.show.assert_not_called()

    def test_launcher_applies_logo_to_app_window_and_taskbar(self):
        app = Mock()
        app.exec.return_value = 0
        main_window = Mock()
        icon = Mock()
        icon.isNull.return_value = False

        with (
            patch.object(launcher_module, "_set_windows_app_user_model_id") as set_app_id,
            patch.object(launcher_module.QtGui, "QIcon", return_value=icon) as qicon,
        ):
            result = run(
                app_factory=lambda argv: app,
                main_window_factory=lambda: main_window,
                login_form_factory=Mock(),
                active_key_checker=lambda: True,
                argv=[],
            )

        self.assertEqual(result, 0)
        set_app_id.assert_called_once_with(launcher_module.APP_USER_MODEL_ID)
        qicon.assert_called_once_with(str(launcher_module._app_icon_path()))
        app.setWindowIcon.assert_called_once_with(icon)
        main_window.setWindowIcon.assert_called_once_with(icon)


if __name__ == "__main__":
    unittest.main()
