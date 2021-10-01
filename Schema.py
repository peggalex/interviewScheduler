from SqliteLib import *
from typing import DefaultDict
from datetime import datetime
from serverUtilities import TimeInterval

INTERVIEWTIME_TABLE = DatedTable("interviewTime")
INTERVIEWTIME_START_COL = INTERVIEWTIME_TABLE.CreateColumn("start", DATETIME_TYPE, isPrimary=True)
INTERVIEWTIME_END_COL = INTERVIEWTIME_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddInterviewTime(cursor: SqliteDB, timeInt: TimeInterval):
    cursor.InsertIntoTable(
        INTERVIEWTIME_TABLE, {
            INTERVIEWTIME_START_COL: [timeInt.time], 
            INTERVIEWTIME_END_COL: [timeInt.end]
        }
    )

def GetInterviewTimes(cursor: SqliteDB) -> list[TimeInterval]:
    interviewTimesObj = cursor.FetchAll(cursor.Q(
        [INTERVIEWTIME_START_COL, INTERVIEWTIME_END_COL],
        INTERVIEWTIME_TABLE
    ))
    interviewTimes = []
    for timeObj in interviewTimesObj:
        getTime = lambda col: datetime.fromisoformat(timeObj[col.name])
        start = getTime(INTERVIEWTIME_START_COL)
        end = getTime(INTERVIEWTIME_END_COL)
        interviewTimes.append(TimeInterval(start, end-start))
    interviewTimes.sort(key = lambda t: t.time)
    return interviewTimes

COMPANY_TABLE = DatedTable("company")
COMPANY_NAME_COL = COMPANY_TABLE.CreateColumn("companyName", VarCharType(50), isPrimary=True)

def AddCompany(cursor: SqliteDB, name: str):
    cursor.InsertIntoTable(
        COMPANY_TABLE, {COMPANY_NAME_COL: [name]}
    )

def GetCompanies(cursor: SqliteDB) -> set[str]:

    return set((
        c[COMPANY_NAME_COL.name] for c in 
        cursor.FetchAll(cursor.Q(
            [COMPANY_NAME_COL],
            COMPANY_TABLE
        ))
    ))

ROOM_TABLE = DatedTable("room")
ROOM_TABLE.CreateForeignKey(COMPANY_NAME_COL, isPrimary=True)
ROOM_NAME_COL = ROOM_TABLE.CreateColumn("roomName", VarCharType(50), isPrimary=True)
ROOM_LENGTH_COL = ROOM_TABLE.CreateColumn("length", INTEGER_TYPE)
ROOM_START_COL = ROOM_TABLE.CreateColumn("start", DATETIME_TYPE)
ROOM_END_COL = ROOM_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddRoom(cursor: SqliteDB, companyName: str, roomName: str, roomLen: str, interval: TimeInterval):
    cursor.InsertIntoTable(
        ROOM_TABLE, {
            COMPANY_NAME_COL: [companyName],
            ROOM_NAME_COL: [roomName],
            ROOM_LENGTH_COL: [roomLen],
            ROOM_START_COL: [interval.time],
            ROOM_END_COL: [interval.end]
        }
    )

def GetRooms(cursor: SqliteDB) -> dict[str, str]:
    roomsObj = cursor.FetchAll(cursor.Q(
        [COMPANY_NAME_COL, ROOM_NAME_COL],
        ROOM_TABLE
    ))

    rooms = {}
    for roomObj in roomsObj:
        companyName = roomObj[COMPANY_NAME_COL.name]
        roomName = roomObj[ROOM_NAME_COL.name]
        existingRooms = rooms.get(companyName, [])
        existingRooms.append(roomName)
        rooms[companyName] = existingRooms # only necessary if: companyName not in rooms

    return rooms

def GetRoomLengths(cursor: SqliteDB) -> dict[str, int]:
    return {
        r[ROOM_NAME_COL.name]:r[ROOM_LENGTH_COL.name] 
        for r in cursor.FetchAll(cursor.Q(
            [ROOM_NAME_COL, ROOM_LENGTH_COL],
            ROOM_TABLE
        ))
    }

def GetRoomIntervals(cursor: SqliteDB) -> dict[str, TimeInterval]:
    roomIntervalsObj = cursor.FetchAll(cursor.Q(
        [ROOM_NAME_COL, ROOM_START_COL, ROOM_END_COL],
        ROOM_TABLE
    ))
    roomIntervals = {}
    for timeObj in roomIntervalsObj:
        getTime = lambda col: datetime.fromisoformat(timeObj[col.name])
        room = timeObj[ROOM_NAME_COL.name]
        start = getTime(INTERVIEWTIME_START_COL)
        end = getTime(INTERVIEWTIME_END_COL)

        roomIntervals[room] = (TimeInterval(start, end-start))
    return roomIntervals

ROOMBREAKS_TABLE = DatedTable("roomBreak")
ROOMBREAKS_TABLE.CreateForeignKey(ROOM_NAME_COL, isPrimary=True)
ROOMBREAKS_START_COL = ROOMBREAKS_TABLE.CreateColumn("start", DATETIME_TYPE, isPrimary=True)
ROOMBREAKS_END_COL = ROOMBREAKS_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddRoomBreak(cursor: SqliteDB,roomName: str, timeInt: TimeInterval):
    cursor.InsertIntoTable(
        ROOMBREAKS_TABLE, {
            ROOM_NAME_COL: [roomName],
            ROOMBREAKS_START_COL: [timeInt.time],
            ROOMBREAKS_END_COL: [timeInt.end]
        }
    )

def GetRoomBreaks(cursor: SqliteDB) -> dict[str, list[TimeInterval]]:
    roomBreaksObj = cursor.FetchAll(cursor.Q(
        [ROOM_NAME_COL, ROOMBREAKS_START_COL, ROOMBREAKS_END_COL],
        ROOMBREAKS_TABLE
    ))

    roomBreaks = {}
    for roomBreakObj in roomBreaksObj:
        name = roomBreakObj[ROOM_NAME_COL.name]
        getTime = lambda col: datetime.fromisoformat(roomBreakObj[col.name])
        start = getTime(ROOMBREAKS_START_COL)
        end = getTime(ROOMBREAKS_END_COL)

        existingBreaks = roomBreaks.get(name, [])
        existingBreaks.append(TimeInterval(start, end-start))
        roomBreaks[name] = existingBreaks
    return roomBreaks

ATTENDEES_TABLE = DatedTable("attendee")
ATTENDEES_ID_COL = ATTENDEES_TABLE.CreateColumn("attendeeID", INTEGER_TYPE, isPrimary=True)

def AddAttendee(cursor: SqliteDB, attendeeId: str):
    cursor.InsertIntoTable(
        ATTENDEES_TABLE, {
            ATTENDEES_ID_COL: [attendeeId]
        }
    )

def GetAttendees(cursor: SqliteDB) -> set[str]:
    return set((
        c[ATTENDEES_ID_COL.name] for c in cursor.FetchAll(cursor.Q(
            [ATTENDEES_ID_COL],
            ATTENDEES_TABLE
        ))
    ))

ATTENDEEBREAKS_TABLE = DatedTable("attendeeBreak")
ATTENDEEBREAKS_TABLE.CreateForeignKey(ATTENDEES_ID_COL, isPrimary=True)
ATTENDEEBREAKS_START_COL = ATTENDEEBREAKS_TABLE.CreateColumn("start", DATETIME_TYPE, isPrimary=True)
ATTENDEEBREAKS_END_COL = ATTENDEEBREAKS_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddAttendeeBreak(cursor: SqliteDB, attendeeId: str, timeInt: TimeInterval):
    cursor.InsertIntoTable(
        ATTENDEEBREAKS_TABLE, {
            ATTENDEES_ID_COL: [attendeeId],
            ATTENDEEBREAKS_START_COL: [timeInt.time],
            ATTENDEEBREAKS_END_COL: [timeInt.end]
        }
    )

def GetAttendeeBreaks(cursor: SqliteDB) -> dict[str, list[TimeInterval]]:
    attendeeBreaksObj = cursor.FetchAll(cursor.Q(
        [ATTENDEES_ID_COL, ATTENDEEBREAKS_START_COL, ATTENDEEBREAKS_END_COL],
        ATTENDEEBREAKS_TABLE
    ))

    attendeeBreaks = {}
    for attendeeBreakObj in attendeeBreaksObj:
        name = attendeeBreakObj[ATTENDEES_ID_COL.name]

        getTime = lambda col: datetime.fromisoformat(attendeeBreakObj[col.name])
        start = getTime(ATTENDEEBREAKS_START_COL)
        end = getTime(ATTENDEEBREAKS_END_COL)

        existingBreaks = attendeeBreaks.get(name, [])
        existingBreaks.append(TimeInterval(start, end-start))
        attendeeBreaks[name] = existingBreaks
    return attendeeBreaks

ATTENDEEPREFS_TABLE = DatedTable("attendeePreference")
ATTENDEEPREFS_TABLE.CreateForeignKey(ATTENDEES_ID_COL, isPrimary=True)
ATTENDEEPREFS_TABLE.CreateForeignKey(COMPANY_NAME_COL, isPrimary=True)
ATTENDEEBREAKS_PREF_COL = ATTENDEEPREFS_TABLE.CreateColumn("preference", INTEGER_TYPE)

def AddAttendeePref(cursor: SqliteDB, attendeeId: str, companyName: str, pref: str):
    cursor.InsertIntoTable(
        ATTENDEEPREFS_TABLE, {
            ATTENDEES_ID_COL: [attendeeId],
            COMPANY_NAME_COL: [companyName],
            ATTENDEEBREAKS_PREF_COL: [pref]
        }
    )

def GetAttendeePrefs(cursor: SqliteDB) -> dict[str, dict[str, int]]:
    attsPrefsObj = cursor.FetchAll(cursor.Q(
        [ATTENDEES_ID_COL, COMPANY_NAME_COL, ATTENDEEBREAKS_PREF_COL],
        ATTENDEEPREFS_TABLE
    ))
    
    attsPrefs = {}
    for attPrefObj in attsPrefsObj:
        att = attPrefObj[ATTENDEES_ID_COL.name]
        company = attPrefObj[COMPANY_NAME_COL.name]
        pref = attPrefObj[ATTENDEEBREAKS_PREF_COL.name]
        attPref = attsPrefs.get(att, {})
        attPref[company] = pref
        attsPrefs[att] = attPref
    return attsPrefs

ROOMCANDIDATES_TABLE = DatedTable("roomCandidate")
ROOMCANDIDATES_TABLE.CreateForeignKey(ROOM_NAME_COL, isPrimary=True)
ROOMCANDIDATES_TABLE.CreateForeignKey(ATTENDEES_ID_COL, isPrimary=True)

def AddRoomCandidate(cursor: SqliteDB, roomName: str, attendeeId: str):
    cursor.InsertIntoTable(
        ROOMCANDIDATES_TABLE, {
            ROOM_NAME_COL: [roomName],
            ATTENDEES_ID_COL: [attendeeId]
        }
    )

def GetRoomCandidates(cursor: SqliteDB) -> dict[str, set[str]]:
    roomCandidatesObj = cursor.FetchAll(cursor.Q(
        [ROOM_NAME_COL, ATTENDEES_ID_COL],
        ROOMCANDIDATES_TABLE
    ))

    roomCandidates = {}
    for roomCandidateObj in roomCandidatesObj:
        room = roomCandidateObj[ROOM_NAME_COL.name]
        att = roomCandidateObj[ATTENDEES_ID_COL.name]

        existingAtts = roomCandidates.get(room, set())
        existingAtts.add(att)
        roomCandidates[room] = existingAtts
    return roomCandidates

TABLES = [
    INTERVIEWTIME_TABLE,
    ATTENDEES_TABLE,
    COMPANY_TABLE,
    ROOM_TABLE,
    ROOMBREAKS_TABLE,
    ATTENDEES_TABLE,
    ATTENDEEBREAKS_TABLE,
    ATTENDEEPREFS_TABLE,
    ROOMCANDIDATES_TABLE
]

def clearAllTables(cursor: SqliteDB):
    for table in TABLES:
        cursor.EmptyTable(table)

if __name__ == "__main__":
    WriteSchema(
        "schema.sql",
        TABLES
    )