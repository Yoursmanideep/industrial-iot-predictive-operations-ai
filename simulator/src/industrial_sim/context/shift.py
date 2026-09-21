from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class ShiftDefinition:
    shift_id: str
    start_local: time
    end_local: time
    workload_multiplier: float


@dataclass(frozen=True)
class ShiftContext:
    shift_id: str
    local_date: str
    local_start: datetime
    local_end: datetime
    workload_multiplier: float


class ShiftResolver:
    def __init__(self, config: dict, business_timezone: str = "Asia/Kolkata") -> None:
        self._timezone = ZoneInfo(business_timezone)
        schedules = config["shift"]["schedules"]
        multipliers = config["shift"]["workload_multiplier"]
        self._shifts = tuple(
            self._build_shift(shift_id, entry, float(multipliers[shift_id]))
            for shift_id, entry in schedules.items()
        )

    def resolve(self, event_time_utc: datetime) -> ShiftContext:
        local = event_time_utc.astimezone(self._timezone)
        for shift in self._shifts:
            start = datetime.combine(local.date(), shift.start_local, self._timezone)
            if shift.start_local <= shift.end_local:
                end = datetime.combine(local.date(), shift.end_local, self._timezone)
                if start <= local < end:
                    return ShiftContext(shift.shift_id, str(local.date()), start, end, shift.workload_multiplier)
            else:
                if local.time() >= shift.start_local:
                    end = datetime.combine(local.date(), shift.end_local, self._timezone)
                    end = end.replace(day=local.day + 1)
                    return ShiftContext(shift.shift_id, str(local.date()), start, end, shift.workload_multiplier)
                previous_date = local.date()
                start_prev = datetime.combine(previous_date, shift.start_local, self._timezone).replace(day=previous_date.day - 1)
                end_prev = datetime.combine(previous_date, shift.end_local, self._timezone)
                if start_prev <= local < end_prev:
                    return ShiftContext(shift.shift_id, str(local.date()), start_prev, end_prev, shift.workload_multiplier)
        raise ValueError(f"No shift found for event time {event_time_utc.isoformat()}")

    @staticmethod
    def _build_shift(shift_id: str, entry: dict, workload_multiplier: float) -> ShiftDefinition:
        start = time.fromisoformat(entry["start_local"])
        end = time.fromisoformat(entry["end_local"])
        return ShiftDefinition(shift_id, start, end, workload_multiplier)
