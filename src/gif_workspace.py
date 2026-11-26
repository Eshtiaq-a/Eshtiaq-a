"""Animated GIF fallback strategy for Section 01 if GitHub Camo SVG animation is restricted.

Activated only if Phase 1 live GitHub Camo verification shows CSS `@keyframes`
scrolling inside `assets/workspace.svg` is blocked, clipped, or stalled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config import (
    MAX_GIF_BYTES,
    MONITOR_SCREEN_BOX,
    WORKSPACE_HEIGHT,
    WORKSPACE_WIDTH,
)
from src.credits_formatter import build_credit_sequence


@dataclass(frozen=True)
class GifFallbackPlan:
    """Computed frame geometry and file-size optimization parameters for GIF fallback."""

    canvas_width: int
    canvas_height: int
    dirty_rect: tuple[int, int, int, int]
    fps: int
    frame_delay_ms: int
    total_frames: int
    scroll_height_px: int
    max_palette_colors: int
    max_bytes: int


def compute_gif_fallback_plan(
    commits_payload: dict[str, Any],
    fps: int = 12,
    scroll_speed_px_per_sec: float = 20.0,
) -> GifFallbackPlan:
    """Compute dirty-rectangle GIF animation parameters targeting < 1.5 MB."""
    _, seq_height, duration_sec = build_credit_sequence(
        commits_payload,
        scroll_speed_px_per_sec=scroll_speed_px_per_sec,
    )
    clamped_fps = max(8, min(15, fps))
    total_frames = max(1, int(round(duration_sec * clamped_fps)))
    return GifFallbackPlan(
        canvas_width=WORKSPACE_WIDTH,
        canvas_height=WORKSPACE_HEIGHT,
        dirty_rect=MONITOR_SCREEN_BOX,
        fps=clamped_fps,
        frame_delay_ms=int(round(1000 / clamped_fps)),
        total_frames=total_frames,
        scroll_height_px=seq_height,
        max_palette_colors=64,
        max_bytes=MAX_GIF_BYTES,
    )


def render_gif_fallback(*_args: Any, **_kwargs: Any) -> None:
    """Placeholder entry point for Pillow/LZW rasterization if SVG Camo test fails."""
    try:
        import PIL  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "GIF fallback requires Pillow (`pip install pillow`) and is only "
            "activated if live GitHub SVG testing fails."
        ) from exc
    raise NotImplementedError(
        "SVG is the active Phase 1 renderer; implement Pillow frame loop here "
        "only if live GitHub Camo SVG testing triggers Decision 04 fallback."
    )
