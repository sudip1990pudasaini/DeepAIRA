#!/usr/bin/env python3
"""DeepAIRA governance checks. Standard library only (Python 3.11+).

This binds the written rules to automated checks so AI-generated changes cannot
quietly drift away from them:

  prompts    registry integrity, pinned hashes, untrusted-input markers
  datasets   golden-dataset schema, manifests, PII scan, timezone/offset sanity
  contexts   bounded-context registry vs. the import-linter layer contract
  datamap    every Django model field is classified in qa/data-map.toml
  tools      every declared dependency is in the vetted tool register
  blockers   every release blocker maps to a real test
  knowledge  AI-DLC shared knowledge exists and stays small (token cost)
  ci         GitHub Actions are pinned to full commit SHAs
  links      relative markdown links resolve

Commands:
  check          run all checks; warnings allowed (use in CI on every commit)
  release-gate   same checks, strict: warnings that mean "not ready" become errors
  manifest       regenerate dataset manifests (counts and hashes)
  rehash-prompts refresh hashes for DRAFT prompts only (approved prompts are immutable)
  gen-importlinter  print the layers block generated from qa/contexts.toml
  cost-gate      compare measured eval costs with qa/cost_budgets.toml
"""
from __future__ import annotations

import argparse
import ast
import configparser
import hashlib
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CHECKS = (
    "prompts", "datasets", "contexts", "datamap", "tools",
    "blockers", "knowledge", "ci", "links", "cost",
)

SEMVER = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?$")
SLUG = re.compile(r"^[a-z][a-z0-9_]*$")
PROMPT_STATUSES = {"draft", "approved", "retired"}
DATASET_STATUSES = {"seed", "candidate", "release"}
TOOL_STATUSES = {"approved", "pending-vetting", "rejected"}
SENSITIVITY = {"public", "internal", "personal", "sensitive", "secret"}
DELETION = {"hard_delete", "anonymize", "retain_legal"}
UNTRUSTED_OPEN = "<untrusted_input>"
UNTRUSTED_CLOSE = "</untrusted_input>"
# Every prompt that sees user content must contain all of these (case-insensitive).
REQUIRED_PROMPT_MARKERS = (
    UNTRUSTED_OPEN,
    UNTRUSTED_CLOSE,
    "untrusted data",
    "never follow instructions",
    "{{output_schema}}",
    "{{untrusted_text}}",
)
CORE_BLOCKERS = {
    "fabricated_or_misattributed_item",
    "wrong_date_accepted_without_confirmation",
    "missed_conflict",
    "action_without_approval",
    "cross_user_data_exposure",
}
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net"}
ALLOWED_EMAIL_SUFFIXES = (".example.com", ".example.org", ".example.net", ".test", ".invalid")
KNOWLEDGE_DIR = Path("aidlc/spaces/default/knowledge/aidlc-shared")
KNOWLEDGE_WORD_LIMIT = 6000  # every AI-DLC stage loads these; keep token cost bounded


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def issue(self, strict: bool, msg: str) -> None:
        """A warning during development, an error at release time."""
        (self.errors if strict else self.warnings).append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


# --------------------------------------------------------------------------- helpers

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_toml(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[tuple[int, object]]:
    rows: list[tuple[int, object]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        rows.append((lineno, json.loads(line)))
    return rows


def _type_ok(value, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def validate_schema(value, schema: dict, path: str = "$") -> list[str]:
    """Validate against a small JSON Schema subset.

    Supported keywords: type (string or list), enum, pattern, minLength, minimum,
    maximum, required, properties, additionalProperties (false only), items, minItems.
    The same schema files can be used with a full validator later.
    """
    errors: list[str] = []
    declared = schema.get("type")
    if declared is not None:
        types = declared if isinstance(declared, list) else [declared]
        if not any(_type_ok(value, t) for t in types):
            return [f"{path}: expected {'|'.join(types)}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                errors.extend(validate_schema(item, props[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected key {key!r}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(value):
                errors.extend(validate_schema(item, schema["items"], f"{path}[{i}]"))
    return errors


# --------------------------------------------------------------------------- prompts

def _prompt_blocks(text: str) -> list[str]:
    parts = re.split(r"(?m)^(?=\[\[prompt\]\])", text)
    return [p for p in parts if p.startswith("[[prompt]]")]


def check_prompts(root: Path, rep: Report, strict: bool) -> None:
    registry = root / "prompts" / "registry.toml"
    if not registry.exists():
        rep.error("prompts/registry.toml is missing")
        return
    entries = load_toml(registry).get("prompt", [])
    seen: set[tuple[str, str]] = set()
    referenced: set[Path] = set()
    latest: dict[str, tuple[tuple[int, ...], dict]] = {}
    for entry in entries:
        label = f"prompt {entry.get('id', '?')}@{entry.get('version', '?')}"
        for key in ("id", "version", "status", "file", "sha256", "output_schema", "schema_sha256"):
            if not entry.get(key):
                rep.error(f"{label}: missing '{key}'")
        pid, version, status = entry.get("id", ""), entry.get("version", ""), entry.get("status", "")
        if pid and not SLUG.match(pid):
            rep.error(f"{label}: id must be snake_case")
        if version and not SEMVER.match(version):
            rep.error(f"{label}: version must be semantic (x.y.z)")
        if status and status not in PROMPT_STATUSES:
            rep.error(f"{label}: status must be one of {sorted(PROMPT_STATUSES)}")
        if (pid, version) in seen:
            rep.error(f"{label}: duplicate id and version")
        seen.add((pid, version))
        if pid and version and SEMVER.match(version):
            key = tuple(int(x) for x in version.split("-")[0].split("."))
            if pid not in latest or key > latest[pid][0]:
                latest[pid] = (key, entry)

        file = entry.get("file")
        if file:
            path = root / file
            referenced.add(path.resolve())
            expected_name = f"prompts/{pid}/v{version}.md"
            if file != expected_name:
                rep.error(f"{label}: file must be {expected_name}")
            if not path.exists():
                rep.error(f"{label}: file {file} not found")
            else:
                if sha256_file(path) != entry.get("sha256"):
                    rep.error(
                        f"{label}: content changed but hash did not. Approved prompts are "
                        "immutable: create a new version file and registry entry. For a draft, "
                        "run `governance.py rehash-prompts`."
                    )
                _check_prompt_text(path.read_text(encoding="utf-8"), label, rep)

        schema_file = entry.get("output_schema")
        if schema_file:
            spath = root / schema_file
            referenced.add(spath.resolve())
            if not spath.exists():
                rep.error(f"{label}: output schema {schema_file} not found")
            else:
                if sha256_file(spath) != entry.get("schema_sha256"):
                    rep.error(f"{label}: output schema changed but schema_sha256 did not")
                try:
                    load_json(spath)
                except json.JSONDecodeError as exc:
                    rep.error(f"{label}: output schema is not valid JSON ({exc})")

        if status == "approved":
            for key in ("tested_model", "eval_run"):
                if not entry.get(key):
                    rep.error(f"{label}: approved prompts need '{key}'")
            run = entry.get("eval_run")
            if run and not (root / run).exists():
                rep.error(f"{label}: eval_run {run} not found")
            if not entry.get("datasets"):
                rep.error(f"{label}: approved prompts need 'datasets'")
        for ds in entry.get("datasets", []):
            if not (root / "qa" / "datasets" / ds / "manifest.json").exists():
                rep.error(f"{label}: dataset '{ds}' has no manifest")

    for pid, (_, entry) in latest.items():
        if entry.get("status") != "approved":
            rep.issue(strict, f"prompt {pid}@{entry.get('version')} is '{entry.get('status')}', not approved")

    prompts_dir = root / "prompts"
    for path in sorted(prompts_dir.glob("*/v*.md")):
        if path.resolve() not in referenced:
            rep.error(f"orphan prompt file not in registry: {path.relative_to(root)}")
    for path in sorted((prompts_dir / "schemas").glob("*.json")) if (prompts_dir / "schemas").exists() else []:
        if path.resolve() not in referenced:
            rep.warn(f"schema file not referenced by any prompt: {path.relative_to(root)}")


def _check_prompt_text(text: str, label: str, rep: Report) -> None:
    lowered = text.lower()
    for marker in REQUIRED_PROMPT_MARKERS:
        if marker.lower() not in lowered:
            rep.error(f"{label}: required marker missing: {marker}")
    # The rules section may mention the tags; the last pair is the real input block.
    open_at, close_at = text.rfind(UNTRUSTED_OPEN), text.rfind(UNTRUSTED_CLOSE)
    placeholder = "{{untrusted_text}}"
    if text.count(UNTRUSTED_OPEN) != text.count(UNTRUSTED_CLOSE):
        rep.error(f"{label}: untrusted-input tags are unbalanced")
    elif open_at >= 0 and close_at > open_at:
        outside = text[:open_at] + text[close_at + len(UNTRUSTED_CLOSE):]
        inside = text[open_at:close_at]
        if placeholder in outside:
            rep.error(f"{label}: {placeholder} appears outside the untrusted-input tags")
        if placeholder not in inside:
            rep.error(f"{label}: {placeholder} must sit inside the untrusted-input tags")
    elif open_at >= 0 or close_at >= 0:
        rep.error(f"{label}: untrusted-input tags are unbalanced")


def rehash_prompts(root: Path) -> list[str]:
    registry = root / "prompts" / "registry.toml"
    text = registry.read_text(encoding="utf-8")
    changed: list[str] = []
    out: list[str] = []
    parts = re.split(r"(?m)^(?=\[\[prompt\]\])", text)
    for part in parts:
        if part.startswith("[[prompt]]"):
            data = tomllib.loads(part).get("prompt", [{}])[0]
            if data.get("status") == "draft":
                for key, file_key in (("sha256", "file"), ("schema_sha256", "output_schema")):
                    path = root / data[file_key]
                    new = sha256_file(path)
                    if new != data.get(key):
                        part = re.sub(rf'(?m)^{key}\s*=\s*"[^"]*"', f'{key} = "{new}"', part)
                        changed.append(f"{data['id']}@{data['version']}: {key}")
            elif data.get("status") == "approved":
                pass  # immutable
        out.append(part)
    registry.write_text("".join(out), encoding="utf-8")
    return changed


# --------------------------------------------------------------------------- datasets

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")
FAKE_PHONE = re.compile(r"555[ .-]?01\d\d")
SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
LONG_DIGITS = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def _luhn(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def pii_findings(text: str) -> list[str]:
    found: list[str] = []
    for match in EMAIL.finditer(text):
        domain = match.group(1).lower()
        if domain not in ALLOWED_EMAIL_DOMAINS and not domain.endswith(ALLOWED_EMAIL_SUFFIXES):
            found.append(f"real-looking email domain: {match.group(0)}")
    for match in PHONE.finditer(text):
        if not FAKE_PHONE.search(match.group(0)):
            found.append(f"phone number not in the 555-01xx fictional range: {match.group(0)}")
    for match in SSN.finditer(text):
        found.append(f"SSN-shaped value: {match.group(0)}")
    for match in LONG_DIGITS.finditer(text):
        if _luhn(match.group(0)):
            found.append("card-number-shaped value (passes Luhn check)")
    return found


def _check_offsets(case: dict, label: str, rep: Report) -> None:
    resolved = case.get("expected", {}).get("resolved")
    if not isinstance(resolved, dict):
        return
    try:
        tz = ZoneInfo(case["input"]["user_timezone"])
    except (KeyError, ZoneInfoNotFoundError):
        rep.error(f"{label}: unknown user_timezone (install the 'tzdata' package?)")
        return
    for key in ("start", "end"):
        value = resolved.get(key)
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            rep.error(f"{label}: resolved.{key} is not ISO 8601: {value!r}")
            continue
        if parsed.tzinfo is None:
            rep.error(f"{label}: resolved.{key} must include a UTC offset")
            continue
        local = parsed.astimezone(tz)
        if local.utcoffset() != parsed.utcoffset():
            rep.error(f"{label}: resolved.{key} offset does not match {tz.key} on that date")
    for cand in resolved.get("candidates", []) or []:
        try:
            parsed = datetime.fromisoformat(cand)
        except ValueError:
            rep.error(f"{label}: candidate {cand!r} is not ISO 8601")
            continue
        if parsed.tzinfo is None:
            rep.error(f"{label}: candidate {cand!r} needs an offset")


def check_datasets(root: Path, rep: Report, strict: bool) -> None:
    base = root / "qa" / "datasets"
    schema_path = base / "schema" / "case.schema.json"
    if not schema_path.exists():
        rep.error("qa/datasets/schema/case.schema.json is missing")
        return
    case_schema = load_json(schema_path)
    manifests = sorted(p for p in base.glob("*/manifest.json") if p.parent.name != "schema")
    if not manifests:
        rep.warn("no dataset manifests found")
    all_ids: dict[str, str] = {}
    for mpath in manifests:
        name = mpath.parent.name
        try:
            manifest = load_json(mpath)
        except json.JSONDecodeError as exc:
            rep.error(f"dataset {name}: manifest is not valid JSON ({exc})")
            continue
        label = f"dataset {name}"
        for key in ("dataset", "category", "id_prefix", "release", "schema_version",
                    "status", "target_cases", "case_files"):
            if key not in manifest:
                rep.error(f"{label}: manifest missing '{key}'")
        if manifest.get("dataset") != name:
            rep.error(f"{label}: manifest 'dataset' must equal the folder name")
        status = manifest.get("status")
        if status not in DATASET_STATUSES:
            rep.error(f"{label}: status must be one of {sorted(DATASET_STATUSES)}")
        total = 0
        tag_counts: dict[str, int] = {}
        unverified = 0
        for cf in manifest.get("case_files", []):
            cpath = mpath.parent / cf.get("path", "")
            if not cpath.exists():
                rep.error(f"{label}: case file {cf.get('path')} not found")
                continue
            if sha256_file(cpath) != cf.get("sha256"):
                rep.error(f"{label}: {cf['path']} changed but manifest hash did not "
                          "(run `governance.py manifest` after reviewing the diff)")
            try:
                rows = read_jsonl(cpath)
            except json.JSONDecodeError as exc:
                rep.error(f"{label}: {cf['path']} has invalid JSON ({exc})")
                continue
            if len(rows) != cf.get("count"):
                rep.error(f"{label}: {cf['path']} has {len(rows)} cases, manifest says {cf.get('count')}")
            for lineno, case in rows:
                total += 1
                cid = case.get("id", f"line{lineno}") if isinstance(case, dict) else f"line{lineno}"
                clabel = f"{label} case {cid}"
                for err in validate_schema(case, case_schema):
                    rep.error(f"{clabel}: {err}")
                if not isinstance(case, dict):
                    continue
                if cid in all_ids:
                    rep.error(f"{clabel}: duplicate id (also in {all_ids[cid]})")
                all_ids[cid] = name
                prefix = manifest.get("id_prefix", "")
                if prefix and not str(cid).startswith(prefix + "-"):
                    rep.error(f"{clabel}: id must start with '{prefix}-'")
                if case.get("category") != manifest.get("category"):
                    rep.error(f"{clabel}: category must be '{manifest.get('category')}'")
                _check_extraction(root, case, clabel, rep)
                _check_offsets(case, clabel, rep)
                for finding in pii_findings(str(case.get("input", {}).get("text", ""))
                                            + " " + str(case.get("notes", ""))):
                    rep.error(f"{clabel}: possible real personal data: {finding}")
                for tag in case.get("tags", []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if case.get("label_status") != "human_verified":
                    unverified += 1
        if manifest.get("target_cases") and total < manifest["target_cases"]:
            rep.issue(strict, f"{label}: {total} of {manifest['target_cases']} target cases")
        if unverified:
            rep.issue(strict, f"{label}: {unverified} case label(s) await human verification")
        if status != "release":
            rep.issue(strict, f"{label}: status is '{status}', not 'release'")
        if status == "release":
            for tag, minimum in manifest.get("required_tags", {}).items():
                if tag_counts.get(tag, 0) < minimum:
                    rep.error(f"{label}: tag '{tag}' has {tag_counts.get(tag, 0)} cases, needs {minimum}")
        else:
            missing = [t for t, m in manifest.get("required_tags", {}).items() if tag_counts.get(t, 0) < m]
            if missing:
                rep.warn(f"{label}: tag coverage still short for {', '.join(sorted(missing))}")


def _check_extraction(root: Path, case: dict, label: str, rep: Report) -> None:
    prompt_id = case.get("prompt_id")
    extraction = case.get("expected", {}).get("extraction") if isinstance(case.get("expected"), dict) else None
    spath = root / "prompts" / "schemas" / f"{prompt_id}.output.schema.json"
    if not spath.exists():
        rep.error(f"{label}: no output schema for prompt_id '{prompt_id}'")
        return
    if extraction is None:
        rep.error(f"{label}: expected.extraction is missing")
        return
    for err in validate_schema(extraction, load_json(spath), "$.expected.extraction"):
        rep.error(f"{label}: {err}")


def update_manifests(root: Path, only: list[str] | None = None) -> list[str]:
    changed: list[str] = []
    base = root / "qa" / "datasets"
    for mpath in sorted(base.glob("*/manifest.json")):
        if mpath.parent.name == "schema" or (only and mpath.parent.name not in only):
            continue
        manifest = load_json(mpath)
        for cf in manifest.get("case_files", []):
            cpath = mpath.parent / cf["path"]
            digest, count = sha256_file(cpath), len(read_jsonl(cpath))
            if cf.get("sha256") != digest or cf.get("count") != count:
                cf["sha256"], cf["count"] = digest, count
                changed.append(f"{mpath.parent.name}/{cf['path']}")
        mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


# --------------------------------------------------------------------------- contexts

def expected_layers(contexts: list[dict]) -> list[list[str]]:
    by_layer: dict[int, list[str]] = {}
    for ctx in contexts:
        by_layer.setdefault(int(ctx["layer"]), []).append(ctx["name"])
    return [sorted(by_layer[k]) for k in sorted(by_layer)]


def layers_block(contexts: list[dict], root_package: str = "deepaira") -> str:
    lines = [" | ".join(f"{root_package}.{n}" for n in layer) for layer in expected_layers(contexts)]
    return "layers =\n" + "\n".join(f"    {line}" for line in lines)


def check_contexts(root: Path, rep: Report, strict: bool) -> None:
    cfile = root / "qa" / "contexts.toml"
    if not cfile.exists():
        rep.error("qa/contexts.toml is missing")
        return
    data = load_toml(cfile)
    root_package = data.get("root_package", "deepaira")
    contexts = data.get("context", [])
    names = [c.get("name") for c in contexts]
    for c in contexts:
        for key in ("name", "layer", "purpose", "table_prefix"):
            if key not in c:
                rep.error(f"context {c.get('name', '?')}: missing '{key}'")
    if len(set(names)) != len(names):
        rep.error("qa/contexts.toml: duplicate context names")
    pkg = root / "src" / root_package
    if pkg.exists():
        on_disk = {p.name for p in pkg.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))}
        for name in sorted(on_disk - set(names)):
            rep.error(f"package {root_package}.{name} exists but is not registered in qa/contexts.toml")
        for name in sorted(set(names) - on_disk):
            rep.error(f"context '{name}' is registered but src/{root_package}/{name} does not exist")
        for name in sorted(on_disk & set(names)):
            if not (pkg / name / "__init__.py").exists():
                rep.error(f"context '{name}' has no __init__.py")
    else:
        rep.error(f"src/{root_package} package is missing")

    ifile = root / ".importlinter"
    if not ifile.exists():
        rep.error(".importlinter is missing")
        return
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(ifile, encoding="utf-8")
    if cp.get("importlinter", "root_package", fallback="") != root_package:
        rep.error(f".importlinter: root_package must be {root_package}")
    layer_contracts = [s for s in cp.sections()
                       if s.startswith("importlinter:contract:") and cp.get(s, "type", fallback="") == "layers"]
    if len(layer_contracts) != 1:
        rep.error(".importlinter: expected exactly one 'layers' contract")
    else:
        raw = cp.get(layer_contracts[0], "layers", fallback="")
        actual = []
        for line in raw.splitlines():
            line = line.strip()
            if line:
                actual.append(sorted(part.strip().removeprefix(f"{root_package}.") for part in line.split("|")))
        if actual != expected_layers(contexts):
            rep.error(".importlinter layers differ from qa/contexts.toml. "
                      "Regenerate with `governance.py gen-importlinter`.")
    forbidden = [s for s in cp.sections()
                 if s.startswith("importlinter:contract:") and cp.get(s, "type", fallback="") == "forbidden"]
    engine_ok = llm_sdk_ok = False
    for s in forbidden:
        sources = cp.get(s, "source_modules", fallback="").split()
        banned = cp.get(s, "forbidden_modules", fallback="").split()
        if sources == [f"{root_package}.engine"] and "django" in banned:
            engine_ok = True
        if "anthropic" in banned and f"{root_package}.extraction" not in sources:
            llm_sdk_ok = True
    if not engine_ok:
        rep.error(".importlinter: missing contract keeping the engine free of Django")
    if not llm_sdk_ok:
        rep.error(".importlinter: missing contract limiting the LLM SDK to the extraction context")


# --------------------------------------------------------------------------- data map

MODEL_FIELD_SUFFIXES = ("Field", "ForeignKey", "OneToOneField", "ManyToManyField")


def model_fields(root: Path) -> set[str]:
    found: set[str] = set()
    pkg = root / "src" / "deepaira"
    if not pkg.exists():
        return found
    for path in pkg.rglob("*.py"):
        rel = path.relative_to(pkg)
        if not rel.parts or (path.name != "models.py" and "models" not in rel.parts[:-1]):
            continue
        context = rel.parts[0]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {ast.unparse(b) for b in node.bases}
            if not any(b == "Model" or b.endswith(".Model") for b in bases):
                continue
            for stmt in node.body:
                targets, value = [], None
                if isinstance(stmt, ast.Assign):
                    targets, value = stmt.targets, stmt.value
                elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                    targets, value = [stmt.target], stmt.value
                if isinstance(value, ast.Call):
                    func = ast.unparse(value.func)
                    if func.split(".")[-1].endswith(MODEL_FIELD_SUFFIXES):
                        for t in targets:
                            if isinstance(t, ast.Name):
                                found.add(f"{context}.{node.name}.{t.id}")
    return found


def check_datamap(root: Path, rep: Report, strict: bool) -> None:
    mfile = root / "qa" / "data-map.toml"
    if not mfile.exists():
        rep.error("qa/data-map.toml is missing")
        return
    entries = load_toml(mfile).get("field", [])
    keys: set[str] = set()
    for e in entries:
        key = e.get("key", "?")
        label = f"data-map {key}"
        for req in ("key", "sensitivity", "store", "retention", "deletion", "purpose"):
            if req not in e:
                rep.error(f"{label}: missing '{req}'")
        if e.get("sensitivity") not in SENSITIVITY:
            rep.error(f"{label}: sensitivity must be one of {sorted(SENSITIVITY)}")
        if e.get("deletion") not in DELETION:
            rep.error(f"{label}: deletion must be one of {sorted(DELETION)}")
        if e.get("sensitivity") in {"sensitive", "secret"} and str(e.get("retention")).lower() == "indefinite":
            rep.error(f"{label}: sensitive or secret data cannot be retained indefinitely")
        if e.get("in_llm_prompt") and e.get("sensitivity") == "secret":
            rep.error(f"{label}: secret data must never enter an LLM prompt")
        if key in keys:
            rep.error(f"{label}: duplicate key")
        keys.add(key)
    actual = model_fields(root)
    for key in sorted(actual - keys):
        rep.error(f"model field {key} is not classified in qa/data-map.toml")
    for key in sorted(k for k in keys - actual if k.count(".") == 2 and (root / "src").exists() and actual):
        rep.warn(f"data-map entry {key} has no matching model field (stale?)")


# --------------------------------------------------------------------------- tools

def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def declared_dependencies(root: Path) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {"pypi": set(), "npm": set()}
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        data = load_toml(pyproject)
        specs: list[str] = list(data.get("project", {}).get("dependencies", []))
        for group in data.get("project", {}).get("optional-dependencies", {}).values():
            specs.extend(group)
        for group in data.get("dependency-groups", {}).values():
            specs.extend(s for s in group if isinstance(s, str))
        for spec in specs:
            m = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
            if m:
                found["pypi"].add(_norm(m.group(1)))
    pkg = root / "package.json"
    if pkg.exists():
        data = load_json(pkg)
        for key in ("dependencies", "devDependencies", "optionalDependencies"):
            found["npm"].update(data.get(key, {}).keys())
    return found


def check_tools(root: Path, rep: Report, strict: bool) -> None:
    rfile = root / "qa" / "tool-register.toml"
    if not rfile.exists():
        rep.error("qa/tool-register.toml is missing")
        return
    register: dict[tuple[str, str], dict] = {}
    for t in load_toml(rfile).get("tool", []):
        for req in ("name", "ecosystem", "purpose", "status", "tier", "exit_plan"):
            if req not in t:
                rep.error(f"tool {t.get('name', '?')}: missing '{req}'")
        if t.get("status") not in TOOL_STATUSES:
            rep.error(f"tool {t.get('name', '?')}: status must be one of {sorted(TOOL_STATUSES)}")
        if t.get("status") == "approved":
            for req in ("license", "vetted_on", "telemetry"):
                if not t.get(req):
                    rep.error(f"tool {t.get('name')}: approved tools need '{req}' (see docs/04-tool-register.md)")
        name = _norm(t.get("name", "")) if t.get("ecosystem") == "pypi" else t.get("name", "")
        register[(t.get("ecosystem", ""), name)] = t
    deps = declared_dependencies(root)
    for eco, names in deps.items():
        for name in sorted(names):
            entry = register.get((eco, name))
            if entry is None:
                rep.error(f"{eco} dependency '{name}' is not in qa/tool-register.toml (vet it first)")
            elif entry.get("status") == "rejected":
                rep.error(f"{eco} dependency '{name}' is rejected in the tool register")
            elif entry.get("status") == "pending-vetting":
                rep.issue(strict, f"{eco} dependency '{name}' is still pending vetting")
    if any(deps.values()):
        if deps["pypi"] and not (root / "uv.lock").exists() and not (root / "requirements.lock").exists():
            rep.issue(strict, "Python dependencies declared but no lockfile (uv.lock) is committed")
        if deps["npm"] and not (root / "package-lock.json").exists() and not (root / "pnpm-lock.yaml").exists():
            rep.issue(strict, "npm dependencies declared but no lockfile is committed")


# --------------------------------------------------------------------------- blockers

def check_blockers(root: Path, rep: Report, strict: bool) -> None:
    bfile = root / "qa" / "release_blockers.toml"
    if not bfile.exists():
        rep.error("qa/release_blockers.toml is missing")
        return
    entries = load_toml(bfile).get("blocker", [])
    ids = {e.get("id") for e in entries}
    for missing in sorted(CORE_BLOCKERS - ids):
        rep.error(f"core release blocker '{missing}' was removed from qa/release_blockers.toml")
    for e in entries:
        label = f"blocker {e.get('id', '?')}"
        for req in ("id", "title", "description", "status", "test_file", "test_name"):
            if not e.get(req):
                rep.error(f"{label}: missing '{req}'")
        if e.get("status") not in {"planned", "implemented"}:
            rep.error(f"{label}: status must be planned or implemented")
            continue
        tpath = root / e.get("test_file", "")
        if e.get("status") == "implemented":
            if not tpath.exists():
                rep.error(f"{label}: marked implemented but {e.get('test_file')} does not exist")
            elif not re.search(rf"def\s+{re.escape(e.get('test_name', ''))}\s*\(", tpath.read_text(encoding="utf-8")):
                rep.error(f"{label}: test function {e.get('test_name')} not found in {e.get('test_file')}")
        else:
            rep.issue(strict, f"{label}: test not implemented yet")


# --------------------------------------------------------------------------- knowledge, ci, links

def check_knowledge(root: Path, rep: Report, strict: bool) -> None:
    kdir = root / KNOWLEDGE_DIR
    files = sorted(kdir.glob("*.md")) if kdir.exists() else []
    if not files:
        rep.error(f"no AI-DLC shared knowledge files in {KNOWLEDGE_DIR}")
        return
    words = 0
    for f in files:
        if not re.match(r"^[a-z0-9][a-z0-9-]*\.md$", f.name):
            rep.error(f"knowledge file name must be lowercase-hyphenated: {f.name}")
        words += len(f.read_text(encoding="utf-8").split())
    if words > KNOWLEDGE_WORD_LIMIT:
        rep.warn(f"shared knowledge is {words} words (limit {KNOWLEDGE_WORD_LIMIT}); "
                 "every AI-DLC stage loads it, so trim it")


USES = re.compile(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)")


def check_ci(root: Path, rep: Report, strict: bool) -> None:
    wf = root / ".github" / "workflows"
    if not wf.exists():
        rep.warn(".github/workflows not found")
        return
    for path in sorted(wf.glob("*.y*ml")):
        for ref in USES.findall(path.read_text(encoding="utf-8")):
            if ref.startswith("./") or ref.startswith("docker://"):
                continue
            if "@" not in ref or not re.fullmatch(r"[0-9a-f]{40}", ref.split("@", 1)[1]):
                rep.issue(strict, f"{path.name}: '{ref}' is not pinned to a full commit SHA")


LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "intents"}


def check_links(root: Path, rep: Report, strict: bool) -> None:
    for path in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#", 1)[0]
            if clean and not (path.parent / clean).exists():
                rep.error(f"{path.relative_to(root)}: broken link {target}")


# --------------------------------------------------------------------------- cost

def check_cost_file(root: Path, rep: Report, strict: bool) -> None:
    cfile = root / "qa" / "cost_budgets.toml"
    if not cfile.exists():
        rep.error("qa/cost_budgets.toml is missing")
        return
    for t in load_toml(cfile).get("task", []):
        for req in ("name", "max_input_tokens", "max_output_tokens", "max_cost_usd"):
            if req not in t:
                rep.error(f"cost budget {t.get('name', '?')}: missing '{req}'")
        for req in ("max_input_tokens", "max_output_tokens", "max_cost_usd"):
            if req in t and not t[req] > 0:
                rep.error(f"cost budget {t.get('name', '?')}: {req} must be positive")


def cost_gate(root: Path, results: dict, baseline: dict | None = None) -> list[str]:
    """Return failures. results: {task: {input_tokens, output_tokens, cost_usd}}."""
    failures: list[str] = []
    budgets = {t["name"]: t for t in load_toml(root / "qa" / "cost_budgets.toml").get("task", [])}
    for task, r in results.items():
        b = budgets.get(task)
        if b is None:
            failures.append(f"{task}: no budget defined")
            continue
        if r.get("input_tokens", 0) > b["max_input_tokens"]:
            failures.append(f"{task}: input tokens {r['input_tokens']} > budget {b['max_input_tokens']}")
        if r.get("output_tokens", 0) > b["max_output_tokens"]:
            failures.append(f"{task}: output tokens {r['output_tokens']} > budget {b['max_output_tokens']}")
        if r.get("cost_usd", 0) > b["max_cost_usd"]:
            failures.append(f"{task}: cost ${r['cost_usd']:.4f} > budget ${b['max_cost_usd']:.4f}")
        if baseline and task in baseline and baseline[task].get("cost_usd"):
            if r.get("cost_usd", 0) > 2 * baseline[task]["cost_usd"]:
                failures.append(f"{task}: cost more than doubled versus baseline")
    return failures


# --------------------------------------------------------------------------- runner / CLI

RUNNERS = {
    "prompts": check_prompts,
    "datasets": check_datasets,
    "contexts": check_contexts,
    "datamap": check_datamap,
    "tools": check_tools,
    "blockers": check_blockers,
    "knowledge": check_knowledge,
    "ci": check_ci,
    "links": check_links,
    "cost": check_cost_file,
}


def run_checks(root: Path, only: list[str] | None = None, strict: bool = False) -> Report:
    rep = Report()
    for name in only or CHECKS:
        RUNNERS[name](root, rep, strict)
    return rep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["check", "release-gate", "manifest", "rehash-prompts",
                                            "gen-importlinter", "cost-gate"])
    parser.add_argument("results", nargs="?", help="cost-gate: results JSON file")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--only", nargs="+", choices=CHECKS)
    parser.add_argument("--dataset", nargs="+")
    parser.add_argument("--baseline")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command in {"check", "release-gate"}:
        rep = run_checks(root, args.only, strict=args.command == "release-gate")
        for w in rep.warnings:
            print(f"WARN   {w}")
        for e in rep.errors:
            print(f"ERROR  {e}")
        print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
        return 0 if rep.ok else 1
    if args.command == "manifest":
        changed = update_manifests(root, args.dataset)
        print("updated:", ", ".join(changed) if changed else "nothing to change")
        return 0
    if args.command == "rehash-prompts":
        changed = rehash_prompts(root)
        print("rehashed:", ", ".join(changed) if changed else "nothing to change (approved prompts are never rehashed)")
        return 0
    if args.command == "gen-importlinter":
        print(layers_block(load_toml(root / "qa" / "contexts.toml").get("context", [])))
        return 0
    if args.command == "cost-gate":
        if not args.results:
            parser.error("cost-gate needs a results JSON file")
        baseline = load_json(Path(args.baseline)) if args.baseline else None
        failures = cost_gate(root, load_json(Path(args.results)), baseline)
        for f in failures:
            print(f"ERROR  {f}")
        print("cost gate passed" if not failures else f"\n{len(failures)} cost gate failure(s)")
        return 0 if not failures else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
