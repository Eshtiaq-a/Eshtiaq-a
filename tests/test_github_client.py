"""Unit tests for src/github_client.py."""

from __future__ import annotations

import io
import json
import socket
import unittest
import urllib.error
from email.message import Message
from typing import Any

from src.github_client import GitHubApiError, GitHubClient, parse_next_link


class _FakeHttpResponse:
    def __init__(self, status: int, body: Any, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self._raw = json.dumps(body).encode("utf-8") if body is not None else b""
        msg = Message()
        for k, v in (headers or {}).items():
            msg[k] = v
        self.headers = msg

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> _FakeHttpResponse:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


def _http_error(url: str, code: int, headers: dict[str, str] | None = None) -> urllib.error.HTTPError:
    msg = Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    return urllib.error.HTTPError(url, code, f"HTTP {code}", msg, io.BytesIO(b"{}"))


class GitHubClientTests(unittest.TestCase):
    """Test REST pagination, retries, rate limits, and non-retryable client errors."""

    def test_parse_next_link(self) -> None:
        header = (
            '<https://api.github.com/users/Eshtiaq-a/repos?page=2>; rel="next", '
            '<https://api.github.com/users/Eshtiaq-a/repos?page=5>; rel="last"'
        )
        self.assertEqual(
            parse_next_link(header),
            "https://api.github.com/users/Eshtiaq-a/repos?page=2",
        )
        self.assertIsNone(parse_next_link(None))

    def test_successful_request_and_pagination(self) -> None:
        calls: list[str] = []

        def fake_opener(req: Any, _timeout: int) -> _FakeHttpResponse:
            calls.append(req.full_url)
            if "page=2" in req.full_url:
                return _FakeHttpResponse(200, [{"id": 2}], {"X-RateLimit-Remaining": "4998"})
            return _FakeHttpResponse(
                200,
                [{"id": 1}],
                {
                    "Link": '<https://api.github.com/items?page=2>; rel="next"',
                    "X-RateLimit-Remaining": "4999",
                },
            )

        client = GitHubClient(token="secret-test-token", opener=fake_opener, sleep_fn=lambda _: None)
        items, status = client.get_paginated("/items")
        self.assertEqual(status, 200)
        self.assertEqual(items, [{"id": 1}, {"id": 2}])
        self.assertEqual(len(calls), 2)
        self.assertEqual(client.last_rate_limit_remaining, 4998)

    def test_404_not_retried_unless_allowed(self) -> None:
        attempts = 0

        def fake_opener(req: Any, _timeout: int) -> Any:
            nonlocal attempts
            attempts += 1
            raise _http_error(req.full_url, 404)

        client = GitHubClient(token="", opener=fake_opener, max_retries=3, sleep_fn=lambda _: None)
        with self.assertRaises(GitHubApiError) as ctx:
            client.request_json("https://api.github.com/repos/x/y")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(attempts, 1)

    def test_409_empty_repo_handled_gracefully(self) -> None:
        attempts = 0

        def fake_opener(req: Any, _timeout: int) -> Any:
            nonlocal attempts
            attempts += 1
            raise _http_error(req.full_url, 409)

        client = GitHubClient(token="", opener=fake_opener, max_retries=3, sleep_fn=lambda _: None)
        commits, status = client.get_branch_commits("Eshtiaq-a", "Eshtiaq-a", "main")
        self.assertEqual(status, 409)
        self.assertEqual(commits, [])
        self.assertEqual(attempts, 1)

    def test_403_rate_limit_and_429_retries_with_backoff(self) -> None:
        sleeps: list[float] = []
        attempts = 0

        def fake_opener(req: Any, _timeout: int) -> Any:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise _http_error(req.full_url, 403, {"X-RateLimit-Remaining": "0", "Retry-After": "2"})
            if attempts == 2:
                raise _http_error(req.full_url, 429, {"Retry-After": "3"})
            return _FakeHttpResponse(200, {"login": "Eshtiaq-a"})

        client = GitHubClient(
            token="",
            opener=fake_opener,
            max_retries=3,
            sleep_fn=sleeps.append,
        )
        profile = client.get_user_profile("Eshtiaq-a")
        self.assertEqual(profile["login"], "Eshtiaq-a")
        self.assertEqual(sleeps, [2.0, 3.0])

    def test_5xx_and_network_timeout_retry_then_raise(self) -> None:
        sleeps: list[float] = []
        attempts = 0

        def fake_opener(req: Any, _timeout: int) -> Any:
            nonlocal attempts
            attempts += 1
            if attempts <= 2:
                raise _http_error(req.full_url, 502)
            raise socket.timeout("timed out")

        client = GitHubClient(
            token="",
            opener=fake_opener,
            max_retries=3,
            backoff_base_sec=0.5,
            sleep_fn=sleeps.append,
        )
        with self.assertRaises(GitHubApiError) as ctx:
            client.request_json("https://api.github.com/users/Eshtiaq-a")
        self.assertTrue(ctx.exception.retryable)
        self.assertEqual(attempts, 4)
        self.assertEqual(sleeps, [0.5, 1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
