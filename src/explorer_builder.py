"""Data model, deduplication, deterministic sorting, and normalization for Section 03 Project Explorer."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from src.config import COMMITS_PATH, CONFIG_PATH, REPOSITORIES_PATH
from src.validators import make_repo_slug, sanitize_github_repo_url
from src.visualizations.repo_galaxy import get_language_color

ExplorerSortOrder = Literal["updated", "stars", "name"]

CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
SAFE_HTTP_URL_RE = re.compile(r"^https?://[^\s<>'\"()\[\]`]+$", re.IGNORECASE)

LANGUAGE_BADGE_MAP: dict[str, tuple[str, str, str, str]] = {
    # language_lower: (tag, bg_hex, border_hex, fg_hex)
    "python": ("PY", "#182e47", "#4b8bbe", "#f2cb62"),
    "typescript": ("TS", "#183052", "#3b82f6", "#7db8ff"),
    "javascript": ("JS", "#332d12", "#d9c242", "#f1e05a"),
    "html": ("HTML", "#391e1a", "#e3623a", "#ff8d6b"),
    "css": ("CSS", "#261d40", "#8b5cf6", "#b89bff"),
    "c": ("C", "#1b2840", "#7b9ec9", "#9ec4f0"),
    "c++": ("C+", "#361a29", "#f34b7d", "#ff7da4"),
    "java": ("JV", "#342214", "#b07219", "#e09a43"),
    "go": ("GO", "#112f3a", "#00add8", "#5cd8f5"),
    "rust": ("RS", "#332019", "#dea584", "#f4be9e"),
    "shell": ("SH", "#142e22", "#73b88d", "#87d4a3"),
    "powershell": ("PS", "#142a40", "#60a5fa", "#93c5fd"),
    "plpgsql": ("SQL", "#122b3d", "#38bdf8", "#7dd3fc"),
    "sql": ("SQL", "#122b3d", "#38bdf8", "#7dd3fc"),
}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", CONTROL_CHAR_RE.sub(" ", str(value or ""))).strip()


def _parse_iso_timestamp(value: Any) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _format_month_year(raw: Any) -> str:
    if not raw:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.strftime("%b %Y")
    except ValueError:
        return "Unknown"


def _truncate_clean(text: str, max_chars: int, ellipsis: str = "...") -> str:
    if len(text) <= max_chars:
        return text
    cutoff = max(1, max_chars - len(ellipsis))
    prefix = text[:cutoff]
    if " " in prefix:
        word_safe = prefix.rsplit(" ", 1)[0].rstrip(" ,;:-")
        if len(word_safe) >= cutoff // 2:
            return word_safe + ellipsis
    return prefix.rstrip() + ellipsis


def _truncate_repo_dir(name: str, max_chars: int) -> str:
    label = f"{name}/"
    if len(label) <= max_chars:
        return label
    keep = max(4, max_chars - 2)
    return f"{name[:keep].rstrip()}…/"


def _sanitize_homepage_url(raw_url: Any) -> str | None:
    candidate = _clean_text(raw_url)
    if candidate and SAFE_HTTP_URL_RE.match(candidate):
        return candidate
    return None


@dataclass(frozen=True)
class ExplorerRow:
    """Presentation-ready single repository entry for the terminal project explorer."""

    repository_id: int
    name: str
    display_name: str
    full_name: str
    html_url: str | None
    homepage: str | None
    dir_mode: str
    status_badge: str | None
    language_tag: str
    language_color: str
    badge_bg: str
    badge_border: str
    badge_fg: str
    primary_language: str
    languages: tuple[str, ...]
    extra_language_count: int
    description: str
    short_description: str
    compact_description_lines: tuple[str, ...]
    stars: int
    forks: int
    commit_count: int
    archived: bool
    is_empty: bool
    is_fork: bool
    updated_at: str
    updated_label: str
    row_slug: str = ""


@dataclass(frozen=True)
class ExplorerModel:
    """Complete dataset-backed Project Explorer model."""

    username: str
    sort_by: ExplorerSortOrder
    total_repositories: int
    active_repositories: int
    total_stars: int
    generated_at: str
    rows: tuple[ExplorerRow, ...]


def resolve_language_badge(language: str | None) -> tuple[str, str, str, str, str]:
    """Return `(tag, dot_color, badge_bg, badge_border, badge_fg)` with fallback."""
    clean = _clean_text(language)
    dot_color = get_language_color(clean or None)
    if not clean or clean.lower() == "unspecified":
        return ("DIR", "#6c768c", "#181d29", "#3c4559", "#8d97ad")
    preset = LANGUAGE_BADGE_MAP.get(clean.lower())
    if preset:
        tag, bg, border, fg = preset
        return (tag, dot_color, bg, border, fg)
    fallback_tag = re.sub(r"[^A-Za-z0-9+]", "", clean).upper()[:3] or "SRC"
    return (fallback_tag, dot_color, "#182238", "#3b5280", "#cdd7ec")


def sort_explorer_repositories(
    repos: list[dict[str, Any]],
    sort_by: ExplorerSortOrder = "updated",
) -> list[dict[str, Any]]:
    """Deterministically deduplicate and sort repositories by `updated`, `stars`, or `name`."""
    deduped: list[dict[str, Any]] = []
    seen_keys: set[tuple[Any, ...]] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        if repo.get("private") is True:
            continue
        repo_id = repo.get("repository_id") or repo.get("id")
        name = _clean_text(repo.get("name"))
        if not name:
            continue
        dedup_key = (
            ("id", int(repo_id))
            if repo_id is not None
            else ("name", name.lower(), _clean_text(repo.get("full_name")).lower())
        )
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        deduped.append(repo)

    def _activity_ts(r: dict[str, Any]) -> float:
        return max(
            _parse_iso_timestamp(r.get("updated_at")),
            _parse_iso_timestamp(r.get("pushed_at")),
        )

    if sort_by == "stars":
        return sorted(
            deduped,
            key=lambda r: (
                -max(0, int(r.get("stars") or 0)),
                -_activity_ts(r),
                _clean_text(r.get("name")).lower(),
                int(r.get("repository_id") or r.get("id") or 0),
            ),
        )
    if sort_by == "name":
        return sorted(
            deduped,
            key=lambda r: (
                _clean_text(r.get("name")).lower(),
                int(r.get("repository_id") or r.get("id") or 0),
            ),
        )
    # Default: recently updated first, deterministic tie-breakers
    return sorted(
        deduped,
        key=lambda r: (
            -_activity_ts(r),
            _clean_text(r.get("name")).lower(),
            int(r.get("repository_id") or r.get("id") or 0),
        ),
    )


def build_explorer_model(
    repositories_data: dict[str, Any],
    commits_data: dict[str, Any] | None = None,
    config_raw: dict[str, Any] | None = None,
    sort_by: ExplorerSortOrder | None = None,
) -> ExplorerModel:
    """Build deterministic Project Explorer rows strictly from Phase 2 dataset inputs."""
    cfg = config_raw or {}
    exp_cfg = cfg.get("explorer") or {}
    raw_sort = str(sort_by or exp_cfg.get("sort_by") or "updated").lower()
    resolved_sort: ExplorerSortOrder = raw_sort if raw_sort in {"updated", "stars", "name"} else "updated"  # type: ignore[assignment]

    username = _clean_text(
        repositories_data.get("username") or cfg.get("username") or "Eshtiaq-a"
    )
    generated_at = _clean_text(repositories_data.get("generated_at") or "")
    generated_date = generated_at[:10] if len(generated_at) >= 10 else "unknown"

    # Derive commit counts per repository strictly from collected commits
    commit_counts: dict[str, int] = {}
    for commit in (commits_data or {}).get("commits") or []:
        if isinstance(commit, dict):
            rname = _clean_text(commit.get("repository_name") or commit.get("repo_name"))
            if rname:
                commit_counts[rname] = commit_counts.get(rname, 0) + 1

    ordered = sort_explorer_repositories(
        list(repositories_data.get("repositories") or []),
        sort_by=resolved_sort,
    )

    rows: list[ExplorerRow] = []
    used_slugs: set[str] = set()
    for idx, repo in enumerate(ordered):
        repo_id = int(repo.get("repository_id") or repo.get("id") or (idx + 1))
        name = _clean_text(repo.get("name"))
        row_slug = make_repo_slug(name, repo_id, used_slugs)
        full_name = _clean_text(repo.get("full_name")) or f"{username}/{name}"
        html_url = sanitize_github_repo_url(repo.get("html_url"), username, name)
        homepage = _sanitize_homepage_url(repo.get("homepage"))

        archived = bool(repo.get("archived", False))
        is_empty = bool(repo.get("is_empty", False))
        is_fork = bool(repo.get("is_fork", False))

        if archived:
            dir_mode = "dr-x"
            status_badge: str | None = "ARCHIVED"
        elif is_empty:
            dir_mode = "d---"
            status_badge = "EMPTY"
        elif homepage:
            dir_mode = "drwx"
            status_badge = "LIVE"
        elif is_fork:
            dir_mode = "drwx"
            status_badge = "FORK"
        else:
            dir_mode = "drwx"
            status_badge = None

        if status_badge == "ARCHIVED":
            max_name_len = 17
        elif status_badge:
            max_name_len = 22
        else:
            max_name_len = 26
        display_name = _truncate_repo_dir(name, max_chars=max_name_len)

        raw_desc = _clean_text(repo.get("description"))
        description = raw_desc if raw_desc else "No description provided."
        short_description = _truncate_clean(description, max_chars=50)
        compact_lines = tuple(
            textwrap.wrap(
                description,
                width=58,
                max_lines=2,
                placeholder="...",
            )
            or [description]
        )

        # Primary + multi-language inspection (no fabricated percentages)
        lang_map = repo.get("languages") or {}
        ordered_langs: list[str] = []
        if isinstance(lang_map, dict):
            ordered_langs = [
                _clean_text(k)
                for k, _ in sorted(
                    lang_map.items(),
                    key=lambda kv: (-int(kv[1] or 0), str(kv[0]).lower()),
                )
                if _clean_text(k)
            ]

        primary_raw = _clean_text(repo.get("primary_language"))
        primary_language = primary_raw or (ordered_langs[0] if ordered_langs else "Unspecified")
        if primary_raw and primary_raw not in ordered_langs:
            ordered_langs.insert(0, primary_raw)
        elif not ordered_langs and primary_language != "Unspecified":
            ordered_langs = [primary_language]

        extra_langs = max(0, len(ordered_langs) - 1)
        tag, dot_col, badge_bg, badge_border, badge_fg = resolve_language_badge(
            None if primary_language == "Unspecified" else primary_language
        )

        stars = max(0, int(repo.get("stars") or 0))
        forks = max(0, int(repo.get("forks") or 0))
        updated_raw = _clean_text(repo.get("updated_at") or repo.get("pushed_at"))
        updated_label = _format_month_year(updated_raw)

        rows.append(
            ExplorerRow(
                repository_id=repo_id,
                name=name,
                display_name=display_name,
                full_name=full_name,
                html_url=html_url,
                homepage=homepage,
                dir_mode=dir_mode,
                status_badge=status_badge,
                language_tag=tag,
                language_color=dot_col,
                badge_bg=badge_bg,
                badge_border=badge_border,
                badge_fg=badge_fg,
                primary_language=primary_language,
                languages=tuple(ordered_langs),
                extra_language_count=extra_langs,
                description=description,
                short_description=short_description,
                compact_description_lines=compact_lines,
                stars=stars,
                forks=forks,
                commit_count=commit_counts.get(name, 0),
                archived=archived,
                is_empty=is_empty,
                is_fork=is_fork,
                updated_at=updated_raw,
                updated_label=updated_label,
                row_slug=row_slug,
            )
        )

    active_count = sum(1 for r in rows if not r.archived and not r.is_empty)
    total_stars = sum(r.stars for r in rows)

    return ExplorerModel(
        username=username,
        sort_by=resolved_sort,
        total_repositories=len(rows),
        active_repositories=active_count,
        total_stars=total_stars,
        generated_at=generated_date,
        rows=tuple(rows),
    )


def load_explorer_inputs(
    repos_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    config_path: Path = CONFIG_PATH,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Read repositories, commits, and profile config datasets from disk."""
    import json

    repos_data = json.loads(repos_path.read_text(encoding="utf-8"))
    commits_data = json.loads(commits_path.read_text(encoding="utf-8")) if commits_path.exists() else {"commits": []}
    config_raw = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    return repos_data, commits_data, config_raw
