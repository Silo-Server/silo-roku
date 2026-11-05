"""Release version checks; run python3 -I -B scripts/test_release_version.py."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("release_version", ROOT / "scripts/release-version.py")
RV = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RV)


class NextReleaseTests(unittest.TestCase):
    def test_first_build_needs_a_version(self):
        with self.assertRaises(RV.ReleaseError):
            RV.next_release([], "build")
        self.assertEqual(RV.next_release([], "build", "1.0.0"),
                         {"version": "1.0.0", "build": "1", "tag": "v1.0.0-beta.1", "previous_tag": ""})

    def test_build_continues_the_unreleased_version(self):
        result = RV.next_release(["v1.0.0-beta.1", "v1.0.0-beta.2"], "build")
        self.assertEqual(result["tag"], "v1.0.0-beta.3")
        self.assertEqual(result["previous_tag"], "v1.0.0-beta.2")

    def test_build_counter_never_resets(self):
        tags = ["v1.0.0-beta.7", "v1.0.0"]
        self.assertEqual(RV.next_release(tags, "minor")["tag"], "v1.1.0-beta.8")
        self.assertEqual(RV.next_release(tags, "patch")["tag"], "v1.0.1-beta.8")

    def test_released_version_takes_no_more_builds(self):
        with self.assertRaises(RV.ReleaseError):
            RV.next_release(["v1.0.0-beta.4", "v1.0.0"], "build")

    def test_draft_counts_as_released(self):
        with self.assertRaises(RV.ReleaseError):
            RV.next_release(["v1.0.0-beta.4"], "build", drafts=["v1.0.0"])
        self.assertEqual(RV.next_release(["v1.0.0-beta.4"], "minor", drafts=["v1.0.0"])["version"], "1.1.0")

    def test_hotfix_while_next_version_is_in_testing(self):
        tags = ["v1.0.0-beta.4", "v1.0.0", "v1.1.0-beta.5", "v1.0.1-beta.6"]
        # The newest unreleased version continues, not the latest tag's.
        self.assertEqual(RV.next_release(tags, "build")["tag"], "v1.1.0-beta.7")

    def test_explicit_version_must_be_newer_than_the_release(self):
        with self.assertRaises(RV.ReleaseError):
            RV.next_release(["v1.1.0-beta.3", "v1.1.0"], "build", "1.0.5")
        with self.assertRaises(RV.ReleaseError):
            RV.next_release([], "build", "1.0")

    def test_other_tags_are_ignored(self):
        result = RV.next_release(["beta-latest", "v1.0", "v1.0.0-rc.1", "v1.0.0-beta.2"], "build")
        self.assertEqual(result["tag"], "v1.0.0-beta.3")


class BetaReleaseTests(unittest.TestCase):
    def test_beta_tag(self):
        self.assertEqual(RV.beta_release("v1.2.0-beta.42"),
                         {"version": "1.2.0", "build": "42", "tag": "v1.2.0-beta.42", "release_tag": "v1.2.0"})

    def test_rejects_store_tags(self):
        for name in ["v1.2.0", "1.2.0-beta.4", "v1.2-beta.4"]:
            with self.assertRaises(RV.ReleaseError):
                RV.beta_release(name)


class StoreNotesTests(unittest.TestCase):
    NOTES = "\n".join([
        "## What's Changed",
        "### 🚀 Features",
        "* feat(cards): draw card overlays by @someone in https://github.com/o/r/pull/39",
        "### Other changes",
        "* ci: rework packaging by @someone in https://github.com/o/r/pull/40",
        "* fix(player): keep playing in https://github.com/o/r/pull/41",
    ])

    def test_keeps_user_facing_entries(self):
        self.assertEqual(RV.store_notes(self.NOTES, 1500), "• Draw card overlays\n• Keep playing")

    def test_fits_the_limit(self):
        notes = RV.store_notes(self.NOTES, 25)
        self.assertLessEqual(len(notes), 25)
        self.assertTrue(notes.endswith("• And more."))

    def test_empty(self):
        self.assertEqual(RV.store_notes("", 1500), "Bug fixes and improvements.")


if __name__ == "__main__":
    unittest.main()
