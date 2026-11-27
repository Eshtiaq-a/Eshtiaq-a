"""Validation helpers for Phase 2 JSON schemas and GitHub-safe SVG assets."""

from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

from src.config import MAX_SVG_BYTES

FORBIDDEN_SVG_TAGS = ("script", "foreignObject")
FORBIDDEN_SVG_ATTR_RE = re.compile(
    r"<(?![!?])(?:[^<>\"']|\"[^\"]*\"|'[^']*')*?\s+(?:[a-z0-9_.-]+:)?on[a-z]+\s*=",
    re.IGNORECASE,
)
EXTERNAL_URL_RE = re.compile(r"https?://", re.IGNORECASE)
SAFE_ANCHOR_URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*/?$")
SAFE_GITHUB_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_github_repo_url(raw_url: Any, username: Any, repo_name: Any) -> str | None:
    """Return an authoritative GitHub HTTPS repo URL or safe fallback; None if unresolvable."""
    candidate = re.sub(r"\s+", " ", _CONTROL_CHAR_RE.sub(" ", str(raw_url or ""))).strip()
    if candidate and SAFE_ANCHOR_URL_RE.match(candidate):
        return candidate
    clean_user = re.sub(r"\s+", "", _CONTROL_CHAR_RE.sub("", str(username or ""))).strip()
    clean_repo = re.sub(r"\s+", "", _CONTROL_CHAR_RE.sub("", str(repo_name or ""))).strip()
    if (
        clean_user
        and clean_repo
        and SAFE_GITHUB_SLUG_RE.match(clean_user)
        and SAFE_GITHUB_SLUG_RE.match(clean_repo)
    ):
        return (
            f"https://github.com/"
            f"{urllib.parse.quote(clean_user, safe='-._')}/"
            f"{urllib.parse.quote(clean_repo, safe='-._')}"
        )
    return None


def make_repo_slug(name: Any, repo_id: Any, used_slugs: set[str] | None = None) -> str:
    """Create a deterministic, collision-free ASCII filename slug for a repository."""
    base = re.sub(r"[^a-z0-9._-]+", "-", str(name or "").lower()).strip("-") or f"repo-{repo_id}"
    slug = base
    if used_slugs is not None:
        if slug in used_slugs:
            slug = f"{base}-{repo_id}"
        counter = 2
        while slug in used_slugs:
            slug = f"{base}-{repo_id}-{counter}"
            counter += 1
        used_slugs.add(slug)
    return slug


def validate_commits_payload(payload: dict[str, Any]) -> None:
    """Verify either Phase 1 sample commit schema or Phase 2 canonical commit schema."""
    if not isinstance(payload, dict) or "commits" not in payload:
        raise ValueError("Commit payload must be a mapping with a 'commits' list.")
    commits = payload["commits"]
    if not isinstance(commits, list):
        raise ValueError("Commit payload 'commits' must be a list.")

    is_sample = bool(payload.get("is_sample_data", False))
    if is_sample and not commits:
        raise ValueError("Sample commit payload 'commits' must be non-empty.")

    if not is_sample:
        top_required = (
            "schema_version",
            "generated_at",
            "username",
            "total_unique_commits",
            "repositories_processed",
            "branches_processed",
            "collection_warnings",
            "is_sample_data",
        )
        for key in top_required:
            if key not in payload:
                raise ValueError(f"Commits payload missing top-level metadata key '{key}'.")
        if payload["total_unique_commits"] != len(commits):
            raise ValueError("Commits payload 'total_unique_commits' does not match len(commits).")

    seen: set[tuple[Any, str]] = set()
    sample_keys = ("repo_id", "repo_name", "sha", "message", "author", "commit_date")
    canonical_keys = (
        "repository_id",
        "repository_name",
        "commit_sha",
        "commit_message",
        "author_name",
        "author_login",
        "committed_at",
        "commit_url",
        "branch_names",
    )

    for idx, rec in enumerate(commits):
        if not isinstance(rec, dict):
            raise ValueError(f"Commit record {idx} must be a dict.")
        if "commit_sha" in rec:
            required_keys = canonical_keys
            repo_id_val = rec.get("repository_id")
            sha_val = rec.get("commit_sha")
        else:
            required_keys = sample_keys
            repo_id_val = rec.get("repo_id")
            sha_val = rec.get("sha")

        for key in required_keys:
            if key not in rec:
                raise ValueError(f"Commit record {idx} missing required key '{key}'.")

        dedup_key = (repo_id_val, str(sha_val))
        if dedup_key in seen:
            raise ValueError(f"Duplicate commit detected for key {dedup_key}.")
        seen.add(dedup_key)


def validate_repositories_payload(payload: dict[str, Any]) -> None:
    """Verify `data/repositories.json` schema and null-safe repository fields."""
    top_required = (
        "schema_version",
        "generated_at",
        "username",
        "is_sample_data",
        "total_public_repositories",
        "collection_warnings",
        "repositories",
    )
    for key in top_required:
        if key not in payload:
            raise ValueError(f"Repositories payload missing top-level key '{key}'.")
    repos = payload["repositories"]
    if not isinstance(repos, list):
        raise ValueError("Repositories payload 'repositories' must be a list.")
    if payload["total_public_repositories"] != len(repos):
        raise ValueError("total_public_repositories mismatch with len(repositories).")

    req_repo_keys = (
        "repository_id",
        "name",
        "description",
        "primary_language",
        "stars",
        "forks",
        "html_url",
        "homepage",
        "archived",
        "created_at",
        "updated_at",
    )
    for idx, repo in enumerate(repos):
        for key in req_repo_keys:
            if key not in repo:
                raise ValueError(f"Repository record {idx} missing key '{key}'.")


def validate_profile_data_payload(payload: dict[str, Any]) -> None:
    """Verify `data/profile_data.json` schema distinguishing sourced vs. calculated metrics."""
    for key in (
        "schema_version",
        "generated_at",
        "username",
        "is_sample_data",
        "directly_sourced_profile",
        "calculated_metrics",
        "contribution_stats",
    ):
        if key not in payload:
            raise ValueError(f"Profile data payload missing key '{key}'.")


def validate_contributions_payload(payload: dict[str, Any]) -> None:
    """Verify `data/contributions.json` calendar schema, date formatting, and totals."""
    required_top = (
        "schema_version",
        "generated_at",
        "username",
        "source",
        "graphql_available",
        "is_sample_data",
        "total_contributions",
        "active_days",
        "max_daily_contributions",
        "date_range",
        "weeks",
    )
    for key in required_top:
        if key not in payload:
            raise ValueError(f"Contributions payload missing top-level key '{key}'.")

    weeks = payload["weeks"]
    if not isinstance(weeks, list):
        raise ValueError("Contributions payload 'weeks' must be a list.")

    iso_date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    sum_counts = 0
    count_active = 0
    observed_max = 0
    seen_dates: set[str] = set()

    for w_idx, week in enumerate(weeks):
        if not isinstance(week, dict) or not isinstance(week.get("days"), list):
            raise ValueError(f"Contribution week {w_idx} must be a dict with 'days' list.")
        for d_idx, day in enumerate(week["days"]):
            if not isinstance(day, dict):
                raise ValueError(f"Contribution day ({w_idx},{d_idx}) must be a dict.")
            date_str = str(day.get("date") or "")
            if not iso_date_re.match(date_str):
                raise ValueError(f"Invalid contribution date format: {date_str!r}.")
            if date_str in seen_dates:
                raise ValueError(f"Duplicate contribution date detected: {date_str!r}.")
            seen_dates.add(date_str)
            cnt = int(day.get("count", -1))
            lvl = int(day.get("level", -1))
            if cnt < 0:
                raise ValueError(f"Negative contribution count on {date_str}: {cnt}.")
            if lvl not in (0, 1, 2, 3, 4):
                raise ValueError(f"Invalid contribution intensity level on {date_str}: {lvl}.")
            sum_counts += cnt
            if cnt > 0:
                count_active += 1
            if cnt > observed_max:
                observed_max = cnt

    if int(payload["total_contributions"]) != sum_counts:
        raise ValueError(
            f"total_contributions ({payload['total_contributions']}) != sum of daily counts ({sum_counts})."
        )
    if int(payload["active_days"]) != count_active:
        raise ValueError(
            f"active_days ({payload['active_days']}) != active days count ({count_active})."
        )
    if int(payload["max_daily_contributions"]) != observed_max:
        raise ValueError(
            f"max_daily_contributions ({payload['max_daily_contributions']}) != max ({observed_max})."
        )


def validate_svg_document(svg_text: str, max_bytes: int = MAX_SVG_BYTES) -> ET.Element:
    """Parse SVG XML and verify GitHub Camo safety, size budget, and animation structure."""
    encoded_len = len(svg_text.encode("utf-8"))
    if encoded_len > max_bytes:
        raise ValueError(f"SVG exceeds size budget: {encoded_len} > {max_bytes} bytes.")

    if FORBIDDEN_SVG_ATTR_RE.search(svg_text):
        raise ValueError("Forbidden inline event attribute pattern detected in SVG.")

    root = ET.fromstring(svg_text)
    if not root.tag.endswith("svg"):
        raise ValueError(f"Root XML tag must be <svg>, got {root.tag!r}.")

    forbidden_lower = {tag.lower() for tag in FORBIDDEN_SVG_TAGS}
    for elem in root.iter():
        local_name = elem.tag.rsplit("}", 1)[-1]
        if local_name.lower() in forbidden_lower:
            raise ValueError(f"Forbidden SVG tag detected: <{local_name}>.")
        for attr_name, attr_val in elem.attrib.items():
            attr_local = attr_name.rsplit("}", 1)[-1].lower()
            if attr_local.startswith("on"):
                raise ValueError(f"Forbidden event attribute detected: {attr_name!r}.")
            if attr_local.endswith("href"):
                if local_name == "a":
                    if not SAFE_ANCHOR_URL_RE.match(attr_val.strip()):
                        raise ValueError(f"Unsafe SVG anchor href detected: {attr_val!r}.")
                elif EXTERNAL_URL_RE.search(attr_val):
                    raise ValueError(f"External href not allowed in self-contained SVG: {attr_val!r}.")

    return root
