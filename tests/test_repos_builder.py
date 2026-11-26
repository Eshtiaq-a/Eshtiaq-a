"""Unit tests for src/repos_builder.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.repos_builder import build_repositories_payload, write_repositories_json
from src.validators import validate_repositories_payload


class _FakeReposClient:
    def __init__(self, repos: list[dict[str, Any]], langs: dict[str, dict[str, int]]) -> None:
        self._repos = repos
        self._langs = langs

    def get_public_repositories(self, username: str) -> list[dict[str, Any]]:
        return [
            r
            for r in self._repos
            if not r.get("private", False)
            and r.get("owner", {}).get("login", "").lower() == username.lower()
        ]

    def get_repository_languages(self, _owner: str, repo: str) -> dict[str, int]:
        return self._langs.get(repo, {})


class ReposBuilderTests(unittest.TestCase):
    """Test repository discovery, null handling, empty/archived flags, and atomic writes."""

    def test_discovers_handles_nulls_empty_archived_and_sorts(self) -> None:
        raw_repos = [
            {
                "id": 10,
                "name": "old-archived",
                "full_name": "Eshtiaq-a/old-archived",
                "owner": {"login": "Eshtiaq-a"},
                "private": False,
                "description": "",
                "language": None,
                "stargazers_count": 5,
                "forks_count": 1,
                "html_url": "https://github.com/Eshtiaq-a/old-archived",
                "homepage": "",
                "archived": True,
                "fork": False,
                "size": 120,
                "default_branch": "main",
                "topics": [],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-02-01T00:00:00Z",
                "pushed_at": "2026-02-01T00:00:00Z",
            },
            {
                "id": 11,
                "name": "Eshtiaq-a",
                "full_name": "Eshtiaq-a/Eshtiaq-a",
                "owner": {"login": "Eshtiaq-a"},
                "private": False,
                "description": None,
                "language": None,
                "stargazers_count": 0,
                "forks_count": 0,
                "html_url": "https://github.com/Eshtiaq-a/Eshtiaq-a",
                "homepage": None,
                "archived": False,
                "fork": False,
                "size": 0,
                "default_branch": "main",
                "topics": [],
                "created_at": "2026-11-26T00:00:00Z",
                "updated_at": "2026-11-26T00:00:00Z",
                "pushed_at": None,
            },
            {
                "id": 12,
                "name": "Wrechship",
                "full_name": "Eshtiaq-a/Wrechship",
                "owner": {"login": "Eshtiaq-a"},
                "private": False,
                "description": "Maritime dataset",
                "language": "Python",
                "stargazers_count": 3,
                "forks_count": 2,
                "html_url": "https://github.com/Eshtiaq-a/Wrechship",
                "homepage": "https://www.wreckship.me/",
                "archived": False,
                "fork": False,
                "size": 7600,
                "default_branch": "main",
                "topics": ["ship"],
                "created_at": "2026-07-24T00:00:00Z",
                "updated_at": "2026-11-04T00:00:00Z",
                "pushed_at": "2026-07-27T00:00:00Z",
            },
            {
                "id": 99,
                "name": "other-user-repo",
                "full_name": "someone/other-user-repo",
                "owner": {"login": "someone"},
                "private": False,
                "size": 100,
            },
            {
                "id": 100,
                "name": "secret-private",
                "full_name": "Eshtiaq-a/secret-private",
                "owner": {"login": "Eshtiaq-a"},
                "private": True,
                "size": 100,
            },
        ]
        client = _FakeReposClient(raw_repos, {"Wrechship": {"Python": 5000, "HTML": 1000}})
        payload = build_repositories_payload(client, "Eshtiaq-a", generated_at="2026-11-26T16:00:00Z")

        validate_repositories_payload(payload)
        self.assertEqual(payload["total_public_repositories"], 3)
        self.assertEqual(payload["archived_repositories"], 1)
        names = [r["name"] for r in payload["repositories"]]
        self.assertEqual(names, ["Wrechship", "Eshtiaq-a", "old-archived"])
        self.assertIsNone(payload["repositories"][1]["description"])
        self.assertIsNone(payload["repositories"][1]["primary_language"])
        self.assertTrue(payload["repositories"][1]["is_empty"])

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "repositories.json"
            write_repositories_json(payload, out)
            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["total_public_repositories"], 3)


if __name__ == "__main__":
    unittest.main()
