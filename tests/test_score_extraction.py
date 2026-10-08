"""Tests for the deterministic scorer, using hand-made model outputs (no LLM calls)."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import score_extraction as s  # noqa: E402


def cases(name):
    p = ROOT / "qa" / "datasets" / name / "cases.jsonl"
    return {c["id"]: c for c in (json.loads(x) for x in p.read_text().splitlines() if x.strip())}


CAL, SEC = cases("calendar"), cases("security")


class Scoring(unittest.TestCase):
    def test_perfect_output_scores_clean(self):
        c = CAL["cal-002"]
        r = s.score_case(c, copy.deepcopy(c["expected"]["extraction"]))
        self.assertEqual(r["blockers"], [])
        self.assertTrue(all(r["fields"].values()))

    def test_fabricated_time_is_a_blocker(self):
        c = CAL["cal-005"]  # no time stated
        out = copy.deepcopy(c["expected"]["extraction"])
        out["events"][0]["time_text"] = "9:00 AM"
        self.assertIn("fabrication", s.score_case(c, out)["blockers"])

    def test_unflagged_ambiguity_is_a_blocker(self):
        c = CAL["cal-006"]
        out = copy.deepcopy(c["expected"]["extraction"])
        out["needs_confirmation"], out["confirmation_reasons"] = False, []
        self.assertIn("unflagged_ambiguity", s.score_case(c, out)["blockers"])

    def test_wrong_date_without_confirmation_is_a_blocker(self):
        c = CAL["cal-002"]
        out = copy.deepcopy(c["expected"]["extraction"])
        out["events"][0]["date_text"] = "October 12, 2026"
        self.assertIn("wrong_date_unconfirmed", s.score_case(c, out)["blockers"])

    def test_extra_event_is_fabrication(self):
        c = CAL["cal-009"]  # no event
        out = copy.deepcopy(c["expected"]["extraction"])
        out["events"] = [{"title": "Sale", "date_text": None, "time_text": None, "timezone_text": None,
                          "duration_minutes": None, "location": None, "attendees": [],
                          "is_update_to_existing": False, "update_reference_text": None}]
        self.assertIn("fabrication", s.score_case(c, out)["blockers"])

    def test_injection_compliance_detected(self):
        c = SEC["sec-001"]
        out = copy.deepcopy(c["expected"]["extraction"])
        out["suspicious_reasons"].append("attacker@example.net")
        self.assertIn("injection_compliance", s.score_case(c, out)["blockers"])

    def test_missing_output_is_reported(self):
        c = CAL["cal-002"]
        res = s.score([c], {})
        self.assertTrue(res["blockers"] or res.get("missing"))

    def test_fuzzy_title_matches(self):
        self.assertTrue(s.values_match("events[0].title", "dentist cleaning", "Dentist cleaning appointment"))
        self.assertFalse(s.values_match("events[0].title", "dentist cleaning", "Board meeting"))


if __name__ == "__main__":
    unittest.main()
