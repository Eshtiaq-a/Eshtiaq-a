"""Extract and format Phase 2 JSON data into Neofetch terminal + Repo Galaxy layout models."""

from __future__ import annotations

import json
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import (
    ASCII_PORTRAIT_PATH,
    COMMITS_PATH,
    CONFIG_PATH,
    PROFILE_DATA_PATH,
    REPOSITORIES_PATH,
)
from src.visualizations.repo_galaxy import RepoGalaxyModel, build_repo_galaxy_model

RIGHT_COL_CHARS = 69
STAT_HALF_CHARS = 33  # 33 + " | " (3) + 33 = 69 chars


@dataclass(frozen=True)
class DotRow:
    """Single key-value row padded with dot leaders."""

    label: str
    value: str
    dots: str


@dataclass(frozen=True)
class StatPairRow:
    """Two-column Neofetch stats row separated by a vertical pipe."""

    left: DotRow
    right: DotRow | None = None


@dataclass(frozen=True)
class NeofetchModel:
    """Presentation-ready data model for Section 02 Repo Galaxy + Neofetch terminal."""

    prompt_prefix: str
    header_title: str
    ascii_lines: tuple[str, ...]
    system_rows: tuple[DotRow, ...]
    about_lines: tuple[str, ...]
    contact_rows: tuple[DotRow, ...]
    stats_rows: tuple[StatPairRow, ...]
    galaxy: RepoGalaxyModel


def make_dot_row(label: str, value: str, total_width: int = RIGHT_COL_CHARS) -> DotRow:
    """Format `▪ {label}: {dots} {value}` aligned cleanly to `total_width`."""
    prefix_len = 2 + len(label) + 2  # "▪ " + label + ": "
    available_val_max = max(8, total_width - prefix_len - 4)
    val = value.strip()
    if len(val) > available_val_max:
        val = val[: available_val_max - 3].rstrip() + "..."
    dot_count = max(2, total_width - prefix_len - len(val) - 1)
    return DotRow(label=label, value=val, dots="." * dot_count)


def _format_uptime(months: Any) -> str | None:
    if not isinstance(months, int) or months < 0:
        return None
    if months < 1:
        return "< 1 month on GitHub"
    unit = "month" if months == 1 else "months"
    return f"{months} {unit} on GitHub"


def _normalize_location(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    return re.sub(r"\s*,\s*", ", ", text)


def _compute_languages_display(
    profile_data: dict[str, Any],
    repositories_data: dict[str, Any],
    max_languages: int = 4,
) -> str:
    """Compute detected programming languages from profile_data or repositories fallback."""
    langs_list = (profile_data.get("calculated_metrics") or {}).get("languages") or []
    ordered: list[str] = [
        str(entry["language"])
        for entry in langs_list
        if isinstance(entry, dict) and entry.get("language")
    ]

    if not ordered:
        totals: dict[str, int] = {}
        for repo in repositories_data.get("repositories") or []:
            if repo.get("is_fork"):
                continue
            repo_langs = repo.get("languages") or {}
            if repo_langs:
                for k, v in repo_langs.items():
                    totals[str(k)] = totals.get(str(k), 0) + int(v)
            elif repo.get("primary_language"):
                pl = str(repo["primary_language"])
                totals[pl] = totals.get(pl, 0) + max(1, int(repo.get("size_kb") or 1))
        ordered = [k for k, _ in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0].lower()))]

    if not ordered:
        return "None detected"
    return ", ".join(ordered[: max(1, max_languages)])


def _load_ascii_lines(ascii_path: Path = ASCII_PORTRAIT_PATH) -> tuple[str, ...]:
    if not ascii_path.exists():
        return ()
    raw_lines = ascii_path.read_text(encoding="utf-8").splitlines()
    return tuple(line.rstrip() for line in raw_lines if line.strip())


def _normalize_display_url(url: str | None, fallback: str) -> str:
    target = (url or "").strip() or fallback
    for prefix in ("https://", "http://"):
        if target.lower().startswith(prefix):
            target = target[len(prefix) :]
    return target.rstrip("/")


def build_neofetch_model(
    profile_data: dict[str, Any],
    repositories_data: dict[str, Any],
    commits_data: dict[str, Any],
    config_raw: dict[str, Any] | None = None,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
) -> NeofetchModel:
    """Assemble verified Phase 2 datasets into a Repo Galaxy + Neofetch terminal model."""
    cfg = config_raw or {}
    nf_cfg = cfg.get("neofetch") or {}
    sourced = profile_data.get("directly_sourced_profile") or {}
    calc = profile_data.get("calculated_metrics") or {}
    contrib = profile_data.get("contribution_stats") or {}

    username = str(
        sourced.get("login")
        or profile_data.get("username")
        or cfg.get("username")
        or "Eshtiaq-a"
    )
    display_name = str(sourced.get("name") or cfg.get("display_name") or username)
    prompt_prefix = f"{username.lower()}@github"

    # Counts directly from actual Phase 2 datasets
    repos_list = repositories_data.get("repositories")
    if isinstance(repos_list, list):
        repo_count = len(repos_list)
        total_stars = sum(int(r.get("stars") or 0) for r in repos_list)
        total_forks = sum(int(r.get("forks") or 0) for r in repos_list)
    else:
        repo_count = int(sourced.get("public_repos") or calc.get("owned_public_repositories") or 0)
        total_stars = int(calc.get("total_stars") or 0)
        total_forks = int(calc.get("total_forks") or 0)

    commits_list = commits_data.get("commits")
    unique_commits = (
        len(commits_list)
        if isinstance(commits_list, list)
        else int(commits_data.get("total_unique_commits") or 0)
    )
    branches_processed = int(
        commits_data.get("branches_processed")
        or calc.get("branches_processed_for_commits")
        or 0
    )

    max_langs = int(nf_cfg.get("max_languages", 4))
    languages_str = _compute_languages_display(profile_data, repositories_data, max_langs)

    # Developer identity & system info rows
    sys_rows: list[DotRow] = [
        make_dot_row("Name", display_name),
        make_dot_row("OS", "GitHub / Developer Universe"),
        make_dot_row("Host", username),
        make_dot_row("Kernel", "Profile Data Engine"),
    ]

    role_val = str(nf_cfg.get("role") or nf_cfg.get("identity") or "").strip()
    if role_val:
        sys_rows.append(make_dot_row("Role", role_val))

    focus_val = str(nf_cfg.get("focus") or "").strip()
    if focus_val:
        sys_rows.append(make_dot_row("Focus", focus_val))

    location_clean = _normalize_location(sourced.get("location") or cfg.get("location"))
    if location_clean:
        sys_rows.append(make_dot_row("Location", location_clean))

    uptime_str = _format_uptime(calc.get("uptime_months"))
    if uptime_str:
        sys_rows.append(make_dot_row("Uptime", uptime_str))

    sys_rows.append(make_dot_row("Packages", f"{repo_count} public repositories"))
    sys_rows.append(make_dot_row("Languages", languages_str))

    # About block (preserve full bio up to 3 lines cleanly without premature truncation)
    bio_raw = str(sourced.get("bio") or "").strip()
    if bio_raw:
        wrapped_bio = textwrap.wrap(bio_raw, width=RIGHT_COL_CHARS, max_lines=3, placeholder="...")
    else:
        wrapped_bio = ["Public GitHub Developer Profile & Open-Source Workspace"]

    # Contact block
    github_display = _normalize_display_url(
        sourced.get("html_url"),
        f"github.com/{username}",
    )
    contact_rows: list[DotRow] = [make_dot_row("GitHub", github_display)]
    linkedin_url = nf_cfg.get("linkedin")
    if linkedin_url:
        contact_rows.append(make_dot_row("LinkedIn", _normalize_display_url(str(linkedin_url), "")))
    blog_url = sourced.get("blog")
    if blog_url:
        contact_rows.append(make_dot_row("Web", _normalize_display_url(str(blog_url), "")))
    for extra in nf_cfg.get("contact_links") or []:
        if isinstance(extra, dict) and extra.get("label") and extra.get("value"):
            contact_rows.append(make_dot_row(str(extra["label"]), str(extra["value"])))

    # GitHub Stats block (never fabricate unavailable GraphQL contributions/streaks)
    followers = sourced.get("followers")
    following = sourced.get("following")
    followers_str = str(followers) if followers is not None else "N/A"
    following_str = str(following) if following is not None else "N/A"

    stats_rows: list[StatPairRow] = [
        StatPairRow(
            left=make_dot_row("Repos", str(repo_count), STAT_HALF_CHARS),
            right=make_dot_row("Stars", str(total_stars), STAT_HALF_CHARS),
        ),
        StatPairRow(
            left=make_dot_row("Commits", str(unique_commits), STAT_HALF_CHARS),
            right=make_dot_row("Branches", str(branches_processed), STAT_HALF_CHARS),
        ),
        StatPairRow(
            left=make_dot_row("Followers", followers_str, STAT_HALF_CHARS),
            right=make_dot_row("Following", following_str, STAT_HALF_CHARS),
        ),
    ]

    if contrib.get("available"):
        tot_contrib = contrib.get("total_contributions")
        active_days = contrib.get("active_days")
        cur_streak = contrib.get("current_streak_days")
        best_streak = contrib.get("best_streak_days")
        stats_rows.append(
            StatPairRow(
                left=make_dot_row(
                    "Contributions",
                    str(tot_contrib) if tot_contrib is not None else "N/A",
                    STAT_HALF_CHARS,
                ),
                right=make_dot_row(
                    "Active days",
                    str(active_days) if active_days is not None else "N/A",
                    STAT_HALF_CHARS,
                ),
            )
        )
        stats_rows.append(
            StatPairRow(
                left=make_dot_row(
                    "Streak",
                    f"{cur_streak}d" if cur_streak is not None else "N/A",
                    STAT_HALF_CHARS,
                ),
                right=make_dot_row(
                    "Best streak",
                    f"{best_streak}d" if best_streak is not None else "N/A",
                    STAT_HALF_CHARS,
                ),
            )
        )
    else:
        stats_rows.append(
            StatPairRow(
                left=make_dot_row("Forks", str(total_forks), STAT_HALF_CHARS),
                right=make_dot_row("Contributions", "unavailable", STAT_HALF_CHARS),
            )
        )

    galaxy_model = build_repo_galaxy_model(
        repositories_data=repositories_data,
        profile_data=profile_data,
        commits_data=commits_data,
    )

    return NeofetchModel(
        prompt_prefix=prompt_prefix,
        header_title=prompt_prefix,
        ascii_lines=_load_ascii_lines(ascii_path),
        system_rows=tuple(sys_rows),
        about_lines=tuple(wrapped_bio),
        contact_rows=tuple(contact_rows),
        stats_rows=tuple(stats_rows),
        galaxy=galaxy_model,
    )


def load_phase2_inputs(
    profile_path: Path = PROFILE_DATA_PATH,
    repos_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    config_path: Path = CONFIG_PATH,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load existing Phase 2 JSON files and config cleanly."""
    profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
    repos_data = json.loads(repos_path.read_text(encoding="utf-8"))
    commits_data = json.loads(commits_path.read_text(encoding="utf-8"))
    config_raw = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    return profile_data, repos_data, commits_data, config_raw
