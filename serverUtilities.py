from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Optional

EXCEL_DATETIME_FORMAT = '%Y-%m-%d %H:%M:00'
BAD_UTILITY = 1000

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
        self.rooms: list[CompanyRoom] = []

    def addCompanyRoom(self, name: str, times: list[datetime], candidates: set[Attendee]) -> CompanyRoom:
        room = CompanyRoom(name, self, times, candidates)
        self.rooms.append(room)
        return room

    def wantsAttendee(self, attendee: Attendee, isCoffeeChat: bool) -> bool:
        return any(room.wantsAttendee(attendee, isCoffeeChat) for room in self.rooms)

    def getAppointmentFor(self, attendee: Optional[Attendee], appToIgnore: Appointment, isCoffeeChat: bool) -> Optional[Appointment]:
        for room in self.rooms:
            app = room.getAppointmentFor(attendee, appToIgnore, isCoffeeChat)
            if app is not None:
                return app
        return None

    def hasAttendee(self, attendee: Attendee, appToIgnore: Appointment, isCoffeeChat: bool) -> bool:
        return self.getAppointmentFor(attendee, appToIgnore, isCoffeeChat) is not None

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

    def getOtherAppAtTime(self, att: Attendee, app: Appointment) -> Optional[Appointment]:
        if att:
            for app2 in self.getOtherAppsAtTime(app):
                if app2 != app and app2.isAttendee(att):
                    return app2
        return None

    def hasOtherAppsAtTime(self, att: Attendee, app: Appointment) -> bool:
        return self.getOtherAppAtTime(att, app) is not None


class CoffeeChat(TimeInterval):
    def __init__(self, capacity: int, timeInt: TimeInterval, orderedCandidates: list[Attendee], room: CompanyRoom):
        super().__init__(timeInt.time, timeInt.length)
        self.capacity = capacity
        self.candidates = orderedCandidates
        self.candidatesSet = set(orderedCandidates)
        self.room = room
        for _ in range(capacity):
            room.appointments.append(
                CoffeeChatAppointment(room, self.time, self.length)
            )
        room.appointments.sort(key=lambda a: a.time)

    def wantsAttendee(self, attendee: Attendee) -> bool:
        return attendee is None or attendee in self.candidatesSet 

    def hasAttendee(self, attendee: Attendee) -> bool:
        return attendee in self.attendees

    def companyPref(self, att: Attendee):
        assert att in self.candidatesSet
        return self.candidates.index(att) + 1

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
            InterviewAppointment(self, time.time, time.length) for time in times
        ]
        self.coffeeChat = None

    def wantsAttendee(self, attendee: Attendee, isCoffeeChat: bool) -> bool:
        if isCoffeeChat and self.coffeeChat is None:
            return False
        elif attendee is None:
            return True
        return attendee in (self.coffeeChat.candidates if isCoffeeChat else self.candidates)

    def getAppointmentFor(self, attendee: Optional[Attendee], appToIgnore: Appointment, isCoffeeChat: bool) -> Optional[Appointment]:
        # app to ignore is an app that shouldn't be included in the appointment search,
        #   enables swapping between two apps in the same company/room
        if attendee:
            for app in self.appointments:
                if app.isAttendee(attendee) and app.isCoffeeChat() == isCoffeeChat and app != appToIgnore:
                    return app
        return None

    def hasAttendee(self, attendee: Optional[Attendee], appToIgnore: Appointment, isCoffeeChat: bool) -> bool:
        return self.getAppointmentFor(attendee, appToIgnore, isCoffeeChat) is not None

    def setCoffeeChat(self, capacity: int, timeInt: TimeInterval, orderedCndidates: list[Attendee]):
        assert(self.coffeeChat is None)
        self.coffeeChat = CoffeeChat(capacity, timeInt, orderedCndidates, self)

    def __repr__(self) -> str:
        return f"{self.company.name} - room {self.name}"

    def toJson(self) -> dict[str, Any]:
        return {
            'candidates': list([c.uid for c in self.candidates]), 
            'coffeeChat': self.coffeeChat.toJson() if self.coffeeChat else None,
            'apps': [app.toJson() for app in self.appointments]
        }
            
class Appointment(TimeInterval):

    def __init__(self, companyRoom: Company, time: datetime, length: timedelta):
        super().__init__(time, length)
        self.companyRoom: CompanyRoom = companyRoom
        self.company: Company = self.companyRoom.company
        self.attendee: Optional[Attendee] = None

    def __repr__(self):
        return f"{self.companyRoom.name}@{self.time.strftime('%b %d %H:%M')}"

    def isCoffeeChat(self) -> bool:
        raise NotImplementedError()

    def isAttendee(self, attendee) -> bool:
        return attendee != None and self.attendee == attendee

    def isEmpty(self) -> bool:
        return self.attendee == None

    # virtual method
    def getSelfUtility(self):
        if self.isEmpty():
            raise Exception("shouldn't call app.getSelfUtility() on an empty app")
        return self.attendee.getPref(self.company)

    """
    # virtual method
    def getUtility(self, att: Attendee) -> list[int]:
        if att is None:
            return [BAD_UTILITY]
        return [int(self.isCoffeeChat()), att.getPref(self.company)]
    """
    def getUtility(self, att: Attendee) -> float:
        if att is None:
            return BAD_UTILITY
        return (100*int(self.isCoffeeChat())) + att.getPref(self.company)

    def cantSwapReason(self, attendee: Attendee, appIntersects: AppointmentIntersects, appToIgnore: Appointment) -> Optional[str]:
        if attendee is not None:
            attId = attendee.uid
            timeStr = repr(TimeInterval(self.time, self.length))

            if not self.companyRoom.wantsAttendee(attendee, self.isCoffeeChat()):
                return f'Room ({self.companyRoom.name}) does not want attendee ({attId})'

            appAtTime = appIntersects.getOtherAppAtTime(attendee, self)
            if appAtTime is not None:
                return f'Attendee ({attId}) has conflicting appointments at time {timeStr}, such as {repr(appAtTime)}'
            
            breakAtTime = attendee.breakAtTime(self)
            if breakAtTime is not None:
                return f'Attendee ({attId}) has a break at the time {timeStr}, which lasts {breakAtTime}'
            
            appAtCompany = self.company.getAppointmentFor(attendee, appToIgnore, self.isCoffeeChat())
            if appAtCompany is not None:
                return f'company ({self.company.name}) already has an appointment for attendee ({attId})'
        return None

    def canSwap(self, attendee: Attendee, appIntersects: AppointmentIntersects, appToIgnore: Appointment) -> bool:
        ValidationException.throwIfFalse(self != appToIgnore)
        return attendee is None or (
            self.companyRoom.wantsAttendee(attendee, self.isCoffeeChat()) 
            and not appIntersects.hasOtherAppsAtTime(attendee, self)
            and not attendee.isBusy(self)
            and not self.company.hasAttendee(attendee, appToIgnore, self.isCoffeeChat())
        )

    def swap(self, attendee: Attendee, appIntersects: AppointmentIntersects, appToIgnore: Appointment):
        if self.canSwap(attendee, appIntersects, appToIgnore):
            self.attendee = attendee
        else:
            raise Exception('tried to swap an attendee which can\'t be swapped')

    def toJson(self) -> dict:
        return {
            'room': self.companyRoom.name,
            'att': self.attendee.uid if self.attendee is not None else None,
            'isCoffeeChat': self.isCoffeeChat(),
            **super().toJson()
        }

class InterviewAppointment(Appointment):

    # @override
    def isCoffeeChat(self) -> bool:
        return False

class CoffeeChatAppointment(Appointment):

    # @override
    def isCoffeeChat(self) -> bool:
        return True

    # @override
    def getSelfUtility(self):
        if self.isEmpty():
            raise Exception("shouldn't call app.getSelfUtility() on an empty app")
        return self.companyRoom.coffeeChat.companyPref(self.attendee)

    """
    # @override
    def getUtility(self, att: Attendee) -> list[int]:
        util = super().getUtility(att)
        if att is not None:
            companyPref = self.companyRoom.coffeeChat.companyPref(att)
            util.insert(1, companyPref)
        return util
    """
    # @override
    def getUtility(self, att: Attendee) -> int:
        if att is None:
            return BAD_UTILITY
        return (100*int(self.isCoffeeChat())) + \
            self.companyRoom.coffeeChat.companyPref(att) + \
            (0.01*att.getPref(self.company))


class CompanyPreference:

    def __init__(self, company: Company, pref: int):
        self.company = company
        self.pref = pref

    def __repr__(self) -> str:
        return f"{str(self.company.name)} = {self.pref}"


class Attendee:

    def __init__(self, uid: int, name: str, prefs: list[CompanyPreference], commitments: list[TimeInterval]):
        self.uid = uid
        self.name = name
        prefs.sort(key = lambda ap: -ap.pref)
        self.prefsLst = prefs
        self.prefsDic = {p.company:p.pref for p in prefs}
        self.commitments = commitments

    def getPref(self, company) -> int:
        return self.prefsDic[company]

    def __repr__(self) -> str:
        return str(self.uid)

    def breakAtTime(self, timeInterval: TimeInterval) -> TimeInterval:
        for commit in self.commitments:
            if commit.isIntersecting(timeInterval):
                return commit

    def isBusy(self, timeInterval: TimeInterval) -> bool:
        return self.breakAtTime(timeInterval) is not None

    def getNoCompaniesWant(self, companies: list[Company], isCoffeeChat: Optional[bool]) -> int:
        return len([c for c in companies if c.wantsAttendee(self, isCoffeeChat)])

    def toJson(self):
        return {
            'name': self.name,
            'commitments': [c.toJson() for c in self.commitments],
            'prefs': {c.name:p for c,p in self.prefsDic.items()}
        }

def getJsonSchedule(companies: list[Company], attendees: list[Attendee], conventionTimes: list[TimeInterval]) -> dict:
    totalRanks, noApps, noAppsChosen, noAtts, varNoApps = getScheduleMetrics(companies)
    
    return {
        'companies': {c.name: c.toJson() for c in companies},
        'attendees': {a.uid: a.toJson() for a in attendees},
        'conventionTimes': [t.toJson() for t in conventionTimes],
        'totalUtility': totalRanks,
        'noAppointments': noApps,
        'noAppointmentsNotEmpty': noAppsChosen,
        'noAttendeeesChosen': noAtts,
        'varNoAppointments': varNoApps
    }
    
def getUtility(companies: list[Company]):
    return sum(sum([app.getSelfUtility() for app in c.getAppointments() if not app.isEmpty()]) for c in companies)

def getScheduleMetrics(companies: list[Company]) -> tuple[int, int, int, int]:
    ranks = []
    noApps = 0
    attToNoApps = {}

    for company in companies:
        for app in company.getAppointments():
            noApps += 1
            if app.isEmpty():
                continue
            att = app.attendee
            attToNoApps[att] = attToNoApps.get(att, 0) + 1
            ranks.append(att.getPref(company))
    
    noAppsLst = list(attToNoApps.values())
    avgNoApps = sum(noAppsLst) / len(noAppsLst)
    varNoApps = sum((x - avgNoApps)**2 for x in noAppsLst) / len(noAppsLst)

    return (
        sum(ranks),
        noApps,
        sum(noAppsLst),
        len(attToNoApps.keys()),
        varNoApps
    )
    

def canSwapBoth(app1, att1, app2, att2, appIntersects):
    assert(not(app1 is None and app2 is None))
    return (
        (app2 is None or app2.canSwap(att1, appIntersects, app1))
        and (app1 is None or app1.canSwap(att2, appIntersects, app2))
    )

def trySwapBoth(app1, att1, app2, att2, appIntersects) -> bool:
    canSwap = canSwapBoth(app1, att1, app2, att2, appIntersects)
    if canSwap:
        if app2:
            app2.swap(att1, appIntersects, app1)
        if app1:
            app1.swap(att2, appIntersects, app2)
    return canSwap

def swapBoth(app1, att1, app2, att2, appIntersects):
    assert(trySwapBoth(app1, att1, app2, att2, appIntersects))

def getAttUtility(app: Optional[Appointment], att: Optional[Attendee]) -> list[int]:
    #return app.getUtility(att) if app else [BAD_UTILITY]
    return app.getUtility(att) if app else BAD_UTILITY
    #return att.prefsDic[app.company] + (16 * int(app.isCoffeeChat())) if app and att else 1000
    # why 1000 and not infinity? 
    # because if we are comparing two options,
    # sum(5, 1000) can be compared to sum(10, 1000)
    # but sum(5, inf) is the same as sum(10, inf)
    # it's important to pick a value s.t. minPref + 1000 > 2*maxPref,
    #   so that it is always more preferable to match two people than one

def shouldSwap(app1, att1, app2, att2, appIntersects) -> bool:
    if not canSwapBoth(app1, att1, app2, att2, appIntersects):
        return False
    currentUtil = getAttUtility(app1, att1) + getAttUtility(app2, att2)
    swapUtil = getAttUtility(app1, att2) + getAttUtility(app2, att1)
    return swapUtil < currentUtil # strictly less than

def getNoApps(companies: list[Company]) -> int:
    return sum(len(c.getAppointments()) for c in companies)

def getNoNotEmptyApps(companies: list[Company]) -> int:
    return sum([len([a for a in c.getAppointments() if not a.isEmpty()]) for c in companies])
