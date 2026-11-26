"""Collect and compute public profile, language, and repository statistics."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import PROFILE_DATA_PATH, atomic_write_json
from src.github_client import GitHubApiError, GitHubClient


def compute_calendar_streaks(days: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Compute (active_days, current_streak, longest_streak) from chronological contribution days."""
    if not days:
        return 0, 0, 0
    ordered = sorted(days, key=lambda d: str(d.get("date", "")))
    active_days = sum(1 for d in ordered if int(d.get("contributionCount", 0)) > 0)

    longest = 0
    running = 0
    for d in ordered:
        if int(d.get("contributionCount", 0)) > 0:
            running += 1
            if running > longest:
                longest = running
        else:
            running = 0

    # Allow today's final day to be 0 if yesterday ended an active streak
    current = 0
    idx = len(ordered) - 1
    if idx >= 0 and int(ordered[idx].get("contributionCount", 0)) == 0:
        idx -= 1
    while idx >= 0 and int(ordered[idx].get("contributionCount", 0)) > 0:
        current += 1
        idx -= 1

    return active_days, current, longest


def compute_github_uptime_months(created_at: str, now: datetime | None = None) -> int:
    """Calculate elapsed whole months on GitHub from profile creation timestamp."""
    if not created_at:
        return 0
    ref_now = now or datetime.now(timezone.utc)
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    months = (ref_now.year - created.year) * 12 + (ref_now.month - created.month)
    if ref_now.day < created.day:
        months -= 1
    return max(0, months)


def build_profile_data_payload(
    client: GitHubClient,
    username: str,
    repositories_payload: dict[str, Any],
    commits_payload: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Assemble `data/profile_data.json` distinguishing sourced vs. calculated values."""
    user = client.get_user_profile(username)
    repos: list[dict[str, Any]] = repositories_payload.get("repositories", [])
    commits: list[dict[str, Any]] = commits_payload.get("commits", [])

    # Aggregate language bytes strictly across non-fork owned public repositories
    lang_bytes: dict[str, int] = {}
    for repo in repos:
        if repo.get("is_fork"):
            continue
        for lang, count in (repo.get("languages") or {}).items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + int(count)

    total_lang_bytes = sum(lang_bytes.values())
    ordered_langs = sorted(lang_bytes.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    language_breakdown = [
        {
            "language": lang,
            "bytes": byte_count,
            "percentage": round((byte_count / total_lang_bytes) * 100, 2) if total_lang_bytes else 0.0,
        }
        for lang, byte_count in ordered_langs
    ]

    # Optional GraphQL contribution calendar (requires GITHUB_TOKEN; never fabricated locally)
    warnings: list[dict[str, Any]] = []
    contribution_stats: dict[str, Any]
    if client.has_token:
        try:
            cal = client.get_contribution_calendar(username)
        except GitHubApiError as exc:
            cal = None
            warnings.append(
                {
                    "stage": "graphql_contributions",
                    "status_code": exc.status_code,
                    "message": str(exc),
                }
            )
        if cal:
            all_days = [
                day
                for week in (cal.get("weeks") or [])
                for day in (week.get("contributionDays") or [])
            ]
            active_days, current_streak, best_streak = compute_calendar_streaks(all_days)
            contribution_stats = {
                "available": True,
                "source": "github_graphql_contributions_collection",
                "total_contributions": int(cal.get("totalContributions", 0)),
                "active_days": active_days,
                "current_streak_days": current_streak,
                "best_streak_days": best_streak,
            }
        else:
            contribution_stats = {
                "available": False,
                "source": "graphql_unavailable_or_failed",
                "total_contributions": None,
                "active_days": None,
                "current_streak_days": None,
                "best_streak_days": None,
            }
    else:
        contribution_stats = {
            "available": False,
            "source": "unauthenticated_rest_fallback_requires_github_token",
            "total_contributions": None,
            "active_days": None,
            "current_streak_days": None,
            "best_streak_days": None,
        }

    # Derived commit-date activity stats (transparently labelled as public-branch REST metrics)
    commit_dates = sorted({c["committed_at"][:10] for c in commits if c.get("committed_at")})

    timestamp = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    return {
        "schema_version": "1.0.0",
        "generated_at": timestamp,
        "username": username,
        "is_sample_data": False,
        "directly_sourced_profile": {
            "login": user.get("login"),
            "name": user.get("name"),
            "bio": user.get("bio"),
            "location": user.get("location"),
            "company": user.get("company"),
            "blog": user.get("blog") or None,
            "html_url": user.get("html_url"),
            "avatar_url": user.get("avatar_url"),
            "public_repos": int(user.get("public_repos") or 0),
            "public_gists": int(user.get("public_gists") or 0),
            "followers": int(user.get("followers") or 0),
            "following": int(user.get("following") or 0),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
        },
        "calculated_metrics": {
            "uptime_months": compute_github_uptime_months(str(user.get("created_at") or ""), now=now_dt),
            "total_stars": sum(int(r.get("stars", 0)) for r in repos),
            "total_forks": sum(int(r.get("forks", 0)) for r in repos),
            "owned_public_repositories": len(repos),
            "non_fork_repositories": sum(1 for r in repos if not r.get("is_fork")),
            "empty_repositories": sum(1 for r in repos if r.get("is_empty")),
            "archived_repositories": sum(1 for r in repos if r.get("archived")),
            "unique_public_commits_collected": len(commits),
            "public_commit_active_days": len(commit_dates),
            "repositories_processed_for_commits": commits_payload.get("repositories_processed", 0),
            "branches_processed_for_commits": commits_payload.get("branches_processed", 0),
            "total_language_bytes": total_lang_bytes,
            "languages": language_breakdown,
        },
        "contribution_stats": contribution_stats,
        "collection_warnings": warnings,
    }


def write_profile_data_json(
    payload: dict[str, Any],
    output_path: Path = PROFILE_DATA_PATH,
) -> Path:
    """Persist validated profile stats atomically."""
    return atomic_write_json(output_path, payload)
