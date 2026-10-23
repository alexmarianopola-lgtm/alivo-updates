import ast
import os
import unittest
from pathlib import Path


APP_DIR = Path(os.environ["ALIYVO_TEST_APP_DIR"])
MAIN = APP_DIR / "main.py"


class CampaignPersistenceAgendaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MAIN.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_version_and_files_are_outside_program_folder(self):
        self.assertIn('ALIYVO_VERSION = "0.23.49"', self.source)
        self.assertIn('USER_DATA_DIR = ALIYVO_USER_DIR / "dados"', self.source)
        self.assertIn('CAMPAIGN_LISTS_FILE = USER_DATA_DIR / "campaign_lists.json"', self.source)
        self.assertIn('CAMPAIGN_DRAFT_FILE = USER_DATA_DIR / "campaign_draft.json"', self.source)

    def test_draft_is_atomic_and_restored(self):
        self.assertIn("def _save_draft(self):", self.source)
        self.assertIn("temp.replace(self.draft_file)", self.source)
        self.assertIn("def _load_draft(self):", self.source)
        self.assertIn("Campanha anterior recuperada automaticamente", self.source)
        self.assertIn("self.message.textChanged.connect(self._schedule_draft_save)", self.source)
        self.assertIn("self.campaign_panel._save_draft()", self.source)

    def test_whatsapp_agenda_import_is_connected(self):
        self.assertIn('QPushButton("📥 Importar agenda do WhatsApp")', self.source)
        self.assertIn("on_import_whatsapp_agenda", self.source)
        self.assertIn("def _campaign_read_whatsapp_agenda(self):", self.source)
        self.assertIn("WPP.contact.list({onlyMyContacts:true})", self.source)
        self.assertIn("def _campaign_show_whatsapp_agenda(self,result):", self.source)
        self.assertIn("panel.add_contacts_from_whatsapp(selected)", self.source)

    def test_direct_send_engine_remains_in_place(self):
        self.assertIn("WPP.chat.sendTextMessage", self.source)
        self.assertIn("WPP.chat.sendFileMessage", self.source)
        self.assertIn("_campaign_wajs_prepare(\"import_agenda\")", self.source)
        self.assertIn("if action==\"send\" and not panel.running", self.source)


if __name__ == "__main__":
    unittest.main()
