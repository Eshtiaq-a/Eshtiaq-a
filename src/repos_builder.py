"""Discover and normalize public GitHub repositories owned by the target user."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import REPOSITORIES_PATH, atomic_write_json
from src.github_client import GitHubApiError, GitHubClient


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_repository(
    raw_repo: dict[str, Any],
    languages: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Convert raw GitHub REST repository payload into canonical schema."""
    size_kb = int(raw_repo.get("size") or 0)
    return {
        "repository_id": int(raw_repo["id"]),
        "name": str(raw_repo["name"]),
        "full_name": str(raw_repo["full_name"]),
        "description": _normalize_optional_str(raw_repo.get("description")),
        "primary_language": _normalize_optional_str(raw_repo.get("language")),
        "languages": dict(sorted((languages or {}).items(), key=lambda kv: (-kv[1], kv[0].lower()))),
        "stars": int(raw_repo.get("stargazers_count") or 0),
        "forks": int(raw_repo.get("forks_count") or 0),
        "html_url": str(raw_repo["html_url"]),
        "homepage": _normalize_optional_str(raw_repo.get("homepage")),
        "archived": bool(raw_repo.get("archived", False)),
        "is_fork": bool(raw_repo.get("fork", False)),
        "is_empty": size_kb == 0,
        "size_kb": size_kb,
        "default_branch": _normalize_optional_str(raw_repo.get("default_branch")),
        "topics": [str(t) for t in (raw_repo.get("topics") or [])],
        "created_at": str(raw_repo.get("created_at") or ""),
        "updated_at": str(raw_repo.get("updated_at") or ""),
        "pushed_at": _normalize_optional_str(raw_repo.get("pushed_at")),
    }


def sort_repositories(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministically sort repositories (non-archived, stars desc, pushed_at desc, name asc)."""
    return sorted(
        repos,
        key=lambda r: (
            bool(r.get("archived", False)),
            bool(r.get("is_empty", False)),
            -int(r.get("stars", 0)),
            -(datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")).timestamp() if r.get("pushed_at") else 0.0),
            str(r.get("name", "")).lower(),
            int(r.get("repository_id", 0)),
        ),
    )


def build_repositories_payload(
    client: GitHubClient,
    username: str,
    fetch_languages: bool = True,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Fetch, normalize, and package all public repositories owned by `username`."""
    raw_repos = client.get_public_repositories(username)
    warnings: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []

    for raw in raw_repos:
        repo_name = str(raw["name"])
        languages: dict[str, int] = {}
        if fetch_languages and int(raw.get("size") or 0) > 0:
            try:
                languages = client.get_repository_languages(username, repo_name)
            except GitHubApiError as exc:
                warnings.append(
                    {
                        "stage": "repository_languages",
                        "repository": repo_name,
                        "status_code": exc.status_code,
                        "message": str(exc),
                    }
                )
        normalized.append(normalize_repository(raw, languages=languages))

    sorted_repos = sort_repositories(normalized)
    timestamp = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": "1.0.0",
        "generated_at": timestamp,
        "username": username,
        "is_sample_data": False,
        "total_public_repositories": len(sorted_repos),
        "non_empty_repositories": sum(1 for r in sorted_repos if not r["is_empty"]),
        "archived_repositories": sum(1 for r in sorted_repos if r["archived"]),
        "collection_warnings": warnings,
        "repositories": sorted_repos,
    }


def write_repositories_json(
    payload: dict[str, Any],
    output_path: Path = REPOSITORIES_PATH,
) -> Path:
    """Persist validated repository catalog atomically."""
    return atomic_write_json(output_path, payload)
