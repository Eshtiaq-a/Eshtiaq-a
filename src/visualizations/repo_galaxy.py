"""Animated GitHub Repo Galaxy SVG component driven by live Phase 2 datasets."""

from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import ASSETS_DIR
from src.validators import sanitize_github_repo_url

GALAXY_CSS_PATH = ASSETS_DIR / "galaxy" / "galaxy_styles.css"

LANGUAGE_COLORS: dict[str, str] = {
    "Python": "#4b8bbe",
    "HTML": "#e3623a",
    "TypeScript": "#3b82f6",
    "JavaScript": "#f1e05a",
    "C": "#7b9ec9",
    "C++": "#f34b7d",
    "CSS": "#8b5cf6",
    "PLpgSQL": "#38bdf8",
    "SQL": "#38bdf8",
    "PowerShell": "#60a5fa",
    "Shell": "#73b88d",
    "Go": "#00add8",
    "Rust": "#dea584",
    "Java": "#b07219",
}
DEFAULT_NODE_COLOR = "#8294ea"

CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


def _clean_text(text: Any) -> str:
    return CONTROL_CHAR_RE.sub(" ", str(text or "")).strip()


def _esc(text: Any) -> str:
    return html.escape(_clean_text(text), quote=True)


def get_language_color(language: str | None) -> str:
    """Resolve consistent galaxy star color for a repository's primary language."""
    if not language:
        return DEFAULT_NODE_COLOR
    return LANGUAGE_COLORS.get(language.strip(), DEFAULT_NODE_COLOR)


def compute_node_radius(stars: int, is_empty: bool = False, archived: bool = False) -> float:
    """Scale galaxy node radius logarithmically by stars with a sensible minimum."""
    if is_empty:
        return 3.4
    if stars <= 0:
        return 4.0 if archived else 4.6
    return round(min(12.5, 4.8 + 2.1 * math.log2(1 + stars)), 2)


def _truncate_label(name: str, max_chars: int = 21) -> str:
    cleaned = _clean_text(name)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


@dataclass(frozen=True)
class GalaxyRepoNode:
    """Single orbiting repository node with resolved orbital coordinates & label geometry."""

    index: int
    name: str
    display_label: str
    description: str
    primary_language: str
    color: str
    stars: int
    commit_count: int
    is_empty: bool
    archived: bool
    ring_index: int
    orbit_radius: float
    angle_deg: float
    node_radius: float
    show_label: bool
    static_x: float
    static_y: float
    label_box: tuple[float, float, float, float] | None
    label_above: bool = False
    html_url: str | None = None


@dataclass(frozen=True)
class GalaxyLanguageStat:
    """Aggregated language entry for the ARM / LANGUAGE galaxy legend."""

    language: str
    color: str
    percentage: float


@dataclass(frozen=True)
class RepoGalaxyModel:
    """Presentation-ready Repo Galaxy model built strictly from real datasets."""

    username: str
    total_stars: int
    repo_count: int
    nodes: tuple[GalaxyRepoNode, ...]
    orbit_radii: tuple[tuple[int, float, str], ...]
    legend_languages: tuple[GalaxyLanguageStat, ...]


def _parse_iso_ts(raw: Any) -> float:
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _compute_legend_languages(
    profile_data: dict[str, Any],
    repos: list[dict[str, Any]],
    max_items: int = 6,
) -> tuple[GalaxyLanguageStat, ...]:
    """Compute real language breakdown percentages from profile_data or repository fallback."""
    calc_langs = (profile_data.get("calculated_metrics") or {}).get("languages") or []
    entries: list[tuple[str, float]] = []
    if calc_langs:
        for item in calc_langs:
            if not isinstance(item, dict) or not item.get("language"):
                continue
            lang = str(item["language"])
            pct = float(item.get("percentage") or 0.0)
            if pct >= 0.05 or len(entries) < max_items:
                entries.append((lang, pct))
    else:
        byte_totals: dict[str, int] = {}
        fallback_counts: dict[str, int] = {}
        for repo in repos:
            if repo.get("is_fork"):
                continue
            repo_langs = repo.get("languages") or {}
            if repo_langs:
                for lang, b in repo_langs.items():
                    byte_totals[str(lang)] = byte_totals.get(str(lang), 0) + max(0, int(b))
            elif repo.get("primary_language"):
                pl = str(repo["primary_language"])
                fallback_counts[pl] = fallback_counts.get(pl, 0) + 1
        source = byte_totals if sum(byte_totals.values()) > 0 else fallback_counts
        total_val = sum(source.values())
        if total_val > 0:
            for lang, val in sorted(source.items(), key=lambda kv: (-kv[1], kv[0].lower())):
                entries.append((lang, round((val / total_val) * 100.0, 1)))

    result: list[GalaxyLanguageStat] = []
    seen_langs: set[str] = set()
    for lang, pct in entries[:max_items]:
        if lang.lower() in seen_langs:
            continue
        seen_langs.add(lang.lower())
        result.append(
            GalaxyLanguageStat(
                language=lang,
                color=get_language_color(lang),
                percentage=round(pct, 1),
            )
        )
    return tuple(result)


def _boxes_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    pad_x: float = 10.0,
    pad_y: float = 8.0,
) -> bool:
    return not (
        a[2] + pad_x <= b[0]
        or b[2] + pad_x <= a[0]
        or a[3] + pad_y <= b[1]
        or b[3] + pad_y <= a[1]
    )


def _box_collides_core(box: tuple[float, float, float, float], cx: float, cy: float, core_r: float = 30.0) -> bool:
    closest_x = max(box[0], min(cx, box[2]))
    closest_y = max(box[1], min(cy, box[3]))
    dx = closest_x - cx
    dy = closest_y - cy
    return (dx * dx + dy * dy) < (core_r * core_r)


def _pick_unlabeled_position(
    orbit_r: float,
    base_angle: float,
    node_r: float,
    cx: float,
    cy: float,
    placed_label_boxes: list[tuple[float, float, float, float]],
    placed_node_circles: list[tuple[float, float, float]],
) -> tuple[float, float, float]:
    """Place an unlabeled node cleanly along its orbit while avoiding placed labels and dots."""
    offsets = [0.0]
    for step in range(10, 181, 10):
        offsets.extend([float(step), -float(step)])

    best_pen = float("inf")
    best_ang = base_angle
    best_x = cx + orbit_r * math.cos(math.radians(base_angle))
    best_y = cy + orbit_r * math.sin(math.radians(base_angle))

    for offset in offsets:
        cand_ang = (base_angle + offset) % 360.0
        rad = math.radians(cand_ang)
        nx = cx + orbit_r * math.cos(rad)
        ny = cy + orbit_r * math.sin(rad)
        dot_box = (nx - node_r - 3.0, ny - node_r - 3.0, nx + node_r + 3.0, ny + node_r + 3.0)
        pen = abs(offset) * 0.002
        for lbox in placed_label_boxes:
            if _boxes_overlap(dot_box, lbox, pad_x=4.0, pad_y=4.0):
                pen += 200.0
        for ox, oy, orad in placed_node_circles:
            if math.hypot(nx - ox, ny - oy) < (node_r + orad + 10.0):
                pen += 40.0
        if pen < best_pen:
            best_pen = pen
            best_ang = cand_ang
            best_x = nx
            best_y = ny
        if best_pen == 0.0:
            break

    return best_ang, best_x, best_y


def _layout_galaxy_nodes(
    repo_specs: list[dict[str, Any]],
    username: str,
    total_stars: int,
    legend: tuple[GalaxyLanguageStat, ...],
    box_x: float,
    box_y: float,
    box_w: float,
    box_h: float,
    max_visible_labels: int,
) -> RepoGalaxyModel:
    """Compute orbital ring placement and collision-free label boxes for ordered repo specs."""
    sky_top = box_y + 78.0
    sky_bottom = box_y + box_h - 94.0
    cx = box_x + box_w / 2.0
    cy = sky_top + (sky_bottom - sky_top) / 2.0

    max_ring_r = min(box_w * 0.31, (sky_bottom - sky_top) * 0.375)
    num_repos = len(repo_specs)

    if num_repos <= 9:
        base_rings = [
            round(max_ring_r * 0.37, 1),
            round(max_ring_r * 0.58, 1),
            round(max_ring_r * 0.79, 1),
            round(max_ring_r * 1.00, 1),
        ]
        ring_capacities = [1, 1, 1, 1] if num_repos <= 4 else [1, 2, 2, 4]
    else:
        base_rings = [
            round(max_ring_r * 0.34, 1),
            round(max_ring_r * 0.50, 1),
            round(max_ring_r * 0.67, 1),
            round(max_ring_r * 0.84, 1),
            round(max_ring_r * 1.00, 1),
        ]
        # Spread labeled candidates across outer wider rings while keeping top-to-bottom ring priority
        ring_capacities = [1, 1, 2, 3, max(4, num_repos)]

    ring_assignments: list[int] = []
    ring_idx = 0
    used_in_ring = 0
    for _ in range(num_repos):
        while ring_idx < len(ring_capacities) - 1 and used_in_ring >= ring_capacities[ring_idx]:
            ring_idx += 1
            used_in_ring = 0
        ring_assignments.append(ring_idx)
        used_in_ring += 1

    per_ring_indices: dict[int, list[int]] = {}
    for idx, r_idx in enumerate(ring_assignments):
        per_ring_indices.setdefault(r_idx, []).append(idx)

    ring_base_angles = (-55.0, 25.0, -145.0, 125.0, -10.0)
    candidate_offsets = [0.0]
    for step in range(5, 181, 5):
        candidate_offsets.extend([float(step), -float(step)])

    placed_label_boxes: list[tuple[float, float, float, float]] = []
    placed_node_circles: list[tuple[float, float, float]] = []
    nodes: list[GalaxyRepoNode] = []

    min_x = box_x + 14.0
    max_x = box_x + box_w - 14.0
    min_y = sky_top + 6.0
    max_y = sky_bottom - 6.0

    for idx, spec in enumerate(repo_specs):
        raw_name = spec["name"]
        wants_label = idx < max_visible_labels

        r_idx = ring_assignments[idx]
        orbit_r = base_rings[min(r_idx, len(base_rings) - 1)]
        peers = per_ring_indices[r_idx]
        pos_in_ring = peers.index(idx)
        ring_count = len(peers)

        stars = spec["stars"]
        is_empty = spec["is_empty"]
        archived = spec["archived"]
        primary_lang = spec["primary_language"]
        color = spec["color"]
        node_r = spec["node_radius"]
        label_str = _truncate_label(raw_name, max_chars=21)
        est_w = max(32.0, len(label_str) * 5.6 + 10.0)
        est_h = 14.0

        golden_bias = (idx * 137.508) % 360.0
        base_angle = (
            golden_bias
            if ring_count == 1
            else (ring_base_angles[r_idx % len(ring_base_angles)] + pos_in_ring * (360.0 / ring_count))
        ) % 360.0

        chosen_angle = base_angle
        chosen_x = cx + orbit_r * math.cos(math.radians(base_angle))
        chosen_y = cy + orbit_r * math.sin(math.radians(base_angle))
        chosen_box: tuple[float, float, float, float] | None = None
        chosen_above = False
        show_label = False

        if wants_label:
            best_penalty = float("inf")
            for offset in candidate_offsets:
                cand_ang = (base_angle + offset) % 360.0
                rad = math.radians(cand_ang)
                nx = cx + orbit_r * math.cos(rad)
                ny = cy + orbit_r * math.sin(rad)

                for side in ("below", "above"):
                    if side == "below":
                        ly_top = ny + node_r + 3.0
                        cand_box = (nx - est_w / 2.0, ly_top, nx + est_w / 2.0, ly_top + est_h)
                        penalty = abs(offset) * 0.004
                    else:
                        ly_bot = ny - node_r - 3.0
                        cand_box = (nx - est_w / 2.0, ly_bot - est_h, nx + est_w / 2.0, ly_bot)
                        penalty = abs(offset) * 0.004 + 0.05

                    if cand_box[0] < min_x or cand_box[2] > max_x or cand_box[1] < min_y or cand_box[3] > max_y:
                        penalty += 800.0
                    if _box_collides_core(cand_box, cx, cy, core_r=33.0):
                        penalty += 500.0
                    for other_box in placed_label_boxes:
                        if _boxes_overlap(cand_box, other_box, pad_x=6.0, pad_y=5.0):
                            penalty += 220.0
                    for ox, oy, orad in placed_node_circles:
                        n_box = (ox - orad - 4.0, oy - orad - 4.0, ox + orad + 4.0, oy + orad + 4.0)
                        if _boxes_overlap(cand_box, n_box, pad_x=4.0, pad_y=4.0):
                            penalty += 150.0
                        if math.hypot(nx - ox, ny - oy) < (node_r + orad + 16.0):
                            penalty += 25.0

                    if penalty < best_penalty:
                        best_penalty = penalty
                        chosen_angle = cand_ang
                        chosen_x = nx
                        chosen_y = ny
                        chosen_box = cand_box
                        chosen_above = side == "above"

            if best_penalty < 150.0 and chosen_box is not None:
                show_label = True
                placed_label_boxes.append(chosen_box)
            else:
                chosen_box = None
                chosen_above = False
                chosen_angle, chosen_x, chosen_y = _pick_unlabeled_position(
                    orbit_r,
                    base_angle,
                    node_r,
                    cx,
                    cy,
                    placed_label_boxes,
                    placed_node_circles,
                )
        else:
            chosen_angle, chosen_x, chosen_y = _pick_unlabeled_position(
                orbit_r,
                base_angle,
                node_r,
                cx,
                cy,
                placed_label_boxes,
                placed_node_circles,
            )

        placed_node_circles.append((chosen_x, chosen_y, node_r))
        nodes.append(
            GalaxyRepoNode(
                index=idx,
                name=raw_name,
                display_label=label_str,
                description=spec["description"],
                primary_language=primary_lang,
                color=color,
                stars=stars,
                commit_count=spec["commit_count"],
                is_empty=is_empty,
                archived=archived,
                ring_index=r_idx,
                orbit_radius=orbit_r,
                angle_deg=round(chosen_angle, 2),
                node_radius=node_r,
                show_label=show_label,
                static_x=round(chosen_x, 2),
                static_y=round(chosen_y, 2),
                label_box=chosen_box,
                label_above=chosen_above,
                html_url=spec.get("html_url"),
            )
        )

    orbit_radii: list[tuple[int, float, str]] = []
    for r_idx, idxs in sorted(per_ring_indices.items()):
        lang_color = nodes[idxs[0]].color if idxs else "#2c4178"
        orbit_radii.append((r_idx, base_rings[r_idx], lang_color))

    if not orbit_radii:
        orbit_radii = [(0, base_rings[0], "#2c4178"), (1, base_rings[1], "#2c4178"), (2, base_rings[-1], "#2c4178")]

    return RepoGalaxyModel(
        username=username,
        total_stars=total_stars,
        repo_count=num_repos,
        nodes=tuple(nodes),
        orbit_radii=tuple(orbit_radii),
        legend_languages=legend,
    )


def build_repo_galaxy_model(
    repositories_data: dict[str, Any],
    profile_data: dict[str, Any],
    commits_data: dict[str, Any] | None = None,
    box_x: float = 24.0,
    box_y: float = 54.0,
    box_w: float = 422.0,
    box_h: float = 506.0,
    max_visible_labels: int = 12,
) -> RepoGalaxyModel:
    """Build deterministic orbital layout for all public repositories without label collisions."""
    sourced = profile_data.get("directly_sourced_profile") or {}
    username = str(sourced.get("login") or profile_data.get("username") or "Eshtiaq-a")

    raw_repos = list(repositories_data.get("repositories") or [])
    commits_list = (commits_data or {}).get("commits") or []
    commit_counts: dict[str, int] = {}
    for c in commits_list:
        if isinstance(c, dict):
            rname = str(c.get("repository_name") or c.get("repo_name") or "")
            if rname:
                commit_counts[rname] = commit_counts.get(rname, 0) + 1

    def sort_key(r: dict[str, Any]) -> tuple[Any, ...]:
        name = str(r.get("name") or "")
        return (
            bool(r.get("archived", False)),
            bool(r.get("is_empty", False)),
            -int(r.get("stars") or 0),
            -commit_counts.get(name, 0),
            -_parse_iso_ts(r.get("pushed_at")),
            name.lower(),
            int(r.get("repository_id") or 0),
        )

    ordered_repos = sorted(raw_repos, key=sort_key)
    total_stars = sum(max(0, int(r.get("stars") or 0)) for r in ordered_repos)

    repo_specs: list[dict[str, Any]] = []
    for idx, repo in enumerate(ordered_repos):
        raw_name = _clean_text(repo.get("name") or f"repo-{idx + 1}")
        stars = max(0, int(repo.get("stars") or 0))
        is_empty = bool(repo.get("is_empty", False))
        archived = bool(repo.get("archived", False))
        primary_lang = _clean_text(repo.get("primary_language") or "") or "Unspecified"
        repo_specs.append(
            {
                "name": raw_name,
                "description": _clean_text(repo.get("description") or "") or "No description provided yet.",
                "primary_language": primary_lang,
                "color": get_language_color(primary_lang),
                "stars": stars,
                "commit_count": commit_counts.get(raw_name, 0),
                "is_empty": is_empty,
                "archived": archived,
                "node_radius": compute_node_radius(stars, is_empty=is_empty, archived=archived),
                "html_url": sanitize_github_repo_url(repo.get("html_url"), username, raw_name),
            }
        )

    legend = _compute_legend_languages(profile_data, ordered_repos, max_items=6)
    return _layout_galaxy_nodes(
        repo_specs=repo_specs,
        username=username,
        total_stars=total_stars,
        legend=legend,
        box_x=box_x,
        box_y=box_y,
        box_w=box_w,
        box_h=box_h,
        max_visible_labels=max_visible_labels,
    )


def reflow_repo_galaxy_model(
    model: RepoGalaxyModel,
    box_x: float,
    box_y: float,
    box_w: float,
    box_h: float,
    max_visible_labels: int = 12,
) -> RepoGalaxyModel:
    """Reflow an existing RepoGalaxyModel into a new viewport box while preserving order and commit stats."""
    repo_specs = [
        {
            "name": node.name,
            "description": node.description,
            "primary_language": node.primary_language,
            "color": node.color,
            "stars": node.stars,
            "commit_count": node.commit_count,
            "is_empty": node.is_empty,
            "archived": node.archived,
            "node_radius": node.node_radius,
            "html_url": node.html_url,
        }
        for node in model.nodes
    ]
    return _layout_galaxy_nodes(
        repo_specs=repo_specs,
        username=model.username,
        total_stars=model.total_stars,
        legend=model.legend_languages,
        box_x=box_x,
        box_y=box_y,
        box_w=box_w,
        box_h=box_h,
        max_visible_labels=max_visible_labels,
    )


def get_galaxy_css(css_path: Path = GALAXY_CSS_PATH) -> str:
    """Return Galaxy CSS rules from asset file (with inline safety fallback)."""
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return """
    .gx-star-a { opacity: 0.8; }
    .gx-core-pulse { opacity: 0.9; }
    """


def render_repo_galaxy_defs(cx: float, cy: float) -> str:
    """Return SVG <defs> gradients and clipPath needed by the Repo Galaxy."""
    _ = (cx, cy)
    return """    <radialGradient id="gx-nebula-bg" cx="50%" cy="48%" r="60%">
      <stop offset="0%" stop-color="#11224a" stop-opacity="0.72" />
      <stop offset="45%" stop-color="#0b1530" stop-opacity="0.45" />
      <stop offset="100%" stop-color="#080c18" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="gx-core-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#e5efff" stop-opacity="0.95" />
      <stop offset="22%" stop-color="#8bb4ff" stop-opacity="0.65" />
      <stop offset="55%" stop-color="#3b5fc0" stop-opacity="0.22" />
      <stop offset="100%" stop-color="#080c18" stop-opacity="0" />
    </radialGradient>"""


def render_repo_galaxy_group(
    model: RepoGalaxyModel,
    box_x: float = 24.0,
    box_y: float = 54.0,
    box_w: float = 422.0,
    box_h: float = 506.0,
) -> str:
    """Render complete Repo Galaxy panel as a self-contained SVG <g> layer."""
    sky_top = box_y + 78.0
    sky_bottom = box_y + box_h - 94.0
    cx = box_x + box_w / 2.0
    cy = sky_top + (sky_bottom - sky_top) / 2.0

    star_word = "Star" if model.total_stars == 1 else "Stars"
    repo_word = "Repository" if model.repo_count == 1 else "Repositories"
    stats_line = f"{model.total_stars} {star_word} · {model.repo_count} {repo_word}"

    # Deterministic scattered twinkling background stars across the galaxy card
    stars_coords = (
        (0.08, 0.24, 1.1, "a"), (0.16, 0.31, 0.8, "b"), (0.27, 0.22, 1.3, "c"),
        (0.41, 0.25, 0.9, "a"), (0.64, 0.22, 1.2, "b"), (0.79, 0.27, 1.0, "c"),
        (0.91, 0.23, 1.4, "a"), (0.11, 0.44, 0.9, "c"), (0.22, 0.56, 1.2, "a"),
        (0.07, 0.67, 1.4, "b"), (0.18, 0.78, 0.9, "c"), (0.31, 0.79, 1.1, "a"),
        (0.71, 0.76, 1.0, "b"), (0.85, 0.69, 1.3, "c"), (0.93, 0.54, 0.9, "a"),
        (0.88, 0.40, 1.1, "b"), (0.76, 0.35, 0.8, "c"), (0.53, 0.21, 0.8, "b"),
        (0.36, 0.68, 0.9, "b"), (0.62, 0.69, 1.1, "a"), (0.14, 0.19, 1.0, "b"),
        (0.83, 0.79, 1.1, "a"), (0.48, 0.78, 0.8, "c"), (0.94, 0.77, 1.0, "b"),
    )
    star_elems = [
        f'<circle class="gx-star-{cls}" cx="{box_x + rx * box_w:.1f}" cy="{box_y + ry * box_h:.1f}" '
        f'r="{r}" fill="#c9d8ff" pointer-events="none" />'
        for rx, ry, r, cls in stars_coords
    ]

    # Orbit tracks (strictly non-interactive so clicks pass cleanly to repository nodes)
    orbit_elems = [
        f'<circle cx="0" cy="0" r="{r_val:.1f}" fill="none" stroke="{ring_col}" '
        f'stroke-width="0.9" stroke-opacity="0.32" stroke-dasharray="3 4" pointer-events="none" />'
        for _, r_val, ring_col in model.orbit_radii
    ]

    # Small glowing dust particles around central galaxy (strictly non-interactive)
    particle_angles = (15, 58, 104, 148, 196, 238, 282, 326)
    particle_radii = (16, 23, 19, 27, 17, 25, 21, 29)
    particle_elems = [
        f'<circle cx="{pr * math.cos(math.radians(pa)):.1f}" cy="{pr * math.sin(math.radians(pa)):.1f}" '
        f'r="{1.1 if i % 2 == 0 else 0.8}" fill="#b9ceff" fill-opacity="0.72" pointer-events="none" />'
        for i, (pa, pr) in enumerate(zip(particle_angles, particle_radii))
    ]

    # Repository orbiting nodes + upright counter-rotated labels wrapped in accessible <a> links
    node_elems: list[str] = []
    for node in model.nodes:
        orbit_cls = f"gx-orbit-{node.ring_index % 5}"
        counter_cls = f"gx-counter-{node.ring_index % 5}"
        halo_r = round(node.node_radius * 2.15, 2)
        hit_r = round(max(13.0, node.node_radius + 7.5), 1)
        dot_opacity = "0.55" if node.archived else ("0.65" if node.is_empty else "0.98")
        stroke_attr = (
            f'stroke="{node.color}" stroke-width="1" stroke-dasharray="2 2" fill="#080c18" fill-opacity="0.3"'
            if node.is_empty
            else f'fill="{node.color}" fill-opacity="{dot_opacity}" stroke="#ffffff" stroke-opacity="0.35" stroke-width="0.6"'
        )
        title_txt = f"{node.name} · {node.primary_language} · {node.stars}★ · {node.commit_count} commits — {node.description}"

        label_markup = ""
        if node.show_label:
            pill_w = max(30.0, len(node.display_label) * 5.3 + 8.0)
            if node.label_above:
                rect_y = -(node.node_radius + 14.3)
                ly = rect_y + 9.2
            else:
                ly = node.node_radius + 11.5
                rect_y = ly - 9.2
            label_markup = (
                f'<rect class="gx-label-hit" x="{-pill_w / 2.0 - 2.0:.1f}" y="{rect_y - 2.0:.1f}" '
                f'width="{pill_w + 4.0:.1f}" height="16.0" rx="4" fill="#080c18" fill-opacity="0.001" />'
                f'<rect class="gx-label-pill" x="{-pill_w / 2.0:.1f}" y="{rect_y:.1f}" width="{pill_w:.1f}" height="12.0" '
                f'rx="3" fill="#080c18" fill-opacity="0.90" stroke="#1e2d57" stroke-width="0.6" />'
                f'<text class="gx-label-text" x="0" y="{ly:.1f}" text-anchor="middle" font-size="8.4" '
                f'fill="{("#8f99ad" if (node.archived or node.is_empty) else "#dce6ff")}">'
                f"{_esc(node.display_label)}</text>"
            )

        node_visual = [
            f'    <title>{_esc(title_txt)}</title>',
            f'    <circle class="gx-node-hit" cx="0" cy="0" r="{hit_r:.1f}" fill="#080c18" fill-opacity="0.001" />',
            f'    <circle class="gx-node-halo" cx="0" cy="0" r="{halo_r}" fill="{node.color}" />',
            f'    <circle class="gx-node-dot" cx="0" cy="0" r="{node.node_radius:.2f}" {stroke_attr} />',
            f'    <circle cx="{-node.node_radius * 0.28:.2f}" cy="{-node.node_radius * 0.28:.2f}" r="{max(0.9, node.node_radius * 0.24):.2f}" fill="#ffffff" fill-opacity="0.7" />',
            f'    <g class="{counter_cls}">',
            f'      <g transform="rotate({-node.angle_deg:.2f})">{label_markup}</g>',
            "    </g>",
        ]
        if node.html_url:
            inner_block = [
                f'    <a class="gx-repo-link" href="{_esc(node.html_url)}" target="_blank" rel="noopener noreferrer" pointer-events="all" aria-label="Open {_esc(node.name)} repository on GitHub">',
                *[f"  {line}" for line in node_visual],
                "    </a>",
            ]
        else:
            inner_block = node_visual

        node_elems.append(
            "\n        ".join(
                [
                    f'<g class="{orbit_cls}" pointer-events="none">',
                    f'  <g transform="rotate({node.angle_deg:.2f}) translate({node.orbit_radius:.1f}, 0)" pointer-events="none">',
                    *inner_block,
                    "  </g>",
                    "</g>",
                ]
            )
        )

    empty_notice = ""
    if model.repo_count == 0:
        empty_notice = (
            f'<text x="0" y="54" text-anchor="middle" font-size="10" fill="#727e96" pointer-events="none">'
            "No public repositories discovered yet</text>"
        )

    # Bottom ARM / LANGUAGE legend (real percentages calculated from dataset)
    legend_y_rule = box_y + box_h - 86.0
    legend_title_y = legend_y_rule + 16.0
    legend_items: list[str] = []
    if model.legend_languages:
        cols = 2
        col_w = (box_w - 36.0) / cols
        for idx, stat in enumerate(model.legend_languages[:6]):
            col = idx % cols
            row = idx // cols
            lx = box_x + 18.0 + col * col_w
            ly = legend_title_y + 18.0 + row * 17.0
            pct_str = f"{stat.percentage:.1f}%" if stat.percentage >= 0.1 else "<0.1%"
            legend_items.append(
                f'<circle cx="{lx + 4:.1f}" cy="{ly - 3.5:.1f}" r="3.6" fill="{stat.color}" pointer-events="none" />'
                f'<text x="{lx + 13:.1f}" y="{ly:.1f}" font-size="10.0" fill="#cdd7ec" pointer-events="none">'
                f'{_esc(stat.language)} <tspan fill="#75819c">· {pct_str}</tspan></text>'
            )
    else:
        legend_items.append(
            f'<text x="{box_x + 18.0:.1f}" y="{legend_title_y + 20.0:.1f}" font-size="10" fill="#75819c" pointer-events="none">'
            "Language breakdown unavailable</text>"
        )

    header_rule_y = box_y + 72.0
    parts = [
        f'<g id="repo-galaxy-panel" class="gx-mono">',
        f'  <defs><clipPath id="gx-box-clip"><rect x="{box_x:.1f}" y="{box_y:.1f}" width="{box_w:.1f}" height="{box_h:.1f}" rx="10" ry="10" /></clipPath></defs>',
        f'  <rect x="{box_x:.1f}" y="{box_y:.1f}" width="{box_w:.1f}" height="{box_h:.1f}" rx="10" ry="10" fill="#080c18" stroke="#2a3c70" stroke-width="1.2" pointer-events="none" />',
        f'  <g clip-path="url(#gx-box-clip)">',
        f'    <ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{box_w * 0.48:.1f}" ry="{box_h * 0.36:.1f}" fill="url(#gx-nebula-bg)" pointer-events="none" />',
        "    " + "\n    ".join(star_elems),
        # Header block (non-interactive)
        f'    <g pointer-events="none">',
        f'      <circle cx="{box_x + 20:.1f}" cy="{box_y + 22:.1f}" r="4" fill="#8294ea" />',
        f'      <circle cx="{box_x + 20:.1f}" cy="{box_y + 22:.1f}" r="7" fill="#8294ea" fill-opacity="0.22" />',
        f'      <text x="{box_x + 32:.1f}" y="{box_y + 26:.1f}" class="gx-title" font-size="12.5" font-weight="700" fill="#e5e9f3">REPO GALAXY</text>',
        f'      <text x="{box_x + box_w - 18:.1f}" y="{box_y + 26:.1f}" text-anchor="end" font-size="11.0" fill="#5aa9ff">@{_esc(model.username)}</text>',
        f'      <text x="{box_x + 18:.1f}" y="{box_y + 44:.1f}" font-size="10.5" font-weight="600" fill="#b8c4db">{_esc(stats_line)}</text>',
        f'      <text x="{box_x + 18:.1f}" y="{box_y + 60:.1f}" font-size="9.5" fill="#707b94">Each star is a repository, sized by its stars.</text>',
        f'      <line x1="{box_x + 16:.1f}" y1="{header_rule_y:.1f}" x2="{box_x + box_w - 16:.1f}" y2="{header_rule_y:.1f}" stroke="#1d2b53" stroke-width="1" stroke-dasharray="3 3" />',
        "    </g>",
        # Galaxy center system
        f'    <g transform="translate({cx:.1f}, {cy:.1f})">',
        # Rotating spiral arms (strictly non-interactive)
        '      <g class="gx-spiral-spin" pointer-events="none">',
        '        <path d="M 0,0 C 26,-16 62,-8 92,-46" fill="none" stroke="#5aa9ff" stroke-width="2.2" stroke-opacity="0.14" stroke-linecap="round" />',
        '        <path d="M 0,0 C -26,16 -62,8 -92,46" fill="none" stroke="#8294ea" stroke-width="2.2" stroke-opacity="0.14" stroke-linecap="round" />',
        '        <path d="M 0,0 C 16,26 10,60 44,92" fill="none" stroke="#4b8bbe" stroke-width="1.8" stroke-opacity="0.12" stroke-linecap="round" />',
        '        <path d="M 0,0 C -16,-26 -10,-60 -44,-92" fill="none" stroke="#e3623a" stroke-width="1.5" stroke-opacity="0.10" stroke-linecap="round" />',
        "      </g>",
        "      " + "\n      ".join(orbit_elems),
        # Central core glow & rotating dashed gyroscope rings (non-interactive)
        '      <g class="gx-ring-spin" pointer-events="none">',
        '        <circle cx="0" cy="0" r="21" fill="none" stroke="#5aa9ff" stroke-width="0.9" stroke-opacity="0.45" stroke-dasharray="4 3" />',
        '        <circle cx="0" cy="0" r="30" fill="none" stroke="#8294ea" stroke-width="0.7" stroke-opacity="0.30" stroke-dasharray="2 5" />',
        "      </g>",
        '      <g class="gx-particles-spin" pointer-events="none">',
        "        " + "\n        ".join(particle_elems),
        "      </g>",
        '      <g class="gx-core-pulse" pointer-events="none">',
        '        <circle cx="0" cy="0" r="34" fill="url(#gx-core-glow)" />',
        '        <circle cx="0" cy="0" r="9.5" fill="#8294ea" fill-opacity="0.38" />',
        '        <circle cx="0" cy="0" r="4.8" fill="#ebf3ff" />',
        "      </g>",
        "      " + "\n      ".join(node_elems),
        f"      {empty_notice}",
        "    </g>",
        # Bottom ARM / LANGUAGE Legend (non-interactive)
        f'    <line x1="{box_x + 16:.1f}" y1="{legend_y_rule:.1f}" x2="{box_x + box_w - 16:.1f}" y2="{legend_y_rule:.1f}" stroke="#1d2b53" stroke-width="1" stroke-dasharray="3 3" pointer-events="none" />',
        f'    <text x="{box_x + 18:.1f}" y="{legend_title_y:.1f}" font-size="8.8" font-weight="700" letter-spacing="1.4" fill="#6f7c99" pointer-events="none">ARM / LANGUAGE</text>',
        "    " + "\n    ".join(legend_items),
        "  </g>",
        "</g>",
    ]
    return "\n    ".join(parts)
