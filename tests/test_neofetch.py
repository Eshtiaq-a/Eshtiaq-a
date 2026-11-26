"""Automated tests for Section 02 Neofetch Developer Terminal."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.config import COMMITS_PATH, CONFIG_PATH, PROFILE_DATA_PATH, REPOSITORIES_PATH
from src.neofetch_builder import (
    RIGHT_COL_CHARS,
    STAT_HALF_CHARS,
    build_neofetch_model,
    load_phase2_inputs,
    make_dot_row,
)
from src.svg_neofetch import build_neofetch_svg, generate_neofetch_svg_file
from src.validators import validate_svg_document


def _row_len(label: str, dots: str, value: str) -> int:
    # "▪ " (2) + label + ": " (2) + dots + " " (1) + value
    return 2 + len(label) + 2 + len(dots) + 1 + len(value)


class NeofetchTests(unittest.TestCase):
    """Validate Neofetch data mapping, edge cases, alignment, and Camo-safe SVG output."""

    def test_valid_real_phase2_datasets_render_cleanly(self) -> None:
        profile_data, repos_data, commits_data, config_raw = load_phase2_inputs(
            PROFILE_DATA_PATH, REPOSITORIES_PATH, COMMITS_PATH, CONFIG_PATH
        )
        model = build_neofetch_model(profile_data, repos_data, commits_data, config_raw)
        svg = build_neofetch_svg(model)
        root = validate_svg_document(svg)

        self.assertEqual(root.attrib.get("viewBox"), "0 0 1009 610")
        self.assertIn("eshtiaq-a@github", svg)
        self.assertIn("Eshtiaq Ahmad", svg)
        self.assertIn("GitHub / Developer Universe", svg)
        self.assertIn("Profile Data Engine", svg)
        self.assertIn(str(len(repos_data["repositories"])), svg)
        self.assertIn(str(len(commits_data["commits"])), svg)
        self.assertNotIn("gitskins.com", svg.lower())

        for row in model.system_rows:
            self.assertEqual(_row_len(row.label, row.dots, row.value), RIGHT_COL_CHARS)
        for pair in model.stats_rows:
            self.assertEqual(_row_len(pair.left.label, pair.left.dots, pair.left.value), STAT_HALF_CHARS)
            if pair.right is not None:
                self.assertEqual(_row_len(pair.right.label, pair.right.dots, pair.right.value), STAT_HALF_CHARS)

    def test_missing_profile_fields_languages_empty_repos_zero_commits_and_unavailable_stats(self) -> None:
        profile_data: dict[str, Any] = {
            "username": "Eshtiaq-a",
            "directly_sourced_profile": {
                "login": None,
                "name": None,
                "bio": None,
                "location": None,
                "html_url": None,
                "followers": None,
                "following": None,
            },
            "calculated_metrics": {"uptime_months": None, "languages": []},
            "contribution_stats": {"available": False},
        }
        repos_data: dict[str, Any] = {"repositories": []}
        commits_data: dict[str, Any] = {"commits": [], "branches_processed": 0}

        model = build_neofetch_model(profile_data, repos_data, commits_data, config_raw={})
        svg = build_neofetch_svg(model)
        validate_svg_document(svg)

        sys_map = {r.label: r.value for r in model.system_rows}
        self.assertEqual(sys_map["Packages"], "0 public repositories")
        self.assertEqual(sys_map["Languages"], "None detected")
        self.assertNotIn("Uptime", sys_map)
        self.assertIn("unavailable", svg)

        # Verify zero fabricated numbers in stats
        stats_text = " ".join(
            f"{p.left.label}={p.left.value} {p.right.label}={p.right.value}"
            for p in model.stats_rows
            if p.right is not None
        )
        self.assertIn("Repos=0", stats_text)
        self.assertIn("Commits=0", stats_text)
        self.assertIn("Branches=0", stats_text)
        self.assertIn("Followers=N/A", stats_text)
        self.assertIn("Contributions=unavailable", stats_text)

    def test_authenticated_contribution_stats_rendered_when_available(self) -> None:
        profile_data: dict[str, Any] = {
            "username": "Eshtiaq-a",
            "directly_sourced_profile": {
                "login": "Eshtiaq-a",
                "name": "Eshtiaq Ahmad",
                "bio": "Bio <script> & test",
                "followers": 2,
                "following": 4,
            },
            "calculated_metrics": {"uptime_months": 10, "languages": []},
            "contribution_stats": {
                "available": True,
                "total_contributions": 77,
                "active_days": 16,
                "current_streak_days": 1,
                "best_streak_days": 5,
            },
        }
        repos_data: dict[str, Any] = {
            "repositories": [
                {"name": "A", "stars": 2, "forks": 1, "is_fork": False, "languages": {"Python": 500}},
                {"name": "B", "stars": 0, "forks": 0, "is_fork": False, "primary_language": None},
            ]
        }
        commits_data: dict[str, Any] = {"commits": [{"commit_sha": "abc"}], "branches_processed": 2}

        model = build_neofetch_model(profile_data, repos_data, commits_data, config_raw={})
        svg = build_neofetch_svg(model)
        validate_svg_document(svg)

        self.assertIn("&lt;script&gt; &amp; test", svg)
        self.assertIn("77", svg)
        self.assertIn("16", svg)
        self.assertIn("1d", svg)
        self.assertIn("5d", svg)
        self.assertIn("Python", svg)

    def test_dot_row_truncation_handles_long_values(self) -> None:
        row = make_dot_row("Languages", "Python, HTML, TypeScript, JavaScript, PLpgSQL, CSS, PowerShell, Shell")
        self.assertEqual(_row_len(row.label, row.dots, row.value), RIGHT_COL_CHARS)
        self.assertTrue(row.value.endswith("..."))

    def test_generate_neofetch_svg_file_atomic_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "neofetch.svg"
            written = generate_neofetch_svg_file(output_path=out)
            self.assertTrue(written.exists())
            svg = written.read_text(encoding="utf-8")
            root = validate_svg_document(svg)
            self.assertEqual(root.attrib.get("width"), "1009")


if __name__ == "__main__":
    unittest.main()
