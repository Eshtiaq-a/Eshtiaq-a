"""Contribution calendar loader, GraphQL/fallback normalizer, and intensity mapper for 3D Contribution City."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.config import CONTRIBUTIONS_PATH, atomic_write_json
from src.github_client import GitHubApiError, GitHubClient
from src.stats_builder import compute_calendar_streaks
from src.validators import validate_contributions_payload

WEEKDAY_NAMES = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
INTENSITY_LABELS = {
    0: "None",
    1: "Low",
    2: "Moderate",
    3: "High",
    4: "Peak",
}
GRAPHQL_LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def _sun_first_weekday(d: date) -> int:
    """Return Sunday=0 .. Saturday=6 weekday index matching GitHub's contribution calendar."""
    return (d.weekday() + 1) % 7


def _compute_intensity_level(
    count: int,
    max_count: int,
    raw_level: Any = None,
) -> int:
    """Map contribution count to discrete intensity tier 0..4 consistently."""
    if count <= 0:
        return 0
    if isinstance(raw_level, str) and raw_level.upper() in GRAPHQL_LEVEL_MAP:
        mapped = GRAPHQL_LEVEL_MAP[raw_level.upper()]
        return max(1, mapped)
    if max_count <= 1:
        return 4 if count >= 1 else 0
    ratio = count / max_count
    if ratio >= 0.75:
        return 4
    if ratio >= 0.45:
        return 3
    if ratio >= 0.20:
        return 2
    return 1


def normalize_contribution_calendar(
    raw_calendar: dict[str, Any],
    username: str,
    source: str,
    graphql_available: bool,
    is_fallback: bool,
    generated_at: str,
    warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Normalize raw week/day contribution records into canonical `data/contributions.json` schema."""
    flat_raw: list[dict[str, Any]] = []
    for week in raw_calendar.get("weeks") or []:
        if not isinstance(week, dict):
            continue
        for day in week.get("contributionDays") or []:
            if not isinstance(day, dict) or not day.get("date"):
                continue
            date_str = str(day["date"])[:10]
            try:
                parsed = date.fromisoformat(date_str)
            except ValueError:
                continue
            cnt = max(0, int(day.get("contributionCount") or 0))
            flat_raw.append(
                {
                    "date": parsed.isoformat(),
                    "parsed": parsed,
                    "count": cnt,
                    "raw_level": day.get("contributionLevel"),
                }
            )

    # Deduplicate by date preserving max count & sort chronologically
    by_date: dict[str, dict[str, Any]] = {}
    for entry in flat_raw:
        key = entry["date"]
        if key not in by_date or entry["count"] > by_date[key]["count"]:
            by_date[key] = entry

    ordered = [by_date[k] for k in sorted(by_date)]
    max_daily = max((item["count"] for item in ordered), default=0)

    # Group into Sunday-start GitHub calendar weeks
    weeks_list: list[dict[str, Any]] = []
    if ordered:
        first_date: date = ordered[0]["parsed"]
        start_sunday = first_date - timedelta(days=_sun_first_weekday(first_date))
        last_date: date = ordered[-1]["parsed"]
        total_days = (last_date - start_sunday).days + 1
        num_weeks = (total_days + 6) // 7

        # Partition sparse or contiguous dates cleanly into weekly columns
        current_week_days: dict[int, list[dict[str, Any]]] = {w: [] for w in range(num_weeks)}
        for item in ordered:
            w_idx = (item["parsed"] - start_sunday).days // 7
            wd = _sun_first_weekday(item["parsed"])
            cnt = item["count"]
            lvl = _compute_intensity_level(cnt, max_daily, item.get("raw_level"))
            current_week_days[w_idx].append(
                {
                    "date": item["date"],
                    "count": cnt,
                    "level": lvl,
                    "intensity_label": INTENSITY_LABELS[lvl],
                    "week_index": w_idx,
                    "weekday": wd,
                    "weekday_name": WEEKDAY_NAMES[wd],
                }
            )

        for w_idx in range(num_weeks):
            days_in_week = sorted(current_week_days[w_idx], key=lambda d: d["weekday"])
            if not days_in_week:
                continue
            week_start = (start_sunday + timedelta(days=w_idx * 7)).isoformat()
            weeks_list.append(
                {
                    "week_index": len(weeks_list),
                    "start_date": week_start,
                    "total_contributions": sum(d["count"] for d in days_in_week),
                    "days": [
                        {**d, "week_index": len(weeks_list)}
                        for d in days_in_week
                    ],
                }
            )

    all_normalized_days = [d for w in weeks_list for d in w["days"]]
    total_contributions = sum(d["count"] for d in all_normalized_days)
    active_days, current_streak, best_streak = compute_calendar_streaks(
        [{"date": d["date"], "contributionCount": d["count"]} for d in all_normalized_days]
    )

    busiest_day: dict[str, Any] | None = None
    if max_daily > 0:
        # Pick highest-count day; tie-break by most recent date
        peak = max(all_normalized_days, key=lambda d: (d["count"], d["date"]))
        busiest_day = {
            "date": peak["date"],
            "count": peak["count"],
            "weekday_name": peak["weekday_name"],
        }

    date_range = {
        "start": all_normalized_days[0]["date"] if all_normalized_days else None,
        "end": all_normalized_days[-1]["date"] if all_normalized_days else None,
    }

    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "username": username,
        "source": source,
        "graphql_available": graphql_available,
        "is_fallback": is_fallback,
        "is_sample_data": False,
        "total_contributions": total_contributions,
        "active_days": active_days,
        "current_streak_days": current_streak,
        "best_streak_days": best_streak,
        "max_daily_contributions": max_daily,
        "busiest_day": busiest_day,
        "date_range": date_range,
        "weeks_count": len(weeks_list),
        "days_count": len(all_normalized_days),
        "weeks": weeks_list,
        "collection_warnings": list(warnings or []),
    }
    validate_contributions_payload(payload)
    return payload


def build_contributions_from_commits(
    commits_payload: dict[str, Any],
    username: str,
    generated_at: str | None = None,
    num_weeks: int = 53,
    warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an honest public-branch commits fallback calendar when GraphQL is unavailable."""
    ts = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        end_date = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
    except ValueError:
        end_date = datetime.now(timezone.utc).date()

    counts_by_day: dict[str, int] = {}
    for commit in commits_payload.get("commits") or []:
        raw_dt = str(commit.get("committed_at") or "")
        if len(raw_dt) >= 10:
            day_key = raw_dt[:10]
            try:
                date.fromisoformat(day_key)
            except ValueError:
                continue
            counts_by_day[day_key] = counts_by_day.get(day_key, 0) + 1

    # Align a clean 53-week (or configured) rolling calendar grid ending at end_date
    end_sunday = end_date - timedelta(days=_sun_first_weekday(end_date))
    start_sunday = end_sunday - timedelta(days=(max(1, num_weeks) - 1) * 7)

    weeks_raw: list[dict[str, Any]] = []
    cursor = start_sunday
    while cursor <= end_date:
        week_days: list[dict[str, Any]] = []
        for _ in range(7):
            if cursor > end_date:
                break
            d_str = cursor.isoformat()
            week_days.append(
                {
                    "date": d_str,
                    "contributionCount": counts_by_day.get(d_str, 0),
                }
            )
            cursor += timedelta(days=1)
        if week_days:
            weeks_raw.append({"contributionDays": week_days})

    return normalize_contribution_calendar(
        raw_calendar={"weeks": weeks_raw},
        username=username,
        source="public_branch_commits_fallback",
        graphql_available=False,
        is_fallback=True,
        generated_at=ts,
        warnings=warnings,
    )


def build_contributions_payload(
    client: GitHubClient,
    username: str,
    commits_payload: dict[str, Any],
    generated_at: str | None = None,
    existing_path: Path | None = None,
) -> dict[str, Any]:
    """Fetch GraphQL contributionCalendar when authenticated, else fall back cleanly without inventing data."""
    ts = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    warnings: list[dict[str, Any]] = []

    if client.has_token:
        try:
            cal = client.get_contribution_calendar(username)
        except GitHubApiError as exc:
            cal = None
            warnings.append(
                {
                    "stage": "graphql_contribution_calendar",
                    "status_code": exc.status_code,
                    "message": str(exc),
                }
            )
        if cal and isinstance(cal.get("weeks"), list):
            return normalize_contribution_calendar(
                raw_calendar=cal,
                username=username,
                source="github_graphql_contributions_collection",
                graphql_available=True,
                is_fallback=False,
                generated_at=ts,
                warnings=warnings,
            )

    # Preserve valid cached GraphQL data over incomplete unauthenticated fallback if requested
    if existing_path is not None and existing_path.exists():
        try:
            import json

            cached = json.loads(existing_path.read_text(encoding="utf-8"))
            validate_contributions_payload(cached)
            if cached.get("graphql_available"):
                return cached
        except Exception:
            pass

    if not client.has_token:
        warnings.append(
            {
                "stage": "graphql_contribution_calendar",
                "status_code": None,
                "message": "GITHUB_TOKEN unavailable; fell back to public-branch commits calendar.",
            }
        )

    return build_contributions_from_commits(
        commits_payload=commits_payload,
        username=username,
        generated_at=ts,
        warnings=warnings,
    )


def write_contributions_json(
    payload: dict[str, Any],
    output_path: Path = CONTRIBUTIONS_PATH,
) -> Path:
    """Persist validated `data/contributions.json` atomically."""
    validate_contributions_payload(payload)
    return atomic_write_json(output_path, payload)
