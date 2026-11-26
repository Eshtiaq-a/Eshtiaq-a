"""Standard-library GitHub REST and GraphQL API client with pagination and retries."""

from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from src.config import (
    DEFAULT_HTTP_TIMEOUT_SEC,
    DEFAULT_MAX_RETRIES,
    GITHUB_API_BASE,
    GITHUB_GRAPHQL_URL,
)

NEXT_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="next"')
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class GitHubApiError(RuntimeError):
    """Structured error raised when a GitHub API request fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


@dataclass(frozen=True)
class ApiResponse:
    """Parsed HTTP response returned by GitHubClient."""

    status_code: int
    data: Any
    headers: dict[str, str]


def parse_next_link(link_header: str | None) -> str | None:
    """Extract the `rel="next"` pagination URL from a GitHub `Link` header."""
    if not link_header:
        return None
    match = NEXT_LINK_RE.search(link_header)
    return match.group(1) if match else None


class GitHubClient:
    """Zero-dependency GitHub API client supporting unauthenticated and token auth."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str = GITHUB_API_BASE,
        graphql_url: str = GITHUB_GRAPHQL_URL,
        timeout_sec: int = DEFAULT_HTTP_TIMEOUT_SEC,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base_sec: float = 1.0,
        sleep_fn: Callable[[float], None] = time.sleep,
        opener: Callable[[urllib.request.Request, int], Any] | None = None,
    ) -> None:
        self._token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.graphql_url = graphql_url
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.backoff_base_sec = backoff_base_sec
        self._sleep = sleep_fn
        self._opener = opener or (
            lambda req, timeout: urllib.request.urlopen(req, timeout=timeout)
        )
        self.requests_made = 0
        self.last_rate_limit_remaining: int | None = None

    @property
    def has_token(self) -> bool:
        """Return True if an authentication token is configured without exposing it."""
        return bool(self._token and self._token.strip())

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Eshtiaq-Developer-Universe/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.has_token:
            headers["Authorization"] = f"Bearer {self._token.strip()}"
        if extra:
            headers.update(extra)
        return headers

    def _update_rate_limit(self, headers: dict[str, str]) -> None:
        rem = headers.get("x-ratelimit-remaining")
        if rem is not None and rem.isdigit():
            self.last_rate_limit_remaining = int(rem)

    def _compute_retry_delay(
        self,
        attempt: int,
        headers: dict[str, str],
        is_rate_limit: bool,
    ) -> float:
        retry_after = headers.get("retry-after")
        if retry_after and retry_after.isdigit():
            return float(min(int(retry_after), 60))
        if is_rate_limit:
            reset_epoch = headers.get("x-ratelimit-reset")
            if reset_epoch and reset_epoch.isdigit():
                wait_sec = max(1, int(reset_epoch) - int(time.time()))
                if wait_sec <= 60:
                    return float(wait_sec)
        return float(self.backoff_base_sec * (2**attempt))

    def request_json(
        self,
        url: str,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        allow_statuses: frozenset[int] = frozenset(),
    ) -> ApiResponse:
        """Execute a JSON HTTP request with bounded retry/backoff and safe error handling."""
        resolved_url = url if url.startswith("http") else f"{self.base_url}{url}"
        payload_bytes = json.dumps(body).encode("utf-8") if body is not None else None
        extra_headers = {"Content-Type": "application/json"} if body is not None else None

        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(
                url=resolved_url,
                data=payload_bytes,
                headers=self._build_headers(extra_headers),
                method=method,
            )
            try:
                self.requests_made += 1
                with self._opener(req, self.timeout_sec) as resp:
                    raw_headers = {k.lower(): v for k, v in resp.headers.items()}
                    self._update_rate_limit(raw_headers)
                    text = resp.read().decode("utf-8")
                    parsed = json.loads(text) if text.strip() else None
                    return ApiResponse(
                        status_code=int(resp.status),
                        data=parsed,
                        headers=raw_headers,
                    )
            except urllib.error.HTTPError as exc:
                err_headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
                self._update_rate_limit(err_headers)
                status = int(exc.code)
                exc.close()
                if status in allow_statuses:
                    return ApiResponse(status_code=status, data=None, headers=err_headers)

                is_rate_limit_403 = status == 403 and (
                    err_headers.get("x-ratelimit-remaining") == "0"
                    or "retry-after" in err_headers
                )
                should_retry = (
                    status in RETRYABLE_STATUS_CODES or is_rate_limit_403
                ) and attempt < self.max_retries

                if should_retry:
                    delay = self._compute_retry_delay(attempt, err_headers, is_rate_limit_403 or status == 429)
                    self._sleep(delay)
                    continue

                raise GitHubApiError(
                    f"GitHub API request failed with HTTP {status} for {url}",
                    status_code=status,
                    retryable=status in RETRYABLE_STATUS_CODES or is_rate_limit_403,
                ) from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
                if attempt < self.max_retries:
                    delay = float(self.backoff_base_sec * (2**attempt))
                    self._sleep(delay)
                    continue
                raise GitHubApiError(
                    f"Network failure while requesting {url}: {type(exc).__name__}",
                    status_code=None,
                    retryable=True,
                ) from exc

        raise GitHubApiError(f"Exhausted retries for {url}", retryable=True)

    def get_paginated(
        self,
        path_or_url: str,
        allow_statuses: frozenset[int] = frozenset(),
    ) -> tuple[list[Any], int]:
        """Collect all pages for a GitHub REST list endpoint via Link pagination."""
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}{path_or_url}"
        items: list[Any] = []
        last_status = 200
        while url:
            resp = self.request_json(url, allow_statuses=allow_statuses)
            last_status = resp.status_code
            if resp.status_code in allow_statuses:
                return items, resp.status_code
            if isinstance(resp.data, list):
                items.extend(resp.data)
            url = parse_next_link(resp.headers.get("link")) or ""
        return items, last_status

    def get_user_profile(self, username: str) -> dict[str, Any]:
        """Fetch public user profile metadata."""
        encoded_user = urllib.parse.quote(username, safe="")
        resp = self.request_json(f"{self.base_url}/users/{encoded_user}")
        if not isinstance(resp.data, dict):
            raise GitHubApiError("Unexpected user profile payload shape from GitHub API.")
        return resp.data

    def get_public_repositories(self, username: str) -> list[dict[str, Any]]:
        """Discover all public repositories owned by `username` across all pages."""
        encoded_user = urllib.parse.quote(username, safe="")
        repos, _ = self.get_paginated(
            f"/users/{encoded_user}/repos?type=owner&per_page=100&sort=updated"
        )
        return [
            repo
            for repo in repos
            if isinstance(repo, dict)
            and not repo.get("private", False)
            and str(repo.get("owner", {}).get("login", "")).lower() == username.lower()
        ]

    def get_repository_branches(self, owner: str, repo: str) -> tuple[list[dict[str, Any]], int]:
        """Fetch all accessible public branches in a repository."""
        enc_owner = urllib.parse.quote(owner, safe="")
        enc_repo = urllib.parse.quote(repo, safe="")
        return self.get_paginated(
            f"/repos/{enc_owner}/{enc_repo}/branches?per_page=100",
            allow_statuses=frozenset({404, 409}),
        )

    def get_branch_commits(
        self,
        owner: str,
        repo: str,
        branch_name: str,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch all paginated commits reachable from `branch_name`."""
        enc_owner = urllib.parse.quote(owner, safe="")
        enc_repo = urllib.parse.quote(repo, safe="")
        enc_branch = urllib.parse.quote(branch_name, safe="")
        return self.get_paginated(
            f"/repos/{enc_owner}/{enc_repo}/commits?sha={enc_branch}&per_page=100",
            allow_statuses=frozenset({404, 409}),
        )

    def get_repository_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Fetch language byte counts for a single repository."""
        enc_owner = urllib.parse.quote(owner, safe="")
        enc_repo = urllib.parse.quote(repo, safe="")
        resp = self.request_json(
            f"{self.base_url}/repos/{enc_owner}/{enc_repo}/languages",
            allow_statuses=frozenset({404, 409}),
        )
        if isinstance(resp.data, dict):
            return {str(k): int(v) for k, v in resp.data.items() if isinstance(v, (int, float))}
        return {}

    def get_contribution_calendar(self, username: str) -> dict[str, Any] | None:
        """Query GitHub GraphQL contributionsCollection when GITHUB_TOKEN is available."""
        if not self.has_token:
            return None
        query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    contributionCount
                    date
                  }
                }
              }
            }
          }
        }
        """
        resp = self.request_json(
            self.graphql_url,
            method="POST",
            body={"query": query, "variables": {"login": username}},
        )
        if not isinstance(resp.data, dict) or resp.data.get("errors"):
            return None
        user_node = (resp.data.get("data") or {}).get("user")
        if not user_node:
            return None
        return (user_node.get("contributionsCollection") or {}).get("contributionCalendar")
