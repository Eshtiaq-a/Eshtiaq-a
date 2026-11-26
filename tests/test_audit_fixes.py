"""Regression and coverage tests for audit-identified data, security, and escaping fixes."""

from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import patch

from src.config import load_profile_config
from src.explorer_builder import build_explorer_model
from src.github_client import GitHubApiError, GitHubClient
from src.readme_builder import build_readme_markdown
from src.repos_builder import _parse_iso_ts, sort_repositories
from src.stats_builder import build_profile_data_payload
from src.svg_workspace import build_workspace_svg
from src.validators import validate_svg_document
from tests.test_github_client import _FakeHttpResponse, _http_error


class SvgValidatorAuditTests(unittest.TestCase):
    """Verify SVG validator rejects event attributes without false-positiving on text."""

    def test_allows_text_and_title_with_only_or_once_equals(self) -> None:
        safe_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100" '
            'aria-label="commit only=1 once=true">'
            '<title>fix only=1 and once=2 edge case</title>'
            '<text x="10" y="20">only=1 once=2 onload-text</text>'
            "</svg>"
        )
        root = validate_svg_document(safe_svg)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_workspace_svg_with_only_and_once_commit_text_passes(self) -> None:
        cfg = load_profile_config()
        commits_payload: dict[str, Any] = {
            "schema_version": "1.0.0",
            "generated_at": "2026-11-26T00:00:00Z",
            "username": "Eshtiaq-a",
            "total_unique_commits": 1,
            "repositories_processed": 1,
            "branches_processed": 1,
            "collection_warnings": [],
            "is_sample_data": False,
            "commits": [
                {
                    "repository_id": 1,
                    "repository_name": "demo-repo",
                    "commit_sha": "abc1234",
                    "commit_message": "fix: query with only=1 and once=2 params",
                    "author_name": "Eshtiaq",
                    "author_login": "Eshtiaq-a",
                    "committed_at": "2026-11-26T12:00:00Z",
                    "commit_url": "https://github.com/Eshtiaq-a/demo-repo/commit/abc1234",
                    "branch_names": ["main"],
                }
            ],
        }
        svg = build_workspace_svg(commits_payload, cfg)
        validate_svg_document(svg)
        self.assertIn("only=1", svg)
        self.assertIn("once=2", svg)

    def test_rejects_inline_event_attributes_and_forbidden_svg_elements(self) -> None:
        malicious_cases = [
            '<svg xmlns="http://www.w3.org/2000/svg"><rect onclick="alert(1)"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><path onmouseover=alert(1)/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><path onmouseover="alert(1)"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" onload="evil()"><rect width="10" height="10"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:x="urn:x"><rect x:onclick="alert(1)"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject width="10" height="10"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/img.png"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><a href="https://evil.example"><rect/></a></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><rect/></a></svg>',
        ]
        for bad_svg in malicious_cases:
            with self.subTest(bad_svg=bad_svg):
                with self.assertRaises(ValueError):
                    validate_svg_document(bad_svg)


class ReposBuilderTimestampTests(unittest.TestCase):
    """Verify safe ISO timestamp parsing and sorting in repos_builder."""

    def test_parse_iso_ts_handles_invalid_and_empty_values(self) -> None:
        self.assertEqual(_parse_iso_ts(None), 0.0)
        self.assertEqual(_parse_iso_ts(""), 0.0)
        self.assertEqual(_parse_iso_ts("not-a-timestamp"), 0.0)
        self.assertGreater(_parse_iso_ts("2026-11-26T12:00:00Z"), 0.0)

    def test_sort_repositories_handles_malformed_pushed_at_and_preserves_valid_order(self) -> None:
        repos = [
            {
                "repository_id": 1,
                "name": "older-valid",
                "archived": False,
                "is_empty": False,
                "stars": 0,
                "pushed_at": "2026-01-01T00:00:00Z",
            },
            {
                "repository_id": 2,
                "name": "malformed-ts",
                "archived": False,
                "is_empty": False,
                "stars": 0,
                "pushed_at": "invalid-date",
            },
            {
                "repository_id": 3,
                "name": "newer-valid",
                "archived": False,
                "is_empty": False,
                "stars": 0,
                "pushed_at": "2026-11-01T00:00:00Z",
            },
        ]
        ordered = sort_repositories(repos)
        self.assertEqual([r["name"] for r in ordered], ["newer-valid", "older-valid", "malformed-ts"])


class GitHubClientAndGraphQLAuditTests(unittest.TestCase):
    """Cover mocked HTTP opener paths for REST discovery, rate-limit reset, and GraphQL."""

    def test_get_public_repositories_pagination_and_filtering(self) -> None:
        requested_urls: list[str] = []

        def fake_opener(req: Any, _timeout: int) -> _FakeHttpResponse:
            requested_urls.append(req.full_url)
            if "page=2" in req.full_url:
                return _FakeHttpResponse(
                    200,
                    [
                        {
                            "id": 30,
                            "name": "page2-public",
                            "owner": {"login": "eshtiaq-a"},
                            "private": False,
                        }
                    ],
                )
            return _FakeHttpResponse(
                200,
                [
                    {
                        "id": 10,
                        "name": "owned-public",
                        "owner": {"login": "Eshtiaq-a"},
                        "private": False,
                    },
                    {
                        "id": 11,
                        "name": "owned-private",
                        "owner": {"login": "Eshtiaq-a"},
                        "private": True,
                    },
                    {
                        "id": 12,
                        "name": "someone-elses-repo",
                        "owner": {"login": "other-user"},
                        "private": False,
                    },
                ],
                {"Link": '<https://api.github.com/users/Eshtiaq-a/repos?page=2>; rel="next"'},
            )

        client = GitHubClient(token="", opener=fake_opener, sleep_fn=lambda _: None)
        repos = client.get_public_repositories("Eshtiaq-a")
        self.assertEqual([r["name"] for r in repos], ["owned-public", "page2-public"])
        self.assertEqual(len(requested_urls), 2)
        self.assertIn("/users/Eshtiaq-a/repos?type=owner&per_page=100&sort=updated", requested_urls[0])

    def test_get_repository_branches_pagination_and_404_409(self) -> None:
        def paginated_opener(req: Any, _timeout: int) -> _FakeHttpResponse:
            if "page=2" in req.full_url:
                return _FakeHttpResponse(200, [{"name": "dev"}])
            return _FakeHttpResponse(
                200,
                [{"name": "main"}],
                {"Link": '<https://api.github.com/repos/Eshtiaq-a/App/branches?page=2>; rel="next"'},
            )

        client = GitHubClient(token="", opener=paginated_opener, sleep_fn=lambda _: None)
        branches, status = client.get_repository_branches("Eshtiaq-a", "App")
        self.assertEqual(status, 200)
        self.assertEqual([b["name"] for b in branches], ["main", "dev"])

        for err_code in (404, 409):
            with self.subTest(err_code=err_code):
                attempts = 0

                def err_opener(req: Any, _timeout: int, code: int = err_code) -> Any:
                    nonlocal attempts
                    attempts += 1
                    raise _http_error(req.full_url, code)

                err_client = GitHubClient(token="", opener=err_opener, max_retries=3, sleep_fn=lambda _: None)
                got_branches, got_status = err_client.get_repository_branches("Eshtiaq-a", "Missing")
                self.assertEqual(got_status, err_code)
                self.assertEqual(got_branches, [])
                self.assertEqual(attempts, 1)

    def test_compute_retry_delay_x_ratelimit_reset_branch(self) -> None:
        client = GitHubClient(token="", backoff_base_sec=1.5, sleep_fn=lambda _: None)
        with patch("src.github_client.time.time", return_value=1_700_000_000.0):
            # Within 60s window uses exact remaining reset delay
            self.assertEqual(
                client._compute_retry_delay(0, {"x-ratelimit-reset": "1700000018"}, is_rate_limit=True),
                18.0,
            )
            # Past reset timestamp clamps to minimum 1.0s
            self.assertEqual(
                client._compute_retry_delay(0, {"x-ratelimit-reset": "1699999990"}, is_rate_limit=True),
                1.0,
            )
            # Over 60s falls back to exponential backoff
            self.assertEqual(
                client._compute_retry_delay(1, {"x-ratelimit-reset": "1700000300"}, is_rate_limit=True),
                3.0,
            )

        # End-to-end 403 x-ratelimit-remaining=0 + x-ratelimit-reset retry
        sleeps: list[float] = []
        attempts = 0

        def rate_limit_opener(req: Any, _timeout: int) -> Any:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise _http_error(
                    req.full_url,
                    403,
                    {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1700000012"},
                )
            return _FakeHttpResponse(200, {"ok": True})

        retry_client = GitHubClient(token="", opener=rate_limit_opener, max_retries=2, sleep_fn=sleeps.append)
        with patch("src.github_client.time.time", return_value=1_700_000_000.0):
            resp = retry_client.request_json("https://api.github.com/rate_limit")
        self.assertEqual(resp.data, {"ok": True})
        self.assertEqual(sleeps, [12.0])

    def test_graphql_contribution_calendar_and_profile_payload_with_token(self) -> None:
        secret_token = "ghp_mocked_secret_token_never_expose"
        seen_auth_headers: list[str | None] = []

        def fake_opener(req: Any, _timeout: int) -> _FakeHttpResponse:
            auth = req.get_header("Authorization")
            seen_auth_headers.append(auth)
            if req.full_url == "https://api.github.com/graphql":
                payload = json.loads(req.data.decode("utf-8"))
                self.assertEqual(payload["variables"]["login"], "Eshtiaq-a")
                return _FakeHttpResponse(
                    200,
                    {
                        "data": {
                            "user": {
                                "contributionsCollection": {
                                    "contributionCalendar": {
                                        "totalContributions": 14,
                                        "weeks": [
                                            {
                                                "contributionDays": [
                                                    {"date": "2026-11-21", "contributionCount": 2},
                                                    {"date": "2026-11-22", "contributionCount": 3},
                                                    {"date": "2026-11-23", "contributionCount": 0},
                                                    {"date": "2026-11-24", "contributionCount": 4},
                                                    {"date": "2026-11-25", "contributionCount": 5},
                                                    {"date": "2026-11-26", "contributionCount": 0},
                                                ]
                                            }
                                        ],
                                    }
                                }
                            }
                        }
                    },
                )
            return _FakeHttpResponse(
                200,
                {
                    "login": "Eshtiaq-a",
                    "name": "Eshtiaq Ahmad",
                    "bio": "Builder",
                    "location": "Dhaka",
                    "company": None,
                    "blog": "",
                    "html_url": "https://github.com/Eshtiaq-a",
                    "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
                    "public_repos": 1,
                    "public_gists": 0,
                    "followers": 2,
                    "following": 4,
                    "created_at": "2025-12-29T09:03:03Z",
                    "updated_at": "2026-11-26T12:00:00Z",
                },
            )

        client = GitHubClient(token=secret_token, opener=fake_opener, sleep_fn=lambda _: None)
        self.assertTrue(client.has_token)

        cal = client.get_contribution_calendar("Eshtiaq-a")
        self.assertIsNotNone(cal)
        self.assertEqual(cal["totalContributions"], 14)

        repos_payload = {
            "repositories": [
                {"name": "demo", "stars": 1, "forks": 0, "is_fork": False, "is_empty": False, "archived": False, "languages": {"Python": 500}}
            ]
        }
        commits_payload = {
            "repositories_processed": 1,
            "branches_processed": 1,
            "commits": [{"committed_at": "2026-11-25T10:00:00Z"}],
        }
        profile_payload = build_profile_data_payload(
            client,
            "Eshtiaq-a",
            repos_payload,
            commits_payload,
            generated_at="2026-11-26T16:00:00Z",
        )

        self.assertEqual(
            profile_payload["contribution_stats"],
            {
                "available": True,
                "source": "github_graphql_contributions_collection",
                "total_contributions": 14,
                "active_days": 4,
                "current_streak_days": 2,
                "best_streak_days": 2,
            },
        )
        self.assertTrue(all(h == f"Bearer {secret_token}" for h in seen_auth_headers))
        self.assertNotIn(secret_token, json.dumps(profile_payload))

        # Verify GraphQL error fallback also keeps token secret
        def failing_graphql_opener(req: Any, _timeout: int) -> Any:
            if req.full_url == "https://api.github.com/graphql":
                raise _http_error(req.full_url, 401)
            return fake_opener(req, _timeout)

        err_client = GitHubClient(token=secret_token, opener=failing_graphql_opener, max_retries=0, sleep_fn=lambda _: None)
        fallback_payload = build_profile_data_payload(
            err_client,
            "Eshtiaq-a",
            repos_payload,
            commits_payload,
            generated_at="2026-11-26T16:00:00Z",
        )
        self.assertFalse(fallback_payload["contribution_stats"]["available"])
        self.assertEqual(fallback_payload["contribution_stats"]["source"], "graphql_unavailable_or_failed")
        self.assertEqual(len(fallback_payload["collection_warnings"]), 1)
        self.assertNotIn(secret_token, json.dumps(fallback_payload))


class ExplorerAndReadmeHardeningTests(unittest.TestCase):
    """Verify homepage URL hardening, ARCHIVED name length budget, and README table escaping."""

    def test_rejects_markdown_breaking_homepage_urls_and_escapes_table_chars(self) -> None:
        repos_data: dict[str, Any] = {
            "username": "Eshtiaq-a",
            "generated_at": "2026-11-27T00:00:00Z",
            "repositories": [
                {
                    "repository_id": 1,
                    "name": "bad-paren-homepage",
                    "description": "Checks [link](https://evil.test) and `code` | pipe & <tag>",
                    "primary_language": "Python",
                    "languages": {"Python": 500},
                    "stars": 1,
                    "forks": 0,
                    "html_url": "https://github.com/Eshtiaq-a/bad-paren-homepage",
                    "homepage": "https://example.com/demo)break",
                    "archived": False,
                    "is_empty": False,
                    "updated_at": "2026-11-26T00:00:00Z",
                },
                {
                    "repository_id": 2,
                    "name": "bad-bracket-backtick",
                    "description": "Clean description",
                    "primary_language": "Python",
                    "languages": {"Python": 200},
                    "stars": 0,
                    "forks": 0,
                    "html_url": "https://github.com/Eshtiaq-a/bad-bracket-backtick",
                    "homepage": "https://example.com/[a]`b`(c)",
                    "archived": False,
                    "is_empty": False,
                    "updated_at": "2026-11-25T00:00:00Z",
                },
                {
                    "repository_id": 3,
                    "name": "valid-live-homepage",
                    "description": "Works cleanly",
                    "primary_language": "TypeScript",
                    "languages": {"TypeScript": 900},
                    "stars": 3,
                    "forks": 0,
                    "html_url": "https://github.com/Eshtiaq-a/valid-live-homepage",
                    "homepage": "https://valid-demo.vercel.app/app?v=1",
                    "archived": False,
                    "is_empty": False,
                    "updated_at": "2026-11-27T00:00:00Z",
                },
            ],
        }
        model = build_explorer_model(repos_data, {"commits": []}, {})
        by_name = {row.name: row for row in model.rows}

        self.assertIsNone(by_name["bad-paren-homepage"].homepage)
        self.assertIsNone(by_name["bad-paren-homepage"].status_badge)
        self.assertIsNone(by_name["bad-bracket-backtick"].homepage)
        self.assertEqual(by_name["valid-live-homepage"].homepage, "https://valid-demo.vercel.app/app?v=1")
        self.assertEqual(by_name["valid-live-homepage"].status_badge, "LIVE")

        md = build_readme_markdown({"username": "Eshtiaq-a"}, {"commits": []}, model)
        self.assertIn(r"Checks \[link\](https://evil.test) and \`code\` \| pipe &amp; &lt;tag&gt;", md)
        self.assertNotIn("demo)break", md)
        self.assertNotIn("[a]`b`(c)", md)
        self.assertIn("[Live](https://valid-demo.vercel.app/app?v=1)", md)

    def test_archived_badge_limits_display_name_length_to_17(self) -> None:
        repos_data: dict[str, Any] = {
            "username": "Eshtiaq-a",
            "generated_at": "2026-11-27T00:00:00Z",
            "repositories": [
                {
                    "repository_id": 10,
                    "name": "very-long-archived-repository-name",
                    "archived": True,
                    "is_empty": False,
                    "updated_at": "2026-11-26T00:00:00Z",
                },
                {
                    "repository_id": 11,
                    "name": "very-long-live-repository-name",
                    "homepage": "https://live.example.com",
                    "archived": False,
                    "is_empty": False,
                    "updated_at": "2026-11-26T00:00:00Z",
                },
                {
                    "repository_id": 12,
                    "name": "very-long-plain-repository-name",
                    "archived": False,
                    "is_empty": False,
                    "updated_at": "2026-11-26T00:00:00Z",
                },
            ],
        }
        model = build_explorer_model(repos_data, {"commits": []}, {})
        by_name = {row.name: row for row in model.rows}

        self.assertEqual(by_name["very-long-archived-repository-name"].status_badge, "ARCHIVED")
        self.assertLessEqual(len(by_name["very-long-archived-repository-name"].display_name), 17)
        self.assertEqual(by_name["very-long-live-repository-name"].status_badge, "LIVE")
        self.assertLessEqual(len(by_name["very-long-live-repository-name"].display_name), 22)
        self.assertIsNone(by_name["very-long-plain-repository-name"].status_badge)
        self.assertLessEqual(len(by_name["very-long-plain-repository-name"].display_name), 26)


if __name__ == "__main__":
    unittest.main()
