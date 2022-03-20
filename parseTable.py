from __future__ import annotations
from datetime import time, timedelta
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

def readConventionTimes(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(CONVENTIONTIME_TABLE)
    cursor.EmptyTable(ROOMINTERVIEW_TABLE)
    cursor.EmptyTable(ROOMBREAKS_TABLE)
    cursor.EmptyTable(ATTENDEEBREAKS_TABLE)
    cursor.EmptyTable(COFFEECHAT_TABLE)

    conventionTimes = []

    for start,end in getCols(doc, 2, True):
        interval = TimeInterval.fromStr(start, end)

        ValidationException.throwIfFalse(
            not any(interval.isIntersecting(t) for t in conventionTimes), 
            f"invalid interview day: interview day {interval} intersects with other intervals {conventionTimes}"
        )
        conventionTimes.append(interval)
        AddConventionTime(cursor, interval)

#companyNames = set()
def readCompanyRoomNames(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(COMPANYROOM_TABLE)
    cursor.EmptyTable(COMPANY_TABLE)

    roomNames = set()
    for (companyName,roomName) in getCols(doc, 2, True):
        ValidationException.throwIfFalse(
            roomName not in roomNames, 
            f"duplicate room name ({roomName})"
        )
        roomNames.add(roomName)
        AddCompanyRoom(cursor, companyName, roomName)

def readRoomInterviews(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ROOMINTERVIEW_TABLE)
    cursor.EmptyTable(INTERVIEWCANDIDATES_TABLE)

    conventionTimes = GetConventionTimes(cursor)
    roomNames: set[str] = set()
    for companyRoomNames in GetCompanyRooms(cursor).values():
        roomNames.update(companyRoomNames)

    roomNamesWithInterview: set[str] = set()
    for roomName,length,startStr,endStr in getCols(doc, 4, True):
        interval = TimeInterval.fromStr(startStr, endStr)

        ValidationException.throwIfFalse(
            roomName in roomNames, 
            f"invalid room name ({roomName})"
        )
        ValidationException.throwIfFalse(
            roomName not in roomNamesWithInterview, 
            f"room name ({roomName}) not unique"
        )
        roomNamesWithInterview.add(roomName)
        ValidationException.throwIfFalse(
            length.isdigit and 0 < int(length), 
            f"invalid length ({length}), must be positive integer"
        )
        ValidationException.throwIfFalse(
            any(interval.isIntersecting(d) for d in conventionTimes), 
            f"invalid interval: break at {interval} does not intersect with interview times: {conventionTimes}"
        )
        AddRoom(cursor, roomName, int(length), interval)

def readRoomBreaks(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ROOMBREAKS_TABLE)

    conventionTimes = GetConventionTimes(cursor)
    roomIntervals = GetRoomIntervals(cursor)
    companyRoomNames = GetCompanyRooms(cursor)
    
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
            any(d.contains(b) for d in conventionTimes), 
            f"invalid break: break at {b} does not intersect with interview times: {conventionTimes}"
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

def readCoffeeChat(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(COFFEECHAT_TABLE)
    cursor.EmptyTable(COFFEECHATCANDIDATES_TABLE)

    conventionTimes = GetConventionTimes(cursor)
    companyRoomNames = GetCompanyRooms(cursor)
    
    coffeeChatRooms: set[str] = set()

    for roomName,capacity,startStr,endStr in getCols(doc, 4, False):
        timeInt = TimeInterval.fromStr(startStr, endStr)

        ValidationException.throwIfFalse(
            any(roomName in rooms for rooms in companyRoomNames.values()), 
            f"invalid room name ({roomName})"
        )
        ValidationException.throwIfFalse(
            roomName not in coffeeChatRooms, 
            f"coffee chat room name ({roomName}) not unique"
        )
        ValidationException.throwIfFalse(
            capacity.isdigit and 0 < int(capacity), 
            f"invalid capacity ({capacity}), must be positive integer"
        )
        ValidationException.throwIfFalse(
            any(d.contains(timeInt) for d in conventionTimes), 
            f"invalid coffee chat: chat at {timeInt} does not intersect with interview times: {conventionTimes}"
        )

        coffeeChatRooms.add(roomName)
        AddCoffeeChat(cursor, roomName, capacity, timeInt)


def readCoffeeChatCandidates(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(COFFEECHATCANDIDATES_TABLE)

    companyRoomNames = GetCompanyRooms(cursor)
    coffeeChatRooms = set(GetCoffeeChatCapacities(cursor).keys())
    
    attendeeIDs = GetAttendees(cursor)
    
    ccCandidates: dict[str, set[int]] = {}
    for roomName in coffeeChatRooms:
            ccCandidates[roomName] = set()

    for roomName,attendeeId,pref in getCols(doc, 3, True):
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
            roomName in coffeeChatRooms,
            f"invalid coffee chat room name ({roomName})"
        )
        ValidationException.throwIfFalse(
            attendeeId not in ccCandidates[roomName],
            f"duplicate attendee ({attendeeId}) for coffee chat candidate ({roomName})"
        )
        ValidationException.throwIfFalse(
            str.isdigit(pref) and 0 < int(pref),
            f"invalid preference ({pref}), must be a positive integer"
        )
        ccCandidates[roomName].add(attendeeId)
        AddCoffeeChatCandidate(cursor, roomName, attendeeId, pref)

    for room,atts in ccCandidates.items():
        ValidationException.throwIfFalse(
            0 < len(atts),
            f'no candidates for a coffee chat room ({room})'
        )

def readAttendeeNames(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ATTENDEES_TABLE)

    attendeeIDs = set()

    for (attendeeID,name) in getCols(doc, 2, True):
        ValidationException.throwIfFalse(
            attendeeID not in attendeeIDs,
            f"duplicate attendee ID ({attendeeID})"
        )
        attendeeIDs.add(attendeeID)
        AddAttendee(cursor, attendeeID,name)

def readAttendeeBreaks(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ATTENDEEBREAKS_TABLE)

    conventionTimes = GetConventionTimes(cursor)
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
            any(d.contains(b) for d in conventionTimes),
            f"invalid break: break at {b} does not intersect with interview times: {conventionTimes}"
        )
        ValidationException.throwIfFalse(
            all(not b.isIntersecting(b2) for b2 in attendeeBreaks[attendeeID]),
            f"invalid break: break at {b} intersects with one of the other breaks {attendeeBreaks[attendeeID]}"
        )
        attendeeBreaks[int(attendeeID)].append(b)
        AddAttendeeBreak(cursor, attendeeID, b)

def readAttendeePrefs(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(ATTENDEEPREFS_TABLE)

    companyNames = set(GetCompanyRooms(cursor).keys())
    attendeeIDs = GetAttendees(cursor)

    # lowestRank = -float('inf')
    lowestRank = -1
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
            str.isdigit(pref) and 0 < int(pref),
            f"invalid preference ({pref}), must be a positive integer"
        )
        lowestRank = max(lowestRank, int(pref))
        attendeePreferences[attendeeID][companyName] = int(pref)
        AddAttendeePref(cursor, attendeeID, companyName, pref)
    
    unspecifiedRank = lowestRank + 1
    for companyName in companyNames:
        for attId,companyPrefs in attendeePreferences.items():
            if companyName not in companyPrefs:
                AddAttendeePref(cursor, attId, companyName, unspecifiedRank)
    # for all attendees, if they havent ranked a company, put them at the lowest rank + 1


#roomCandidates = {a: set() for a in roomNames}
def readInterviewCandidates(doc: str, cursor: SqliteDB):
    cursor.EmptyTable(INTERVIEWCANDIDATES_TABLE)

    companyRoomNames = GetCompanyRooms(cursor)
    roomsWithInterview = GetRoomsWithInterview(cursor)
    attendeeIDs = GetAttendees(cursor)
    
    roomCandidates: dict[str, set[int]] = {}
    for roomNames in companyRoomNames.values():
        for roomName in roomNames:
            roomCandidates[roomName] = set()

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
            roomName in roomsWithInterview,
            f"room name ({roomName}) does not have interviews"
        )
        ValidationException.throwIfFalse(
            attendeeId not in roomCandidates[roomName],
            f"duplicate attendee for room candidate ({roomName})"
        )
        roomCandidates[roomName].add(attendeeId)
        AddInterviewCandidate(cursor, roomName, attendeeId)

def getSomeTimes(conventionTimes: list[TimeInterval], mins: int, breaks: list[TimeInterval], interval: TimeInterval) -> list[TimeInterval]:
    times = []

    for timeInt in [t for t in conventionTimes if t.isIntersecting(interval)]:
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
    conventionTimes = GetConventionTimes(cursor)

    companyRoomNames = GetCompanyRooms(cursor)
    roomLengths = GetRoomLengths(cursor)
    roomIntervals = GetRoomIntervals(cursor)
    roomBreaks = GetRoomBreaks(cursor)

    attendeeIdToName = GetAttendeeNames(cursor)
    attendeePrefs = GetAttendeePrefs(cursor)
    attendeeBreaks = GetAttendeeBreaks(cursor)

    interviewCandidates = GetInterviewCandidates(cursor)

    coffeeChatCapacities = GetCoffeeChatCapacities(cursor)
    coffeeChatTimes = GetCoffeeChatTimes(cursor)
    coffeeChatCandidates = GetCoffeeChatCandidates(cursor)

    mandatoryTables = [
        (conventionTimes, 'Interview Times'),
        (companyRoomNames, 'Company Rooms'),
        (attendeeIdToName, 'Attendees')
    ]

    for table, tableName in mandatoryTables:
        ValidationException.throwIfFalse(
            0 < len(table),
            f'a mandatory table ({tableName}) is empty'
        )

    companyNameToCompany = {name:Company(name) for name in companyRoomNames.keys()}
    for company in companyNameToCompany.values():
        companies.append(company)

    attendeeIDToAttendee = {}
    for attId,name in attendeeIdToName.items():
        prefs = []
        for companyName in companyNameToCompany:
            pref = attendeePrefs.get(attId, {}).get(companyName, 0)
            prefs.append(CompanyPreference(companyNameToCompany[companyName], pref))
        
        att = Attendee(attId, name, prefs, attendeeBreaks.get(attId, []))
        attendeeIDToAttendee[attId] = att
        attendees.append(att)

    for companyName,roomNames in companyRoomNames.items():
        for roomName in roomNames:
            company = companyNameToCompany[companyName]
            interval = roomIntervals.get(roomName, None)
            breaks = roomBreaks.get(roomName, [])

            # if we have a coffeeChat, don't generate an appointment at that time
            if roomName in coffeeChatTimes:
                breaks.append(coffeeChatTimes[roomName])

            times = getSomeTimes(conventionTimes, roomLengths[roomName], breaks, interval) if interval is not None else []
            room = company.addCompanyRoom(
                roomName,
                times, 
                [attendeeIDToAttendee[attId] for attId in interviewCandidates.get(roomName,[])]
            )
            if roomName in coffeeChatTimes:
                room.setCoffeeChat(
                    coffeeChatCapacities[roomName], 
                    coffeeChatTimes[roomName], 
                    [attendeeIDToAttendee[attId] for attId in coffeeChatCandidates[roomName]]
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
