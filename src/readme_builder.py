"""Sanitized three-section GitHub profile README.md generator."""

from __future__ import annotations

import html
import re
import urllib.parse
from pathlib import Path
from typing import Any

from src.config import README_PATH, atomic_write_text
from src.explorer_builder import SAFE_HTTP_URL_RE, ExplorerModel, ExplorerRow
from src.validators import make_repo_slug, sanitize_github_repo_url
from src.visualizations.repo_galaxy import RepoGalaxyModel

CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
SAFE_GITHUB_PROFILE_RE = re.compile(r"^https://github\.com/[A-Za-z0-9._-]+/?$")


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", CONTROL_CHAR_RE.sub(" ", str(value or ""))).strip()


def _esc_attr(value: Any) -> str:
    return html.escape(_clean(value), quote=True)


def _esc_md_table(value: Any) -> str:
    escaped = _esc_attr(value)
    for ch in ("|", "[", "]", "`"):
        escaped = escaped.replace(ch, f"\\{ch}")
    return escaped


def _safe_profile_url(profile_data: dict[str, Any], username: str) -> str:
    raw = _clean((profile_data.get("directly_sourced_profile") or {}).get("html_url"))
    if SAFE_GITHUB_PROFILE_RE.match(raw):
        return raw
    safe_user = urllib.parse.quote(username or "Eshtiaq-a", safe="-._")
    return f"https://github.com/{safe_user}"


def _render_repo_link_strip(prefix_label: str, rows: tuple[ExplorerRow, ...]) -> str:
    linked = [row for row in rows if row.html_url]
    if not linked:
        return f"<sub><b>{_esc_attr(prefix_label)}:</b> No public repositories discovered yet.</sub>"
    anchors = [
        f'<a href="{_esc_attr(row.html_url)}" target="_blank" rel="noopener noreferrer" title="{_esc_attr(row.description)}"><code>{_esc_attr(row.name)}/</code></a>'
        for row in linked
    ]
    return f"<sub><b>{_esc_attr(prefix_label)}:</b> " + " · ".join(anchors) + "</sub>"


def _render_galaxy_cards_block(
    username: str,
    galaxy_model: RepoGalaxyModel | None,
    explorer_model: ExplorerModel,
) -> str:
    """Render a 2-column grid of individually clickable dark-galaxy repository cards."""
    entries: list[tuple[str, str, str, str, str]] = []
    seen_slugs: set[str] = set()
    used_slugs: set[str] = set()

    if galaxy_model is not None:
        for idx, node in enumerate(galaxy_model.nodes):
            url = sanitize_github_repo_url(node.html_url, username, node.name)
            if not url:
                continue
            slug = node.card_slug or make_repo_slug(node.name, node.repository_id or (idx + 1), used_slugs)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            used_slugs.add(slug)
            entries.append((node.name, slug, url, node.description, node.primary_language))
    else:
        for idx, row in enumerate(explorer_model.rows):
            url = sanitize_github_repo_url(row.html_url, username, row.name)
            if not url:
                continue
            slug = row.row_slug or make_repo_slug(row.name, row.repository_id or (idx + 1), used_slugs)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            used_slugs.add(slug)
            entries.append((row.name, slug, url, row.description, row.primary_language))

    if not entries:
        return ""

    anchors: list[str] = []
    for name, slug, url, desc, primary_lang in entries:
        anchors.append(
            f'<a href="{_esc_attr(url)}" target="_blank" rel="noopener noreferrer" '
            f'title="{_esc_attr(name)} — {_esc_attr(desc)}">'
            f'<img src="assets/repos/{_esc_attr(slug)}.svg" width="49%" '
            f'alt="{_esc_attr(name)} repository card — {_esc_attr(primary_lang)}" /></a>'
        )

    rows_html: list[str] = []
    for i in range(0, len(anchors), 2):
        pair = " ".join(anchors[i : i + 2])
        rows_html.append(f"  {pair}")
    return "<br />\n".join(rows_html)


def _render_explorer_slices_block(model: ExplorerModel, repos_tab_url: str) -> str:
    """Render contiguous clickable terminal header, per-repo rows, and footer for GitHub README."""
    header_tag = (
        f'<a href="{_esc_attr(repos_tab_url)}" target="_blank" rel="noopener noreferrer">'
        f'<img src="assets/explorer/header.svg" width="100%" align="top" '
        f'alt="{_esc_attr(model.username)} terminal project explorer header showing ls ~/projects" /></a>'
    )
    footer_tag = (
        f'<a href="{_esc_attr(repos_tab_url)}" target="_blank" rel="noopener noreferrer">'
        f'<img src="assets/explorer/footer.svg" width="100%" align="top" '
        f'alt="{_esc_attr(model.username)} terminal project explorer status footer" /></a>'
    )
    if not model.rows:
        empty_tag = (
            f'<a href="{_esc_attr(repos_tab_url)}" target="_blank" rel="noopener noreferrer">'
            '<img src="assets/explorer/rows/_empty.svg" width="100%" align="top" '
            'alt="No public repositories discovered yet" /></a>'
        )
        return header_tag + empty_tag + footer_tag

    row_tags: list[str] = []
    for row in model.rows:
        img_tag = (
            f'<img src="assets/explorer/rows/{_esc_attr(row.row_slug)}.svg" width="100%" align="top" '
            f'alt="{_esc_attr(row.name)}/ — {_esc_attr(row.description)}" />'
        )
        if row.html_url:
            row_tags.append(
                f'<a href="{_esc_attr(row.html_url)}" target="_blank" rel="noopener noreferrer" '
                f'title="{_esc_attr(row.name)} — {_esc_attr(row.description)}">{img_tag}</a>'
            )
        else:
            row_tags.append(img_tag)

    return header_tag + "".join(row_tags) + footer_tag


def _render_accessible_directory(rows: tuple[ExplorerRow, ...]) -> str:
    if not rows:
        return ""
    lines = [
        "<details>",
        f"<summary>Accessible Directory Index &amp; Full Descriptions ({len(rows)} public repositories)</summary>",
        "",
        "| Repository | Description | Languages | Stars | Updated | Live |",
        "|---|---|---|---:|---|---|",
    ]
    for row in rows:
        repo_link = (
            f'<a href="{_esc_attr(row.html_url)}" target="_blank" rel="noopener noreferrer"><code>{_esc_md_table(row.name)}/</code></a>'
            if row.html_url
            else f"<code>{_esc_md_table(row.name)}/</code>"
        )
        desc_txt = _esc_md_table(row.description)
        langs_txt = _esc_md_table(", ".join(row.languages) if row.languages else row.primary_language)
        safe_homepage = row.homepage if (row.homepage and SAFE_HTTP_URL_RE.match(row.homepage)) else None
        live_cell = f"[Live]({_esc_attr(safe_homepage.replace('|', '%7C'))})" if safe_homepage else "—"
        lines.append(
            f"| {repo_link} | {desc_txt} | {langs_txt} | ★ {row.stars} | {_esc_md_table(row.updated_label)} | {live_cell} |"
        )
    lines.extend(["", "</details>"])
    return "\n".join(lines)


def _render_city_summary(
    contributions_data: dict[str, Any] | None,
    profile_data: dict[str, Any],
    commits_data: dict[str, Any],
) -> str:
    """Render concise Contribution City caption strictly from real dataset metrics."""
    if contributions_data:
        total = int(contributions_data.get("total_contributions") or 0)
        active = int(contributions_data.get("active_days") or 0)
        busiest = contributions_data.get("busiest_day") or {}
        busiest_txt = (
            f" · Peak: {_esc_attr(busiest['date'])} ({int(busiest['count'])})"
            if busiest.get("date") and int(busiest.get("count") or 0) > 0
            else ""
        )
        src_note = " · <i>(commits fallback)</i>" if contributions_data.get("is_fallback") else ""
        return f"<sub><b>3D Contribution City:</b> {total} contributions across {active} active days{busiest_txt}{src_note}</sub>"

    cstats = profile_data.get("contribution_stats") or {}
    if cstats.get("available") and cstats.get("total_contributions") is not None:
        total = int(cstats.get("total_contributions") or 0)
        active = int(cstats.get("active_days") or 0)
        return f"<sub><b>3D Contribution City:</b> {total} contributions across {active} active days</sub>"

    commit_total = int(commits_data.get("total_unique_commits") or len(commits_data.get("commits") or []))
    return f"<sub><b>3D Contribution City:</b> {commit_total} public-branch commits visualized</sub>"


def build_readme_markdown(
    profile_data: dict[str, Any],
    commits_data: dict[str, Any],
    explorer_model: ExplorerModel,
    use_gif_workspace: bool = False,
    galaxy_model: RepoGalaxyModel | None = None,
    contributions_data: dict[str, Any] | None = None,
) -> str:
    """Assemble the complete sanitized four-section README.md cleanly."""
    username = _clean(explorer_model.username or profile_data.get("username") or "Eshtiaq-a")
    profile_url = _safe_profile_url(profile_data, username).rstrip("/")
    repos_tab_url = f"{profile_url}?tab=repositories"

    workspace_asset = "assets/workspace.gif" if use_gif_workspace else "assets/workspace.svg"
    commit_count = int(commits_data.get("total_unique_commits") or len(commits_data.get("commits") or []))
    branches_count = int(commits_data.get("branches_processed") or 0)
    repos_processed = int(commits_data.get("repositories_processed") or explorer_model.total_repositories)

    galaxy_cards_block = _render_galaxy_cards_block(username, galaxy_model, explorer_model)
    galaxy_links = _render_repo_link_strip("Repo Galaxy", explorer_model.rows)
    city_summary = _render_city_summary(contributions_data, profile_data, commits_data)
    explorer_block = _render_explorer_slices_block(explorer_model, repos_tab_url)
    quick_links = _render_repo_link_strip("~/projects", explorer_model.rows)
    accessible_dir = _render_accessible_directory(explorer_model.rows)

    sections = [
        "<!-- Auto-generated by Eshtiaq Developer Universe. Do not edit manually. -->",
        "",
        '<p align="center">',
        f'  <img src="{workspace_asset}" width="100%" alt="{_esc_attr(username)} pixel-art developer workspace with MacBook connected to external monitor scrolling multi-branch commit credits" />',
        "</p>",
        "",
        '<p align="center">',
        f"  <sub><b>External Monitor Credits Feed:</b> {commit_count} unique commits across {branches_count} accessible public branches in {repos_processed} repositories</sub>",
        "</p>",
        "",
        '<p align="center">',
        '  <img src="assets/divider.svg" width="100%" alt="" />',
        "</p>",
        "",
        '<p align="center">',
        f'  <a href="{_esc_attr(repos_tab_url)}" target="_blank" rel="noopener noreferrer" title="Browse {_esc_attr(username)} public repositories on GitHub"><img src="assets/neofetch.svg" width="100%" alt="{_esc_attr(username)} animated Repo Galaxy and Neofetch developer terminal" /></a>',
        "</p>",
    ]

    if galaxy_cards_block:
        sections.extend(
            [
                "",
                '<p align="center">',
                galaxy_cards_block,
                "</p>",
            ]
        )

    sections.extend(
        [
            "",
            '<p align="center">',
            f"  {galaxy_links}",
            "</p>",
            "",
            '<p align="center">',
            '  <img src="assets/divider.svg" width="100%" alt="" />',
            "</p>",
            "",
            '<p align="center">',
            f'  <a href="{_esc_attr(profile_url)}" target="_blank" rel="noopener noreferrer" title="View {_esc_attr(username)} GitHub contribution activity"><img src="assets/contribution_city.svg" width="100%" alt="{_esc_attr(username)} 3D isometric GitHub Contribution City" /></a>',
            "</p>",
            "",
            '<p align="center">',
            f"  {city_summary}",
            "</p>",
            "",
            '<p align="center">',
            '  <img src="assets/divider.svg" width="100%" alt="" />',
            "</p>",
            "",
            '<p align="center">',
            f"  {explorer_block}",
            "</p>",
            "",
            '<p align="center">',
            f"  {quick_links}",
            "</p>",
        ]
    )

    if accessible_dir:
        sections.extend(["", accessible_dir])

    sections.append("")
    return "\n".join(sections)


def write_readme_markdown(
    content: str,
    output_path: Path = README_PATH,
) -> Path:
    """Persist README.md atomically."""
    return atomic_write_text(output_path, content)
