"""Automated tests for 3D Contribution City data integration, isometric geometry, SVG, and README placement."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from src.config import COMMITS_PATH, CONFIG_PATH, PROFILE_DATA_PATH, REPOSITORIES_PATH
from src.contributions_builder import (
    build_contributions_from_commits,
    build_contributions_payload,
    normalize_contribution_calendar,
)
from src.github_client import GitHubClient
from src.main import run_full_profile_pipeline
from src.svg_city import build_standalone_city_html, generate_city_svg_file
from src.validators import validate_contributions_payload, validate_svg_document
from src.visualizations.contribution_city import (
    CITY_HEIGHT,
    CITY_WIDTH,
    build_contribution_city_model,
    build_contribution_city_svg,
    compute_building_height,
    iso_project,
)


class _FakeResponse:
    def __init__(self, status: int, data: Any) -> None:
        self.status = status
        self._body = json.dumps(data).encode("utf-8")
        self.headers: dict[str, str] = {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class ContributionCityTests(unittest.TestCase):
    """Verify data integrity, isometric geometry, SVG validity, interactivity, and README integration."""

    def setUp(self) -> None:
        self.commits_data = json.loads(COMMITS_PATH.read_text(encoding="utf-8"))
        self.repos_data = json.loads(REPOSITORIES_PATH.read_text(encoding="utf-8"))
        self.profile_data = json.loads(PROFILE_DATA_PATH.read_text(encoding="utf-8"))

    def test_graphql_calendar_normalization_totals_streaks_and_busiest_day(self) -> None:
        raw_cal = {
            "totalContributions": 21,
            "weeks": [
                {
                    "contributionDays": [
                        {"date": "2026-11-15", "contributionCount": 0, "contributionLevel": "NONE"},
                        {"date": "2026-11-16", "contributionCount": 2, "contributionLevel": "FIRST_QUARTILE"},
                        {"date": "2026-11-17", "contributionCount": 5, "contributionLevel": "SECOND_QUARTILE"},
                        {"date": "2026-11-18", "contributionCount": 0, "contributionLevel": "NONE"},
                        {"date": "2026-11-19", "contributionCount": 9, "contributionLevel": "FOURTH_QUARTILE"},
                        {"date": "2026-11-20", "contributionCount": 5, "contributionLevel": "THIRD_QUARTILE"},
                    ]
                }
            ],
        }
        payload = normalize_contribution_calendar(
            raw_calendar=raw_cal,
            username="Eshtiaq-a",
            source="github_graphql_contributions_collection",
            graphql_available=True,
            is_fallback=False,
            generated_at="2026-11-21T00:00:00Z",
        )
        validate_contributions_payload(payload)
        self.assertEqual(payload["total_contributions"], 21)
        self.assertEqual(payload["active_days"], 4)
        self.assertEqual(payload["max_daily_contributions"], 9)
        self.assertEqual(payload["best_streak_days"], 2)
        self.assertEqual(payload["current_streak_days"], 2)
        self.assertEqual(payload["busiest_day"]["date"], "2026-11-19")
        self.assertEqual(payload["busiest_day"]["count"], 9)
        self.assertEqual(payload["weeks"][0]["total_contributions"], 21)

        # Duplicate/negative payloads must be rejected cleanly by validator
        bad_payload = json.loads(json.dumps(payload))
        bad_payload["total_contributions"] = 999
        with self.assertRaises(ValueError):
            validate_contributions_payload(bad_payload)

    def test_graphql_client_integration_and_unauthenticated_fallback_never_expose_tokens(self) -> None:
        secret = "ghp_secret_city_token_999"

        def graphql_opener(req: Any, _timeout: int) -> _FakeResponse:
            if "graphql" in req.full_url:
                return _FakeResponse(
                    200,
                    {
                        "data": {
                            "user": {
                                "contributionsCollection": {
                                    "contributionCalendar": {
                                        "totalContributions": 12,
                                        "weeks": [
                                            {
                                                "contributionDays": [
                                                    {"date": "2026-11-22", "contributionCount": 4},
                                                    {"date": "2026-11-23", "contributionCount": 8},
                                                ]
                                            }
                                        ],
                                    }
                                }
                            }
                        }
                    },
                )
            return _FakeResponse(200, {})

        auth_client = GitHubClient(token=secret, opener=graphql_opener, sleep_fn=lambda _: None)
        gql_payload = build_contributions_payload(auth_client, "Eshtiaq-a", self.commits_data)
        self.assertTrue(gql_payload["graphql_available"])
        self.assertEqual(gql_payload["total_contributions"], 12)
        self.assertNotIn(secret, json.dumps(gql_payload))

        # Unauthenticated fallback uses real public-branch commits without fabricating extra numbers
        anon_client = GitHubClient(token="", sleep_fn=lambda _: None)
        fallback_payload = build_contributions_payload(anon_client, "Eshtiaq-a", self.commits_data)
        validate_contributions_payload(fallback_payload)
        self.assertFalse(fallback_payload["graphql_available"])
        self.assertTrue(fallback_payload["is_fallback"])
        self.assertEqual(fallback_payload["source"], "public_branch_commits_fallback")
        self.assertGreater(fallback_payload["total_contributions"], 0)

    def test_isometric_geometry_heights_painter_order_and_viewbox_bounds(self) -> None:
        # Height increases monotonically with level & count; 0 gives flat ground tile
        h0 = compute_building_height(0, 10, 0)
        h1 = compute_building_height(1, 10, 1)
        h2 = compute_building_height(4, 10, 2)
        h3 = compute_building_height(7, 10, 3)
        h4 = compute_building_height(10, 10, 4)
        self.assertEqual(h0, 1.8)
        self.assertTrue(h0 < h1 < h2 < h3 < h4)

        px0, py0 = iso_project(0, 0, 0, 215.0, 148.0, 12.6, 6.3)
        px1, py1 = iso_project(1, 0, 0, 215.0, 148.0, 12.6, 6.3)
        self.assertGreater(px1, px0)
        self.assertGreater(py1, py0)

        payload = build_contributions_from_commits(
            self.commits_data,
            username="Eshtiaq-a",
            generated_at="2026-11-27T06:00:00Z",
        )
        model = build_contribution_city_model(payload)
        # Painter's sort order must be strictly non-decreasing on (col + row, col)
        keys = [(t.col + t.row, t.col) for t in model.tiles]
        self.assertEqual(keys, sorted(keys))

        svg = build_contribution_city_svg(payload)
        root = validate_svg_document(svg)
        self.assertEqual(root.attrib.get("viewBox"), f"0 0 {CITY_WIDTH} {CITY_HEIGHT}")
        self.assertEqual(root.attrib.get("width"), str(CITY_WIDTH))
        self.assertEqual(root.attrib.get("height"), str(CITY_HEIGHT))

        # Every polygon vertex in the city must lie strictly within the SVG canvas
        for poly in root.iter():
            if poly.tag.rsplit("}", 1)[-1] == "polygon":
                coords = [tuple(map(float, p.split(","))) for p in poly.attrib["points"].split()]
                for vx, vy in coords:
                    self.assertGreaterEqual(vx, 0.0)
                    self.assertLessEqual(vx, float(CITY_WIDTH))
                    self.assertGreaterEqual(vy, 0.0)
                    self.assertLessEqual(vy, float(CITY_HEIGHT))

    def test_svg_colors_animations_interactivity_determinism_and_standalone_page(self) -> None:
        payload = build_contributions_from_commits(
            self.commits_data,
            username="Eshtiaq-a",
            generated_at="2026-11-27T06:00:00Z",
        )
        svg1 = build_contribution_city_svg(payload)
        svg2 = build_contribution_city_svg(payload)
        self.assertEqual(svg1, svg2)

        for marker in (
            "#080c18",
            "#3bd4eb",
            "#7ef9ff",
            "@keyframes cityGrow",
            "@keyframes cityBeaconPulse",
            "prefers-reduced-motion: reduce",
            'class="city-tile"',
            'tabindex="0"',
            'role="graphics-symbol"',
            "0 contributions",
        ):
            self.assertIn(marker, svg1)

        root = validate_svg_document(svg1)
        tile_groups = [
            el for el in root.iter()
            if el.tag.rsplit("}", 1)[-1] == "g" and el.attrib.get("class") == "city-tile"
        ]
        self.assertEqual(len(tile_groups), payload["days_count"])
        for g in tile_groups[:10]:
            self.assertIn("data-date", g.attrib)
            self.assertIn("data-count", g.attrib)
            self.assertIn("aria-label", g.attrib)

        html_page = build_standalone_city_html(svg1, "Eshtiaq-a")
        self.assertIn("city-inspector", html_page)
        self.assertIn("data-date", html_page)

        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            c_json = t / "contributions.json"
            c_svg = t / "city.svg"
            c_json.write_text(json.dumps(payload), encoding="utf-8")
            written = generate_city_svg_file(contributions_path=c_json, output_path=c_svg)
            self.assertEqual(written.read_text(encoding="utf-8"), svg1)

    def test_readme_section_ordering_and_pipeline_regeneration_on_contribution_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            repos_file = t / "repositories.json"
            commits_file = t / "commits.json"
            profile_file = t / "profile_data.json"
            contrib_file = t / "contributions.json"
            city_svg_file = t / "assets" / "contribution_city.svg"
            readme_file = t / "README.md"

            repos_file.write_text(json.dumps(self.repos_data), encoding="utf-8")
            commits_file.write_text(json.dumps(self.commits_data), encoding="utf-8")
            profile_file.write_text(json.dumps(self.profile_data), encoding="utf-8")

            c1 = build_contributions_from_commits(
                self.commits_data,
                username="Eshtiaq-a",
                generated_at="2026-11-27T06:00:00Z",
            )
            contrib_file.write_text(json.dumps(c1), encoding="utf-8")

            run_full_profile_pipeline(
                repositories_path=repos_file,
                commits_path=commits_file,
                profile_data_path=profile_file,
                contributions_path=contrib_file,
                workspace_svg_path=t / "workspace.svg",
                neofetch_svg_path=t / "neofetch.svg",
                repo_cards_dir=t / "assets" / "repos",
                contribution_city_svg_path=city_svg_file,
                explorer_svg_path=t / "explorer.svg",
                explorer_slices_dir=t / "explorer",
                divider_svg_path=t / "divider.svg",
                readme_path=readme_file,
                from_cache=True,
            )

            readme = readme_file.read_text(encoding="utf-8")
            idx_room = readme.index("assets/workspace.svg")
            idx_neofetch = readme.index("assets/neofetch.svg")
            idx_galaxy_cards = readme.index("assets/repos/")
            idx_city = readme.index("assets/contribution_city.svg")
            idx_explorer = readme.index("assets/explorer/header.svg")
            self.assertTrue(idx_room < idx_neofetch < idx_galaxy_cards < idx_city < idx_explorer)

            # Mutate contribution count -> city SVG & README summary regenerate with new totals
            c2 = json.loads(json.dumps(c1))
            c2["weeks"][-1]["days"][-1]["count"] += 15
            c2["weeks"][-1]["days"][-1]["level"] = 4
            c2["weeks"][-1]["days"][-1]["intensity_label"] = "Peak"
            c2["weeks"][-1]["total_contributions"] += 15
            c2["total_contributions"] += 15
            c2["max_daily_contributions"] = max(
                d["count"] for w in c2["weeks"] for d in w["days"]
            )
            c2["active_days"] = sum(1 for w in c2["weeks"] for d in w["days"] if d["count"] > 0)
            contrib_file.write_text(json.dumps(c2), encoding="utf-8")

            before_svg = city_svg_file.read_text(encoding="utf-8")
            run_full_profile_pipeline(
                repositories_path=repos_file,
                commits_path=commits_file,
                profile_data_path=profile_file,
                contributions_path=contrib_file,
                workspace_svg_path=t / "workspace.svg",
                neofetch_svg_path=t / "neofetch.svg",
                repo_cards_dir=t / "assets" / "repos",
                contribution_city_svg_path=city_svg_file,
                explorer_svg_path=t / "explorer.svg",
                explorer_slices_dir=t / "explorer",
                divider_svg_path=t / "divider.svg",
                readme_path=readme_file,
                from_cache=True,
            )
            after_svg = city_svg_file.read_text(encoding="utf-8")
            self.assertNotEqual(before_svg, after_svg)
            self.assertIn(f"{c2['total_contributions']} contributions", readme_file.read_text(encoding="utf-8"))
            self.assertNotIn("assets/", " ".join(re.findall(r'href="([^"]+)"', readme_file.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()
