"""Unit and integration tests for stats_builder, Phase 2 pipeline, and live API."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.credits_builder import build_commits_payload
from src.github_client import GitHubClient
from src.main import run_phase2_pipeline
from src.repos_builder import build_repositories_payload
from src.stats_builder import (
    build_profile_data_payload,
    compute_calendar_streaks,
    compute_github_uptime_months,
)
from src.svg_workspace import build_workspace_svg
from src.config import load_profile_config
from src.validators import (
    validate_commits_payload,
    validate_profile_data_payload,
    validate_repositories_payload,
    validate_svg_document,
)


class _FakePipelineClient:
    has_token = False
    requests_made = 5
    last_rate_limit_remaining = 55

    def get_user_profile(self, username: str) -> dict[str, Any]:
        return {
            "login": username,
            "name": "Eshtiaq Ahmad",
            "bio": "Student",
            "location": "Dhaka, Bangladesh",
            "company": None,
            "blog": "",
            "html_url": f"https://github.com/{username}",
            "avatar_url": "https://avatars.githubusercontent.com/u/251981857?v=4",
            "public_repos": 2,
            "public_gists": 0,
            "followers": 2,
            "following": 4,
            "created_at": "2025-12-29T09:03:03Z",
            "updated_at": "2026-11-26T15:00:00Z",
        }

    def get_public_repositories(self, username: str) -> list[dict[str, Any]]:
        return [
            {
                "id": 101,
                "name": "Wrechship",
                "full_name": f"{username}/Wrechship",
                "owner": {"login": username},
                "private": False,
                "description": "Shipwreck dataset",
                "language": "Python",
                "stargazers_count": 0,
                "forks_count": 0,
                "html_url": f"https://github.com/{username}/Wrechship",
                "homepage": None,
                "archived": False,
                "fork": False,
                "size": 100,
                "default_branch": "main",
                "topics": [],
                "created_at": "2026-07-24T10:00:00Z",
                "updated_at": "2026-11-04T20:00:00Z",
                "pushed_at": "2026-07-27T20:00:00Z",
            },
            {
                "id": 102,
                "name": username,
                "full_name": f"{username}/{username}",
                "owner": {"login": username},
                "private": False,
                "description": None,
                "language": None,
                "stargazers_count": 0,
                "forks_count": 0,
                "html_url": f"https://github.com/{username}/{username}",
                "homepage": None,
                "archived": False,
                "fork": False,
                "size": 0,
                "default_branch": "main",
                "topics": [],
                "created_at": "2026-11-26T15:00:00Z",
                "updated_at": "2026-11-26T15:00:00Z",
                "pushed_at": None,
            },
        ]

    def get_repository_languages(self, _owner: str, repo: str) -> dict[str, int]:
        return {"Python": 8000, "HTML": 2000} if repo == "Wrechship" else {}

    def get_repository_branches(self, _owner: str, repo: str) -> tuple[list[dict[str, Any]], int]:
        if repo == "Wrechship":
            return [{"name": "main"}], 200
        return [], 409

    def get_branch_commits(self, _owner: str, _repo: str, _branch: str) -> tuple[list[dict[str, Any]], int]:
        return [
            {
                "sha": "abcdef0123456789abcdef0123456789abcdef01",
                "html_url": "https://github.com/Eshtiaq-a/Wrechship/commit/abcdef01",
                "commit": {
                    "message": "feat: add interactive ship coordinates & <filter>",
                    "author": {"name": "Eshtiaq_Ah", "date": "2026-07-27T20:38:00Z"},
                    "committer": {"date": "2026-07-27T20:38:00Z"},
                },
                "author": {"login": "Eshtiaq-a"},
                "parents": [{"sha": "000"}],
            }
        ], 200


class StatsAndPipelineTests(unittest.TestCase):
    """Test stats math, unauthenticated GraphQL fallback, atomic pipeline, and real SVG output."""

    def test_calendar_streaks_and_uptime(self) -> None:
        days = [
            {"date": "2026-11-23", "contributionCount": 2},
            {"date": "2026-11-24", "contributionCount": 3},
            {"date": "2026-11-25", "contributionCount": 1},
            {"date": "2026-11-26", "contributionCount": 0},
        ]
        active, current, best = compute_calendar_streaks(days)
        self.assertEqual((active, current, best), (3, 3, 3))
        months = compute_github_uptime_months(
            "2025-12-29T09:03:03Z",
            now=datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(months, 10)

    def test_end_to_end_pipeline_and_workspace_svg_real_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            summary = run_phase2_pipeline(
                repositories_path=t / "repositories.json",
                commits_path=t / "commits.json",
                profile_data_path=t / "profile_data.json",
                workspace_svg_path=t / "workspace.svg",
                client=_FakePipelineClient(),  # type: ignore[arg-type]
            )
            self.assertFalse(summary["commits"]["is_sample_data"])
            self.assertFalse(summary["profile_data"]["contribution_stats"]["available"])
            svg_text = (t / "workspace.svg").read_text(encoding="utf-8")
            validate_svg_document(svg_text)
            self.assertIn("WRECHSHIP", svg_text)
            self.assertIn("&lt;filter&gt;", svg_text)
            self.assertIn("THE END?", svg_text)
            self.assertNotIn("SAMPLE DATA PROTOTYPE", svg_text)

    def test_empty_commits_renders_graceful_empty_state_svg(self) -> None:
        cfg = load_profile_config()
        empty_payload = {
            "schema_version": "1.0.0",
            "generated_at": "2026-11-26T00:00:00Z",
            "username": "Eshtiaq-a",
            "total_unique_commits": 0,
            "repositories_processed": 0,
            "branches_processed": 0,
            "collection_warnings": [],
            "is_sample_data": False,
            "commits": [],
        }
        validate_commits_payload(empty_payload)
        svg = build_workspace_svg(empty_payload, cfg)
        validate_svg_document(svg)
        self.assertIn("NO PUBLIC COMMITS DISCOVERED YET", svg)

    @unittest.skipUnless(
        os.environ.get("RUN_LIVE_GITHUB_TESTS") == "1",
        "Set RUN_LIVE_GITHUB_TESTS=1 to run live public GitHub API integration check.",
    )
    def test_live_public_github_integration_eshtiaq_a(self) -> None:
        client = GitHubClient()
        repos_payload = build_repositories_payload(client, "Eshtiaq-a")
        commits_payload = build_commits_payload(client, "Eshtiaq-a", repos_payload["repositories"])
        profile_payload = build_profile_data_payload(client, "Eshtiaq-a", repos_payload, commits_payload)

        validate_repositories_payload(repos_payload)
        validate_commits_payload(commits_payload)
        validate_profile_data_payload(profile_payload)
        self.assertEqual(profile_payload["username"], "Eshtiaq-a")
        self.assertFalse(commits_payload["is_sample_data"])
        self.assertGreater(repos_payload["total_public_repositories"], 0)
        self.assertGreater(commits_payload["total_unique_commits"], 0)


if __name__ == "__main__":
    unittest.main()
