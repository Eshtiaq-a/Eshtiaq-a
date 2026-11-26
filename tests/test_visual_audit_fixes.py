"""Regression tests for visual layout, collision avoidance, and compact mode audit fixes."""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from typing import Any

from src.config import (
    COMMITS_PATH,
    CONFIG_PATH,
    PROFILE_DATA_PATH,
    REPOSITORIES_PATH,
    WORKSPACE_PALETTE as P,
    load_profile_config,
)
from src.explorer_builder import ExplorerModel, ExplorerRow, build_explorer_model
from src.neofetch_builder import build_neofetch_model, load_phase2_inputs
from src.svg_workspace import build_workspace_svg
from src.validators import validate_svg_document
from src.visualizations.neofetch_terminal import build_neofetch_terminal_svg
from src.visualizations.project_explorer import build_explorer_svg
from src.visualizations.repo_galaxy import (
    _box_collides_core,
    _boxes_overlap,
    build_repo_galaxy_model,
    reflow_repo_galaxy_model,
)

SVG_NS = "{http://www.w3.org/2000/svg}"


def _make_28_repo_dataset() -> tuple[dict[str, Any], dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    langs = ("Python", "TypeScript", "HTML", "JavaScript", "C", "Rust", "Go")
    for idx in range(28):
        repos.append(
            {
                "repository_id": 1000 + idx,
                "name": f"project-alpha-service-{idx:02d}",
                "description": f"Synthetic benchmark repository {idx:02d}",
                "primary_language": langs[idx % len(langs)],
                "languages": {langs[idx % len(langs)]: 10_000 - idx * 100},
                "stars": (28 - idx) * 2 if idx < 12 else idx % 3,
                "forks": 0,
                "html_url": f"https://github.com/Eshtiaq-a/project-alpha-service-{idx:02d}",
                "archived": idx == 27,
                "is_empty": idx == 26,
                "pushed_at": f"2026-11-{(idx % 26) + 1:02d}T12:00:00Z",
            }
        )
    profile = {
        "username": "Eshtiaq-a",
        "directly_sourced_profile": {"login": "Eshtiaq-a"},
        "calculated_metrics": {"languages": []},
        "contribution_stats": {"available": False},
    }
    return {"repositories": repos}, profile


class VisualAuditFixesTests(unittest.TestCase):
    """Verify every layout and visual regression fix from the repository audit."""

    def setUp(self) -> None:
        self.profile_data, self.repos_data, self.commits_data, self.config_raw = load_phase2_inputs(
            PROFILE_DATA_PATH, REPOSITORIES_PATH, COMMITS_PATH, CONFIG_PATH
        )
        self.config = load_profile_config(CONFIG_PATH)

    def _assert_galaxy_collision_free(
        self,
        galaxy: Any,
        box_x: float,
        box_y: float,
        box_w: float,
        box_h: float,
    ) -> None:
        sky_top = box_y + 78.0
        sky_bottom = box_y + box_h - 94.0
        cx = box_x + box_w / 2.0
        cy = sky_top + (sky_bottom - sky_top) / 2.0

        labeled_nodes = [n for n in galaxy.nodes if n.show_label]
        self.assertGreater(len(labeled_nodes), 0)
        boxes = [n.label_box for n in labeled_nodes]
        self.assertTrue(all(b is not None for b in boxes))

        for i, box in enumerate(boxes):
            assert box is not None
            self.assertGreaterEqual(box[0], box_x + 14.0)
            self.assertLessEqual(box[2], box_x + box_w - 14.0)
            self.assertGreaterEqual(box[1], sky_top + 6.0)
            self.assertLessEqual(box[3], sky_bottom - 6.0)
            self.assertFalse(
                _box_collides_core(box, cx, cy, core_r=33.0),
                f"Label box {i} collided with galaxy core: {box}",
            )
            for j in range(i + 1, len(boxes)):
                other = boxes[j]
                assert other is not None
                self.assertFalse(
                    _boxes_overlap(box, other, pad_x=2.0, pad_y=2.0),
                    f"Pairwise label overlap between {i} and {j}: {box} vs {other}",
                )

    def test_28_repo_galaxy_zero_overlaps_and_core_collisions_on_desktop_and_compact(self) -> None:
        repos_28, profile = _make_28_repo_dataset()

        desktop_galaxy = build_repo_galaxy_model(
            repositories_data=repos_28,
            profile_data=profile,
            box_x=24.0,
            box_y=54.0,
            box_w=422.0,
            box_h=506.0,
        )
        self.assertEqual(len(desktop_galaxy.nodes), 28)
        self._assert_galaxy_collision_free(desktop_galaxy, 24.0, 54.0, 422.0, 506.0)

        compact_galaxy = reflow_repo_galaxy_model(
            desktop_galaxy,
            box_x=24.0,
            box_y=54.0,
            box_w=512.0,
            box_h=446.0,
        )
        self.assertEqual(len(compact_galaxy.nodes), 28)
        self._assert_galaxy_collision_free(compact_galaxy, 24.0, 54.0, 512.0, 446.0)

        # Even if caller forces max_visible_labels=28 on compact, colliding labels are suppressed rather than overlapped
        crowded_compact = build_repo_galaxy_model(
            repositories_data=repos_28,
            profile_data=profile,
            box_x=24.0,
            box_y=54.0,
            box_w=512.0,
            box_h=446.0,
            max_visible_labels=28,
        )
        self._assert_galaxy_collision_free(crowded_compact, 24.0, 54.0, 512.0, 446.0)

        # Real 8 repositories keep all 8 visible labels cleanly on both desktop and compact
        real_desktop = build_repo_galaxy_model(
            repositories_data=self.repos_data,
            profile_data=self.profile_data,
            commits_data=self.commits_data,
            box_x=24.0,
            box_y=54.0,
            box_w=422.0,
            box_h=506.0,
        )
        self.assertEqual(sum(1 for n in real_desktop.nodes if n.show_label), 8)
        self._assert_galaxy_collision_free(real_desktop, 24.0, 54.0, 422.0, 506.0)

        real_compact = reflow_repo_galaxy_model(
            real_desktop,
            box_x=24.0,
            box_y=54.0,
            box_w=512.0,
            box_h=446.0,
        )
        self.assertEqual(sum(1 for n in real_compact.nodes if n.show_label), 8)
        self._assert_galaxy_collision_free(real_compact, 24.0, 54.0, 512.0, 446.0)

    def test_neofetch_compact_preserves_commit_counts_tooltips_and_ring_order(self) -> None:
        model = build_neofetch_model(self.profile_data, self.repos_data, self.commits_data, self.config_raw)
        desktop_svg = build_neofetch_terminal_svg(model, layout="desktop")
        compact_svg = build_neofetch_terminal_svg(model, layout="compact")
        desktop_root = validate_svg_document(desktop_svg)
        compact_root = validate_svg_document(compact_svg)

        compact_galaxy = reflow_repo_galaxy_model(
            model.galaxy,
            box_x=24.0,
            box_y=54.0,
            box_w=512.0,
            box_h=446.0,
        )
        self.assertEqual(
            [(n.name, n.ring_index, n.commit_count) for n in compact_galaxy.nodes],
            [(n.name, n.ring_index, n.commit_count) for n in model.galaxy.nodes],
        )

        # Verify real commit_count tooltip ("31 commits") and matching inner ring placement for Wrechship
        self.assertIn("Wrechship", compact_svg)
        self.assertIn("31 commits", compact_svg)

        def _extract_node_rings(root: ET.Element) -> dict[str, tuple[str, str]]:
            mapping: dict[str, tuple[str, str]] = {}
            for g in root.iter(f"{SVG_NS}g"):
                cls = g.attrib.get("class", "")
                if cls.startswith("gx-orbit-"):
                    for title in g.iter(f"{SVG_NS}title"):
                        txt = title.text or ""
                        repo_name = txt.split(" · ", 1)[0]
                        mapping[repo_name] = (cls, txt)
            return mapping

        desktop_rings = _extract_node_rings(desktop_root)
        compact_rings = _extract_node_rings(compact_root)
        self.assertEqual(set(desktop_rings.keys()), set(compact_rings.keys()))
        for repo_name in desktop_rings:
            self.assertEqual(desktop_rings[repo_name][0], compact_rings[repo_name][0])
            self.assertEqual(desktop_rings[repo_name][1], compact_rings[repo_name][1])

    def test_desktop_explorer_archived_badge_clears_description_column(self) -> None:
        repos = {
            "username": "Eshtiaq-a",
            "generated_at": "2026-11-27T00:00:00Z",
            "repositories": [
                {
                    "repository_id": 501,
                    "name": "extremely-long-repository-name-that-needs-truncation",
                    "description": "Archived long description that starts at x=332 cleanly",
                    "primary_language": "Python",
                    "languages": {"Python": 5000},
                    "stars": 12,
                    "forks": 1,
                    "html_url": "https://github.com/Eshtiaq-a/extremely-long-repository-name-that-needs-truncation",
                    "archived": True,
                    "is_empty": False,
                    "updated_at": "2026-11-20T00:00:00Z",
                }
            ],
        }
        model = build_explorer_model(repos, {"commits": []}, {})
        svg = build_explorer_svg(model, layout="desktop")
        root = validate_svg_document(svg)

        # Also check defensive clamp when a caller directly supplies a 22-char display_name with ARCHIVED
        direct_row = ExplorerRow(
            repository_id=502,
            name="extremely-long-repository-22",
            display_name="extremely-long-reposit…/",
            full_name="Eshtiaq-a/extremely-long-repository-22",
            html_url="https://github.com/Eshtiaq-a/extremely-long-repository-22",
            homepage=None,
            dir_mode="dr-x",
            status_badge="ARCHIVED",
            language_tag="PY",
            language_color="#4b8bbe",
            badge_bg="#182e47",
            badge_border="#4b8bbe",
            badge_fg="#f2cb62",
            primary_language="Python",
            languages=("Python",),
            extra_language_count=0,
            description="Direct row description",
            short_description="Direct row description",
            compact_description_lines=("Direct row description",),
            stars=3,
            forks=0,
            commit_count=0,
            archived=True,
            is_empty=False,
            is_fork=False,
            updated_at="2026-11-20T00:00:00Z",
            updated_label="Nov 2026",
        )
        direct_model = ExplorerModel(
            username="Eshtiaq-a",
            sort_by="updated",
            total_repositories=1,
            active_repositories=0,
            total_stars=3,
            generated_at="2026-11-27",
            rows=(direct_row,),
        )
        direct_svg = build_explorer_svg(direct_model, layout="desktop")
        direct_root = validate_svg_document(direct_svg)

        for doc_root in (root, direct_root):
            archived_rects = [
                r
                for r in doc_root.iter(f"{SVG_NS}rect")
                if r.attrib.get("fill") == "#292018" and r.attrib.get("height") == "15"
            ]
            self.assertEqual(len(archived_rects), 1)
            pill_x = float(archived_rects[0].attrib["x"])
            pill_w = float(archived_rects[0].attrib["width"])
            self.assertLess(pill_x + pill_w, 330.0)

    def test_compact_explorer_long_25_char_username_has_no_prompt_summary_overlap(self) -> None:
        long_user = "a_very_long_username_25ch"
        self.assertEqual(len(long_user), 25)
        repos = {
            "username": long_user,
            "generated_at": "2026-11-27T00:00:00Z",
            "repositories": [
                {
                    "repository_id": 1,
                    "name": "sample-project",
                    "description": "Compact explorer test project",
                    "primary_language": "Python",
                    "languages": {"Python": 2000},
                    "stars": 12345,
                    "forks": 0,
                    "html_url": f"https://github.com/{long_user}/sample-project",
                    "archived": False,
                    "is_empty": False,
                    "updated_at": "2026-11-27T00:00:00Z",
                }
            ],
        }
        model = build_explorer_model(repos, {"commits": []}, {})
        compact_svg = build_explorer_svg(model, layout="compact")
        root = validate_svg_document(compact_svg)

        top_texts = [t for t in root.iter(f"{SVG_NS}text") if t.attrib.get("y") == "65"]
        self.assertEqual(len(top_texts), 2)
        left_prompt_text = "".join(top_texts[0].itertext())
        right_summary_text = "".join(top_texts[1].itertext())

        self.assertIn("ls ~/projects", left_prompt_text)
        left_x = float(top_texts[0].attrib["x"])
        left_end_x = left_x + len(left_prompt_text) * 7.5
        right_x = float(top_texts[1].attrib["x"])
        right_start_x = right_x - len(right_summary_text) * 6.5
        self.assertLess(left_end_x + 20.0, right_start_x)

        # Bottom footer should keep full 25-char username cleanly left of "synced ..."
        footer_texts = [t for t in root.iter(f"{SVG_NS}text") if t.attrib.get("x") == "22"]
        self.assertEqual(len(footer_texts), 1)
        footer_prompt_txt = "".join(footer_texts[0].itertext())
        self.assertIn(f"{long_user}@github", footer_prompt_txt)
        cursor_rects = [r for r in root.iter(f"{SVG_NS}rect") if "exp-cursor" in r.attrib.get("class", "")]
        self.assertEqual(len(cursor_rects), 1)
        cursor_right = float(cursor_rects[0].attrib["x"]) + float(cursor_rects[0].attrib["width"])
        self.assertLess(cursor_right, 420.0)

    def test_workspace_mug_coaster_and_cable_clear_monitor_bezel(self) -> None:
        svg = build_workspace_svg(self.commits_data, self.config)
        root = validate_svg_document(svg)

        bezel_rects = [
            r
            for r in root.iter(f"{SVG_NS}rect")
            if r.attrib.get("fill") == P["monitor_outer"] and r.attrib.get("x") == "414"
        ]
        self.assertEqual(len(bezel_rects), 1)
        bezel_left = float(bezel_rects[0].attrib["x"])
        bezel_right = bezel_left + float(bezel_rects[0].attrib["width"])
        self.assertEqual((bezel_left, bezel_right), (414.0, 686.0))

        # Verify coaster, mug, handle, and steam elements sit strictly right of monitor bezel x=686 and on desk <= 742
        coaster_rects = [
            r
            for r in root.iter(f"{SVG_NS}rect")
            if r.attrib.get("fill") == P["wood_dark"] and r.attrib.get("y") == "295"
        ]
        self.assertEqual(len(coaster_rects), 1)

        mug_and_steam = [
            r
            for r in root.iter(f"{SVG_NS}rect")
            if (
                r.attrib.get("fill") in {P["mug_cream"], P["mug_shadow"]}
                or "mug-steam-" in r.attrib.get("class", "")
            )
            and float(r.attrib.get("y", "0")) >= 250.0
            and float(r.attrib.get("y", "0")) <= 300.0
            and float(r.attrib.get("x", "0")) >= 650.0
        ]
        mug_bounds_rects = coaster_rects + mug_and_steam
        self.assertGreaterEqual(len(mug_bounds_rects), 9)

        for rect in mug_bounds_rects:
            rx0 = float(rect.attrib["x"])
            rx1 = rx0 + float(rect.attrib["width"])
            self.assertGreater(rx0, bezel_right, f"Element {rect.attrib} collides with monitor bezel x={bezel_right}")
            self.assertLessEqual(rx1, 742.0, f"Element {rect.attrib} exceeds desk right edge x=742")

        # Verify Raspberry Pi box no longer sits atop the MacBook-to-monitor cable run (x=422..493)
        pi_rects = [
            r
            for r in root.iter(f"{SVG_NS}rect")
            if r.attrib.get("fill") == P["monitor_inner"] and r.attrib.get("y") == "289"
        ]
        self.assertEqual(len(pi_rects), 1)
        pi_x = float(pi_rects[0].attrib["x"])
        self.assertGreater(pi_x, 596.0)


if __name__ == "__main__":
    unittest.main()
