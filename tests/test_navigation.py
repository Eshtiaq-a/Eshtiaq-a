"""Automated tests for interactive navigation in Project Explorer (SVG + README) and Repo Galaxy."""

from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from src.config import COMMITS_PATH, CONFIG_PATH, PROFILE_DATA_PATH, REPOSITORIES_PATH
from src.explorer_builder import build_explorer_model, load_explorer_inputs
from src.main import run_full_profile_pipeline
from src.neofetch_builder import build_neofetch_model, load_phase2_inputs
from src.readme_builder import build_readme_markdown
from src.svg_explorer import write_explorer_slices
from src.svg_neofetch import build_neofetch_svg
from src.validators import validate_svg_document
from src.visualizations.project_explorer import build_explorer_slice_svgs, build_explorer_svg


class ProjectExplorerAndGalaxyNavigationTests(unittest.TestCase):
    """Verify authoritative GitHub html_url links, pointer-events, no /assets/ redirects, and pruning."""

    def setUp(self) -> None:
        self.profile_data, self.repos_data, self.commits_data, self.config_raw = load_phase2_inputs(
            PROFILE_DATA_PATH, REPOSITORIES_PATH, COMMITS_PATH, CONFIG_PATH
        )

    def test_explorer_svg_and_readme_link_every_real_repository_without_assets_hrefs(self) -> None:
        model = build_explorer_model(self.repos_data, self.commits_data, self.config_raw)
        svg = build_explorer_svg(model)
        root = validate_svg_document(svg)
        slices = build_explorer_slice_svgs(model)
        readme = build_readme_markdown(self.profile_data, self.commits_data, model)

        # Verify all 8 repositories in unified SVG
        svg_anchors = [
            el
            for el in root.iter()
            if el.tag.rsplit("}", 1)[-1] == "a"
        ]
        self.assertEqual(len(svg_anchors), 8)
        expected_urls = {r["html_url"] for r in self.repos_data["repositories"]}
        self.assertEqual({a.attrib.get("href") for a in svg_anchors}, expected_urls)
        for anchor in svg_anchors:
            self.assertEqual(anchor.attrib.get("target"), "_blank")
            self.assertEqual(anchor.attrib.get("rel"), "noopener noreferrer")
            self.assertNotIn("/assets/", anchor.attrib.get("href", ""))

        # Verify every clickable row slice in README wraps its image in <a href="repo_html_url" ...>
        self.assertEqual(len(slices["rows"]), 8)  # type: ignore[arg-type]
        for row in model.rows:
            expected_slice_img = f'src="assets/explorer/rows/{row.row_slug}.svg"'
            expected_anchor_prefix = (
                f'<a href="{row.html_url}" target="_blank" rel="noopener noreferrer"'
            )
            self.assertIn(expected_slice_img, readme)
            self.assertIn(expected_anchor_prefix, readme)
            row_idx = readme.index(expected_slice_img)
            preceding = readme[max(0, row_idx - 500) : row_idx]
            self.assertIn(f'href="{row.html_url}"', preceding)

        # Zero anchor hrefs point to /assets/
        hrefs = re.findall(r'href="([^"]+)"', readme)
        self.assertTrue(len(hrefs) >= 24)
        for href in hrefs:
            self.assertNotIn("/assets/", href)
            self.assertNotStartsWith(href, "assets/") if hasattr(self, "assertNotStartsWith") else self.assertFalse(href.startswith("assets/"))
            self.assertTrue(href.startswith("https://"))

    def test_explorer_sorting_preserves_matching_repository_links(self) -> None:
        for sort_mode in ("updated", "stars", "name"):
            model = build_explorer_model(
                self.repos_data, self.commits_data, self.config_raw, sort_by=sort_mode  # type: ignore[arg-type]
            )
            svg = build_explorer_svg(model)
            root = validate_svg_document(svg)
            anchors = [
                el.attrib.get("href")
                for el in root.iter()
                if el.tag.rsplit("}", 1)[-1] == "a"
            ]
            expected_order = [r.html_url for r in model.rows]
            self.assertEqual(anchors, expected_order)

    def test_dynamic_repo_addition_and_removal_updates_links_and_prunes_stale_slices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            repos_file = t / "repositories.json"
            commits_file = t / "commits.json"
            profile_file = t / "profile_data.json"
            slices_dir = t / "explorer"
            readme_file = t / "README.md"

            added_repos = copy.deepcopy(self.repos_data)
            added_repos["repositories"].append(
                {
                    "repository_id": 987654321,
                    "name": "auto-discovered-galaxy-app",
                    "full_name": "Eshtiaq-a/auto-discovered-galaxy-app",
                    "description": "Dynamically synced repository",
                    "primary_language": "Python",
                    "languages": {"Python": 4200},
                    "stars": 5,
                    "forks": 1,
                    "html_url": "https://github.com/Eshtiaq-a/auto-discovered-galaxy-app",
                    "homepage": None,
                    "archived": False,
                    "is_fork": False,
                    "is_empty": False,
                    "updated_at": "2026-12-01T12:00:00Z",
                    "created_at": "2026-12-01T12:00:00Z",
                    "pushed_at": "2026-12-01T12:00:00Z",
                }
            )
            added_repos["total_public_repositories"] = len(added_repos["repositories"])

            repos_file.write_text(json.dumps(added_repos), encoding="utf-8")
            commits_file.write_text(json.dumps(self.commits_data), encoding="utf-8")
            profile_file.write_text(json.dumps(self.profile_data), encoding="utf-8")

            run_full_profile_pipeline(
                repositories_path=repos_file,
                commits_path=commits_file,
                profile_data_path=profile_file,
                workspace_svg_path=t / "workspace.svg",
                neofetch_svg_path=t / "neofetch.svg",
                explorer_svg_path=t / "explorer.svg",
                explorer_slices_dir=slices_dir,
                divider_svg_path=t / "divider.svg",
                readme_path=readme_file,
                from_cache=True,
            )

            new_row_svg = slices_dir / "rows" / "auto-discovered-galaxy-app.svg"
            self.assertTrue(new_row_svg.exists())
            readme_added = readme_file.read_text(encoding="utf-8")
            neofetch_added = (t / "neofetch.svg").read_text(encoding="utf-8")
            self.assertIn("https://github.com/Eshtiaq-a/auto-discovered-galaxy-app", readme_added)
            self.assertIn("https://github.com/Eshtiaq-a/auto-discovered-galaxy-app", neofetch_added)

            # Remove repository -> stale row SVG pruned & links vanish cleanly
            removed_repos = copy.deepcopy(self.repos_data)
            repos_file.write_text(json.dumps(removed_repos), encoding="utf-8")
            run_full_profile_pipeline(
                repositories_path=repos_file,
                commits_path=commits_file,
                profile_data_path=profile_file,
                workspace_svg_path=t / "workspace.svg",
                neofetch_svg_path=t / "neofetch.svg",
                explorer_svg_path=t / "explorer.svg",
                explorer_slices_dir=slices_dir,
                divider_svg_path=t / "divider.svg",
                readme_path=readme_file,
                from_cache=True,
            )
            self.assertFalse(new_row_svg.exists())
            self.assertNotIn("auto-discovered-galaxy-app", readme_file.read_text(encoding="utf-8"))
            self.assertNotIn("auto-discovered-galaxy-app", (t / "neofetch.svg").read_text(encoding="utf-8"))

    def test_repo_galaxy_nodes_and_labels_are_clickable_and_layered_safely(self) -> None:
        model = build_neofetch_model(self.profile_data, self.repos_data, self.commits_data, self.config_raw)
        svg = build_neofetch_svg(model)
        root = validate_svg_document(svg)

        links = [
            el
            for el in root.iter()
            if el.tag.rsplit("}", 1)[-1] == "a" and "gx-repo-link" in el.attrib.get("class", "")
        ]
        self.assertEqual(len(links), 8)
        expected_urls = {r["html_url"] for r in self.repos_data["repositories"]}
        self.assertEqual({lnk.attrib.get("href") for lnk in links}, expected_urls)

        for lnk in links:
            self.assertEqual(lnk.attrib.get("target"), "_blank")
            self.assertEqual(lnk.attrib.get("rel"), "noopener noreferrer")
            self.assertEqual(lnk.attrib.get("pointer-events"), "all")
            child_classes = {c.attrib.get("class", "") for c in lnk.iter()}
            self.assertIn("gx-node-hit", child_classes)
            self.assertIn("gx-node-dot", child_classes)
            self.assertIn("gx-label-pill", child_classes)
            self.assertIn("gx-label-text", child_classes)

        # Verify all decorative galaxy rings, stars, core glow, and orbit groups use pointer-events="none"
        for elem in root.iter():
            cls = elem.attrib.get("class", "")
            if any(
                marker in cls
                for marker in (
                    "gx-star-",
                    "gx-spiral-spin",
                    "gx-ring-spin",
                    "gx-particles-spin",
                    "gx-core-pulse",
                    "gx-orbit-",
                )
            ):
                self.assertEqual(
                    elem.attrib.get("pointer-events"),
                    "none",
                    f"Decorative element class {cls!r} must not intercept pointer events",
                )

        # Preserves authoritative html_url even when label truncates AND in compact mode
        custom_repos = copy.deepcopy(self.repos_data)
        custom_repos["repositories"].append(
            {
                "repository_id": 555555,
                "name": "very-long-galaxy-node-repository-with-truncated-display-label",
                "html_url": "https://github.com/Eshtiaq-a/authoritative-custom-url-slug",
                "description": "Truncated label still preserves authoritative html_url",
                "primary_language": "TypeScript",
                "stars": 12,
                "archived": False,
                "is_empty": False,
            }
        )
        custom_repos["repositories"].append(
            {
                "repository_id": 666666,
                "name": "invalid repo name with spaces",
                "html_url": "javascript:alert(1)",
                "description": "Invalid url with unresolvable slug omits anchor gracefully",
                "primary_language": "Python",
                "stars": 0,
                "archived": False,
                "is_empty": False,
            }
        )
        custom_model = build_neofetch_model(self.profile_data, custom_repos, self.commits_data, self.config_raw)
        desktop_svg = build_neofetch_svg(custom_model, layout="desktop")
        compact_svg = build_neofetch_svg(custom_model, layout="compact")
        validate_svg_document(desktop_svg)
        validate_svg_document(compact_svg)

        for rendered in (desktop_svg, compact_svg):
            self.assertIn("https://github.com/Eshtiaq-a/authoritative-custom-url-slug", rendered)
            self.assertIn("very-long-galaxy-nod…", rendered)
            self.assertNotIn("javascript:", rendered)
            self.assertNotIn("invalid repo name with spaces", [
                el.attrib.get("href", "")
                for el in ET.fromstring(rendered).iter()
                if el.tag.rsplit("}", 1)[-1] == "a"
            ])


if __name__ == "__main__":
    unittest.main()
