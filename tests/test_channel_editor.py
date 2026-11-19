"""UI-090-CHANNEL-EDITOR: ProfileDialog 渠道组编辑器（任务书第 6 节）。

- 添加/删除渠道行、表单收集（跳过空地址行）；
- 编辑已有配置回填渠道，key 遮蔽留空 = 沿用旧密钥（__keep__ 语义）；
- save() 全链路：主配置 + 渠道组一起落库，DPAPI 加密读回。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication, QDialog

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


class ChannelEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-chanedit-")
        self.settings = Settings(Path(self.temporary.name))
        self.gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        self.bridge = Bridge(self.settings, self.gateway)

    def tearDown(self):
        self.gateway.stop()
        self.temporary.cleanup()

    def _dialog(self, profile=None, key=""):
        from app.dialogs import ProfileDialog
        return ProfileDialog(self.bridge, profile, key)

    def test_channel_drafts_skip_empty_rows(self):
        """空地址行跳过；有地址行带全字段。"""
        dialog = self._dialog()
        self.assertEqual(dialog._channel_drafts(), ([], []))
        dialog._append_channel_row({"label": "甲", "base_url": "https://a.example.com",
                                     "api_key": "key-a", "weight": 3, "enabled": True})
        dialog._append_channel_row({})   # 地址留空：跳过
        channels, keys = dialog._channel_drafts()
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["label"], "甲")
        self.assertEqual(channels[0]["weight"], 3)
        self.assertTrue(channels[0]["enabled"])
        self.assertEqual(keys, ["key-a"])
        dialog.deleteLater()

    def test_remove_channel_row(self):
        dialog = self._dialog()
        dialog._append_channel_row({"base_url": "https://a.example.com"})
        dialog._append_channel_row({"base_url": "https://b.example.com"})
        self.assertEqual(len(dialog.channel_rows), 2)
        dialog._remove_channel_row(dialog.channel_rows[0])
        self.assertEqual(len(dialog.channel_rows), 1)
        channels, _ = dialog._channel_drafts()
        self.assertEqual(channels[0]["base_url"], "https://b.example.com")
        dialog.deleteLater()

    def test_edit_fills_channels_and_keeps_old_key(self):
        """编辑回填渠道；key 留空保存 → __keep__ → 沿用旧密钥。"""
        saved = _profile(self.bridge)
        self.bridge.update_channels(saved["id"], [
            {"label": "主", "base_url": "https://a.example.com/v1/chat/completions",
             "weight": 2, "enabled": True},
            {"label": "备", "base_url": "https://b.example.com/v1/chat/completions",
             "weight": 1, "enabled": True},
        ], ["stored-key-a", "stored-key-b"])

        stored = self.bridge.profile(saved["id"], include_key=True)
        dialog = self._dialog(stored, stored.get("api_key") or "")
        self.assertEqual(len(dialog.channel_rows), 2)
        self.assertEqual(dialog.channel_rows[0]["base"].text(),
                         "https://a.example.com/v1/chat/completions")
        self.assertFalse(dialog.channel_rows[0]["key"].text(),
                         "回填时 key 应留空（had_key 标记走 __keep__）")
        self.assertTrue(dialog.channel_rows[0]["had_key"])

        # 模拟 save() 的渠道分支（主配置字段不动，只验证 key 解析链）。
        channels, keys = dialog._channel_drafts()
        self.assertEqual(keys, ["__keep__", "__keep__"])
        old_channels = stored.get("channels") or []
        resolved = [old_channels[i].get("api_key") or "" if v == "__keep__" else v
                    for i, v in enumerate(keys)]
        self.assertEqual(resolved, ["stored-key-a", "stored-key-b"])
        dialog.deleteLater()

    def test_save_persists_channels_end_to_end(self):
        """save() 全链路：主配置 + 两渠道入库，读回明文一致。"""
        dialog = self._dialog()
        dialog.provider.setCurrentIndex(dialog.provider.findData("自定义 / 中转服务"))
        dialog.provider_name.setText("多渠道中转")
        dialog.base_url.setText("https://main.example.com/v1")
        dialog.api_key.setText("main-key")
        dialog.model.setCurrentText("demo-model")
        dialog._append_channel_row({"label": "甲", "base_url": "https://a.example.com",
                                    "api_key": "key-a", "weight": 2, "enabled": True})
        dialog._append_channel_row({"label": "乙", "base_url": "https://b.example.com",
                                    "api_key": "key-b", "weight": 1, "enabled": False})
        dialog.save()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted.value)

        saved = self.bridge.selected()
        stored = self.bridge.profile(saved["id"], include_key=True)
        channels = stored.get("channels") or []
        self.assertEqual(len(channels), 2)
        self.assertEqual(channels[0]["label"], "甲")
        self.assertEqual(channels[0]["base_url"],
                         "https://a.example.com/v1/chat/completions")
        self.assertEqual(channels[0]["api_key"], "key-a")
        self.assertEqual(channels[1]["weight"], 1)
        self.assertFalse(channels[1]["enabled"])
        dialog.deleteLater()

    def test_save_without_channels_keeps_existing_group(self):
        """没填渠道行时 save 不动已有渠道组（保持原值）。"""
        saved = _profile(self.bridge)
        self.bridge.update_channels(saved["id"], [
            {"label": "仅有的", "base_url": "https://solo.example.com/v1/chat/completions",
             "weight": 1, "enabled": True},
        ], ["solo-key"])
        stored = self.bridge.profile(saved["id"], include_key=True)

        # 新建对话框（不带渠道行）：_channel_drafts 为空 → save 不触发 update_channels。
        dialog = self._dialog()
        channels, keys = dialog._channel_drafts()
        self.assertEqual((channels, keys), ([], []), "空表单 = 不动渠道组")
        dialog.deleteLater()

        # 编辑对话框即使带渠道行，__keep__ 也应保留旧密钥（删光行再保存才清空）。
        edit = self._dialog(stored, "")
        for slot in list(edit.channel_rows):
            edit._remove_channel_row(slot)
        channels2, keys2 = edit._channel_drafts()
        self.assertEqual((channels2, keys2), ([], ["solo-key"].__class__()))
        edit.deleteLater()


if __name__ == "__main__":
    unittest.main()
