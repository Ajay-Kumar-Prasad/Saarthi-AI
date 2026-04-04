"""
Google Fit REST API client for the Health Agent.

All functions here call the real Google Fit REST API using the user's OAuth
access token (auto-refreshed via auth.google_oauth.get_valid_access_token).

Google Fit uses nanosecond epoch timestamps for its API.
Data source IDs used:
  - derived:com.google.step_count.delta:com.google.android.gms:estimated_steps
  - derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended
  - derived:com.google.heart_rate.bpm:com.google.android.gms:resting_heart_rate<-merge_heart_rate_summary
  - derived:com.google.sleep.segment:com.google.android.gms:merged
"""

import logging
from datetime import datetime, timedelta, timezone, date as DateType
from typing import Any

import httpx

from auth.google_oauth import get_valid_access_token
from models.schemas import SleepSession, ActivitySession, DailyMetrics

logger = logging.getLogger(__name__)

FIT_BASE = "https://www.googleapis.com/fitness/v1/users/me"

# Google Fit activity type IDs → human-readable names
ACTIVITY_TYPE_MAP: dict[int, str] = {
    0: "in_vehicle",
    7: "walking",
    8: "running",
    9: "aerobics",
    10: "badminton",
    11: "baseball",
    12: "basketball",
    13: "biathlon",
    1: "biking",
    14: "hand_biking",
    16: "boxing",
    15: "circuit_training",
    17: "cross_country_skiing",
    18: "cross_fit",
    19: "curling",
    20: "cycling",
    21: "dancing",
    22: "diving",
    24: "elliptical",
    25: "ergometer",
    26: "fencing",
    27: "football_american",
    28: "football_australian",
    29: "football_soccer",
    30: "frisbee_disc",
    31: "gardening",
    32: "golf",
    33: "gymnastics",
    34: "handball",
    35: "hiking",
    36: "hockey",
    37: "horseback_riding",
    38: "housework",
    39: "ice_skating",
    40: "jumping_rope",
    41: "kayaking",
    42: "kettlebell_training",
    43: "kickboxing",
    44: "kitesurfing",
    45: "martial_arts",
    46: "meditation",
    47: "mixed_martial_arts",
    48: "p90x",
    49: "paragliding",
    50: "pilates",
    51: "polo",
    52: "racquetball",
    53: "rock_climbing",
    54: "rowing",
    55: "rowing_machine",
    56: "rugby",
    57: "jogging",
    58: "sailing",
    59: "scuba_diving",
    60: "skateboarding",
    61: "skating",
    62: "skiing",
    63: "snowboarding",
    64: "snowmobile",
    65: "snowshoeing",
    66: "squash",
    67: "stair_climbing",
    68: "stand_up_paddleboarding",
    69: "still",
    70: "strength_training",
    71: "surfing",
    72: "swimming",
    73: "swimming_pool",
    74: "swimming_open_water",
    75: "table_tennis",
    76: "team_sports",
    77: "tennis",
    78: "treadmill",
    79: "volleyball",
    80: "volleyball_beach",
    81: "volleyball_indoor",
    82: "wakeboarding",
    83: "walking_fitness",
    84: "walking_nordic",
    85: "walking_treadmill",
    86: "weightlifting",
    87: "wheelchair",
    88: "windsurfing",
    89: "yoga",
    90: "zumba",
    92: "diving",
    93: "ergometer_rowing",
    94: "ice_hockey",
    95: "indoor_cycling",
    96: "indoor_running",
    97: "indoor_skiing",
    98: "indoor_snowboarding",
    99: "indoor_surfing",
    100: "kickboxing",
    101: "indoor_volleyball",
}

# Sleep stage type IDs from Google Fit
SLEEP_STAGE_MAP: dict[int, str] = {
    1: "awake",
    2: "sleep",         # generic / unspecified
    3: "out_of_bed",
    4: "light",
    5: "deep",
    6: "rem",
}


def _ns(dt: datetime) -> int:
    """Convert datetime to nanosecond epoch timestamp (Google Fit format)."""
    return int(dt.timestamp() * 1_000_000_000)


def _days_range(days: int) -> tuple[datetime, datetime]:
    """Return (start, end) datetimes for the last N days ending now."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start, end


async def _fit_get(
    user_id: str, path: str, params: dict | None = None
) -> dict[str, Any]:
    """Authenticated GET request to the Google Fit REST API."""
    access_token = await get_valid_access_token(user_id)
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{FIT_BASE}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()


async def _fit_post(
    user_id: str, path: str, body: dict
) -> dict[str, Any]:
    """Authenticated POST request to the Google Fit REST API."""
    access_token = await get_valid_access_token(user_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    url = f"{FIT_BASE}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


# ── Sleep ─────────────────────────────────────────────────────────────────────

async def fetch_sleep_data(user_id: str, days: int = 7) -> list[SleepSession]:
    """
    Fetch sleep sessions from Google Fit for the last `days` days.
    Uses the sessions endpoint which returns SLEEP activity type (72).
    Also calls the sleep segment dataset to get detailed sleep stages.
    """
    start, end = _days_range(days)

    params = {
        "startTime": start.isoformat(),
        "endTime": end.isoformat(),
        "activityType": 72,  # Sleep
    }

    try:
        data = await _fit_get(user_id, "sessions", params)
    except httpx.HTTPStatusError as e:
        logger.error(f"Google Fit sessions error for user {user_id}: {e}")
        return []

    sessions_raw = data.get("session", [])
    sleep_sessions: list[SleepSession] = []

    for session in sessions_raw:
        start_ms = int(session.get("startTimeMillis", 0))
        end_ms = int(session.get("endTimeMillis", 0))
        if not start_ms or not end_ms:
            continue

        start_dt = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)
        duration_minutes = int((end_ms - start_ms) / 60000)

        # Try to fetch detailed sleep stages for this session
        stages = await _fetch_sleep_stages(
            user_id=user_id,
            start_ns=start_ms * 1_000_000,
            end_ns=end_ms * 1_000_000,
        )

        sleep_sessions.append(
            SleepSession(
                date=start_dt.strftime("%Y-%m-%d"),
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
                duration_minutes=duration_minutes,
                sleep_stages=stages if stages else None,
            )
        )

    # Sort by date descending (most recent first)
    sleep_sessions.sort(key=lambda s: s.start_time, reverse=True)
    logger.info(f"Fetched {len(sleep_sessions)} sleep sessions for user {user_id}")
    return sleep_sessions


async def _fetch_sleep_stages(
    user_id: str, start_ns: int, end_ns: int
) -> dict[str, int] | None:
    """
    Fetch granular sleep stages (light/deep/rem/awake) for a specific sleep window.
    Returns a dict of stage_name -> minutes, or None if no stage data available.
    """
    dataset_id = f"{start_ns}-{end_ns}"
    data_source = "derived:com.google.sleep.segment:com.google.android.gms:merged"

    try:
        data = await _fit_get(
            user_id,
            f"dataSources/{data_source}/datasets/{dataset_id}",
        )
    except httpx.HTTPStatusError:
        return None

    stage_minutes: dict[str, int] = {"light": 0, "deep": 0, "rem": 0, "awake": 0}
    for point in data.get("point", []):
        stage_val = point.get("value", [{}])[0].get("intVal", 2)
        stage_name = SLEEP_STAGE_MAP.get(stage_val, "sleep")
        start_ns_pt = int(point.get("startTimeNanos", 0))
        end_ns_pt = int(point.get("endTimeNanos", 0))
        duration_min = int((end_ns_pt - start_ns_pt) / 60_000_000_000)
        if stage_name in stage_minutes:
            stage_minutes[stage_name] += duration_min

    return stage_minutes if any(stage_minutes.values()) else None


# ── Activity Sessions ─────────────────────────────────────────────────────────

async def fetch_activity_sessions(
    user_id: str, days: int = 7
) -> list[ActivitySession]:
    """
    Fetch workout/activity sessions from Google Fit for the last `days` days.
    Excludes sleep (type 72) and still/in-vehicle sessions.
    """
    start, end = _days_range(days)
    params = {
        "startTime": start.isoformat(),
        "endTime": end.isoformat(),
    }

    try:
        data = await _fit_get(user_id, "sessions", params)
    except httpx.HTTPStatusError as e:
        logger.error(f"Google Fit sessions error: {e}")
        return []

    excluded_types = {69, 0, 72}  # still, in_vehicle, sleep
    sessions: list[ActivitySession] = []

    for session in data.get("session", []):
        activity_type_id = session.get("activityType", 0)
        if activity_type_id in excluded_types:
            continue

        start_ms = int(session.get("startTimeMillis", 0))
        end_ms = int(session.get("endTimeMillis", 0))
        if not start_ms or not end_ms:
            continue

        start_dt = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)
        duration_minutes = int((end_ms - start_ms) / 60000)
        activity_name = ACTIVITY_TYPE_MAP.get(activity_type_id, f"activity_{activity_type_id}")

        # Fetch calories and heart rate for this session window
        calories = await _fetch_calories_in_window(user_id, start_ms * 1_000_000, end_ms * 1_000_000)
        steps = await _fetch_steps_in_window(user_id, start_ms * 1_000_000, end_ms * 1_000_000)
        avg_hr = await _fetch_avg_heart_rate_in_window(user_id, start_ms * 1_000_000, end_ms * 1_000_000)

        sessions.append(
            ActivitySession(
                date=start_dt.strftime("%Y-%m-%d"),
                activity_type=activity_name,
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
                duration_minutes=duration_minutes,
                calories_burned=calories,
                steps=steps,
                avg_heart_rate=avg_hr,
            )
        )

    sessions.sort(key=lambda s: s.start_time, reverse=True)
    logger.info(f"Fetched {len(sessions)} activity sessions for user {user_id}")
    return sessions


# ── Daily Aggregates (steps + calories) ──────────────────────────────────────

async def fetch_daily_metrics(user_id: str, days: int = 7) -> list[DailyMetrics]:
    """
    Fetch daily step counts, calories burned, and active minutes
    aggregated per day for the last `days` days.
    Uses the aggregateBy endpoint for efficient bulk fetch.
    """
    start, end = _days_range(days)
    body = {
        "aggregateBy": [
            {"dataTypeName": "com.google.step_count.delta"},
            {"dataTypeName": "com.google.calories.expended"},
            {"dataTypeName": "com.google.active_minutes"},
        ],
        "bucketByTime": {"durationMillis": 86400000},  # 1 day buckets
        "startTimeMillis": int(start.timestamp() * 1000),
        "endTimeMillis": int(end.timestamp() * 1000),
    }

    try:
        data = await _fit_post(user_id, "dataset:aggregate", body)
    except httpx.HTTPStatusError as e:
        logger.error(f"Google Fit aggregate error: {e}")
        return []

    metrics: list[DailyMetrics] = []
    for bucket in data.get("bucket", []):
        bucket_start_ms = int(bucket.get("startTimeMillis", 0))
        day_str = datetime.fromtimestamp(
            bucket_start_ms / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d")

        steps = None
        calories = None
        active_minutes = None

        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                values = point.get("value", [])
                if not values:
                    continue
                data_source_id = dataset.get("dataSourceId", "")
                if "step_count" in data_source_id:
                    steps = sum(v.get("intVal", 0) for v in values)
                elif "calories" in data_source_id:
                    calories = round(sum(v.get("fpVal", 0.0) for v in values), 2)
                elif "active_minutes" in data_source_id:
                    active_minutes = sum(v.get("intVal", 0) for v in values)

        metrics.append(
            DailyMetrics(
                date=day_str,
                total_steps=steps,
                total_calories=calories,
                active_minutes=active_minutes,
            )
        )

    metrics.sort(key=lambda m: m.date, reverse=True)
    logger.info(f"Fetched daily metrics for {len(metrics)} days for user {user_id}")
    return metrics


async def fetch_heart_rate(user_id: str, days: int = 7) -> list[dict[str, Any]]:
    """
    Fetch resting heart rate per day for the last `days` days.
    Returns list of {date, resting_heart_rate} dicts.
    """
    start, end = _days_range(days)
    body = {
        "aggregateBy": [
            {
                "dataTypeName": "com.google.heart_rate.bpm",
                "dataSourceId": (
                    "derived:com.google.heart_rate.bpm:"
                    "com.google.android.gms:resting_heart_rate<-merge_heart_rate_summary"
                ),
            }
        ],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": int(start.timestamp() * 1000),
        "endTimeMillis": int(end.timestamp() * 1000),
    }

    try:
        data = await _fit_post(user_id, "dataset:aggregate", body)
    except httpx.HTTPStatusError as e:
        logger.error(f"Google Fit heart rate error: {e}")
        return []

    results: list[dict[str, Any]] = []
    for bucket in data.get("bucket", []):
        bucket_start_ms = int(bucket.get("startTimeMillis", 0))
        day_str = datetime.fromtimestamp(
            bucket_start_ms / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d")

        rhr: float | None = None
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                for val in point.get("value", []):
                    fp = val.get("fpVal")
                    if fp:
                        rhr = round(fp, 1)

        if rhr is not None:
            results.append({"date": day_str, "resting_heart_rate": rhr})

    results.sort(key=lambda r: r["date"], reverse=True)
    return results


# ── Window-level helpers (internal) ──────────────────────────────────────────

async def _fetch_calories_in_window(
    user_id: str, start_ns: int, end_ns: int
) -> float | None:
    dataset_id = f"{start_ns}-{end_ns}"
    data_source = (
        "derived:com.google.calories.expended:"
        "com.google.android.gms:merge_calories_expended"
    )
    try:
        data = await _fit_get(user_id, f"dataSources/{data_source}/datasets/{dataset_id}")
        total = sum(
            v.get("fpVal", 0.0)
            for point in data.get("point", [])
            for v in point.get("value", [])
        )
        return round(total, 2) if total > 0 else None
    except httpx.HTTPStatusError:
        return None


async def _fetch_steps_in_window(
    user_id: str, start_ns: int, end_ns: int
) -> int | None:
    dataset_id = f"{start_ns}-{end_ns}"
    data_source = (
        "derived:com.google.step_count.delta:"
        "com.google.android.gms:estimated_steps"
    )
    try:
        data = await _fit_get(user_id, f"dataSources/{data_source}/datasets/{dataset_id}")
        total = sum(
            v.get("intVal", 0)
            for point in data.get("point", [])
            for v in point.get("value", [])
        )
        return total if total > 0 else None
    except httpx.HTTPStatusError:
        return None


async def _fetch_avg_heart_rate_in_window(
    user_id: str, start_ns: int, end_ns: int
) -> float | None:
    dataset_id = f"{start_ns}-{end_ns}"
    data_source = (
        "derived:com.google.heart_rate.bpm:"
        "com.google.android.gms:merge_heart_rate_bpm"
    )
    try:
        data = await _fit_get(user_id, f"dataSources/{data_source}/datasets/{dataset_id}")
        values = [
            v.get("fpVal", 0.0)
            for point in data.get("point", [])
            for v in point.get("value", [])
            if v.get("fpVal", 0.0) > 0
        ]
        return round(sum(values) / len(values), 1) if values else None
    except httpx.HTTPStatusError:
        return None
