import ast
import os
import unittest
from pathlib import Path


APP_DIR = Path(os.environ["ALIYVO_TEST_APP_DIR"])
MAIN = APP_DIR / "main.py"


class AltTabFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MAIN.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.main_window = next(
            node for node in cls.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
        )
        cls.methods = {
            node.name: node for node in cls.main_window.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_version_and_activation_handler(self):
        self.assertIn('ALIYVO_VERSION = "0.23.48"', self.source)
        self.assertIn("changeEvent", self.methods)
        self.assertIn("_restore_whatsapp_composer_focus", self.methods)
        change = ast.get_source_segment(
            self.source, self.methods["changeEvent"]
        )
        self.assertIn("QEvent.Type.ActivationChange", change)
        self.assertIn("self.isActiveWindow()", change)
        self.assertIn("QTimer.singleShot(90", change)
        self.assertIn("QTimer.singleShot(280", change)

    def test_composer_focus_uses_native_and_dom_focus(self):
        method = ast.get_source_segment(
            self.source, self.methods["_restore_whatsapp_composer_focus"]
        )
        self.assertIn("self.web.setFocus", method)
        self.assertIn("main.querySelector(\"footer\")", method)
        self.assertIn("[contenteditable='true'][role='textbox']", method)
        self.assertIn("editor.focus({preventScroll:true})", method)
        self.assertIn("self.web.page().runJavaScript(js,finished)", method)

    def test_does_not_steal_focus_from_tools_or_dialogs(self):
        method = ast.get_source_segment(
            self.source, self.methods["_restore_whatsapp_composer_focus"]
        )
        self.assertIn("_aliyvo_focus_blocked", method)
        self.assertIn("_quick_mode_tool", method)
        self.assertIn("QApplication.activeModalWidget()", method)
        for panel in (
            "technical_panel", "prazo_panel", "campaign_panel",
            "update_panel", "plate_panel",
        ):
            self.assertIn(panel, method)


if __name__ == "__main__":
    unittest.main()
