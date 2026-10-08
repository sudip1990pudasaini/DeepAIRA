"""Tests for tools/governance.py. Each failure mode is checked on a throwaway copy of the repo."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import governance as g  # noqa: E402

COPY_DIRS = ("prompts", "qa", "src", "aidlc", ".github")
COPY_FILES = (".importlinter", "pyproject.toml")


class Repo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for d in COPY_DIRS:
            if (ROOT / d).exists():
                shutil.copytree(ROOT / d, self.root / d)
        for f in COPY_FILES:
            if (ROOT / f).exists():
                shutil.copy(ROOT / f, self.root / f)
        self.addCleanup(self._tmp.cleanup)

    def run_check(self, only=None, strict=False):
        return g.run_checks(self.root, only, strict)

    def edit(self, rel, fn):
        p = self.root / rel
        p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")

    def assertError(self, rep, fragment):
        self.assertTrue(any(fragment in e for e in rep.errors), f"no error containing {fragment!r}: {rep.errors}")


class RepoIsHealthy(Repo):
    def test_repo_has_no_errors_in_dev_mode(self):
        rep = g.run_checks(ROOT)
        self.assertEqual(rep.errors, [])

    def test_release_gate_fails_today_by_design(self):
        rep = g.run_checks(ROOT, strict=True)
        self.assertTrue(rep.errors, "release gate should fail while prompts are drafts and datasets are seeds")


class PromptChecks(Repo):
    P = "prompts/extract_event/v0.1.0.md"

    def test_hash_mismatch(self):
        self.edit(self.P, lambda t: t + "\nextra\n")
        self.assertError(self.run_check(["prompts"]), "content changed but hash did not")

    def test_rehash_fixes_draft(self):
        self.edit(self.P, lambda t: t + "\nextra\n")
        g.rehash_prompts(self.root)
        self.assertEqual(self.run_check(["prompts"]).errors, [])

    def test_orphan_prompt(self):
        d = self.root / "prompts" / "other_prompt"
        d.mkdir()
        (d / "v0.1.0.md").write_text("x", encoding="utf-8")
        self.assertError(self.run_check(["prompts"]), "orphan prompt file")

    def test_missing_marker(self):
        self.edit(self.P, lambda t: t.replace("untrusted data", "data"))
        g.rehash_prompts(self.root)
        self.assertError(self.run_check(["prompts"]), "required marker missing")

    def test_placeholder_outside_tags(self):
        self.edit(self.P, lambda t: t.replace("## Output", "Text: {{untrusted_text}}\n\n## Output"))
        g.rehash_prompts(self.root)
        self.assertError(self.run_check(["prompts"]), "appears outside the untrusted-input tags")

    def test_approved_needs_eval_run(self):
        self.edit("prompts/registry.toml", lambda t: t.replace('status = "draft"', 'status = "approved"', 1))
        self.assertError(self.run_check(["prompts"]), "approved prompts need 'tested_model'")

    def test_approved_prompt_is_immutable(self):
        self.edit("prompts/registry.toml", lambda t: t.replace('status = "draft"', 'status = "approved"', 1))
        g.rehash_prompts(self.root)
        self.edit(self.P, lambda t: t + "\nchange\n")
        g.rehash_prompts(self.root)  # must not rewrite approved hashes
        self.assertError(self.run_check(["prompts"]), "content changed but hash did not")


class DatasetChecks(Repo):
    C = "qa/datasets/calendar/cases.jsonl"

    def rewrite(self, fn):
        rows = [json.loads(x) for x in (self.root / self.C).read_text().splitlines() if x.strip()]
        fn(rows)
        (self.root / self.C).write_text("".join(json.dumps(r) + "\n" for r in rows))

    def test_manifest_hash_mismatch(self):
        self.edit(self.C, lambda t: t.replace("dentist", "dentist2", 1))
        self.assertError(self.run_check(["datasets"]), "manifest hash did not")

    def test_bad_enum(self):
        self.rewrite(lambda r: r[0].update(difficulty="impossible"))
        g.update_manifests(self.root)
        self.assertError(self.run_check(["datasets"]), "difficulty")

    def test_duplicate_id(self):
        self.rewrite(lambda r: r[1].update(id=r[0]["id"]))
        g.update_manifests(self.root)
        self.assertError(self.run_check(["datasets"]), "duplicate id")

    def test_real_looking_email_rejected(self):
        self.rewrite(lambda r: r[0]["input"].update(text="Contact jane.doe@gmail.com"))
        g.update_manifests(self.root)
        self.assertError(self.run_check(["datasets"]), "possible real personal data")

    def test_ssn_and_card_rejected(self):
        self.rewrite(lambda r: r[0]["input"].update(text="SSN 123-45-6789 card 4111 1111 1111 1111"))
        g.update_manifests(self.root)
        errs = " ".join(self.run_check(["datasets"]).errors)
        self.assertIn("SSN", errs)
        self.assertIn("card", errs)

    def test_wrong_offset_rejected(self):
        # October in Chicago is -05:00; -06:00 is wrong.
        self.rewrite(lambda r: r[0]["expected"]["resolved"].update(start="2026-10-08T14:30:00-06:00"))
        g.update_manifests(self.root)
        self.assertError(self.run_check(["datasets"]), "offset does not match")

    def test_expected_must_match_prompt_schema(self):
        self.rewrite(lambda r: r[0]["expected"]["extraction"].update(confidence=7))
        g.update_manifests(self.root)
        self.assertError(self.run_check(["datasets"]), "confidence")


class ContextChecks(Repo):
    def test_unregistered_package(self):
        d = self.root / "src" / "deepaira" / "rogue"
        d.mkdir()
        (d / "__init__.py").write_text("")
        self.assertError(self.run_check(["contexts"]), "not registered")

    def test_layers_mismatch(self):
        self.edit(".importlinter", lambda t: t.replace("deepaira.items\n", "deepaira.items | deepaira.capture\n", 1))
        self.assertError(self.run_check(["contexts"]), "layers differ")

    def test_missing_engine_contract(self):
        self.edit(".importlinter", lambda t: t.replace("    django\n", "", 1))
        self.assertError(self.run_check(["contexts"]), "engine free of Django")


class DataMapAndTools(Repo):
    def test_model_field_must_be_classified(self):
        m = self.root / "src" / "deepaira" / "items" / "models.py"
        m.write_text("from django.db import models\n\nclass Item(models.Model):\n    nickname = models.CharField(max_length=20)\n")
        self.assertError(self.run_check(["datamap"]), "items.Item.nickname is not classified")

    def test_secret_cannot_enter_prompt(self):
        self.edit("qa/data-map.toml", lambda t: t.replace('sensitivity = "secret"\nstore = "postgres"\nretention = "until account deleted"\ndeletion = "hard_delete"\npurpose = "Sign-in"\nin_llm_prompt = false',
                  'sensitivity = "secret"\nstore = "postgres"\nretention = "until account deleted"\ndeletion = "hard_delete"\npurpose = "Sign-in"\nin_llm_prompt = true'))
        self.assertError(self.run_check(["datamap"]), "secret data must never enter an LLM prompt")

    def test_unregistered_dependency(self):
        self.edit("pyproject.toml", lambda t: t.replace('dependencies = ["tzdata"]', 'dependencies = ["tzdata", "left-pad-py"]'))
        self.assertError(self.run_check(["tools"]), "left-pad-py")

    def test_pending_tool_blocks_release_only(self):
        self.assertEqual(self.run_check(["tools"]).errors, [])
        self.assertTrue(self.run_check(["tools"], strict=True).errors)


class BlockerAndCostChecks(Repo):
    def test_core_blocker_cannot_be_removed(self):
        self.edit("qa/release_blockers.toml", lambda t: re.sub(r'\[\[blocker\]\]\nid = "missed_conflict".*?(?=\[\[blocker\]\]|\Z)', "", t, flags=re.S))
        self.assertError(self.run_check(["blockers"]), "missed_conflict")

    def test_implemented_blocker_needs_real_test(self):
        self.edit("qa/release_blockers.toml", lambda t: t.replace('status = "planned"', 'status = "implemented"', 1))
        self.assertError(self.run_check(["blockers"]), "does not exist")

    def test_cost_gate(self):
        over = {"extract_event": {"input_tokens": 99999, "output_tokens": 10, "cost_usd": 0.001}}
        self.assertTrue(g.cost_gate(self.root, over))
        ok = {"extract_event": {"input_tokens": 1000, "output_tokens": 100, "cost_usd": 0.005}}
        self.assertEqual(g.cost_gate(self.root, ok), [])
        doubled = g.cost_gate(self.root, ok, {"extract_event": {"cost_usd": 0.002}})
        self.assertTrue(any("doubled" in f for f in doubled))

    def test_unpinned_action_blocks_release_only(self):
        self.assertEqual(self.run_check(["ci"]).errors, [])
        self.assertTrue(self.run_check(["ci"], strict=True).errors)


class SchemaValidator(unittest.TestCase):
    def test_subset(self):
        schema = {"type": "object", "required": ["a"], "additionalProperties": False,
                  "properties": {"a": {"type": "integer", "minimum": 1},
                                 "b": {"type": ["string", "null"], "enum": ["x", None]}}}
        self.assertEqual(g.validate_schema({"a": 1, "b": None}, schema), [])
        self.assertTrue(g.validate_schema({"a": 0}, schema))
        self.assertTrue(g.validate_schema({}, schema))
        self.assertTrue(g.validate_schema({"a": 1, "c": 1}, schema))
        self.assertTrue(g.validate_schema({"a": True}, schema))


if __name__ == "__main__":
    unittest.main()
