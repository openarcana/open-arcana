"""Regression checks for evidence integrity and the files consumed by readers/agents."""
import copy
from contextlib import closing
import csv
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("build", ROOT / "scripts" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class EvidenceValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package, cls.original = build.load()

    def setUp(self):
        self.tables = copy.deepcopy(self.original)

    def errors(self):
        return build.validate(self.package, self.tables)

    def test_canonical_records_validate(self):
        self.assertEqual(self.errors(), [])

    def test_unsourced_insufficient_claim_is_rejected(self):
        self.tables["claims"][0].update(claim_support="insufficient", supporting_source_ids="", contradicting_source_ids="")
        self.assertTrue(any("at least one source" in e for e in self.errors()))

    def test_duplicate_source_cannot_count_as_independent(self):
        self.tables["claims"][0].update(
            claim_support="independently_corroborated", supporting_source_ids="SRC-0001;SRC-0001",
            independent_source_ids="SRC-0001;SRC-0001", review_status="reviewed", locators="whole work")
        errors = self.errors()
        self.assertTrue(any("duplicate" in e for e in errors))
        self.assertTrue(any("distinct independent_source_ids" in e for e in errors))

    def test_corroboration_cannot_ignore_contradictions(self):
        claim = next(c for c in self.tables["claims"] if c["claim_support"] == "independently_corroborated")
        claim["contradicting_source_ids"] = "SRC-0001"
        self.assertTrue(any("cannot have contradicting" in e for e in self.errors()))

    def test_single_source_label_cannot_hide_contradictions_or_independence(self):
        claim = self.tables["claims"][0]
        claim["contradicting_source_ids"] = "SRC-0001"
        self.assertTrue(any("require contradicted" in e for e in self.errors()))
        claim.update(contradicting_source_ids="", supporting_source_ids="SRC-0001;SRC-0002",
                     independent_source_ids="SRC-0001;SRC-0002")
        self.assertTrue(any("single_source cannot declare" in e for e in self.errors()))

    def test_independence_requires_supporting_membership_and_assessment(self):
        claim = self.tables["claims"][0]
        claim.update(claim_support="independently_corroborated", independent_source_ids="SRC-0001;SRC-0003")
        errors = self.errors()
        self.assertTrue(any("subset" in e for e in errors))
        self.assertTrue(any("needs review, locators" in e for e in errors))

    def test_partial_and_duplicate_list_entries_are_rejected(self):
        for value in ("SRC-0002;", ";SRC-0002", "SRC-0002; SRC-0003", "SRC-0002;SRC-0002"):
            with self.subTest(value=value):
                self.tables["claims"][0]["supporting_source_ids"] = value
                self.assertTrue(self.errors())

    def test_broken_foreign_keys_are_rejected(self):
        self.tables["claims"][0]["supporting_source_ids"] = "SRC-9999"
        self.assertTrue(any("not found in sources" in e for e in self.errors()))

    def test_malformed_rows_report_errors_without_crashing(self):
        for value in (None, ["extra", "cells"]):
            with self.subTest(value=value):
                self.tables["sources"][0]["title"] = value
                self.assertTrue(any("malformed row" in e for e in self.errors()))

    def test_malformed_or_active_urls_are_rejected(self):
        for url in ("not-a-url", "javascript:alert(1)", "https://", "https://example.org:bad/", "https://u:p@example.org/", "https://example.org/a\nb"):
            with self.subTest(url=url):
                self.tables["sources"][0]["url"] = url
                self.assertTrue(any("absolute HTTP(S)" in e for e in self.errors()))

    def test_assessed_authenticity_requires_basis(self):
        self.tables["sources"][0].update(source_authenticity="verified", verification_notes="")
        self.assertTrue(any("authenticity needs verification_notes" in e for e in self.errors()))

    def test_current_practice_requires_period(self):
        self.tables["claims"][0].update(claim_type="current_practice", period="")
        self.assertTrue(any("current_practice needs a period" in e for e in self.errors()))

    def test_leaks_and_nonprint_formats_are_eligible(self):
        source = self.tables["sources"][0]
        source.update(provenance="intrusion;anonymous_posting", source_authenticity="unassessed", rights="unknown")
        for format_name in ("video", "audio", "document", "collection"):
            with self.subTest(format_name=format_name):
                source["source_type"] = format_name
                self.assertEqual(self.errors(), [])

    def test_artifacts_can_use_content_identifiers_without_http_links(self):
        artifact = self.tables["source_artifacts"][1]
        artifact.update(url="", sha256="", size_bytes="")
        self.assertTrue(artifact["btih"])
        self.assertEqual(self.errors(), [])
        artifact["btih"] = ""
        artifact["ipfs_cid"] = "Qm" + "a" * 44
        self.assertEqual(self.errors(), [])
        artifact["ipfs_cid"] = ""
        self.assertTrue(any("URL or content identifier" in e for e in self.errors()))

    def test_artifact_capture_identity_must_be_consistent(self):
        artifact = self.tables["source_artifacts"][0]
        artifact["size_bytes"] = ""
        self.assertTrue(any("supplied together" in e for e in self.errors()))
        artifact.update(size_bytes="100", sha256="not-a-hash")
        self.assertTrue(any("sha256" in e for e in self.errors()))

    def test_artifact_urls_dates_and_relationships_are_checked(self):
        artifact = self.tables["source_artifacts"][0]
        artifact.update(url="javascript:alert(1)", accessed_on="2026-02-30", source_id="SRC-9999")
        errors = self.errors()
        self.assertTrue(any("absolute HTTP(S)" in e for e in errors))
        self.assertTrue(any("valid calendar date" in e for e in errors))
        self.assertTrue(any("not found in sources" in e for e in errors))

    def test_shared_payloads_are_flagged_without_becoming_ineligible(self):
        original = self.tables["source_artifacts"][0]
        duplicate = {**original, "id": "ARTF-9999", "source_id": "SRC-0001"}
        self.tables["source_artifacts"].append(duplicate)
        dataset, _ = build.snapshot(self.package)
        quality = build.build_quality(self.tables, dataset)
        flagged = {issue["record_id"] for issue in quality["issues"] if issue["code"] == "shared_artifact_bytes"}
        self.assertEqual(flagged, {original["id"], duplicate["id"]})
        self.assertEqual(self.errors(), [])

    def test_status_evidence_requires_a_real_date_and_matching_claim(self):
        self.tables["restricted_items"][0].update(status_as_of="2026-02-30", status_claim_ids="CLM-0077")
        errors = self.errors()
        self.assertTrue(any("valid calendar date" in e for e in errors))
        self.assertTrue(any("for this item" in e for e in errors))

    def test_status_date_and_claim_ids_must_travel_together(self):
        self.tables["restricted_items"][0]["status_as_of"] = "2026-11-04"
        self.assertTrue(any("supplied together" in e for e in self.errors()))

    def test_incomplete_evidence_is_reported_without_being_excluded(self):
        dataset, _ = build.snapshot(self.package)
        quality = build.build_quality(self.tables, dataset)
        issues = {(i["table"], i["record_id"], i["code"]) for i in quality["issues"]}
        for source in self.tables["sources"]:
            if not source["content_hash"]:
                self.assertIn(("sources", source["id"], "source_without_content_hash"), issues)
        self.assertIn(("claims", "CLM-0002", "claim_insufficient"), issues)
        self.assertEqual(self.errors(), [])


class PackageLoadingTests(unittest.TestCase):
    def test_parent_absolute_and_hidden_paths_are_rejected(self):
        for value in ("../data/a.csv", "/tmp/a.csv", ".private/a.csv", "data/../a.csv", "https://example.org/a.csv"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    build.resource_path({"name": "test", "path": value}, ROOT / "datapackage.json")

    def test_symlinks_cannot_escape_package(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            package_root = parent / "package"
            package_root.mkdir()
            outside = parent / "outside.csv"
            outside.write_text("id\n", encoding="utf-8")
            (package_root / "table.csv").symlink_to(outside)
            with self.assertRaises(ValueError):
                build.resource_path({"name": "test", "path": "table.csv"}, package_root / "datapackage.json")

    def test_bad_headers_are_rejected_even_when_table_is_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resource = {"name": "test", "path": "table.csv", "schema": {"fields": [{"name": "id"}]}}
            (root / "datapackage.json").write_text(json.dumps({"resources": [resource]}), encoding="utf-8")
            (root / "table.csv").write_text("wrong\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "columns"):
                build.load(root / "datapackage.json")
            (root / "table.csv").write_text("id\n", encoding="utf-8")
            self.assertEqual(build.load(root / "datapackage.json")[1], {"test": []})


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package, cls.tables = build.load()
        cls.dataset, cls.inputs = build.snapshot(cls.package)

    def test_export_contract_and_sql_joins_preserve_all_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build.write_outputs(self.package, self.tables, root, self.dataset, self.inputs, parquet=False)
            self.assertEqual(build.check_exports(self.package, self.tables, self.dataset, self.inputs, root), [])
            claims = [json.loads(line) for line in (root / "exports/claims.jsonl").read_text().splitlines()]
            self.assertEqual(len(claims), len(self.tables["claims"]))
            for claim in claims:
                self.assertEqual(claim["dataset"], self.dataset)
                self.assertEqual(claim["tradition"]["id"], claim["item"]["tradition_id"])
                self.assertEqual([s["id"] for s in claim["supporting_sources"]], build.split(claim["supporting_source_ids"]))
                self.assertEqual([s["id"] for s in claim["contradicting_sources"]], build.split(claim["contradicting_source_ids"]))
                for source in claim["supporting_sources"] + claim["contradicting_sources"]:
                    expected_artifacts = [artifact for artifact in self.tables["source_artifacts"]
                                          if artifact["source_id"] == source["id"]]
                    self.assertEqual(source["artifacts"], expected_artifacts)
                    for artifact in expected_artifacts:
                        if artifact["inspection_status"] != "complete":
                            self.assertTrue(any(issue["record_id"] == artifact["id"]
                                                for issue in claim["quality_issues"]))
                if claim["review_status"] != "reviewed":
                    self.assertTrue(any(i["record_id"] == claim["id"] and i["code"] == "record_" + claim["review_status"]
                                        for i in claim["quality_issues"]))
            catalog = (root / "CATALOG.md").read_text()
            self.assertIn("| Review |", catalog)
            self.assertEqual(catalog.count(" · unreviewed:"), sum(c["review_status"] == "unreviewed" for c in self.tables["claims"]))
            self.assertEqual(catalog.count("| unreviewed |"), sum(d["review_status"] == "unreviewed" for d in self.tables["disclosures"]))
            with closing(sqlite3.connect(root / "exports/open-arcana.sqlite")) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM source_artifacts").fetchone()[0],
                                 len(self.tables["source_artifacts"]))
                actual = db.execute("SELECT claim_id, source_id, role, counted_independent FROM claim_sources").fetchall()
                expected = [(c["id"], sid, role, int(sid in build.split(c["independent_source_ids"])))
                            for c in self.tables["claims"] for role in ("supporting", "contradicting")
                            for sid in build.split(c[f"{role}_source_ids"])]
                self.assertCountEqual(actual, expected)
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_stale_catalog_export_and_checksum_are_detected(self):
        for relative in ("CATALOG.md", "exports/claims.jsonl", "exports/SHA256SUMS"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                build.write_outputs(self.package, self.tables, root, self.dataset, self.inputs, parquet=False)
                path = root / relative
                path.write_text(path.read_text() + "tampered\n", encoding="utf-8")
                self.assertTrue(build.check_exports(self.package, self.tables, self.dataset, self.inputs, root))

    def test_stale_sqlite_records_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build.write_outputs(self.package, self.tables, root, self.dataset, self.inputs, parquet=False)
            with closing(sqlite3.connect(root / "exports/open-arcana.sqlite")) as db, db:
                db.execute("UPDATE claims SET statement = 'tampered' WHERE id = 'CLM-0001'")
            errors = build.check_exports(self.package, self.tables, self.dataset, self.inputs, root)
            self.assertTrue(any("stale generated file: exports/open-arcana.sqlite" in e for e in errors))

    def test_markdown_values_cannot_inject_links_or_html(self):
        text = build.md("[forged](https://example.org) <script>bad</script> | `reviewed`\nnext")
        self.assertNotIn("[forged]", text)
        self.assertNotIn("<script>", text)
        self.assertIn("\\|", text)
        self.assertIn("<br>", text)
        self.assertNotIn("(", build.link_url("https://example.org/a(b)"))


if __name__ == "__main__":
    unittest.main()
