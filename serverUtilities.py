from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Optional

EXCEL_DATETIME_FORMAT = '%Y-%m-%d %H:%M:00'

class ValidationException(Exception):
    
    @staticmethod
    def throwIfFalse(cond: bool, msg: str = ''):
        if not cond:
            raise ValidationException(msg)

def timesIntersect(time1: datetime, length1: timedelta, time2: datetime, length2: timedelta):
    latestStart = max(time1, time2)
    earliestEnd = min(time1 + length1, time2 + length2)
    return latestStart < earliestEnd

TimeIntervalHash = tuple[datetime, datetime]

class TimeInterval:

    def __init__(self, time: datetime, length: timedelta):
        self.time = time
        self.length = length
        self.end = self.time + self.length
        self.timeHash: TimeIntervalHash = (self.time, self.end)
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


class Company:

    def __init__(self, name: str):
        self.name = name
        self.rooms = []

    def addCompanyRoom(self, name: str, times: list[datetime], candidates: set[Attendee]) -> CompanyRoom:
        room = CompanyRoom(name, self, times, candidates)
        self.rooms.append(room)
        return room

    def wantsAttendee(self, attendee: Attendee, isCoffeeChat: bool) -> bool:
        return any(room.wantsAttendee(attendee, isCoffeeChat) for room in self.rooms)

    def hasAttendee(self, attendee: Attendee, appToIgnore: Appointment, isCoffeeChat: bool) -> bool:
        return any(room.hasAttendee(attendee, appToIgnore, isCoffeeChat) for room in self.rooms)

    def getAppointments(self) -> list[Appointment]:
        apps = []
        for room in self.rooms:
            apps.extend(room.appointments)
        return apps

    def __repr__(self) -> str:
        return self.name

    def toJson(self) -> list:
        return {r.name: r.toJson() for r in self.rooms}

class AppointmentIntersects:

    def __init__(self, companies: list[Company]):
        self.appsAtTime = self.getAppsAtTimes(companies)

    @staticmethod
    def getAppsAtTimes(companies: list[Company]) -> dict[TimeIntervalHash, set[Appointment]]:

        def getAppsAtTime(app: Appointment) -> set[Appointment]:
            overlapping = set()
            for c in companies:
                for app2 in c.getAppointments():
                    if app.isIntersecting(app2):
                        overlapping.add(app2)
            return overlapping

        appsAtTime = {}
        for c in companies:
            for app in c.getAppointments():
                if app.timeHash not in appsAtTime:
                    appsAtTime[app.timeHash] = getAppsAtTime(app)
        return appsAtTime

    def getOtherAppsAtTime(self, app):
        appsAtTime = self.appsAtTime[app.timeHash]
        return appsAtTime - {app}

    def hasOtherAppsAtTime(self, att: Attendee, app: Appointment) -> bool:
        if att:
            for app2 in self.getOtherAppsAtTime(app):
                if app2 != app and app2.isAttendee(att):
                    return True
        return False


class CoffeeChat(TimeInterval):
    def __init__(self, capacity: int, timeInt: TimeInterval, candidates: set[Attendee], room: CompanyRoom):
        super().__init__(timeInt.time, timeInt.length)
        self.capacity = capacity
        self.candidates = candidates
        self.room = room
        for _ in range(capacity):
            room.appointments.append(
                Appointment(room, self.time, self.length, isCoffeeChat=True)
            )
        room.appointments.sort(key=lambda a: a.time)

    def wantsAttendee(self, attendee: Attendee) -> bool:
        return attendee is None or attendee in self.candidates 

    def hasAttendee(self, attendee: Attendee) -> bool:
        return attendee in self.attendees

    def toJson(self) -> dict:
        return {
            "capacity": self.capacity,
            "candidates": [a.uid for a in self.candidates],
            **super().toJson()
        }

class CompanyRoom:

    def __init__(
        self, 
        name: str, 
        company: Company, 
        times: list[datetime], 
        candidates: set[Attendee]
     ):
        self.name = name
        self.company = company
        self.times = times
        self.candidates = candidates
        self.appointments = [
            Appointment(self, time.time, time.length) for time in times
        ]
        self.coffeeChat = None

    def wantsAttendee(self, attendee: Attendee, isCoffeeChat: bool) -> bool:
        if isCoffeeChat and self.coffeeChat is None:
            return False
        elif attendee is None:
            return True
        return attendee in (self.coffeeChat.candidates if isCoffeeChat else self.candidates)

    def hasAttendee(self, attendee: Attendee, appToIgnore: Appointment, isCoffeeChat: bool) -> bool:
        if attendee:
            for app in self.appointments:
                if app.isAttendee(attendee) and app.isCoffeeChat == isCoffeeChat and app != appToIgnore:
                    return True
        return False       

    def setCoffeeChat(self, capacity: int, timeInt: TimeInterval, candidates: set[Attendee]):
        assert(self.coffeeChat is None)
        self.coffeeChat = CoffeeChat(capacity, timeInt, candidates, self)

    def __repr__(self) -> str:
        return f"{self.company.name} - room {self.name}"

    def toJson(self) -> dict[str, Any]:
        return {
            'candidates': list([c.uid for c in self.candidates]), 
            'coffeeChat': self.coffeeChat.toJson() if self.coffeeChat else None,
            'apps': [app.toJson() for app in self.appointments]
        }
            
class Appointment(TimeInterval):

    def __init__(self, companyRoom: Company, time: datetime, length: timedelta, isCoffeeChat=False):
        super().__init__(time, length)
        self.companyRoom = companyRoom
        self.company: Company = self.companyRoom.company
        self.attendee = None
        self.isCoffeeChat = isCoffeeChat

    def __repr__(self):
        return f"{self.company.name}-{self.companyRoom.name}@{self.time.strftime('%b %d %H:%M')}"

    def isAttendee(self, attendee):
        return attendee != None and self.attendee == attendee

    def isEmpty(self):
        return self.attendee == None

    def getUtility(self):
        return self.attendee.getPref(self.company) if not self.isEmpty() else 0

    def cantSwapReason(self, attendee: Attendee, appIntersects: AppointmentIntersects, appToIgnore: Appointment) -> Optional[str]:
        if attendee is not None:
            attId = attendee.uid
            timeStr = repr(TimeInterval(self.time, self.length))

            if not self.companyRoom.wantsAttendee(attendee, self.isCoffeeChat):
                return f'Room ({self.companyRoom.name}) does not want attendee ({attId})'
            if appIntersects.hasOtherAppsAtTime(attendee, self):
                return f'Attendee ({attId}) has other apps at time {timeStr}'
            if attendee.isBusy(self):
                return f'Attendee ({attId}) has a break at time {timeStr}'
            if self.company.hasAttendee(attendee, appToIgnore, self.isCoffeeChat):
                return f'company ({self.company.name}) already has an appointment for attendee ({attId})'
        return None

    def canSwap(self, attendee: Attendee, appIntersects: AppointmentIntersects, appToIgnore: Appointment) -> bool:
        ValidationException.throwIfFalse(self != appToIgnore)
        return attendee is None or (
            self.companyRoom.wantsAttendee(attendee, self.isCoffeeChat) 
            and not appIntersects.hasOtherAppsAtTime(attendee, self)
            and not attendee.isBusy(self)
            and not self.company.hasAttendee(attendee, appToIgnore, self.isCoffeeChat)
        )

    def swap(self, attendee: Attendee, appToAppsAtTime: dict[Appointment, set[Appointment]], appToIgnore: Appointment):
        if self.canSwap(attendee, appToAppsAtTime, appToIgnore):
            self.attendee = attendee
        else:
            raise Exception('tried to swap an attendee which can\'t be swapped')

    def toJson(self) -> dict:
        return {
            'room': self.companyRoom.name,
            'att': self.attendee.uid if self.attendee is not None else None,
            'isCoffeeChat': self.isCoffeeChat,
            **super().toJson()
        }

class CompanyPreference:

    def __init__(self, company: Company, pref: int):
        self.company = company
        self.pref = pref

    def __repr__(self) -> str:
        return f"{str(self.company.name)} = {self.pref}"


class Attendee:

    def __init__(self, uid: int, prefs: list[CompanyPreference], commitments: list[TimeInterval]):
        self.uid = uid
        prefs.sort(key = lambda ap: -ap.pref)
        self.prefsLst = prefs
        self.prefsDic = {p.company:p.pref for p in prefs}
        self.commitments = commitments

    def getPref(self, company) -> int:
        return self.prefsDic[company]

    def __repr__(self) -> str:
        return str(self.uid)

    def isBusy(self, timeInterval: TimeInterval) -> bool:
        return any(commit.isIntersecting(timeInterval) for commit in self.commitments)

    def getNoCompaniesWant(self, companies: list[Company], isCoffeeChat: bool) -> int:
        return len([c for c in companies if c.wantsAttendee(self, isCoffeeChat)])

    def toJson(self):
        return {
            'commitments': [c.toJson() for c in self.commitments],
            'prefs': {c.name:p for c,p in self.prefsDic.items()}
        }

def getJsonSchedule(companies: list[Company], attendees: list[Attendee], interviewTimes: list[TimeInterval]) -> dict:
    return {
        'companies': {c.name: c.toJson() for c in companies},
        'attendees': {a.uid: a.toJson() for a in attendees},
        'interviewTimes': [t.toJson() for t in interviewTimes],
        'totalUtility': getUtility(companies),
        'noAppointments': getNoApps(companies),
        'noAttendeesChosen': getNoNotEmptyApps(companies) 
    }
    
def getUtility(companies: list[Company]):
    return sum(sum([app.getUtility() for app in c.getAppointments()]) for c in companies)

def canSwapBoth(app1, att1, app2, att2, appIntersects):
    assert(not(app1 is None and app2 is None))
    return (
        (app2 is None or app2.canSwap(att1, appIntersects, app1))
        and (app1 is None or app1.canSwap(att2, appIntersects, app2))
    )

def swapBoth(app1, att1, app2, att2, appIntersects):
    assert(canSwapBoth(app1, att1, app2, att2, appIntersects))
    if app2:
        app2.swap(att1, appIntersects, app1)
    if app1:
        app1.swap(att2, appIntersects, app2)

def getAttUtility(app, att) -> int:
    return att.prefsDic[app.company] if app and att else 1000
    # why 1000 and not infinity? because if we are comparing two options,
    # sum(5, 1000) can be compared to sum(10, 1000)
    # but sum(5, inf) is the same as sum(10, inf)
    # it's important to pick a value s.t. minPref + 1000 > 2*maxPref,
    #   so that it is always more preferable to match two people than one

def shouldSwap(app1, att1, app2, att2, appIntersects) -> bool:
    canSwap = canSwapBoth(app1, att1, app2, att2, appIntersects)
    currentUtil = getAttUtility(app1, att1) + getAttUtility(app2, att2)
    swapUtil = getAttUtility(app1, att2) + getAttUtility(app2, att1)
    return canSwap and swapUtil < currentUtil # strictly less than

def getNoApps(companies: list[Company]) -> int:
    return sum(len(c.getAppointments()) for c in companies)

def getNoNotEmptyApps(companies: list[Company]) -> int:
    return sum([len([a for a in c.getAppointments() if not a.isEmpty()]) for c in companies])
