"""Automated unit and integration tests for Section 03 Terminal Project Explorer & README integration."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.config import COMMITS_PATH, CONFIG_PATH, PROFILE_DATA_PATH, REPOSITORIES_PATH
from src.explorer_builder import (
    build_explorer_model,
    load_explorer_inputs,
    resolve_language_badge,
    sort_explorer_repositories,
)
from src.main import run_full_profile_pipeline
from src.readme_builder import build_readme_markdown
from src.svg_explorer import generate_explorer_svg_file
from src.validators import validate_svg_document
from src.visualizations.project_explorer import build_explorer_svg, build_section_divider_svg
from tests.test_stats_builder import _FakePipelineClient


class ExplorerAndReadmeTests(unittest.TestCase):
    """Validate repository discovery, terminal UI, edge cases, safety, sorting, and README output."""

    def setUp(self) -> None:
        self.repos_data, self.commits_data, self.config_raw = load_explorer_inputs(
            REPOSITORIES_PATH, COMMITS_PATH, CONFIG_PATH
        )

    def test_renders_all_real_repositories_with_terminal_chrome_and_links(self) -> None:
        model = build_explorer_model(self.repos_data, self.commits_data, self.config_raw)
        svg = build_explorer_svg(model)
        root = validate_svg_document(svg)

        self.assertEqual(model.total_repositories, 8)
        self.assertEqual(model.sort_by, "updated")
        self.assertEqual(root.attrib.get("width"), "1009")

        # Verify macOS window controls, terminal header, and command prompt
        for expected in (
            "#ff5f56",
            "#ffbd2e",
            "#27c93f",
            "~/projects",
            " ls ~/projects",
            ".exp-row:hover",
            "prefers-reduced-motion: reduce",
        ):
            self.assertIn(expected, svg)

        # Every discovered repository appears with exact GitHub link & real language info
        for repo in self.repos_data["repositories"]:
            self.assertIn(repo["html_url"], svg)
            self.assertIn(repo["name"], svg)
        self.assertIn("stash-money-manager/", svg)

        # Default updated sorting places most recently updated repository first
        self.assertEqual(model.rows[0].name, "Eshtiaq-a")
        self.assertEqual(model.rows[1].name, "Clear-Cut-")
        self.assertEqual(model.rows[2].name, "Portfolio-main")

    def test_sorting_modes_updated_stars_name_and_deduplication(self) -> None:
        sample_repos = [
            {
                "repository_id": 1,
                "name": "zeta-app",
                "stars": 2,
                "updated_at": "2026-01-01T00:00:00Z",
                "pushed_at": "2026-01-01T00:00:00Z",
            },
            {
                "repository_id": 2,
                "name": "Alpha-Tool",
                "stars": 15,
                "updated_at": "2026-05-01T00:00:00Z",
                "pushed_at": "2026-05-01T00:00:00Z",
            },
            {
                "repository_id": 3,
                "name": "beta-newest",
                "stars": 0,
                "updated_at": "2026-11-25T00:00:00Z",
                "pushed_at": "2026-11-25T00:00:00Z",
            },
            # Intentional duplicate repository_id + private repo should both be excluded cleanly
            {
                "repository_id": 2,
                "name": "Alpha-Tool",
                "stars": 15,
                "updated_at": "2026-05-01T00:00:00Z",
            },
            {
                "repository_id": 4,
                "name": "hidden-private",
                "private": True,
                "stars": 999,
                "updated_at": "2026-12-01T00:00:00Z",
            },
        ]

        by_updated = [r["name"] for r in sort_explorer_repositories(sample_repos, sort_by="updated")]
        by_stars = [r["name"] for r in sort_explorer_repositories(sample_repos, sort_by="stars")]
        by_name = [r["name"] for r in sort_explorer_repositories(sample_repos, sort_by="name")]

        self.assertEqual(by_updated, ["beta-newest", "Alpha-Tool", "zeta-app"])
        self.assertEqual(by_stars, ["Alpha-Tool", "zeta-app", "beta-newest"])
        self.assertEqual(by_name, ["Alpha-Tool", "beta-newest", "zeta-app"])

    def test_automatic_addition_and_deletion_updates_explorer_without_hardcoding(self) -> None:
        added_repos = copy.deepcopy(self.repos_data)
        added_repos["repositories"].append(
            {
                "repository_id": 888888,
                "name": "neural-notes-cli",
                "full_name": "Eshtiaq-a/neural-notes-cli",
                "description": "Fast terminal semantic search over local Markdown notes",
                "primary_language": "Go",
                "languages": {"Go": 18000, "Shell": 400},
                "stars": 19,
                "forks": 2,
                "html_url": "https://github.com/Eshtiaq-a/neural-notes-cli",
                "homepage": None,
                "archived": False,
                "is_fork": False,
                "is_empty": False,
                "updated_at": "2026-12-05T12:00:00Z",
                "pushed_at": "2026-12-05T12:00:00Z",
            }
        )
        model_added = build_explorer_model(added_repos, self.commits_data, self.config_raw)
        svg_added = build_explorer_svg(model_added)
        validate_svg_document(svg_added)

        self.assertEqual(model_added.total_repositories, 9)
        self.assertEqual(model_added.rows[0].name, "neural-notes-cli")
        self.assertIn("neural-notes-cli/", svg_added)
        self.assertIn("★ 19", svg_added)
        self.assertIn("Go", svg_added)
        self.assertIn("+1", svg_added)

        removed_repos = copy.deepcopy(added_repos)
        removed_repos["repositories"] = [
            r for r in removed_repos["repositories"] if r["name"] != "test"
        ]
        model_removed = build_explorer_model(removed_repos, self.commits_data, self.config_raw)
        svg_removed = build_explorer_svg(model_removed)
        validate_svg_document(svg_removed)
        self.assertEqual(model_removed.total_repositories, 8)
        self.assertNotIn("https://github.com/Eshtiaq-a/test", svg_removed)

    def test_missing_fields_escaping_long_descriptions_empty_dataset_and_compact_layout(self) -> None:
        # Unknown language returns neutral DIR badge without crashing
        tag, _, _, _, _ = resolve_language_badge(None)
        self.assertEqual(tag, "DIR")
        custom_tag, _, _, _, _ = resolve_language_badge("Zig")
        self.assertEqual(custom_tag, "ZIG")

        long_desc = (
            "Extremely detailed research repository investigating <xml> & JSON parsing performance "
            "across distributed worker pools with comprehensive benchmarks and zero allocations"
        )
        edge_repos: dict[str, Any] = {
            "username": "Eshtiaq-a",
            "generated_at": "2026-11-27T00:00:00Z",
            "repositories": [
                {
                    "repository_id": 10,
                    "name": "no-meta-project",
                    "description": None,
                    "primary_language": None,
                    "languages": {},
                    "stars": 0,
                    "forks": 0,
                    "html_url": "javascript:alert(1)",  # unsafe URL must sanitize to GitHub URL
                    "homepage": "javascript:evil()",
                    "archived": True,
                    "is_empty": False,
                    "updated_at": "2026-11-01T00:00:00Z",
                },
                {
                    "repository_id": 11,
                    "name": "very-long-repository-directory-name-exceeding-limit",
                    "description": long_desc,
                    "primary_language": "C++",
                    "languages": {"C++": 5000, "CMake": 300, "Python": 200},
                    "stars": 7,
                    "forks": 1,
                    "html_url": "https://github.com/Eshtiaq-a/very-long-repository-directory-name-exceeding-limit",
                    "homepage": "https://example.com/demo",
                    "archived": False,
                    "is_empty": False,
                    "updated_at": "2026-11-27T00:00:00Z",
                },
            ],
        }
        model = build_explorer_model(edge_repos, {"commits": []}, {})
        svg = build_explorer_svg(model)
        validate_svg_document(svg)

        self.assertIn("No description provided.", svg)
        self.assertIn("Unspecified", svg)
        self.assertIn("ARCHIVED", svg)
        self.assertIn("dr-x", svg)
        self.assertIn("&lt;xml&gt; &amp; JSON", svg)
        self.assertNotIn("javascript:", svg)

        # Compact responsive layout check
        compact_svg = build_explorer_svg(model, layout="compact")
        compact_root = validate_svg_document(compact_svg)
        self.assertEqual(compact_root.attrib.get("width"), "560")
        self.assertIn("very-long-reposito", compact_svg)

        # Empty dataset graceful handling
        empty_model = build_explorer_model({"username": "Eshtiaq-a", "repositories": []}, {"commits": []}, {})
        empty_svg = build_explorer_svg(empty_model)
        validate_svg_document(empty_svg)
        self.assertIn("No public repositories discovered yet", empty_svg)

    def test_validator_rejects_unsafe_anchors_and_external_images(self) -> None:
        bad_anchor = '<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><rect width="10" height="10"/></a></svg>'
        with self.assertRaises(ValueError):
            validate_svg_document(bad_anchor)

        bad_image = '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/img.png" width="10" height="10"/></svg>'
        with self.assertRaises(ValueError):
            validate_svg_document(bad_image)

        divider_svg = build_section_divider_svg()
        validate_svg_document(divider_svg)

    def test_readme_assembly_and_full_pipeline_atomic_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            out_exp = t / "explorer.svg"
            out_div = t / "divider.svg"
            out_slices = t / "explorer"
            generate_explorer_svg_file(
                output_path=out_exp,
                slices_dir=out_slices,
                divider_path=out_div,
            )
            self.assertTrue(out_exp.exists())
            self.assertTrue(out_div.exists())
            self.assertTrue((out_slices / "header.svg").exists())
            self.assertTrue((out_slices / "footer.svg").exists())
            validate_svg_document(out_exp.read_text(encoding="utf-8"))

            summary = run_full_profile_pipeline(
                repositories_path=t / "repositories.json",
                commits_path=t / "commits.json",
                profile_data_path=t / "profile_data.json",
                workspace_svg_path=t / "workspace.svg",
                neofetch_svg_path=t / "neofetch.svg",
                explorer_svg_path=t / "explorer.svg",
                explorer_slices_dir=out_slices,
                divider_svg_path=t / "divider.svg",
                readme_path=t / "README.md",
                client=_FakePipelineClient(),  # type: ignore[arg-type]
            )
            self.assertGreater(summary["explorer_bytes"], 1000)
            readme = (t / "README.md").read_text(encoding="utf-8")
            self.assertIn("assets/workspace.svg", readme)
            self.assertIn("assets/neofetch.svg", readme)
            self.assertIn("assets/explorer/header.svg", readme)
            self.assertIn("assets/explorer/rows/wrechship.svg", readme)
            self.assertIn("assets/explorer/footer.svg", readme)
            self.assertIn("https://github.com/Eshtiaq-a/Wrechship", readme)
            self.assertIn("Shipwreck dataset", readme)

        # Also validate escaping in README builder with special HTML/Markdown table characters
        tricky_repos = {
            "username": "Eshtiaq-a",
            "repositories": [
                {
                    "repository_id": 50,
                    "name": "escape-check",
                    "description": 'Compare a | b & <tag> "quoted"',
                    "primary_language": "Python",
                    "languages": {"Python": 100},
                    "stars": 1,
                    "forks": 0,
                    "html_url": "https://github.com/Eshtiaq-a/escape-check",
                    "homepage": None,
                    "archived": False,
                    "is_empty": False,
                    "updated_at": "2026-11-26T00:00:00Z",
                }
            ],
        }
        tricky_model = build_explorer_model(tricky_repos, {"commits": []}, {})
        tricky_md = build_readme_markdown({"username": "Eshtiaq-a"}, {"commits": []}, tricky_model)
        self.assertIn("&lt;tag&gt;", tricky_md)
        self.assertIn("a \\| b &amp;", tricky_md)


if __name__ == "__main__":
    unittest.main()
