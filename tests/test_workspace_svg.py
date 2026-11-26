"""Automated tests for Phase 1 Pixel-Art Workspace and Movie-Credit SVG."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.config import SAMPLE_COMMITS_PATH, load_profile_config
from src.credits_formatter import build_credit_sequence
from src.gif_workspace import compute_gif_fallback_plan
from src.svg_workspace import build_workspace_svg, generate_workspace_svg_file
from src.validators import validate_commits_payload, validate_svg_document
from src.workspace_scene import resolve_is_daytime


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

    def test_monstera_deliciosa_and_vertical_only_coffee_steam(self) -> None:
        night_svg = build_workspace_svg(self.payload, self.config, theme="night")
        validate_svg_document(night_svg)
        # Monstera fenestrations, light back leaf & rounded cream pot present
        self.assertIn("#56c95e", night_svg)
        self.assertIn("#73dc78", night_svg)
        self.assertIn("#7a4a2b", night_svg)

        # Steam animations must go straight up (translateY only, zero scaleX/translateX drift)
        steam_blocks = re.findall(r"@keyframes\s+(?:steamRise|steamPuff)\s*\{\{?(.*?)\}\}", night_svg, re.S)
        # Extract from <style> block cleanly
        style_section = night_svg[night_svg.index("<style>") : night_svg.index("</style>")]
        for name in ("steamRise", "steamPuff"):
            m = re.search(rf"@keyframes\s+{name}\s*\{{(.*?)\n\s*\}}", style_section, re.S)
            self.assertIsNotNone(m, f"Missing @keyframes {name}")
            block = m.group(1)  # type: ignore[union-attr]
            self.assertNotIn("scaleX", block)
            self.assertNotIn("translateX", block)
            self.assertIn("translateY", block)

    def test_day_night_schedule_switches_window_and_desk_lamp_cleanly(self) -> None:
        # Asia/Dhaka = UTC+6: 00:00 UTC -> 06:00 AM (day); 12:00 UTC -> 06:00 PM (night)
        self.assertFalse(resolve_is_daytime("Asia/Dhaka", "auto", datetime(2026, 11, 26, 23, 59, tzinfo=timezone.utc)))
        self.assertTrue(resolve_is_daytime("Asia/Dhaka", "auto", datetime(2026, 11, 27, 0, 0, tzinfo=timezone.utc)))
        self.assertTrue(resolve_is_daytime("Asia/Dhaka", "auto", datetime(2026, 11, 27, 11, 59, tzinfo=timezone.utc)))
        self.assertFalse(resolve_is_daytime("Asia/Dhaka", "auto", datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)))

        day_svg = build_workspace_svg(self.payload, self.config, theme="day")
        night_svg = build_workspace_svg(self.payload, self.config, theme="night")
        validate_svg_document(day_svg)
        validate_svg_document(night_svg)

        # Day: lamp glow cone element omitted (light off), sunny sky + sun + clouds rendered
        self.assertNotIn('<polygon class="lamp-glow-cone"', day_svg)
        self.assertIn('fill="#4ca8f5"', day_svg)
        self.assertIn('fill="#ffd94a"', day_svg)
        self.assertIn('<g class="cloud-drift-1">', day_svg)
        self.assertIn('<g class="cloud-drift-2">', day_svg)
        self.assertNotIn('<line class="shooting-star-1"', day_svg)

        # Night: lamp glow cone element present (light on), dark night sky + moon + shooting stars
        self.assertIn('<polygon class="lamp-glow-cone"', night_svg)
        self.assertIn('fill="#0a1a39"', night_svg)
        self.assertIn('<line class="shooting-star-1"', night_svg)
        self.assertNotIn('<g class="cloud-drift-1">', night_svg)


if __name__ == "__main__":
    unittest.main()
