from __future__ import annotations
from datetime import datetime, timedelta
from typing import Callable
from os.path import exists
from serverUtilities import ValidationException, TimeInterval
from Schema import *
import cProfile

""" 
============
love u rach!
============
"""

def getLines(doc: str) -> list[str]:
    return [l for l in [line.strip().strip('\ufeff') for line in doc.split('\n')[1:]] if l]

def getCols(doc: str, noCols: int, throwIfEmpty: bool) -> list[list[str]]:
    cols = [l.split(',') for l in getLines(doc)]
    ValidationException.throwIfFalse(
        all(len(x)==noCols for x in cols),
        f"invalid csv: must have exactly {noCols} column(s)"
    )
    if throwIfEmpty:
        ValidationException.throwIfFalse(
            0 < len(cols),
            'table cannot be empty'
        )
    return cols

def getFileContents(fn: str) -> str:
    ValidationException.throwIfFalse(
        exists(fn), f"invalid file name ({fn}): does not exist"
    )
    with open(fn, 'r', encoding='utf-8') as f:
        return f.read()

def parseJsonSchedule(data: dict) -> tuple[
            list[Attendee], 
            list[Company], 
            list[TimeInterval],
            Optional[Appointment], 
            Optional[Attendee], 
            Optional[Appointment], 
            Optional[Attendee]
        ]:

    attendeesJson, companiesJson = data['attendees'], data['companies']
    app1Json, att1Id, app2Json, att2Id = [data[k] for k in ['app1', 'att1', 'app2', 'att2']]

    interviewTimes = [TimeInterval.fromStr(t['start'], t['end']) for t in data['interviewTimes']]

    companyNameToCompany = {}
    for companyName in companiesJson.keys():
        companyNameToCompany[companyName] = Company(companyName)

    attendeeIdToAttendee = {}
    for attIdStr, attendeeJson in attendeesJson.items():
        attId = int(attIdStr)
        prefs = [
            CompanyPreference(companyNameToCompany[companyName], pref)
            for companyName, pref in attendeeJson['prefs'].items()
        ]
        commitments = [TimeInterval.fromStr(c['start'], c['end']) for c in attendeeJson['commitments']]
        attendeeIdToAttendee[attId] = Attendee(attId, prefs, commitments)

    for companyName, company in companyNameToCompany.items():
        for roomName, roomJson in companiesJson[companyName].items():
            times = [TimeInterval.fromStr(app['start'], app['end']) for app in roomJson['apps']]
            candidates = [attendeeIdToAttendee[attId] for attId in roomJson['candidates']]
            company.addCompanyRoom(roomName, times, candidates)

            assert(len(roomJson['apps']) == len(company.rooms[-1].appointments))
            for i in range(len(roomJson['apps'])):
                att = roomJson['apps'][i]['att']
                if att is not None:
                    company.rooms[-1].appointments[i].attendee = attendeeIdToAttendee[att]

    def getApp(appJson: dict) -> Optional[Appointment]:
        if appJson is None:
            return None

        for company in companyNameToCompany.values():
            for room in company.rooms:
                if room.name == appJson['room']:
                    for app in room.appointments:
                        if app.time == datetime.fromisoformat(appJson['start']):
                            # datetime equality does not need to be the same object
                            return app
        raise ValidationException('what the hey?')

    getAttId = lambda attId: attendeeIdToAttendee[attId] if attId is not None else None

    att1, att2 = [getAttId(attId) for attId in (att1Id, att2Id)]
    app1, app2 = [getApp(j) for j in [app1Json, app2Json]]
    ValidationException.throwIfFalse(att1 != att2)
    ValidationException.throwIfFalse(
        all(
            app is None or app.attendee == att 
            for app,att in ((app1, att1), (app2, att2))
        ),
        'if app and att is defined, app.att = att must be true'
    )
    ValidationException.throwIfFalse(
        all(
            not(app is None and att is None)
            for app,att in ((app1, att1), (app2, att2))
        ),
        'it must not be the case that app and att are None'
    )
    ValidationException.throwIfFalse(
        any(att is not None for att in (att1, att2)),
        'must be at least one att'
    )

    return (
        list(companyNameToCompany.values()),
        list(attendeeIdToAttendee.values()), 
        interviewTimes,
        app1, 
        att1, 
        app2, 
        att2
    )


class Company:

    def __init__(self, name: str):
        self.name = name
        self.rooms = []

    def addCompanyRoom(self, name: str, times: list[datetime], candidates: list[Attendee]):
        self.rooms.append(CompanyRoom(name, self, times, candidates))
        return self

    def wantsAttendee(self, attendee: Attendee) -> bool:
        return any(room.wantsAttendee(attendee) for room in self.rooms)

    def hasAttendee(self, attendee: Attendee) -> bool:
        return any(room.hasAttendee(attendee) for room in self.rooms)

    def getAppointments(self) -> list[Appointment]:
        apps = []
        for room in self.rooms:
            apps.extend(room.appointments)
        return apps

    def __repr__(self) -> str:
        return self.name

    def toJson(self) -> list:
        return {r.name: r.toJson() for r in self.rooms}


def hasOtherAppsAtTime(att: Attendee, timeInt: TimeInterval) -> bool:
    if att:
        for c in [c for c in companies if c.wantsAttendee(att)]:
            for app in c.getAppointments():
                if app.isAttendee(att) and timeInt.isIntersecting(app):
                    return True
    return False


def hasOtherAppsAtTimeCached(att: Attendee, app2: Appointment, overlappingAppCache: dict[Appointment][set[Appointment]]) -> bool:
    if att:
        for app in overlappingAppCache[app2]:
                if app.isAttendee(att) and app2.isIntersecting(app):
                    return True
    return False

class CompanyRoom:

    def __init__(self, name: str, company: Company, times: list[datetime], candidates: list[Attendee]):
        self.name = name
        self.company = company
        self.times = times
        self.candidates = set(candidates)
        self.appointments = [
            Appointment(self, time.time, time.length) for time in times
        ]

    def wantsAttendee(self, attendee: Attendee) -> bool:
        return attendee is None or attendee in self.candidates 

    def hasAttendee(self, attendee: Attendee) -> bool:
        if attendee:
            for app in self.appointments:
                if app.isAttendee(attendee):
                    return True
        return False       

    def __repr__(self) -> str:
        return f"{self.company.name} - room {self.name}"

    def toJson(self) -> dict[str, Any]:
        return {
            'candidates': list([c.uid for c in self.candidates]), 
            'apps': [app.toJson() for app in self.appointments]
        }
            
class Appointment(TimeInterval):

    def __init__(self, companyRoom: Company, time: datetime, length: timedelta):
        super().__init__(time, length)
        self.companyRoom = companyRoom
        self.company = self.companyRoom.company
        self.attendee = None

    def __repr__(self):
        return f"{self.company.name}-{self.companyRoom.name}@{self.time.strftime('%b %d %H:%M')}"

    def isAttendee(self, attendee):
        return attendee != None and self.attendee == attendee

    def isEmpty(self):
        return self.attendee == None

    def getUtility(self):
        return self.attendee.getPref(self.company) if not self.isEmpty() else 0

    def cantSwapReason(self, attendee: Attendee, overlappingAppCache: dict[Appointment, set[Appointment]]) -> Optional[str]:
        if attendee is not None:
            attId = attendee.uid
            timeStr = repr(TimeInterval(self.time, self.length))

            if not self.companyRoom.wantsAttendee(attendee):
                return f'Room ({self.companyRoom.name}) does not want attendee ({attId})'
            if hasOtherAppsAtTimeCached(attendee, self, overlappingAppCache):
                return f'Attendee ({attId}) has other apps at time ({timeStr})'
            if attendee.isBusy(self):
                return f'Attendee ({attId}) has a break at time ({timeStr})'
            if self.company.hasAttendee(attendee):
                return f'company ({self.company.name}) already has an appointment for attendee ({attId})'
        return None

    def canSwap(self, attendee: Attendee, overlappingAppCache: dict[Appointment, set[Appointment]]) -> bool:
        return attendee is None or (
            self.companyRoom.wantsAttendee(attendee) 
            and not hasOtherAppsAtTimeCached(attendee, self, overlappingAppCache)
            and not attendee.isBusy(self)
            and not self.company.hasAttendee(attendee)
        )

    def swap(self, attendee: Attendee, overlappingAppCache: dict[Appointment, set[Appointment]]):
        if self.canSwap(attendee, overlappingAppCache):
            self.attendee = attendee
        else:
            raise Exception('tried to swap an attendee which can\'t be swapped')

    def toJson(self) -> dict:
        return {
            'room': self.companyRoom.name,
            'att': self.attendee.uid if self.attendee is not None else None,
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

    def toJson(self):
        return {
            'commitments': [c.toJson() for c in self.commitments],
            'prefs': {c.name:p for c,p in self.prefsDic.items()}
        }

def readInterviewTimes(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(INTERVIEWTIME_TABLE)
    interviewTimes = []

    for start,end in getCols(doc, 2, True):
        interval = TimeInterval.fromStr(start, end)

        ValidationException.throwIfFalse(
            not any(interval.isIntersecting(t) for t in interviewTimes), 
            f"invalid interview day: interview day {interval} intersects with other intervals {interviewTimes}"
        )
        interviewTimes.append(interval)
        AddInterviewTime(cursor, interval)

#companyNames = set()
def readCompanyNames(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(COMPANY_TABLE)

    companyNames = set()
    for (name,) in getCols(doc, 1, True):
        ValidationException.throwIfFalse(
            name not in companyNames, 
            f"duplicate company name ({name})"
        )
        companyNames.add(name)
        AddCompany(cursor, name)

def readRoomNames(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ROOM_TABLE)

    interviewTimes = GetInterviewTimes(cursor)
    companyNames = GetCompanies(cursor)
    roomNames = set()

    for companyName,roomName,length,startStr,endStr in getCols(doc, 5, True):
        interval = TimeInterval.fromStr(startStr, endStr)

        ValidationException.throwIfFalse(
            companyName in companyNames, 
            f"invalid company name ({companyName})"
        )
        ValidationException.throwIfFalse(
            roomName not in roomNames, 
            f"room name ({roomName}) not unique"
        )
        roomNames.add(roomName)
        ValidationException.throwIfFalse(
            length.isdigit and 0 < int(length), 
            f"invalid length ({length}), must be positive integer"
        )
        ValidationException.throwIfFalse(
            any(interval.isIntersecting(d) for d in interviewTimes), 
            f"invalid interval: break at {interval} does not intersect with interview times: {interviewTimes}"
        )
        AddRoom(cursor, companyName, roomName, int(length), interval)

def readRoomBreaks(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ROOMBREAKS_TABLE)

    interviewTimes = GetInterviewTimes(cursor)
    roomIntervals = GetRoomIntervals(cursor)
    companyRoomNames = GetRooms(cursor)
    
    companyRoomBreaks = {}
    for roomNames in companyRoomNames.values():
        for roomName in roomNames:
            companyRoomBreaks[roomName] = []

    for roomName,startStr,endStr in getCols(doc, 3, False):
        b = TimeInterval.fromStr(startStr, endStr)

        ValidationException.throwIfFalse(
            roomName in companyRoomBreaks, 
            f"invalid room name ({roomName})"
        )
        ValidationException.throwIfFalse(
            any(d.contains(b) for d in interviewTimes), 
            f"invalid break: break at {b} does not intersect with interview times: {interviewTimes}"
        )
        ValidationException.throwIfFalse(
            roomIntervals[roomName].contains(b),
            f"invalid break: break at {b} does not intersect with room time: {roomIntervals[roomName]}"
        )
        ValidationException.throwIfFalse(
            all(not b.isIntersecting(b2) for b2 in companyRoomBreaks.get(roomName, [])),
            f"invalid break: break at {b} intersects with one of the other breaks {companyRoomBreaks[roomName]}"
        )

        companyRoomBreaks[roomName].append(b)
        AddRoomBreak(cursor, roomName, b)
     
def readAttendeeNames(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ATTENDEES_TABLE)

    attendeeIDs = set()

    for (attendeeID,) in getCols(doc, 1, True):
        ValidationException.throwIfFalse(
            attendeeID not in attendeeIDs,
            f"duplicate attendee ID ({attendeeID})"
        )
        attendeeIDs.add(attendeeID)
        AddAttendee(cursor, attendeeID)

def readAttendeeBreaks(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ATTENDEEBREAKS_TABLE)

    interviewTimes = GetInterviewTimes(cursor)
    attendeeIDs = GetAttendees(cursor)

    attendeeBreaks = {a: [] for a in attendeeIDs}

    for attendeeID,startStr,endStr in getCols(doc, 3, False):
        attendeeID = int(attendeeID)
        b = TimeInterval.fromStr(startStr, endStr)

        ValidationException.throwIfFalse(
            attendeeID in attendeeIDs,
            f"invalid attendee ID ({attendeeID})"
        )
        ValidationException.throwIfFalse(
            any(d.contains(b) for d in interviewTimes),
            f"invalid break: break at {b} does not intersect with interview times: {interviewTimes}"
        )
        ValidationException.throwIfFalse(
            all(not b.isIntersecting(b2) for b2 in attendeeBreaks[attendeeID]),
            f"invalid break: break at {b} intersects with one of the other breaks {attendeeBreaks[attendeeID]}"
        )
        attendeeBreaks[int(attendeeID)].append(b)
        AddAttendeeBreak(cursor, attendeeID, b)

def readAttendeePrefs(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ATTENDEEPREFS_TABLE)

    companyNames = GetCompanies(cursor)
    attendeeIDs = GetAttendees(cursor)

    attendeePreferences = {a: {} for a in attendeeIDs}
    for attendeeID,companyName,pref in getCols(doc, 3, False):
        attendeeID = int(attendeeID)
        ValidationException.throwIfFalse(
            attendeeID in attendeeIDs,
            f"invalid attendee ID ({attendeeID})"
        )
        ValidationException.throwIfFalse(
            companyName in companyNames,
            f"invalid company name ({companyName})"
        )
        ValidationException.throwIfFalse(
            companyName not in attendeePreferences[attendeeID],
            f"duplicate company preference for attendee '{attendeeID}' for company '{companyName}'"
        )
        ValidationException.throwIfFalse(
            str.isdigit(pref) and 0 <= int(pref),
            f"invalid preference ({pref}), must be non-negative integer"
        )
        attendeePreferences[attendeeID][companyName] = int(pref)
        AddAttendeePref(cursor, attendeeID, companyName, pref)

#roomCandidates = {a: set() for a in roomNames}
def readRoomCandidates(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ROOMCANDIDATES_TABLE)

    companyRoomNames = GetRooms(cursor)
    attendeeIDs = GetAttendees(cursor)
    
    roomCandidates = {}
    for roomNames in companyRoomNames.values():
        for roomName in roomNames:
            roomCandidates[roomName] = []

    for roomName,attendeeId in getCols(doc, 2, True):
        attendeeId = int(attendeeId)

        ValidationException.throwIfFalse(
            attendeeId in attendeeIDs,
            f"invalid attendee ID ({attendeeId})"
        )
        ValidationException.throwIfFalse(
            any((roomName in roomNames) for roomNames in companyRoomNames.values()),
            f"invalid room name ({roomName})"
        )
        ValidationException.throwIfFalse(
            attendeeId not in roomCandidates[roomName],
            f"duplicate attendee for room candidate ({roomName})"
        )
        roomCandidates[roomName].append(attendeeId)
        AddRoomCandidate(cursor, roomName, attendeeId)

    ValidationException.throwIfFalse(
        any(0 < len(atts) for atts in roomCandidates.values()),
        'no room candidates'
    )

def getSomeTimes(interviewTimes: list[TimeInterval], mins: int, breaks: list[TimeInterval], interval: TimeInterval) -> list[TimeInterval]:
    times = []

    for timeInt in [t for t in interviewTimes if t.isIntersecting(interval)]:
        startTime = max(timeInt.time, interval.time) # start time in secs
        endTime = min(timeInt.end, interval.end)

        newTime = startTime
        # loop invariant: $newTimeInt.end <= $endTime
        while True:
            # create a new TimeInterval starting at $newTime, lasting for $mins
            newTimeInt = TimeInterval(newTime, timedelta(minutes = mins))

            # if the new time is out of bounds, stop early
            if endTime < newTimeInt.end:
                break
            
            # $newTime should be moved to the new latest time...
            newTime = newTimeInt.end
            isOnBreak = False
            for b in breaks:
                if newTimeInt.isIntersecting(b):
                    # ...however, if it intersects with a break, 
                    #   move $time to the end of the break
                    isOnBreak = True
                    newTime = b.end
                    break

            if not isOnBreak:
                times.append(newTimeInt)
    return times


def setAttendeeAndCompanies(cursor: SqliteDB, companies: list[Company], attendees: list[Attendee]):
    interviewTimes = GetInterviewTimes(cursor)
    companyNames = GetCompanies(cursor) 
    companyRoomNames = GetRooms(cursor)
    roomLengths = GetRoomLengths(cursor)
    roomIntervals = GetRoomIntervals(cursor)
    roomBreaks= GetRoomBreaks(cursor)
    attendeeIds = GetAttendees(cursor)
    attendeePrefs = GetAttendeePrefs(cursor)
    attendeeBreaks = GetAttendeeBreaks(cursor)
    roomCandidates = GetRoomCandidates(cursor)

    mandatoryTables = [
        (interviewTimes, 'Interview Times'),
        (companyNames, 'Company Names'),
        (companyRoomNames, 'Rooms'),
        (roomLengths, 'Rooms'),
        (roomIntervals, 'Rooms'),
        (attendeeIds, 'Attendees'),
        (roomCandidates, 'Room Candidates')
    ]

    for table, tableName in mandatoryTables:
        ValidationException.throwIfFalse(
            0 < len(table),
            f'a mandatory table ({tableName}) is empty'
        )

    companyNameToCompany = {name:Company(name) for name in companyNames}
    for company in companyNameToCompany.values():
        companies.append(company)

    attendeeIDToAttendee = {}
    for attId in attendeeIds:
        prefs = []
        for companyName in companyNameToCompany:
            pref = attendeePrefs.get(attId, {}).get(companyName, 0)
            prefs.append(CompanyPreference(companyNameToCompany[companyName], pref))
        
        att = Attendee(attId, prefs, attendeeBreaks.get(attId, []))
        attendeeIDToAttendee[attId] = att
        attendees.append(att)

    for companyName,roomNames in companyRoomNames.items():
        for roomName in roomNames:
            company = companyNameToCompany[companyName]
            interval = roomIntervals[roomName]
            times = getSomeTimes(interviewTimes, roomLengths[roomName], roomBreaks.get(roomName, []), interval)
            company.addCompanyRoom(
                roomName,
                times, 
                [attendeeIDToAttendee[attId] for attId in roomCandidates.get(roomName,[])]
            )

getTime = lambda day, hour, minute: day + timedelta(hours=hour, minutes=minute)

def getJsonSchedule(companies: list[Company], attendees: list[Attendee], interviewTimes: list[TimeInterval], totalUtility: int, noApps: int, noAttsChosen: int):
    return {
        'companies': {c.name: c.toJson() for c in companies},
        'attendees': {a.uid: a.toJson() for a in attendees},
        'interviewTimes': [t.toJson() for t in interviewTimes],
        'totalUtility': totalUtility,
        'noAppointments': noApps,
        'noAttendeesChosen': noAttsChosen 
    }

def trySwap(
            companies: list[Company], 
            attendees: list[Attendee], 
            interviewTimes: list[TimeInterval],
            app1: Optional[Appointment], 
            att1: Optional[Attendee], 
            app2: Optional[Appointment], 
            att2: Optional[Attendee]
        ):
        
    print("start:", datetime.now().strftime("%H:%M:%S"))
    chosenAttendees = [
        a for a in attendees 
        if any(c.wantsAttendee(a) for c in companies)
    ]

    def getUtility():
        return sum(sum([app.getUtility() for app in c.getAppointments()]) for c in companies)

    noApps = sum(len(c.getAppointments()) for c in companies)

    def getOverlappingAppsForApp(companies: list[Company], app: Appointment, cache: dict[Appointment, set[Appointment]]) -> set[Appointment]:
        overlapping = set()
        for c in companies:
            for app2 in c.getAppointments():
                cond = app in cache[app2] if app2 in cache else app.isIntersecting(app2)
                #cond = app.isIntersecting(app2) 
                if app != app2 and cond:
                    overlapping.add(app2)
        return overlapping

    def getOverlappingApps(companies: list[Company]) -> dict[Appointment, set[Appointment]]:
        cache = {}
        for c in companies:
            for app in c.getAppointments():
                cache[app] = getOverlappingAppsForApp(companies, app, cache)
        return cache

    print('getOverlappingApps')
    print("\tstart:", datetime.now().strftime("%H:%M:%S"))
    overlappingAppCache = getOverlappingApps(companies)
    print("\tstop:", datetime.now().strftime("%H:%M:%S"))
    print('')

    def canSwapBoth(app1, att1, app2, att2):
        assert(not(app1 is None and app2 is None))
        return (
            (app2 is None or app2.canSwap(att1, overlappingAppCache))
            and (app1 is None or app1.canSwap(att2, overlappingAppCache))
        )

    def swapBoth(app1, att1, app2, att2):
        assert(canSwapBoth(app1, att1, app2, att2))
        if app2:
            app2.swap(att1, overlappingAppCache)
        if app1:
            app1.swap(att2, overlappingAppCache)

    def printStatus():
        print(
            "\tavg utility:", 
            f'{getUtility()/len(chosenAttendees):.3f}', 
            'matched:', 
            f'{sum([len([a for a in c.getAppointments() if not a.isEmpty()]) for c in companies])}/{noApps}\n'
        )  

    printStatus()
    print('swapBoth')

    if not canSwapBoth(app1, att1, app2, att2):
        reason1 = None if app1 is None else app1.cantSwapReason(att2, overlappingAppCache)
        reason2 = None if app2 is None else app2.cantSwapReason(att1, overlappingAppCache)
        reason = reason1 or reason2
        ValidationException.throwIfFalse(reason is not None)
        return {'error': reason}, 400
    swapBoth(app1, att1, app2, att2)
    printStatus()
    print("stop:", datetime.now().strftime("%H:%M:%S"))
    return {'data': getJsonSchedule(
        companies, 
        attendees, 
        interviewTimes, 
        getUtility(), 
        noApps, 
        sum([len([a for a in c.getAppointments() if not a.isEmpty()]) for c in companies])
    )}, 200

def run(companies: list[Company], attendees: list[Attendee], interviewTimes: list[TimeInterval]):
    print("start:", datetime.now().strftime("%H:%M:%S"))
    chosenAttendees = [
        a for a in attendees 
        if any(c.wantsAttendee(a) for c in companies)
    ]
    
    def getUtility():
        return sum(sum([app.getUtility() for app in c.getAppointments()]) for c in companies)

    noApps = sum(len(c.getAppointments()) for c in companies)

    def getNoCompanies(att: Attendee) -> int:
        return len([c for c in companies if c.wantsAttendee(att)])

    def getOverlappingAppsForApp(companies: list[Company], app: Appointment, cache: dict[Appointment, set[Appointment]]) -> set[Appointment]:
        overlapping = set()
        for c in companies:
            for app2 in c.getAppointments():
                cond = app in cache[app2] if app2 in cache else app.isIntersecting(app2)
                #cond = app.isIntersecting(app2) 
                if app != app2 and cond:
                    overlapping.add(app2)
        return overlapping

    def getOverlappingApps(companies: list[Company]) -> dict[Appointment, set[Appointment]]:
        cache = {}
        for c in companies:
            for app in c.getAppointments():
                cache[app] = getOverlappingAppsForApp(companies, app, cache)
        return cache

    print('getOverlappingApps')
    print("\tstart:", datetime.now().strftime("%H:%M:%S"))
    overlappingAppCache = getOverlappingApps(companies)
    print("\tstop:", datetime.now().strftime("%H:%M:%S"))
    print('')

    def updateEmptyAppsCache(cache: dict[Appointment, set[Appointment]], notEmptyApp: Appointment):
        for app in cache[notEmptyApp]:
            cache[app].remove(notEmptyApp)
        cache.pop(notEmptyApp)

    def canSwapBoth(app1, att1, app2, att2):
        assert(not(app1 is None and app2 is None))
        return (
            (app2 is None or app2.canSwap(att1, overlappingAppCache))
            and (app1 is None or app1.canSwap(att2, overlappingAppCache))
        )

    def swapBoth(app1, att1, app2, att2):
        assert(canSwapBoth(app1, att1, app2, att2))
        if app2:
            app2.swap(att1, overlappingAppCache)
        if app1:
            app1.swap(att2, overlappingAppCache)

    def tryMatchEveryone(atts: list[Attendee]):

        atts = sorted(atts, key = lambda att: -len(att.commitments))
        noCompaniesCache = {a.uid: getNoCompanies(a) for a in atts}

        emptyAppsCache = {app:appSet.copy() for app,appSet in overlappingAppCache.items()} 
        # deep copy

        while True:
            changed = False

            for i in reversed(range(1, max([getNoCompanies(a) for a in atts])+1)):
                ith_atts = [a for a in atts if noCompaniesCache[a.uid]==i]
                
                while ith_atts:
                    newAtt = ith_atts.pop()

                    validApps = []
                    for c in companies:
                        if c.wantsAttendee(newAtt):
                            for app in c.getAppointments():
                                if app.isEmpty() and app.canSwap(newAtt, overlappingAppCache):
                                    validApps.append(app)
                    if validApps:
                        app = max(validApps, key=lambda app: (
                                len(emptyAppsCache[app]), 
                                newAtt.getPref(app.company)
                            )
                            # choose the least busy spot with the highest preference
                        )
                        app.swap(newAtt, overlappingAppCache)
                        #print('free appointments:', sum([len([app for app in c.getAppointments() if app.isEmpty()]) for c in companies]))
                        updateEmptyAppsCache(emptyAppsCache, app)
                        changed = True
                        #printApps()

            if not changed:
                break

    print('\ttryMatchEveryone')
    print("\tstart:", datetime.now().strftime("%H:%M:%S"))
    tryMatchEveryone(chosenAttendees)
    print("\tstop:", datetime.now().strftime("%H:%M:%S"))
    #printApps()
    '''print(
        "candidates:", len(chosenAttendees),
        "spots:", noApps,
        "filled:", sum([len([app for app in c.getAppointments() if not app.isEmpty()]) for c in companies])
    )'''

    #printApps()
    #printAtts()

    def getAttUtility(app, att):
        return att.prefsDic[app.company] if app and att else -1000

    def shouldSwap(app1, att1, app2, att2):
        canSwap = canSwapBoth(app1, att1, app2, att2)
        currentUtil = getAttUtility(app1, att1) + getAttUtility(app2, att2)
        swapUtil = getAttUtility(app1, att2) + getAttUtility(app2, att1)
        return canSwap and currentUtil < swapUtil # strictly less than

    def maxPref():

        appAtts = []
        for c in companies:
            for room in c.rooms:
                attsNotChosen = set(room.candidates)
                for app in room.appointments:
                    appAtts.append([app, app.attendee])
                    if not app.isEmpty():
                        attsNotChosen.remove(app.attendee)
                appAtts.extend([[None, att] for att in attsNotChosen])

        while True:

            changed = False

            #print("avg utility:", getUtility()/len(atts), 'matched:', len(atts))
            
            i = 0
            for i in range(len(appAtts)-1):
                currentApp, currentAtt = appAtts[i]
                for j in range(i+1, len(appAtts)):
                    existingApp, existingAtt = appAtts[j]
                    if currentAtt == existingAtt:
                        continue
                    if (currentApp is None) and (existingApp is None): continue
                    if shouldSwap(currentApp, currentAtt, existingApp, existingAtt):
                        #print("swapped!", currentApp, currentAtt, existingApp, existingAtt)
                        swapBoth(currentApp, currentAtt, existingApp, existingAtt)
                        appAtts[i][1] = existingAtt
                        appAtts[j][1] = currentAtt
                        changed = True
                        break

                if changed: break
            
            if not changed: break

    def printStatus():
        print(
            "\tavg utility:", 
            f'{getUtility()/len(chosenAttendees):.3f}', 
            'matched:', 
            f'{sum([len([a for a in c.getAppointments() if not a.isEmpty()]) for c in companies])}/{noApps}\n'
        )  

    printStatus()
    print('\tmaxPref')
    print("\tstart:", datetime.now().strftime("%H:%M:%S"))
    maxPref()
    print("\tstop:", datetime.now().strftime("%H:%M:%S"))    
    printStatus()
    #printApps()
    '''print(
        "candidates:", len(chosenAttendees),
        "spots:", noApps,
        "filled:", sum([len([app for app in c.getAppointments() if not app.isEmpty()]) for c in companies])
    )'''
    #printAtts(ret)

    def moveToStartOfDay():
            
        while True:
            changed = False
            for c in companies:

                apps = sorted(c.getAppointments(), key=lambda app: app.time.timestamp())

                for i in range(len(apps)):
                    app1 = apps[i]
                    if not app1.isEmpty():
                        continue
                    for j in reversed(range(i + 1, len(apps))):
                        app2 = apps[j]
                        if not app2.isEmpty():
                            att2 = app2.attendee
                            app2.swap(None, overlappingAppCache)
                            
                            if app1.canSwap(att2, overlappingAppCache):
                                app1.swap(att2, overlappingAppCache)
                                changed = True
                                #print(app1, "swapped", att.uid)
                                #printApps()
                                break
                            else:
                                changed2 = False

                                for k in range(i):
                                    app3 = apps[k]
                                    if app3.isEmpty(): continue
                                    att3 = app3.attendee
                                    app3.swap(None, overlappingAppCache)
                                    if app1.canSwap(att3, overlappingAppCache) and app3.canSwap(att2, overlappingAppCache):
                                        #print('ternary swap')
                                        app1.swap(att3, overlappingAppCache)
                                        app3.swap(att2, overlappingAppCache)
                                        changed2 = True
                                        break
                                    else:
                                        app3.swap(att3, overlappingAppCache)

                                if not changed2:
                                    app2.swap(att2, overlappingAppCache)
                                else:
                                    changed = True
                                    break
                    
            if not changed: break
                
    print('\tmoveToStartOfDay')
    print("\tstart:", datetime.now().strftime("%H:%M:%S"))
    moveToStartOfDay()
    print("\tstop:", datetime.now().strftime("%H:%M:%S"))    
    printStatus()

    print('\tmaxPref')
    print("\tstart:", datetime.now().strftime("%H:%M:%S"))
    maxPref()
    print("\tstop:", datetime.now().strftime("%H:%M:%S"))    
    printStatus()

    #printApps()
    print("stop:", datetime.now().strftime("%H:%M:%S"))
    return getJsonSchedule(
        companies, 
        attendees, 
        interviewTimes, 
        getUtility(), 
        noApps, 
        sum([len([a for a in c.getAppointments() if not a.isEmpty()]) for c in companies])
    )

def tryToReadTable(cursor: SqliteDB, readFunc: Callable[[str, SqliteDB], None], tableName: str):
    while True:
        fileName = input(f'enter {tableName} table file name: ')
        try:
            ValidationException.throwIfFalse(
                fileName.split('.')[-1] == 'csv',
                f'invalid file name ({fileName}): not .csv'
            )
            readFunc(getFileContents(fileName), cursor)
            print('\t', '...validated.')
            break
        except ValidationException as e:
            print('\t', str(e))
        except Exception as e:
            raise e

debugging = True

if __name__ == "__main__":
    with SqliteDB() as cursor:
        clearAllTables(cursor)

        if debugging:
            for func, filename in [
                (readInterviewTimes, 'interviewDays.csv'),
                (readCompanyNames, 'companyList.csv'),
                (readRoomNames, 'companyRoomsList.csv'),
                (readRoomBreaks, 'companyBreakList.csv'),
                (readAttendeeNames, 'attendeesList.csv'),
                (readAttendeeBreaks, 'attendeeBreaksList.csv'),
                (readAttendeePrefs, 'attendeePreferencesList.csv'),
                (readRoomCandidates, 'roomCandidatesList.csv')
            ]:
                func(getFileContents(filename), cursor)
        else:
            for func, tableName in [
                (readInterviewTimes, 'interview times list'),
                (readCompanyNames, 'company list'),
                (readRoomNames, 'room list'),
                (readRoomBreaks, 'room breaks list'),
                (readAttendeeNames, 'attendees list'),
                (readAttendeeBreaks, 'attendee breaks list'),
                (readAttendeePrefs, 'attendee preferences list'),
                (readRoomCandidates, 'room candidates list')
            ]:
                tryToReadTable(cursor, func, tableName)

        companies = []
        attendees = []
        setAttendeeAndCompanies(cursor, companies, attendees)

        print('done readin')

        #cProfile.run('run(companies, attendees, GetInterviewTimes(cursor))')
        run(companies, attendees, GetInterviewTimes(cursor))