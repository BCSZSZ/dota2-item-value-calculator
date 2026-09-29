import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_data as updater


class SnapshotTests(unittest.TestCase):
    def test_commented_group_names_and_duplicate_items(self):
        source = "\n".join('"' + group + '" // comment\n{ "item" "item_blink" "item" "item_blink" }' for group in updater.GROUPS)
        groups = updater.parse_shops(source)
        self.assertEqual(groups["magics"], ["blink"])
        self.assertEqual(len(groups), 11)

    def test_free_items_are_included_and_missing_data_is_rejected(self):
        item = {"dname": "Observer Ward", "cost": 0, "img": "/ward.png"}
        self.assertEqual(updater.validate_items({"ward": item}, {"consumables": ["ward"]}), ["ward"])
        with self.assertRaises(ValueError):
            updater.validate_items({}, {"consumables": ["ward"]})

    def test_same_patch_only_checks_version(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "data").mkdir()
            snapshot = site / "data/items.json"
            snapshot.write_text('{"patch":"7.41f"}')
            before = snapshot.read_bytes()
            response = json.dumps({"patches": [{"patch_number": "7.41f", "patch_timestamp": 10}]}).encode()
            with patch.object(updater, "fetch", return_value=response) as fetch:
                self.assertFalse(updater.sync(site))
                fetch.assert_called_once_with(updater.PATCHES)
            self.assertEqual(snapshot.read_bytes(), before)

    def test_failed_update_preserves_previous_version(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "data").mkdir()
            snapshot = site / "data/items.json"
            snapshot.write_text('{"patch":"7.41e"}')
            before = snapshot.read_bytes()
            response = json.dumps({"patches": [{"patch_number": "7.41f", "patch_timestamp": 10}]}).encode()
            with patch.object(updater, "fetch", side_effect=[response, OSError("upstream unavailable")]):
                with self.assertRaises(OSError):
                    updater.sync(site)
            self.assertEqual(snapshot.read_bytes(), before)

    def test_waits_for_upstream_instead_of_publishing_old_data(self):
        with tempfile.TemporaryDirectory() as folder:
            version = json.dumps({"patches": [{"patch_number": "7.42", "patch_timestamp": 2000000000}]}).encode()
            old_commit = json.dumps([{"sha": "old", "commit": {"committer": {"date": "2026-01-01T00:00:00Z"}}}]).encode()
            with patch.object(updater, "fetch", side_effect=[version, old_commit]) as fetch:
                self.assertFalse(updater.sync(Path(folder)))
                self.assertEqual(fetch.call_count, 2)
            self.assertFalse((Path(folder) / "data/items.json").exists())

    def test_new_patch_is_published_once_after_all_assets_succeed(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            version = json.dumps({"patches": [{"patch_number": "7.42", "patch_timestamp": 1}]}).encode()
            commit = json.dumps([{"sha": "new", "commit": {"committer": {"date": "2026-01-01T00:00:00Z"}}}]).encode()
            items = json.dumps({"blink": {"dname": "Blink", "cost": 2250, "img": "/blink.png"}}).encode()
            shops = "\n".join('"' + g + '" { "item" "item_blink" }' for g in updater.GROUPS).encode()
            with patch.object(updater, "fetch", side_effect=[version, commit, commit, items, shops, b"\x89PNG\r\n\x1a\n"]):
                self.assertTrue(updater.sync(site))
            data = json.loads((site / "data/items.json").read_text())
            self.assertEqual(data["patch"], "7.42")
            self.assertEqual(data["count"], 1)
            with patch.object(updater, "fetch", return_value=version) as fetch:
                self.assertFalse(updater.sync(site))
                fetch.assert_called_once_with(updater.PATCHES)


if __name__ == "__main__":
    unittest.main()
