"""Unit tests for multi-branch commit collection and deduplication in src/credits_builder.py."""

from __future__ import annotations

import unittest
from typing import Any

from src.credits_builder import build_commits_payload
from src.github_client import GitHubApiError
from src.validators import validate_commits_payload


def _raw_commit(
    sha: str,
    msg: str,
    date: str,
    author_name: str | None = "Eshtiaq_Ah",
    author_login: str | None = "Eshtiaq-a",
    parents: int = 1,
) -> dict[str, Any]:
    commit_author = {"name": author_name, "date": date} if author_name else {"date": date}
    return {
        "sha": sha,
        "html_url": f"https://github.com/Eshtiaq-a/repo/commit/{sha}",
        "commit": {
            "message": msg,
            "author": commit_author,
            "committer": {"date": date},
        },
        "author": {"login": author_login} if author_login else None,
        "parents": [{"sha": f"p{i}"} for i in range(parents)],
    }


class _FakeCreditsClient:
    def __init__(
        self,
        branches_by_repo: dict[str, tuple[list[dict[str, Any]], int]],
        commits_by_branch: dict[tuple[str, str], tuple[list[dict[str, Any]], int] | Exception],
    ) -> None:
        self._branches = branches_by_repo
        self._commits = commits_by_branch

    def get_repository_branches(self, _owner: str, repo: str) -> tuple[list[dict[str, Any]], int]:
        return self._branches.get(repo, ([], 409))

    def get_branch_commits(self, _owner: str, repo: str, branch: str) -> tuple[list[dict[str, Any]], int]:
        val = self._commits[(repo, branch)]
        if isinstance(val, Exception):
            raise val
        return val


class CreditsBuilderTests(unittest.TestCase):
    """Validate multi-branch deduplication, merge handling, partial errors, and sorting."""

    def test_multi_branch_dedup_cross_repo_identity_merge_and_chronological_sort(self) -> None:
        repos = [
            {"repository_id": 1, "name": "Alpha", "is_empty": False},
            {"repository_id": 2, "name": "Beta", "is_empty": False},
            {"repository_id": 3, "name": "EmptyRepo", "is_empty": True},
        ]
        shared_sha = "1111111111111111111111111111111111111111"
        merge_sha = "2222222222222222222222222222222222222222"
        feature_sha = "3333333333333333333333333333333333333333"

        branches = {
            "Alpha": ([{"name": "main"}, {"name": "feature/ui"}], 200),
            "Beta": ([{"name": "main"}], 200),
        }
        commits = {
            ("Alpha", "main"): (
                [
                    _raw_commit(merge_sha, "Merge pull request #1\n\nMultiline body", "2026-05-10T10:00:00Z", parents=2),
                    _raw_commit(shared_sha, "init alpha", "2026-05-01T10:00:00Z"),
                    _raw_commit(shared_sha, "init alpha", "2026-05-01T10:00:00Z"),  # duplicate in same branch
                ],
                200,
            ),
            ("Alpha", "feature/ui"): (
                [
                    _raw_commit(feature_sha, "feat: ui card", "2026-05-05T12:00:00Z", author_name=None, author_login=None),
                    _raw_commit(shared_sha, "init alpha", "2026-05-01T10:00:00Z"),  # shared ancestor on 2 branches
                ],
                200,
            ),
            ("Beta", "main"): (
                [
                    # Same SHA string in a DIFFERENT repository must remain distinct
                    _raw_commit(shared_sha, "init beta", "2026-04-01T08:00:00Z"),
                ],
                200,
            ),
        }

        payload = build_commits_payload(_FakeCreditsClient(branches, commits), "Eshtiaq-a", repos)
        validate_commits_payload(payload)

        self.assertFalse(payload["is_sample_data"])
        self.assertTrue(payload["complete_coverage"])
        self.assertEqual(payload["total_unique_commits"], 4)
        self.assertEqual(payload["repositories_processed"], 2)
        self.assertEqual(payload["repositories_skipped"], 1)
        self.assertEqual(payload["branches_processed"], 3)

        # Chronological oldest-to-newest order
        ordered = payload["commits"]
        self.assertEqual([c["repository_name"] for c in ordered], ["Beta", "Alpha", "Alpha", "Alpha"])
        self.assertEqual([c["committed_at"] for c in ordered], [
            "2026-04-01T08:00:00Z",
            "2026-05-01T10:00:00Z",
            "2026-05-05T12:00:00Z",
            "2026-05-10T10:00:00Z",
        ])

        # Shared commit preserves both branches sorted
        self.assertEqual(ordered[1]["branch_names"], ["feature/ui", "main"])
        # Missing author metadata handled safely
        self.assertIsNone(ordered[2]["author_name"])
        self.assertIsNone(ordered[2]["author_login"])
        # Merge commit & multiline message preserved intact
        self.assertTrue(ordered[3]["is_merge"])
        self.assertIn("\n\nMultiline body", ordered[3]["commit_message"])

    def test_partial_branch_failure_records_warning_and_marks_incomplete(self) -> None:
        repos = [{"repository_id": 1, "name": "Alpha", "is_empty": False}]
        branches = {"Alpha": ([{"name": "main"}, {"name": "broken"}], 200)}
        commits: dict[tuple[str, str], Any] = {
            ("Alpha", "main"): ([_raw_commit("aaa", "ok", "2026-01-01T00:00:00Z")], 200),
            ("Alpha", "broken"): GitHubApiError("HTTP 500", status_code=500, retryable=True),
        }

        payload = build_commits_payload(_FakeCreditsClient(branches, commits), "Eshtiaq-a", repos)
        validate_commits_payload(payload)
        self.assertFalse(payload["complete_coverage"])
        self.assertEqual(payload["total_unique_commits"], 1)
        self.assertEqual(payload["branches_skipped"], 1)
        self.assertEqual(len(payload["collection_warnings"]), 1)
        self.assertEqual(payload["collection_warnings"][0]["branch"], "broken")


if __name__ == "__main__":
    unittest.main()
