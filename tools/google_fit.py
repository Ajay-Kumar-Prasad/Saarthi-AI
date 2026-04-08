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

import json
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
    0: "In vehicle",
    3: "Still (not moving)",
    4: "Unknown (unable to detect activity)",
    5: "Tilting (sudden device gravity change)",
    7: "Walking",
    8: "Running",
    9: "Aerobics",
    10: "Badminton",
    11: "Baseball",
    12: "Basketball",
    13: "Biathlon",
    1: "Biking",
    14: "Handbiking",
    15: "Mountain biking",
    16: "Road biking",
    17: "Spinning",
    18: "Stationary biking",
    19: "Utility biking",
    20: "Boxing",
    21: "Calisthenics",
    22: "Circuit training",
    23: "Cricket",
    113: "Crossfit",
    106: "Curling",
    24: "Dancing",
    102: "Diving",
    117: "Elevator",
    25: "Elliptical",
    103: "Ergometer",
    118: "Escalator",
    26: "Fencing",
    27: "Football (American)",
    28: "Football (Australian)",
    29: "Football (Soccer)",
    30: "Frisbee",
    31: "Gardening",
    32: "Golf",
    122: "Guided Breathing",
    33: "Gymnastics",
    34: "Handball",
    114: "HIIT",
    35: "Hiking",
    36: "Hockey",
    37: "Horseback riding",
    38: "Housework",
    104: "Ice skating",
    115: "Interval Training",
    39: "Jumping rope",
    40: "Kayaking",
    41: "Kettlebell training",
    42: "Kickboxing",
    43: "Kitesurfing",
    44: "Martial arts",
    45: "Meditation",
    46: "Mixed martial arts",
    108: "Other (unclassified fitness activity)",
    47: "P90X exercises",
    48: "Paragliding",
    49: "Pilates",
    50: "Polo",
    51: "Racquetball",
    52: "Rock climbing",
    53: "Rowing",
    54: "Rowing machine",
    55: "Rugby",
    56: "Jogging",
    57: "Running on sand",
    58: "Running (treadmill)",
    59: "Sailing",
    60: "Scuba diving",
    61: "Skateboarding",
    62: "Skating",
    63: "Cross skating",
    105: "Indoor skating",
    64: "Inline skating (rollerblading)",
    65: "Skiing",
    66: "Back-country skiing",
    67: "Cross-country skiing",
    68: "Downhill skiing",
    69: "Kite skiing",
    70: "Roller skiing",
    71: "Sledding",
    73: "Snowboarding",
    74: "Snowmobile",
    75: "Snowshoeing",
    120: "Softball",
    76: "Squash",
    77: "Stair climbing",
    78: "Stair-climbing machine",
    79: "Stand-up paddleboarding",
    80: "Strength training",
    81: "Surfing",
    82: "Swimming",
    84: "Swimming (open water)",
    83: "Swimming (swimming pool)",
    85: "Table tennis (ping pong)",
    86: "Team sports",
    87: "Tennis",
    88: "Treadmill (walking or running)",
    89: "Volleyball",
    90: "Volleyball (beach)",
    91: "Volleyball (indoor)",
    92: "Wakeboarding",
    93: "Walking (fitness)",
    94: "Nordic walking",
    95: "Walking (treadmill)",
    116: "Walking (stroller)",
    96: "Waterpolo",
    97: "Weightlifting",
    98: "Wheelchair",
    99: "Windsurfing",
    100: "Yoga",
    101: "Zumba"
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
        logger.info(f"[fetch_sleep_data] Raw sessions data for user {user_id}: {json.dumps(data)[:500]}")
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

    # Log all activityType IDs and names for debugging
    activity_types_seen = {}
    for session in data.get("session", []):
        activity_type_id = session.get("activityType", 0)
        activity_name = ACTIVITY_TYPE_MAP.get(activity_type_id, f"activity_{activity_type_id}")
        activity_types_seen.setdefault(activity_type_id, activity_name)

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


# async def fetch_heart_rate(user_id: str, days: int = 7) -> list[dict[str, Any]]:
#     """
#     Fetch resting heart rate per day for the last `days` days.
#     Returns list of {date, resting_heart_rate} dicts.
#     """
#     start, end = _days_range(days)
#     body = {
#         "aggregateBy": [
#             {
#                 "dataTypeName": "com.google.heart_rate.bpm",
#                 "dataSourceId": (
#                     "derived:com.google.heart_rate.bpm:"
#                     "com.google.android.gms:resting_heart_rate<-merge_heart_rate_summary"
#                 ),
#             }
#         ],
#         "bucketByTime": {"durationMillis": 86400000},
#         "startTimeMillis": int(start.timestamp() * 1000),
#         "endTimeMillis": int(end.timestamp() * 1000),
#     }

#     try:
#         data = await _fit_post(user_id, "dataset:aggregate", body)
#         logger.info(f"[fetch_heart_rate] Raw heart rate data for user {user_id}: {json.dumps(data)[:500]}")
#     except httpx.HTTPStatusError as e:
#         logger.error(f"Google Fit heart rate error: {e}")
#         return []

#     results: list[dict[str, Any]] = []
#     for bucket in data.get("bucket", []):
#         bucket_start_ms = int(bucket.get("startTimeMillis", 0))
#         day_str = datetime.fromtimestamp(
#             bucket_start_ms / 1000, tz=timezone.utc
#         ).strftime("%Y-%m-%d")

#         rhr: float | None = None
#         for dataset in bucket.get("dataset", []):
#             for point in dataset.get("point", []):
#                 for val in point.get("value", []):
#                     fp = val.get("fpVal")
#                     if fp:
#                         rhr = round(fp, 1)

#         if rhr is not None:
#             results.append({"date": day_str, "resting_heart_rate": rhr})

#     results.sort(key=lambda r: r["date"], reverse=True)
#     return results


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
