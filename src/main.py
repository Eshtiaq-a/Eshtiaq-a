"""Phase 2 orchestrator: collect public GitHub data, validate schemas, and render workspace SVG."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.config import (
    COMMITS_PATH,
    CONFIG_PATH,
    PROFILE_DATA_PATH,
    REPOSITORIES_PATH,
    WORKSPACE_SVG_PATH,
    atomic_write_text,
    load_profile_config,
)
from src.credits_builder import build_commits_payload, write_commits_json
from src.github_client import GitHubClient
from src.repos_builder import build_repositories_payload, write_repositories_json
from src.stats_builder import build_profile_data_payload, write_profile_data_json
from src.svg_workspace import build_workspace_svg
from src.validators import (
    validate_commits_payload,
    validate_profile_data_payload,
    validate_repositories_payload,
    validate_svg_document,
)


def run_phase2_pipeline(
    config_path: Path = CONFIG_PATH,
    repositories_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    profile_data_path: Path = PROFILE_DATA_PATH,
    workspace_svg_path: Path = WORKSPACE_SVG_PATH,
    client: GitHubClient | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Fetch all public repos/branches/commits/stats, validate, and atomically persist outputs."""
    profile_cfg = load_profile_config(config_path)
    gh_client = client or GitHubClient()

    repos_payload = build_repositories_payload(gh_client, profile_cfg.username)
    commits_payload = build_commits_payload(
        gh_client,
        profile_cfg.username,
        repos_payload["repositories"],
    )
    profile_payload = build_profile_data_payload(
        gh_client,
        profile_cfg.username,
        repos_payload,
        commits_payload,
    )

    # Validate all generated artifacts in memory BEFORE writing anything to disk
    validate_repositories_payload(repos_payload)
    validate_commits_payload(commits_payload)
    validate_profile_data_payload(profile_payload)
    svg_text = build_workspace_svg(commits_payload, profile_cfg)
    validate_svg_document(svg_text)

    if not dry_run:
        write_repositories_json(repos_payload, repositories_path)
        write_commits_json(commits_payload, commits_path)
        write_profile_data_json(profile_payload, profile_data_path)
        atomic_write_text(workspace_svg_path, svg_text)

    return {
        "repositories": repos_payload,
        "commits": commits_payload,
        "profile_data": profile_payload,
        "svg_bytes": len(svg_text.encode("utf-8")),
        "requests_made": gh_client.requests_made,
        "rate_limit_remaining": gh_client.last_rate_limit_remaining,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect real public GitHub data and update workspace.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing files.")
    args = parser.parse_args()

    summary = run_phase2_pipeline(dry_run=args.dry_run)
    repos = summary["repositories"]
    commits = summary["commits"]
    print(
        f"Collected {repos['total_public_repositories']} repos, "
        f"{commits['branches_processed']} branches, "
        f"{commits['total_unique_commits']} unique commits, "
        f"SVG {summary['svg_bytes']} bytes "
        f"({summary['requests_made']} API requests)."
    )


if __name__ == "__main__":
    main()
