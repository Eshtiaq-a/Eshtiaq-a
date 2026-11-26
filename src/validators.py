"""Validation helpers for Phase 2 JSON schemas and GitHub-safe SVG assets."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from src.config import MAX_SVG_BYTES

FORBIDDEN_SVG_TAGS = ("script", "foreignObject")
FORBIDDEN_SVG_ATTR_RE = re.compile(r"\bon[a-z]+\s*=", re.IGNORECASE)
EXTERNAL_URL_RE = re.compile(r"https?://", re.IGNORECASE)


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


def validate_svg_document(svg_text: str, max_bytes: int = MAX_SVG_BYTES) -> ET.Element:
    """Parse SVG XML and verify GitHub Camo safety, size budget, and animation structure."""
    encoded_len = len(svg_text.encode("utf-8"))
    if encoded_len > max_bytes:
        raise ValueError(f"SVG exceeds size budget: {encoded_len} > {max_bytes} bytes.")

    root = ET.fromstring(svg_text)
    if not root.tag.endswith("svg"):
        raise ValueError(f"Root XML tag must be <svg>, got {root.tag!r}.")

    for elem in root.iter():
        local_name = elem.tag.rsplit("}", 1)[-1]
        if local_name in FORBIDDEN_SVG_TAGS:
            raise ValueError(f"Forbidden SVG tag detected: <{local_name}>.")
        for attr_name, attr_val in elem.attrib.items():
            if attr_name.lower().startswith("on"):
                raise ValueError(f"Forbidden event attribute detected: {attr_name!r}.")
            if attr_name.lower().endswith("href") and EXTERNAL_URL_RE.search(attr_val):
                raise ValueError(f"External href not allowed in self-contained SVG: {attr_val!r}.")

    if FORBIDDEN_SVG_ATTR_RE.search(svg_text):
        raise ValueError("Forbidden inline event attribute pattern detected in SVG.")
    return root
