export type DailyMetric = {
  date: string
  total_steps?: number | null
  total_calories?: number | null
  active_minutes?: number | null
  resting_heart_rate?: number | null
}

export type ActivitySession = {
  date: string
  activity_type: string
  start_time: string
  end_time: string
  duration_minutes: number
  calories_burned?: number | null
  steps?: number | null
  distance_meters?: number | null
  avg_heart_rate?: number | null
}

export type HealthSummary = {
  user_id: string
  period_days: number
  sleep_sessions: Array<Record<string, unknown>>
  activity_sessions: ActivitySession[]
  daily_metrics: DailyMetric[]
  avg_sleep_minutes?: number | null
  avg_steps?: number | null
  avg_resting_heart_rate?: number | null
  total_active_minutes?: number | null
}
