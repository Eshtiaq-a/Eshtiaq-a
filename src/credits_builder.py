"""Collect and deduplicate public commits across all accessible public branches."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import COMMITS_PATH, atomic_write_json
from src.github_client import GitHubApiError, GitHubClient

ACCESSIBLE_HISTORY_NOTE = (
    "Commits are collected across all accessible public branches (refs/heads/*) "
    "of public repositories owned by the profile owner. Commits in private "
    "repositories, force-pushed/rebased orphaned commits unreachable from current "
    "branch heads, or unmerged tag-only commits are inaccessible via the public "
    "REST branch-commit traversal."
)


def _parse_iso_timestamp(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _extract_commit_record(
    repo_id: int,
    repo_name: str,
    branch_name: str,
    raw_commit: dict[str, Any],
) -> dict[str, Any]:
    commit_obj = raw_commit.get("commit") or {}
    author_meta = commit_obj.get("author") or {}
    committer_meta = commit_obj.get("committer") or {}
    gh_author = raw_commit.get("author") or {}

    committed_at = str(
        committer_meta.get("date")
        or author_meta.get("date")
        or ""
    )
    author_name_raw = author_meta.get("name") or committer_meta.get("name") or gh_author.get("login")
    author_name = str(author_name_raw).strip() if author_name_raw else None
    author_login = str(gh_author["login"]) if isinstance(gh_author, dict) and gh_author.get("login") else None
    parents = raw_commit.get("parents") or []

    return {
        "repository_id": repo_id,
        "repository_name": repo_name,
        "commit_sha": str(raw_commit["sha"]),
        "commit_message": str(commit_obj.get("message") or ""),
        "author_name": author_name,
        "author_login": author_login,
        "committed_at": committed_at,
        "commit_url": str(raw_commit.get("html_url") or ""),
        "branch_names": [branch_name],
        "is_merge": len(parents) > 1,
    }


def build_commits_payload(
    client: GitHubClient,
    username: str,
    repositories: list[dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Collect, deduplicate by (repository_id, commit_sha), and sort all branch commits."""
    deduped: dict[tuple[int, str], dict[str, Any]] = {}
    warnings: list[dict[str, Any]] = []
    repos_processed = 0
    repos_skipped = 0
    branches_processed = 0
    branches_skipped = 0
    had_incomplete_error = False

    for repo in repositories:
        repo_id = int(repo["repository_id"])
        repo_name = str(repo["name"])

        if repo.get("is_empty"):
            repos_skipped += 1
            warnings.append(
                {
                    "level": "info",
                    "repository": repo_name,
                    "branch": None,
                    "reason": "empty_repository_size_zero",
                }
            )
            continue

        try:
            branches, branch_status = client.get_repository_branches(username, repo_name)
        except GitHubApiError as exc:
            repos_skipped += 1
            had_incomplete_error = True
            warnings.append(
                {
                    "level": "error",
                    "repository": repo_name,
                    "branch": None,
                    "status_code": exc.status_code,
                    "reason": f"branch_enumeration_failed: {exc}",
                }
            )
            continue

        if branch_status in (404, 409) or not branches:
            repos_skipped += 1
            warnings.append(
                {
                    "level": "info",
                    "repository": repo_name,
                    "branch": None,
                    "status_code": branch_status,
                    "reason": "no_accessible_branches_or_empty_repository",
                }
            )
            continue

        repos_processed += 1
        for branch in branches:
            branch_name = str(branch.get("name") or "")
            if not branch_name:
                branches_skipped += 1
                continue
            try:
                raw_commits, commit_status = client.get_branch_commits(
                    username, repo_name, branch_name
                )
            except GitHubApiError as exc:
                branches_skipped += 1
                had_incomplete_error = True
                warnings.append(
                    {
                        "level": "error",
                        "repository": repo_name,
                        "branch": branch_name,
                        "status_code": exc.status_code,
                        "reason": f"commit_pagination_failed: {exc}",
                    }
                )
                continue

            if commit_status in (404, 409):
                branches_skipped += 1
                warnings.append(
                    {
                        "level": "warning",
                        "repository": repo_name,
                        "branch": branch_name,
                        "status_code": commit_status,
                        "reason": "branch_empty_or_unavailable",
                    }
                )
                continue

            branches_processed += 1
            for raw_commit in raw_commits:
                sha = str(raw_commit.get("sha") or "")
                if not sha:
                    continue
                key = (repo_id, sha)
                if key in deduped:
                    existing = deduped[key]
                    if branch_name not in existing["branch_names"]:
                        existing["branch_names"].append(branch_name)
                        existing["branch_names"].sort()
                else:
                    deduped[key] = _extract_commit_record(
                        repo_id=repo_id,
                        repo_name=repo_name,
                        branch_name=branch_name,
                        raw_commit=raw_commit,
                    )

    ordered_commits = sorted(
        deduped.values(),
        key=lambda c: (
            _parse_iso_timestamp(c["committed_at"]),
            c["repository_name"].lower(),
            c["commit_sha"],
        ),
    )

    timestamp = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": "1.0.0",
        "generated_at": timestamp,
        "username": username,
        "scope": "all_accessible_public_branches",
        "is_sample_data": False,
        "total_unique_commits": len(ordered_commits),
        "repositories_processed": repos_processed,
        "repositories_skipped": repos_skipped,
        "branches_processed": branches_processed,
        "branches_skipped": branches_skipped,
        "complete_coverage": not had_incomplete_error,
        "collection_warnings": warnings,
        "accessible_history_note": ACCESSIBLE_HISTORY_NOTE,
        "commits": ordered_commits,
    }


def write_commits_json(
    payload: dict[str, Any],
    output_path: Path = COMMITS_PATH,
) -> Path:
    """Persist validated commits payload atomically."""
    return atomic_write_json(output_path, payload)
