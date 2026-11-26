"""Format commit records into cinematic SVG movie end-credit blocks."""

from __future__ import annotations

import html
import re
import textwrap
from dataclasses import dataclass
from typing import Any

from src.config import MONITOR_SCREEN_BOX, WORKSPACE_PALETTE

CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True)
class CreditLine:
    """Single rendered text or rule line inside the movie-credit scroll track."""

    kind: str  # 'title' | 'subtitle' | 'badge' | 'repo' | 'message' | 'meta' | 'rule' | 'spacer'
    text: str
    y: int
    font_size: float = 8.0
    color: str = "#e9ecf2"
    bold: bool = False
    letter_spacing: float = 0.0


def clean_text(value: str) -> str:
    """Strip control characters and normalize whitespace."""
    cleaned = CONTROL_CHARS_RE.sub(" ", value or "")
    return " ".join(cleaned.split())


def _extract_display_fields(commit: dict[str, Any]) -> tuple[str, str, str, str, bool]:
    """Normalize both Phase 1 sample records and Phase 2 canonical records for display."""
    repo_name = clean_text(
        str(commit.get("repository_name") or commit.get("repo_name") or "unknown-repo")
    )

    raw_msg = str(commit.get("commit_message") or commit.get("message") or "")
    first_line = next((ln for ln in raw_msg.splitlines() if ln.strip()), "")
    msg_display = clean_text(first_line) or "Commit recorded"

    raw_date = str(commit.get("committed_at") or commit.get("commit_date") or "")
    date_str = clean_text(raw_date)[:10] or "Unknown date"

    raw_author = commit.get("author_name") or commit.get("author") or commit.get("author_login")
    author_str = clean_text(str(raw_author)) if raw_author else "Unknown author"

    is_merge = bool(commit.get("is_merge", False))
    return repo_name, msg_display, date_str, author_str, is_merge


def build_credit_sequence(
    payload: dict[str, Any],
    scroll_speed_px_per_sec: float = 20.0,
) -> tuple[list[CreditLine], int, float]:
    """Convert commit JSON payload into a timed, centered movie-credit line sequence."""
    commits: list[dict[str, Any]] = payload["commits"]
    is_sample = bool(payload.get("is_sample_data", False))
    _, _, _, screen_h = MONITOR_SCREEN_BOX

    lines: list[CreditLine] = []
    y = 26

    # Cinematic Opening Title Card
    lines.append(CreditLine("rule", "", y, color=WORKSPACE_PALETTE["credit_divider"]))
    y += 18
    lines.append(
        CreditLine(
            "subtitle",
            "A PRODUCTION BY",
            y,
            font_size=7.0,
            color=WORKSPACE_PALETTE["credit_title"],
            letter_spacing=1.2,
        )
    )
    y += 15
    lines.append(
        CreditLine(
            "title",
            "ESHTIAQ AHMAD",
            y,
            font_size=11.0,
            color=WORKSPACE_PALETTE["cream"],
            bold=True,
            letter_spacing=1.5,
        )
    )
    y += 16
    lines.append(
        CreditLine(
            "subtitle",
            "GITHUB CHRONICLES",
            y,
            font_size=8.0,
            color=WORKSPACE_PALETTE["credit_repo"],
            bold=True,
            letter_spacing=1.0,
        )
    )
    y += 13
    if is_sample:
        lines.append(
            CreditLine(
                "badge",
                "[ SAMPLE DATA PROTOTYPE ]",
                y,
                font_size=6.8,
                color=WORKSPACE_PALETTE["credit_title"],
                letter_spacing=0.6,
            )
        )
        y += 13
    lines.append(CreditLine("rule", "", y, color=WORKSPACE_PALETTE["credit_divider"]))
    y += 46

    repo_names_seen: set[str] = set()
    if not commits:
        lines.append(
            CreditLine(
                "subtitle",
                "NO PUBLIC COMMITS DISCOVERED YET",
                y,
                font_size=7.8,
                color=WORKSPACE_PALETTE["credit_meta"],
            )
        )
        y += 24
    else:
        # Chronological Credit Roll Grouped by Consecutive Repository
        current_repo: str | None = None
        for commit in commits:
            repo_name, msg_display, date_str, author_str, is_merge = _extract_display_fields(commit)
            repo_names_seen.add(repo_name)
            if repo_name != current_repo:
                if current_repo is not None:
                    y += 8
                current_repo = repo_name
                lines.append(
                    CreditLine(
                        "repo",
                        repo_name.upper()[:28],
                        y,
                        font_size=8.5,
                        color=WORKSPACE_PALETTE["credit_repo"],
                        bold=True,
                        letter_spacing=0.8,
                    )
                )
                y += 13

            wrapped = textwrap.wrap(msg_display, width=35, max_lines=2, placeholder="...")
            for msg_line in wrapped:
                lines.append(
                    CreditLine(
                        "message",
                        msg_line,
                        y,
                        font_size=7.8,
                        color=WORKSPACE_PALETTE["credit_text"],
                    )
                )
                y += 11

            merge_tag = "  •  MERGE" if is_merge else ""
            meta_line = f"{date_str}  •  {author_str[:20]}{merge_tag}"
            lines.append(
                CreditLine(
                    "meta",
                    meta_line,
                    y,
                    font_size=6.6,
                    color=WORKSPACE_PALETTE["credit_meta"],
                )
            )
            y += 15

    # Cinematic Closing Sequence
    y += 12
    lines.append(CreditLine("rule", "", y, color=WORKSPACE_PALETTE["credit_divider"]))
    y += 18
    lines.append(
        CreditLine(
            "subtitle",
            "FILMED IN DHAKA, BANGLADESH",
            y,
            font_size=6.8,
            color=WORKSPACE_PALETTE["credit_meta"],
            letter_spacing=0.6,
        )
    )
    y += 13
    lines.append(
        CreditLine(
            "subtitle",
            f"CAST: {len(commits)} COMMITS  •  {len(repo_names_seen)} REPOS",
            y,
            font_size=6.8,
            color=WORKSPACE_PALETTE["credit_repo"],
            letter_spacing=0.5,
        )
    )
    y += 22
    lines.append(
        CreditLine(
            "title",
            "THE END?",
            y,
            font_size=10.5,
            color=WORKSPACE_PALETTE["credit_title"],
            bold=True,
            letter_spacing=1.4,
        )
    )
    y += 15
    lines.append(
        CreditLine(
            "title",
            "THE JOURNEY CONTINUES.",
            y,
            font_size=8.6,
            color=WORKSPACE_PALETTE["cream"],
            bold=True,
            letter_spacing=0.9,
        )
    )
    y += 20
    lines.append(CreditLine("rule", "", y, color=WORKSPACE_PALETTE["credit_divider"]))

    total_height = y + max(48, screen_h // 2)
    speed = max(8.0, float(scroll_speed_px_per_sec))
    duration_sec = round(total_height / speed, 2)
    return lines, total_height, duration_sec


def render_credit_lines_svg(lines: list[CreditLine], center_x: float) -> str:
    """Serialize CreditLine entries into XML-escaped SVG elements."""
    out: list[str] = []
    rule_x1 = center_x - 68
    rule_x2 = center_x + 68
    for item in lines:
        if item.kind == "rule":
            out.append(
                f'<line x1="{rule_x1:.0f}" y1="{item.y}" x2="{rule_x2:.0f}" y2="{item.y}" '
                f'stroke="{item.color}" stroke-width="1" stroke-dasharray="3 2" />'
            )
            continue
        if item.kind == "spacer":
            continue

        escaped = html.escape(item.text, quote=True)
        weight = ' font-weight="700"' if item.bold else ""
        spacing = (
            f' letter-spacing="{item.letter_spacing:.1f}"'
            if item.letter_spacing > 0
            else ""
        )
        out.append(
            f'<text x="{center_x:.0f}" y="{item.y}" text-anchor="middle" '
            f'font-size="{item.font_size:.1f}" fill="{item.color}"{weight}{spacing}>'
            f"{escaped}</text>"
        )
    return "\n      ".join(out)
