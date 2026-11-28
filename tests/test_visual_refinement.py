"""Comprehensive unit tests for Section 01 visual refinement & Section 02 Repo Galaxy + Neofetch."""

from __future__ import annotations

import copy
import unittest
from typing import Any

from src.config import COMMITS_PATH, CONFIG_PATH, PROFILE_DATA_PATH, REPOSITORIES_PATH, load_profile_config
from src.neofetch_builder import build_neofetch_model, load_phase2_inputs
from src.svg_neofetch import build_neofetch_svg
from src.svg_workspace import build_workspace_svg
from src.validators import validate_svg_document
from src.visualizations.repo_galaxy import (
    DEFAULT_NODE_COLOR,
    _boxes_overlap,
    build_repo_galaxy_model,
    compute_node_radius,
    get_language_color,
)


class VisualRefinementAndGalaxyTests(unittest.TestCase):
    """Test enriched room details/animations and Repo Galaxy edge cases & collision guards."""

    def setUp(self) -> None:
        self.profile_data, self.repos_data, self.commits_data, self.config_raw = load_phase2_inputs(
            PROFILE_DATA_PATH, REPOSITORIES_PATH, COMMITS_PATH, CONFIG_PATH
        )
        self.config = load_profile_config(CONFIG_PATH)

    def test_workspace_svg_contains_inhabited_details_and_all_mandatory_animations(self) -> None:
        svg = build_workspace_svg(self.commits_data, self.config)
        validate_svg_document(svg)

        # Verify movie credits remain intact and real commits render
        for token in ("@keyframes scrollCredits", "#credits-track", "CLEAR-CUT-", "THE JOURNEY CONTINUES."):
            self.assertIn(token, svg)

        # Verify secondary subtle animations & static prefers-reduced-motion fallback exist
        for anim_cls in (
            "clock-min-hand",
            "clock-hour-hand",
            "mug-steam-1",
            "cat-tail-wag",
            "cat-breathe",
            "star-twinkle-a",
            "lamp-glow-cone",
            "prefers-reduced-motion: reduce",
        ):
            self.assertIn(anim_cls, svg)

    def test_galaxy_renders_all_8_existing_repos_with_zero_label_collisions(self) -> None:
        model = build_neofetch_model(self.profile_data, self.repos_data, self.commits_data, self.config_raw)
        galaxy = model.galaxy

        expected_count = len(self.repos_data["repositories"])
        self.assertGreaterEqual(expected_count, 8)
        self.assertEqual(galaxy.repo_count, expected_count)
        self.assertEqual(len(galaxy.nodes), expected_count)

        # Ensure zero pairwise label collisions in static/initial layout
        labeled_boxes = [n.label_box for n in galaxy.nodes if n.show_label and n.label_box is not None]
        self.assertEqual(len(labeled_boxes), expected_count)
        for i in range(len(labeled_boxes)):
            for j in range(i + 1, len(labeled_boxes)):
                self.assertFalse(
                    _boxes_overlap(labeled_boxes[i], labeled_boxes[j], pad_x=2.0, pad_y=2.0),
                    f"Labels overlap between node {i} and node {j}: {labeled_boxes[i]} vs {labeled_boxes[j]}",
                )

        # Verify ASCII portrait removed and Repo Galaxy integrated cleanly
        svg = build_neofetch_svg(model)
        validate_svg_document(svg)
        self.assertIn("REPO GALAXY", svg)
        self.assertIn("@Eshtiaq-a", svg)
        self.assertIn("ARM / LANGUAGE", svg)
        self.assertIn("stash-money-manager", svg)
        self.assertNotIn("=-cc**sss", svg)
        self.assertIn("gxCoreSpin", svg)
        self.assertIn("prefers-reduced-motion: reduce", svg)

    def test_adding_and_removing_repository_updates_galaxy_automatically(self) -> None:
        extended_repos = copy.deepcopy(self.repos_data)
        extended_repos["repositories"].append(
            {
                "repository_id": 999999,
                "name": "quantum-search-engine",
                "full_name": "Eshtiaq-a/quantum-search-engine",
                "description": "Automatic discovery test repo",
                "primary_language": "Rust",
                "languages": {"Rust": 12000},
                "stars": 42,
                "forks": 3,
                "html_url": "https://github.com/Eshtiaq-a/quantum-search-engine",
                "homepage": None,
                "archived": False,
                "is_fork": False,
                "is_empty": False,
                "size_kb": 42,
                "pushed_at": "2026-11-26T20:00:00Z",
                "created_at": "2026-11-26T19:00:00Z",
                "updated_at": "2026-11-26T20:00:00Z",
            }
        )
        extended_repos["total_public_repositories"] = len(extended_repos["repositories"])

        base_count = len(self.repos_data["repositories"])
        model_added = build_neofetch_model(self.profile_data, extended_repos, self.commits_data, self.config_raw)
        self.assertEqual(model_added.galaxy.repo_count, base_count + 1)
        self.assertEqual(model_added.galaxy.total_stars, 42)
        names_added = {n.name for n in model_added.galaxy.nodes}
        self.assertIn("quantum-search-engine", names_added)

        svg_added = build_neofetch_svg(model_added)
        validate_svg_document(svg_added)
        self.assertIn("quantum-search-engine", svg_added)
        self.assertIn("42 Stars", svg_added)

        # Removing a repo removes it cleanly from the galaxy
        shrunk_repos = copy.deepcopy(self.repos_data)
        shrunk_repos["repositories"] = [
            r for r in shrunk_repos["repositories"] if r["name"] != "test"
        ]
        shrunk_repos["total_public_repositories"] = len(shrunk_repos["repositories"])
        model_removed = build_neofetch_model(self.profile_data, shrunk_repos, self.commits_data, self.config_raw)
        self.assertEqual(model_removed.galaxy.repo_count, base_count - 1)
        self.assertNotIn("test", {n.name for n in model_removed.galaxy.nodes})

    def test_zero_star_min_size_distinct_language_colors_and_missing_fields(self) -> None:
        self.assertGreaterEqual(compute_node_radius(0), 4.0)
        self.assertGreater(compute_node_radius(10), compute_node_radius(0))
        self.assertNotEqual(get_language_color("Python"), get_language_color("HTML"))
        self.assertNotEqual(get_language_color("TypeScript"), get_language_color("JavaScript"))
        self.assertEqual(get_language_color(None), DEFAULT_NODE_COLOR)

        sparse_repos: dict[str, Any] = {
            "repositories": [
                {
                    "repository_id": 1,
                    "name": "missing-meta-repo",
                    "description": None,
                    "primary_language": None,
                    "languages": {},
                    "stars": 0,
                    "forks": 0,
                    "html_url": "https://github.com/Eshtiaq-a/missing-meta-repo",
                    "archived": False,
                    "is_empty": False,
                },
                {
                    "repository_id": 2,
                    "name": "missing-meta-repo",  # intentional duplicate name
                    "description": "Clean <xml> & escaping check",
                    "primary_language": "HTML",
                    "languages": {"HTML": 500},
                    "stars": 3,
                    "forks": 0,
                    "html_url": "https://github.com/Eshtiaq-a/missing-meta-repo",
                    "archived": False,
                    "is_empty": False,
                },
            ]
        }
        sparse_profile = {
            "username": "Eshtiaq-a",
            "directly_sourced_profile": {"login": "Eshtiaq-a"},
            "calculated_metrics": {"languages": []},
            "contribution_stats": {"available": False},
        }
        model = build_neofetch_model(sparse_profile, sparse_repos, {"commits": [], "branches_processed": 0}, {})
        svg = build_neofetch_svg(model)
        validate_svg_document(svg)
        self.assertEqual(len(model.galaxy.nodes), 2)
        self.assertIn("&lt;xml&gt; &amp; escaping check", svg)

    def test_empty_dataset_and_large_repo_count_fallback(self) -> None:
        empty_profile = {
            "username": "Eshtiaq-a",
            "directly_sourced_profile": {"login": "Eshtiaq-a"},
            "calculated_metrics": {"languages": []},
            "contribution_stats": {"available": False},
        }
        empty_model = build_neofetch_model(empty_profile, {"repositories": []}, {"commits": []}, {})
        empty_svg = build_neofetch_svg(empty_model)
        validate_svg_document(empty_svg)
        self.assertIn("0 Stars · 0 Repositories", empty_svg)
        self.assertIn("No public repositories discovered yet", empty_svg)
        self.assertIn("Language breakdown unavailable", empty_svg)

        # Large repo count stress test (30 repositories)
        large_repos = {
            "repositories": [
                {
                    "repository_id": i + 1,
                    "name": f"service-module-{i:02d}",
                    "description": f"Generated test service {i}",
                    "primary_language": ("Python", "TypeScript", "HTML", "JavaScript", "C")[i % 5],
                    "languages": {},
                    "stars": i % 7,
                    "forks": 0,
                    "html_url": f"https://github.com/Eshtiaq-a/service-module-{i:02d}",
                    "archived": False,
                    "is_empty": False,
                }
                for i in range(30)
            ]
        }
        large_model = build_neofetch_model(empty_profile, large_repos, {"commits": []}, {})
        self.assertEqual(len(large_model.galaxy.nodes), 30)
        labeled = [n for n in large_model.galaxy.nodes if n.show_label]
        self.assertEqual(len(labeled), 12)
        large_svg = build_neofetch_svg(large_model)
        validate_svg_document(large_svg)
        self.assertIn("30 Repositories", large_svg)

    def test_compact_responsive_stacked_layout_renders_valid_svg(self) -> None:
        model = build_neofetch_model(self.profile_data, self.repos_data, self.commits_data, self.config_raw)
        compact_svg = build_neofetch_svg(model, layout="compact")
        root = validate_svg_document(compact_svg)
        self.assertEqual(root.attrib.get("width"), "560")
        self.assertGreaterEqual(int(root.attrib.get("height", "0")), 940)
        self.assertIn("REPO GALAXY", compact_svg)


if __name__ == "__main__":
    unittest.main()
