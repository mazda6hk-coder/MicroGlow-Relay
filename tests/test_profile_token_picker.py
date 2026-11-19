"""添加/修改模型对话框：模型列表只在手动点击时读取，Token 只给固定档位。

背景：之前粘贴地址 + KEY 后 800ms 防抖自动拉取供应商模型列表，
填错一个字符就发一次请求、返回一堆无关模型，还容易顶掉把手上正在输的模型名。
现在改成「点一下才读」；输入/输出 Token 也从自由数字改成摆出来的固定档位。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from storage import Settings  # noqa: E402
from server import Gateway  # noqa: E402
from app.bridge import Bridge  # noqa: E402


def _profile(bridge, **overrides):
    base = {
        "provider": "自定义 / 中转服务",
        "provider_name": "测试中转",
        "protocol": "chat",
        "base_url": "https://api.example.com/v1/chat/completions",
        "model": "demo-model",
        "tool_calls": True,
        "image_input": False,
        "thinking": False,
    }
    base.update(overrides)
    return bridge.save_profile(base, "main-key-1")


class TokenPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_input_presets_are_fixed_numbers(self):
        from app.dialogs import INPUT_TOKEN_CHOICES, TokenPicker

        labels = [label for _value, label in INPUT_TOKEN_CHOICES]
        values = [value for value, _label in INPUT_TOKEN_CHOICES]
        self.assertEqual(labels, ["256K", "384K", "512K", "768K", "1M"])
        self.assertEqual(values, [262144, 393216, 524288, 786432, 1048576])
        picker = TokenPicker(INPUT_TOKEN_CHOICES)
        try:
            self.assertEqual(picker.value(), 262144)
            picker.setValue(1048576)
            self.assertEqual(picker.value(), 1048576)
            self.assertEqual(len(picker._buttons), 5)
        finally:
            picker.deleteLater()

    def test_output_presets_are_fixed_numbers(self):
        from app.dialogs import OUTPUT_TOKEN_CHOICES, TokenPicker

        self.assertEqual(OUTPUT_TOKEN_CHOICES, [(65536, "64K"), (131072, "128K")])
        picker = TokenPicker(OUTPUT_TOKEN_CHOICES)
        try:
            picker.setValue(131072)
            self.assertEqual(picker.value(), 131072)
        finally:
            picker.deleteLater()

    def test_value_outside_presets_falls_back_to_manual_entry(self):
        """旧配置里的 128000 / 8192 不在档位内：走「手动」档，不再伪装成档位芯片。"""
        from app.dialogs import OUTPUT_TOKEN_CHOICES, TokenPicker

        picker = TokenPicker(OUTPUT_TOKEN_CHOICES)
        try:
            picker.setValue(8192)
            self.assertEqual(picker.value(), 8192)
            self.assertEqual(len(picker._buttons), 2)
            self.assertTrue(picker._manual_button.isChecked())
            self.assertEqual(picker._manual.text(), "8,192")
        finally:
            picker.deleteLater()

    def test_manual_entry_accepts_numbers_and_falls_back_on_garbage(self):
        """手动档：输入数字立即生效；非法输入回退到最近一次有效值。"""
        from app.dialogs import OUTPUT_TOKEN_CHOICES, TokenPicker

        picker = TokenPicker(OUTPUT_TOKEN_CHOICES)
        try:
            picker._manual.setText("96000")
            self.assertTrue(picker._manual_button.isChecked())
            self.assertEqual(picker.value(), 96000)
            picker._manual.setText("abc")      # 非法：回退最近有效值，不炸
            self.assertEqual(picker.value(), 96000)
            picker._buttons[65536].click()     # 点回档位：手动输入清空
            self.assertEqual(picker.value(), 65536)
            self.assertEqual(picker._manual.text(), "")
        finally:
            picker.deleteLater()


class ProfileDialogBehaviourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-picker-")
        self.settings = Settings(Path(self.temporary.name))
        self.gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        self.bridge = Bridge(self.settings, self.gateway)

    def tearDown(self):
        self.gateway.stop()
        self.temporary.cleanup()

    def _dialog(self, profile=None, key=""):
        from app.dialogs import ProfileDialog
        return ProfileDialog(self.bridge, profile, key)

    def test_new_profile_defaults_to_512k_and_128k(self):
        dialog = self._dialog()
        try:
            self.assertEqual(dialog.input_tokens.value(), 524288)
            self.assertEqual(dialog.output_tokens.value(), 131072)
        finally:
            dialog.deleteLater()

    def test_editing_legacy_profile_keeps_its_numbers(self):
        profile = _profile(self.bridge, input_tokens=128000, output_tokens=8192)
        dialog = self._dialog(profile, "main-key-1")
        try:
            self.assertEqual(dialog.input_tokens.value(), 128000)
            self.assertEqual(dialog.output_tokens.value(), 8192)
            dialog.save()
            self.assertEqual(dialog.result(), QDialog.Accepted)
        finally:
            dialog.deleteLater()
        saved = self.bridge.profile(profile["id"], include_key=True)
        self.assertEqual((saved["input_tokens"], saved["output_tokens"]), (128000, 8192))

    def test_typing_connection_details_does_not_fetch_models(self):
        """填完地址/KEY 后干等：不发请求、下拉里也没有任何模型。"""
        calls = []

        def fake(profile, on_done, on_error):
            calls.append(profile)
            on_done(["m-a", "m-b"])

        self.bridge.discover_models = fake
        dialog = self._dialog()
        try:
            dialog.provider_name.setText("测试中转")
            dialog.base_url.setText("https://api.example.com/v1")
            dialog.api_key.setText("sk-test-123")
            dialog.model.setCurrentText("")
            QTest.qWait(1500)          # 覆盖旧实现的 800ms 防抖窗口
            self.assertEqual(calls, [])
            self.assertEqual(dialog.fetched_models, [])
            self.assertEqual(dialog.model.count(), 0)
            self.assertFalse(dialog.model_choices.isEnabled())

            dialog.discover_models()   # 只有手动点「获取可用模型」才发请求
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["base_url"], "https://api.example.com/v1/chat/completions")
            self.assertEqual(dialog.model.count(), 2)
            self.assertTrue(dialog.model_choices.isEnabled())
        finally:
            dialog.deleteLater()

    def test_changing_connection_clears_previous_results(self):
        dialog = self._dialog()
        try:
            dialog._models_ready(["m-a", "m-b"])
            self.assertEqual(dialog.model.count(), 2)
            dialog.base_url.setText("https://other.example.com/v1")
            self.assertEqual(dialog.fetched_models, [])
            self.assertEqual(dialog.model.count(), 0)
        finally:
            dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
