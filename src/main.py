"""Profile data & SVG/README pipeline orchestrator for Eshtiaq Developer Universe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.config import (
    ASCII_PORTRAIT_PATH,
    COMMITS_PATH,
    CONFIG_PATH,
    DIVIDER_SVG_PATH,
    EXPLORER_SLICES_DIR,
    EXPLORER_SVG_PATH,
    NEOFETCH_SVG_PATH,
    PROFILE_DATA_PATH,
    README_PATH,
    REPOSITORIES_PATH,
    WORKSPACE_SVG_PATH,
    atomic_write_text,
    load_profile_config,
)
from src.credits_builder import build_commits_payload, write_commits_json
from src.explorer_builder import ExplorerSortOrder, build_explorer_model
from src.github_client import GitHubClient
from src.neofetch_builder import build_neofetch_model
from src.readme_builder import build_readme_markdown, write_readme_markdown
from src.repos_builder import build_repositories_payload, write_repositories_json
from src.stats_builder import build_profile_data_payload, write_profile_data_json
from src.svg_explorer import write_explorer_slices
from src.svg_neofetch import build_neofetch_svg
from src.svg_workspace import build_workspace_svg
from src.validators import (
    validate_commits_payload,
    validate_profile_data_payload,
    validate_repositories_payload,
    validate_svg_document,
)
from src.visualizations.project_explorer import (
    build_explorer_slice_svgs,
    build_explorer_svg,
    build_section_divider_svg,
)


def _render_and_validate_profile_assets(
    repos_payload: dict[str, Any],
    commits_payload: dict[str, Any],
    profile_payload: dict[str, Any],
    config_raw: dict[str, Any],
    profile_cfg: Any,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    sort_by: ExplorerSortOrder | None = None,
) -> dict[str, Any]:
    """Validate datasets and render all three SVG sections, slices, divider, and README in memory."""
    validate_repositories_payload(repos_payload)
    validate_commits_payload(commits_payload)
    validate_profile_data_payload(profile_payload)

    workspace_svg = build_workspace_svg(commits_payload, profile_cfg)
    validate_svg_document(workspace_svg)

    neofetch_model = build_neofetch_model(
        profile_data=profile_payload,
        repositories_data=repos_payload,
        commits_data=commits_payload,
        config_raw=config_raw,
        ascii_path=ascii_path,
    )
    neofetch_svg = build_neofetch_svg(neofetch_model)
    validate_svg_document(neofetch_svg)

    explorer_model = build_explorer_model(
        repositories_data=repos_payload,
        commits_data=commits_payload,
        config_raw=config_raw,
        sort_by=sort_by,
    )
    explorer_svg = build_explorer_svg(explorer_model)
    validate_svg_document(explorer_svg)
    explorer_slices = build_explorer_slice_svgs(explorer_model)

    divider_svg = build_section_divider_svg()
    validate_svg_document(divider_svg)

    readme_md = build_readme_markdown(
        profile_data=profile_payload,
        commits_data=commits_payload,
        explorer_model=explorer_model,
    )

    return {
        "workspace_svg": workspace_svg,
        "neofetch_svg": neofetch_svg,
        "explorer_svg": explorer_svg,
        "explorer_slices": explorer_slices,
        "divider_svg": divider_svg,
        "readme_md": readme_md,
        "explorer_model": explorer_model,
    }


def run_phase2_pipeline(
    config_path: Path = CONFIG_PATH,
    repositories_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    profile_data_path: Path = PROFILE_DATA_PATH,
    workspace_svg_path: Path = WORKSPACE_SVG_PATH,
    neofetch_svg_path: Path | None = None,
    explorer_svg_path: Path | None = None,
    explorer_slices_dir: Path | None = None,
    divider_svg_path: Path | None = None,
    readme_path: Path | None = None,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    client: GitHubClient | None = None,
    dry_run: bool = False,
    sort_by: ExplorerSortOrder | None = None,
) -> dict[str, Any]:
    """Fetch public repos/branches/commits/stats, validate, and atomically persist requested outputs."""
    profile_cfg = load_profile_config(config_path)
    config_raw = json.loads(config_path.read_text(encoding="utf-8"))
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

    rendered = _render_and_validate_profile_assets(
        repos_payload=repos_payload,
        commits_payload=commits_payload,
        profile_payload=profile_payload,
        config_raw=config_raw,
        profile_cfg=profile_cfg,
        ascii_path=ascii_path,
        sort_by=sort_by,
    )

    if not dry_run:
        write_repositories_json(repos_payload, repositories_path)
        write_commits_json(commits_payload, commits_path)
        write_profile_data_json(profile_payload, profile_data_path)
        atomic_write_text(workspace_svg_path, rendered["workspace_svg"])
        if neofetch_svg_path is not None:
            atomic_write_text(neofetch_svg_path, rendered["neofetch_svg"])
        if explorer_svg_path is not None:
            atomic_write_text(explorer_svg_path, rendered["explorer_svg"])
        if explorer_slices_dir is not None:
            write_explorer_slices(rendered["explorer_slices"], slices_dir=explorer_slices_dir)
        if divider_svg_path is not None:
            atomic_write_text(divider_svg_path, rendered["divider_svg"])
        if readme_path is not None:
            write_readme_markdown(rendered["readme_md"], readme_path)

    return {
        "repositories": repos_payload,
        "commits": commits_payload,
        "profile_data": profile_payload,
        "svg_bytes": len(rendered["workspace_svg"].encode("utf-8")),
        "neofetch_bytes": len(rendered["neofetch_svg"].encode("utf-8")),
        "explorer_bytes": len(rendered["explorer_svg"].encode("utf-8")),
        "requests_made": gh_client.requests_made,
        "rate_limit_remaining": gh_client.last_rate_limit_remaining,
    }


def run_full_profile_pipeline(
    config_path: Path = CONFIG_PATH,
    repositories_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    profile_data_path: Path = PROFILE_DATA_PATH,
    workspace_svg_path: Path = WORKSPACE_SVG_PATH,
    neofetch_svg_path: Path = NEOFETCH_SVG_PATH,
    explorer_svg_path: Path = EXPLORER_SVG_PATH,
    explorer_slices_dir: Path = EXPLORER_SLICES_DIR,
    divider_svg_path: Path = DIVIDER_SVG_PATH,
    readme_path: Path = README_PATH,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    client: GitHubClient | None = None,
    dry_run: bool = False,
    from_cache: bool = False,
    sort_by: ExplorerSortOrder | None = None,
) -> dict[str, Any]:
    """Run complete 3-section profile generation (live API fetch or cached JSON datasets)."""
    if not from_cache:
        return run_phase2_pipeline(
            config_path=config_path,
            repositories_path=repositories_path,
            commits_path=commits_path,
            profile_data_path=profile_data_path,
            workspace_svg_path=workspace_svg_path,
            neofetch_svg_path=neofetch_svg_path,
            explorer_svg_path=explorer_svg_path,
            explorer_slices_dir=explorer_slices_dir,
            divider_svg_path=divider_svg_path,
            readme_path=readme_path,
            ascii_path=ascii_path,
            client=client,
            dry_run=dry_run,
            sort_by=sort_by,
        )

    profile_cfg = load_profile_config(config_path)
    config_raw = json.loads(config_path.read_text(encoding="utf-8"))
    repos_payload = json.loads(repositories_path.read_text(encoding="utf-8"))
    commits_payload = json.loads(commits_path.read_text(encoding="utf-8"))
    profile_payload = json.loads(profile_data_path.read_text(encoding="utf-8"))

    rendered = _render_and_validate_profile_assets(
        repos_payload=repos_payload,
        commits_payload=commits_payload,
        profile_payload=profile_payload,
        config_raw=config_raw,
        profile_cfg=profile_cfg,
        ascii_path=ascii_path,
        sort_by=sort_by,
    )

    if not dry_run:
        atomic_write_text(workspace_svg_path, rendered["workspace_svg"])
        atomic_write_text(neofetch_svg_path, rendered["neofetch_svg"])
        atomic_write_text(explorer_svg_path, rendered["explorer_svg"])
        write_explorer_slices(rendered["explorer_slices"], slices_dir=explorer_slices_dir)
        atomic_write_text(divider_svg_path, rendered["divider_svg"])
        write_readme_markdown(rendered["readme_md"], readme_path)

    return {
        "repositories": repos_payload,
        "commits": commits_payload,
        "profile_data": profile_payload,
        "svg_bytes": len(rendered["workspace_svg"].encode("utf-8")),
        "neofetch_bytes": len(rendered["neofetch_svg"].encode("utf-8")),
        "explorer_bytes": len(rendered["explorer_svg"].encode("utf-8")),
        "requests_made": 0,
        "rate_limit_remaining": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect public GitHub data and generate all three profile sections + README.md."
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing files.")
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Re-render SVGs and README.md from existing data/*.json files without network requests.",
    )
    parser.add_argument(
        "--sort-by",
        choices=("updated", "stars", "name"),
        default=None,
        help="Override Section 03 Project Explorer sorting strategy.",
    )
    args = parser.parse_args()

    summary = run_full_profile_pipeline(
        dry_run=args.dry_run,
        from_cache=args.from_cache,
        sort_by=args.sort_by,
    )
    repos = summary["repositories"]
    commits = summary["commits"]
    print(
        f"Processed {repos['total_public_repositories']} repos, "
        f"{commits['branches_processed']} branches, "
        f"{commits['total_unique_commits']} commits | "
        f"workspace={summary['svg_bytes']}B, neofetch={summary['neofetch_bytes']}B, "
        f"explorer={summary['explorer_bytes']}B ({summary['requests_made']} API requests)."
    )


if __name__ == "__main__":
    main()
