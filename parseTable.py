from __future__ import annotations
from datetime import timedelta
from os.path import exists
from serverUtilities import Attendee, Company, CompanyPreference, ValidationException, TimeInterval
from Schema import *

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