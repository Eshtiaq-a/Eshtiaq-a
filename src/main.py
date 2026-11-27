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
    CONTRIBUTION_CITY_PAGES_HTML_PATH,
    CONTRIBUTION_CITY_SVG_PATH,
    CONTRIBUTIONS_PATH,
    DIVIDER_SVG_PATH,
    EXPLORER_SLICES_DIR,
    EXPLORER_SVG_PATH,
    NEOFETCH_SVG_PATH,
    PROFILE_DATA_PATH,
    README_PATH,
    REPO_GALAXY_PAGES_HTML_PATH,
    REPOS_CARDS_DIR,
    REPOSITORIES_PATH,
    WORKSPACE_SVG_PATH,
    atomic_write_text,
    load_profile_config,
)
from src.contributions_builder import (
    build_contributions_from_commits,
    build_contributions_payload,
    write_contributions_json,
)
from src.credits_builder import build_commits_payload, write_commits_json
from src.explorer_builder import ExplorerSortOrder, build_explorer_model
from src.github_client import GitHubClient
from src.neofetch_builder import build_neofetch_model
from src.readme_builder import build_readme_markdown, write_readme_markdown
from src.repos_builder import build_repositories_payload, write_repositories_json
from src.stats_builder import build_profile_data_payload, write_profile_data_json
from src.svg_city import write_standalone_city_page
from src.svg_explorer import write_explorer_slices
from src.svg_neofetch import build_neofetch_svg, write_repo_galaxy_cards, write_standalone_galaxy_page
from src.svg_workspace import build_workspace_svg
from src.validators import (
    validate_commits_payload,
    validate_contributions_payload,
    validate_profile_data_payload,
    validate_repositories_payload,
    validate_svg_document,
)
from src.visualizations.contribution_city import build_contribution_city_svg
from src.visualizations.project_explorer import (
    build_explorer_slice_svgs,
    build_explorer_svg,
    build_section_divider_svg,
)
from src.visualizations.repo_galaxy import build_repo_galaxy_cards
from src.workspace_scene import WorkspaceTheme


def _render_and_validate_profile_assets(
    repos_payload: dict[str, Any],
    commits_payload: dict[str, Any],
    profile_payload: dict[str, Any],
    config_raw: dict[str, Any],
    profile_cfg: Any,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    sort_by: ExplorerSortOrder | None = None,
    workspace_theme: WorkspaceTheme = "auto",
    contributions_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate datasets and render all four SVG sections, slices, cards, divider, and README in memory."""
    validate_repositories_payload(repos_payload)
    validate_commits_payload(commits_payload)
    validate_profile_data_payload(profile_payload)
    resolved_contributions = contributions_payload or build_contributions_from_commits(
        commits_payload=commits_payload,
        username=profile_cfg.username,
    )
    validate_contributions_payload(resolved_contributions)

    workspace_svg = build_workspace_svg(commits_payload, profile_cfg, theme=workspace_theme)
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

    repo_cards = build_repo_galaxy_cards(neofetch_model.galaxy)
    for _, card_svg in repo_cards:
        validate_svg_document(card_svg)

    city_svg = build_contribution_city_svg(resolved_contributions)
    validate_svg_document(city_svg)

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
        galaxy_model=neofetch_model.galaxy,
        contributions_data=resolved_contributions,
    )

    return {
        "workspace_svg": workspace_svg,
        "neofetch_svg": neofetch_svg,
        "neofetch_model": neofetch_model,
        "repo_cards": repo_cards,
        "city_svg": city_svg,
        "contributions": resolved_contributions,
        "explorer_svg": explorer_svg,
        "explorer_slices": explorer_slices,
        "divider_svg": divider_svg,
        "readme_md": readme_md,
        "explorer_model": explorer_model,
    }


def _resolve_repo_cards_dir(
    repo_cards_dir: Path | None,
    readme_path: Path | None,
) -> Path | None:
    if repo_cards_dir is not None:
        return repo_cards_dir
    if readme_path is None:
        return None
    if readme_path == README_PATH:
        return REPOS_CARDS_DIR
    return readme_path.parent / "assets" / "repos"


def _resolve_galaxy_pages_path(
    galaxy_pages_path: Path | None,
    readme_path: Path | None,
) -> Path | None:
    if galaxy_pages_path is not None:
        return galaxy_pages_path
    if readme_path == README_PATH:
        return REPO_GALAXY_PAGES_HTML_PATH
    return None


def _resolve_contributions_path(
    contributions_path: Path | None,
    repositories_path: Path,
) -> Path:
    if contributions_path is not None:
        return contributions_path
    if repositories_path == REPOSITORIES_PATH:
        return CONTRIBUTIONS_PATH
    return repositories_path.parent / "contributions.json"


def _resolve_city_svg_path(
    contribution_city_svg_path: Path | None,
    readme_path: Path | None,
) -> Path | None:
    if contribution_city_svg_path is not None:
        return contribution_city_svg_path
    if readme_path is None:
        return None
    if readme_path == README_PATH:
        return CONTRIBUTION_CITY_SVG_PATH
    return readme_path.parent / "assets" / "contribution_city.svg"


def _resolve_city_pages_path(
    city_pages_path: Path | None,
    readme_path: Path | None,
) -> Path | None:
    if city_pages_path is not None:
        return city_pages_path
    if readme_path == README_PATH:
        return CONTRIBUTION_CITY_PAGES_HTML_PATH
    return None


def run_phase2_pipeline(
    config_path: Path = CONFIG_PATH,
    repositories_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    profile_data_path: Path = PROFILE_DATA_PATH,
    contributions_path: Path | None = None,
    workspace_svg_path: Path = WORKSPACE_SVG_PATH,
    neofetch_svg_path: Path | None = None,
    repo_cards_dir: Path | None = None,
    galaxy_pages_path: Path | None = None,
    contribution_city_svg_path: Path | None = None,
    city_pages_path: Path | None = None,
    explorer_svg_path: Path | None = None,
    explorer_slices_dir: Path | None = None,
    divider_svg_path: Path | None = None,
    readme_path: Path | None = None,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    client: GitHubClient | None = None,
    dry_run: bool = False,
    sort_by: ExplorerSortOrder | None = None,
    workspace_theme: WorkspaceTheme = "auto",
) -> dict[str, Any]:
    """Fetch public repos/branches/commits/stats/contributions, validate, and atomically persist outputs."""
    profile_cfg = load_profile_config(config_path)
    config_raw = json.loads(config_path.read_text(encoding="utf-8"))
    gh_client = client or GitHubClient()

    effective_contributions_path = _resolve_contributions_path(contributions_path, repositories_path)

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
    contributions_payload = build_contributions_payload(
        gh_client,
        profile_cfg.username,
        commits_payload,
        existing_path=effective_contributions_path if effective_contributions_path.exists() else None,
    )

    rendered = _render_and_validate_profile_assets(
        repos_payload=repos_payload,
        commits_payload=commits_payload,
        profile_payload=profile_payload,
        config_raw=config_raw,
        profile_cfg=profile_cfg,
        ascii_path=ascii_path,
        sort_by=sort_by,
        workspace_theme=workspace_theme,
        contributions_payload=contributions_payload,
    )

    effective_cards_dir = _resolve_repo_cards_dir(repo_cards_dir, readme_path)
    effective_pages_path = _resolve_galaxy_pages_path(galaxy_pages_path, readme_path)
    effective_city_svg_path = _resolve_city_svg_path(contribution_city_svg_path, readme_path)
    effective_city_pages_path = _resolve_city_pages_path(city_pages_path, readme_path)

    if not dry_run:
        write_repositories_json(repos_payload, repositories_path)
        write_commits_json(commits_payload, commits_path)
        write_profile_data_json(profile_payload, profile_data_path)
        write_contributions_json(contributions_payload, effective_contributions_path)
        atomic_write_text(workspace_svg_path, rendered["workspace_svg"])
        if neofetch_svg_path is not None:
            atomic_write_text(neofetch_svg_path, rendered["neofetch_svg"])
        if effective_cards_dir is not None:
            write_repo_galaxy_cards(rendered["neofetch_model"].galaxy, cards_dir=effective_cards_dir)
        if effective_pages_path is not None:
            write_standalone_galaxy_page(
                rendered["neofetch_svg"],
                profile_cfg.username,
                output_path=effective_pages_path,
            )
        if effective_city_svg_path is not None:
            atomic_write_text(effective_city_svg_path, rendered["city_svg"])
        if effective_city_pages_path is not None:
            write_standalone_city_page(
                rendered["city_svg"],
                profile_cfg.username,
                output_path=effective_city_pages_path,
            )
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
        "contributions": contributions_payload,
        "svg_bytes": len(rendered["workspace_svg"].encode("utf-8")),
        "neofetch_bytes": len(rendered["neofetch_svg"].encode("utf-8")),
        "city_bytes": len(rendered["city_svg"].encode("utf-8")),
        "repo_cards_count": len(rendered["repo_cards"]),
        "explorer_bytes": len(rendered["explorer_svg"].encode("utf-8")),
        "requests_made": gh_client.requests_made,
        "rate_limit_remaining": gh_client.last_rate_limit_remaining,
    }


def run_full_profile_pipeline(
    config_path: Path = CONFIG_PATH,
    repositories_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    profile_data_path: Path = PROFILE_DATA_PATH,
    contributions_path: Path | None = None,
    workspace_svg_path: Path = WORKSPACE_SVG_PATH,
    neofetch_svg_path: Path = NEOFETCH_SVG_PATH,
    repo_cards_dir: Path | None = None,
    galaxy_pages_path: Path | None = None,
    contribution_city_svg_path: Path | None = None,
    city_pages_path: Path | None = None,
    explorer_svg_path: Path = EXPLORER_SVG_PATH,
    explorer_slices_dir: Path = EXPLORER_SLICES_DIR,
    divider_svg_path: Path = DIVIDER_SVG_PATH,
    readme_path: Path = README_PATH,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    client: GitHubClient | None = None,
    dry_run: bool = False,
    from_cache: bool = False,
    sort_by: ExplorerSortOrder | None = None,
    workspace_theme: WorkspaceTheme = "auto",
) -> dict[str, Any]:
    """Run complete 4-section profile generation (live API fetch or cached JSON datasets)."""
    if not from_cache:
        return run_phase2_pipeline(
            config_path=config_path,
            repositories_path=repositories_path,
            commits_path=commits_path,
            profile_data_path=profile_data_path,
            contributions_path=contributions_path,
            workspace_svg_path=workspace_svg_path,
            neofetch_svg_path=neofetch_svg_path,
            repo_cards_dir=repo_cards_dir,
            galaxy_pages_path=galaxy_pages_path,
            contribution_city_svg_path=contribution_city_svg_path,
            city_pages_path=city_pages_path,
            explorer_svg_path=explorer_svg_path,
            explorer_slices_dir=explorer_slices_dir,
            divider_svg_path=divider_svg_path,
            readme_path=readme_path,
            ascii_path=ascii_path,
            client=client,
            dry_run=dry_run,
            sort_by=sort_by,
            workspace_theme=workspace_theme,
        )

    profile_cfg = load_profile_config(config_path)
    config_raw = json.loads(config_path.read_text(encoding="utf-8"))
    repos_payload = json.loads(repositories_path.read_text(encoding="utf-8"))
    commits_payload = json.loads(commits_path.read_text(encoding="utf-8"))
    profile_payload = json.loads(profile_data_path.read_text(encoding="utf-8"))

    effective_contributions_path = _resolve_contributions_path(contributions_path, repositories_path)
    if effective_contributions_path.exists():
        contributions_payload = json.loads(effective_contributions_path.read_text(encoding="utf-8"))
    else:
        contributions_payload = build_contributions_from_commits(
            commits_payload=commits_payload,
            username=profile_cfg.username,
        )

    rendered = _render_and_validate_profile_assets(
        repos_payload=repos_payload,
        commits_payload=commits_payload,
        profile_payload=profile_payload,
        config_raw=config_raw,
        profile_cfg=profile_cfg,
        ascii_path=ascii_path,
        sort_by=sort_by,
        workspace_theme=workspace_theme,
        contributions_payload=contributions_payload,
    )

    effective_cards_dir = _resolve_repo_cards_dir(repo_cards_dir, readme_path)
    effective_pages_path = _resolve_galaxy_pages_path(galaxy_pages_path, readme_path)
    effective_city_svg_path = _resolve_city_svg_path(contribution_city_svg_path, readme_path)
    effective_city_pages_path = _resolve_city_pages_path(city_pages_path, readme_path)

    if not dry_run:
        if not effective_contributions_path.exists():
            write_contributions_json(contributions_payload, effective_contributions_path)
        atomic_write_text(workspace_svg_path, rendered["workspace_svg"])
        atomic_write_text(neofetch_svg_path, rendered["neofetch_svg"])
        if effective_cards_dir is not None:
            write_repo_galaxy_cards(rendered["neofetch_model"].galaxy, cards_dir=effective_cards_dir)
        if effective_pages_path is not None:
            write_standalone_galaxy_page(
                rendered["neofetch_svg"],
                profile_cfg.username,
                output_path=effective_pages_path,
            )
        if effective_city_svg_path is not None:
            atomic_write_text(effective_city_svg_path, rendered["city_svg"])
        if effective_city_pages_path is not None:
            write_standalone_city_page(
                rendered["city_svg"],
                profile_cfg.username,
                output_path=effective_city_pages_path,
            )
        atomic_write_text(explorer_svg_path, rendered["explorer_svg"])
        write_explorer_slices(rendered["explorer_slices"], slices_dir=explorer_slices_dir)
        atomic_write_text(divider_svg_path, rendered["divider_svg"])
        write_readme_markdown(rendered["readme_md"], readme_path)

    return {
        "repositories": repos_payload,
        "commits": commits_payload,
        "profile_data": profile_payload,
        "contributions": contributions_payload,
        "svg_bytes": len(rendered["workspace_svg"].encode("utf-8")),
        "neofetch_bytes": len(rendered["neofetch_svg"].encode("utf-8")),
        "city_bytes": len(rendered["city_svg"].encode("utf-8")),
        "repo_cards_count": len(rendered["repo_cards"]),
        "explorer_bytes": len(rendered["explorer_svg"].encode("utf-8")),
        "requests_made": 0,
        "rate_limit_remaining": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect public GitHub data and generate all four profile sections + README.md."
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
        help="Override Section 04 Project Explorer sorting strategy.",
    )
    parser.add_argument(
        "--theme",
        choices=("auto", "day", "night"),
        default="auto",
        help="Section 01 workspace lighting theme (auto = day 06:00-17:59, night 18:00-05:59 in configured timezone).",
    )
    args = parser.parse_args()

    summary = run_full_profile_pipeline(
        dry_run=args.dry_run,
        from_cache=args.from_cache,
        sort_by=args.sort_by,
        workspace_theme=args.theme,
    )
    repos = summary["repositories"]
    commits = summary["commits"]
    print(
        f"Processed {repos['total_public_repositories']} repos, "
        f"{commits['branches_processed']} branches, "
        f"{commits['total_unique_commits']} commits | "
        f"workspace={summary['svg_bytes']}B, neofetch={summary['neofetch_bytes']}B, "
        f"city={summary['city_bytes']}B, explorer={summary['explorer_bytes']}B ({summary['requests_made']} API requests)."
    )


if __name__ == "__main__":
    main()
