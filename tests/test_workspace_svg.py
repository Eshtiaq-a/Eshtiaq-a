"""Automated tests for Phase 1 Pixel-Art Workspace and Movie-Credit SVG."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.config import SAMPLE_COMMITS_PATH, load_profile_config
from src.credits_formatter import build_credit_sequence
from src.gif_workspace import compute_gif_fallback_plan
from src.svg_workspace import build_workspace_svg, generate_workspace_svg_file
from src.validators import validate_commits_payload, validate_svg_document


class WorkspaceSvgTests(unittest.TestCase):
    """Validate Phase 1 workspace visual generation, escaping, and constraints."""

    def setUp(self) -> None:
        self.config = load_profile_config()
        self.payload = json.loads(SAMPLE_COMMITS_PATH.read_text(encoding="utf-8"))

    def test_sample_payload_is_explicitly_labelled_and_valid(self) -> None:
        self.assertTrue(self.payload.get("is_sample_data"))
        validate_commits_payload(self.payload)

    def test_rejects_female_character_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_cfg = Path(tmp) / "profile.json"
            bad_cfg.write_text(
                json.dumps(
                    {
                        "username": "Eshtiaq-a",
                        "display_name": "Eshtiaq Ahmad",
                        "workspace": {"human_character_gender": "female"},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_profile_config(bad_cfg)

    def test_credit_sequence_includes_opening_repos_commits_and_closing(self) -> None:
        lines, seq_height, duration = build_credit_sequence(self.payload)
        texts = [line.text for line in lines if line.text]
        joined = "\n".join(texts)

        self.assertGreater(seq_height, 200)
        self.assertGreater(duration, 10.0)
        self.assertIn("A PRODUCTION BY", joined)
        self.assertIn("ESHTIAQ AHMAD", joined)
        self.assertIn("[ SAMPLE DATA PROTOTYPE ]", joined)
        self.assertIn("SAMPLE-FINANCE-CLI", joined)
        self.assertIn("THE END?", joined)
        self.assertIn("THE JOURNEY CONTINUES.", joined)

    def test_svg_generation_escaping_and_camo_safety(self) -> None:
        svg = build_workspace_svg(self.payload, self.config)
        root = validate_svg_document(svg)
        self.assertEqual(root.attrib.get("viewBox"), "0 0 988 504")
        self.assertIn('id="monitor-screen-clip"', svg)
        self.assertIn("@keyframes scrollCredits", svg)
        self.assertIn("&lt;budget&gt; thresholds &amp;", svg)
        self.assertIn("edge totals", svg)
        self.assertNotIn("gitskins.com", svg.lower())

    def test_rejects_duplicate_commit_shas(self) -> None:
        dup_payload = {
            "is_sample_data": True,
            "commits": [self.payload["commits"][0], self.payload["commits"][0]],
        }
        with self.assertRaises(ValueError):
            validate_commits_payload(dup_payload)

    def test_gif_fallback_plan_targets_camo_budget(self) -> None:
        plan = compute_gif_fallback_plan(self.payload, fps=12)
        self.assertEqual(plan.dirty_rect, (429, 132, 246, 142))
        self.assertLessEqual(plan.max_palette_colors, 64)
        self.assertGreater(plan.total_frames, 100)

    def test_write_workspace_svg_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "workspace.svg"
            written = generate_workspace_svg_file(output_path=out)
            self.assertTrue(written.exists())
            self.assertGreater(written.stat().st_size, 5_000)


if __name__ == "__main__":
    unittest.main()
