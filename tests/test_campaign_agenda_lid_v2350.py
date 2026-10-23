from pathlib import Path
import os
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("ALIYVO_TEST_APP_DIR", ROOT / "work" / "current" / "_app")) / "main.py"


class CampaignAgendaLidTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_version_and_two_agenda_sources(self):
        self.assertIn('ALIYVO_VERSION = "0.23.50"', self.source)
        self.assertIn('WPP.contact.list({onlyMyContacts:true})', self.source)
        self.assertIn('WPP.chat.list({onlyUsers:true})', self.source)

    def test_lid_is_resolved_or_kept_as_valid_chat(self):
        self.assertIn('WPP.contact.getPnLidEntry(sid)', self.source)
        self.assertIn('stored_chat_id.endswith("@lid")', self.source)
        self.assertIn('stored_chat_id if valid_chat_id else phone+"@c.us"', self.source)

    def test_import_accepts_contacts_without_exposed_phone(self):
        self.assertIn('key=phone or chat_id', self.source)
        self.assertIn('if not phone and not valid_chat_id:continue', self.source)


if __name__ == "__main__":
    unittest.main()
