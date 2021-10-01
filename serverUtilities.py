from __future__ import annotations
from datetime import datetime, timedelta

class ValidationException(Exception):
    
    @staticmethod
    def throwIfFalse(cond: bool, msg: str = ''):
        if not cond:
            raise ValidationException(msg)

def timesIntersect(time1: datetime, length1: timedelta, time2: datetime, length2: timedelta):
    latestStart = max(time1, time2)
    earliestEnd = min(time1 + length1, time2 + length2)
    return latestStart < earliestEnd

class TimeInterval:

    def __init__(self, time: datetime, length: timedelta):
        self.time = time
        self.length = length
        self.end = self.time + self.length
        assert self.time < self.end

    def isIntersecting(self, timeInterval: TimeInterval) -> bool:
        return timesIntersect(self.time, self.length, timeInterval.time, timeInterval.length)

    def contains(self, timeInterval: TimeInterval) -> bool:
        return self.time <= timeInterval.time and timeInterval.end <= self.end

    def __repr__(self) -> str:
        return (
            f"{self.time.strftime('%b %d')}: "
            + f"[{self.time.strftime('%H:%M')},{(self.length + self.time).strftime('%H:%M')}]"
        )

    @staticmethod
    def fromStr(startStr: str, endStr: str) -> TimeInterval:
        try:
            d1, d2 = [datetime.fromisoformat(d) for d in (startStr, endStr)]
        except ValueError:
            raise ValidationException(f"invalid iso format dates: '{startStr}' and '{endStr}'")
        ValidationException.throwIfFalse(
            d1 < d2,
            f"invalid dates: start date ({d1}) is not smaller than end date ({d2})"
        )
        return TimeInterval(d1, d2-d1)    

    def toJson(self) -> dict:
        return {'start': self.time.isoformat(), 'end': self.end.isoformat()}    
