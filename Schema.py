from SqliteLib import *
from typing import DefaultDict
from datetime import datetime
from serverUtilities import CoffeeChat, TimeInterval

TABLES: list[DatedTable] = []
def createTable(name: str) -> DatedTable:
    if name in [t.name for t in TABLES]:
        raise Exception(f'duplicate name: {name}')
    table = DatedTable(name)
    TABLES.append(table)
    return table

INTERVIEWTIME_TABLE = createTable("interviewTime")
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

COMPANY_TABLE = createTable("company")
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

ROOM_TABLE = createTable("room")
ROOM_TABLE.CreateForeignKey(COMPANY_NAME_COL, isPrimary=False)
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
        rooms[companyName] = rooms.get(companyName, []) + [roomName]

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

ROOMBREAKS_TABLE = createTable("roomBreak")
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
        timeInt = TimeInterval(start, end-start)

        roomBreaks[name] = roomBreaks.get(name, []) + [timeInt]
    return roomBreaks


COFFEECHAT_TABLE = createTable("coffeeChat")
COFFEECHAT_TABLE.CreateForeignKey(ROOM_NAME_COL, isPrimary=True)
COFFEECHAT_CAPACITY_COL = COFFEECHAT_TABLE.CreateColumn("capacity", INTEGER_TYPE)
COFFEECHAT_START_COL = COFFEECHAT_TABLE.CreateColumn("start", DATETIME_TYPE)
COFFEECHAT_END_COL = COFFEECHAT_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddCoffeeChat(cursor: SqliteDB, roomName: str, capacity: str, interval: TimeInterval):
    cursor.InsertIntoTable(
        COFFEECHAT_TABLE, {
            ROOM_NAME_COL: [roomName],
            COFFEECHAT_CAPACITY_COL: [capacity],
            COFFEECHAT_START_COL: [interval.time],
            COFFEECHAT_END_COL: [interval.end]
        }
    )

def GetCoffeeChatTimes(cursor: SqliteDB) -> dict[str, TimeInterval]:
    coffeeChatsObj = cursor.FetchAll(cursor.Q(
        [ROOM_NAME_COL, COFFEECHAT_START_COL, COFFEECHAT_END_COL],
        COFFEECHAT_TABLE
    ))

    coffeeChatTimes = {}
    for coffeeChatObj in coffeeChatsObj:
        room = coffeeChatObj[ROOM_NAME_COL.name]
        getTime = lambda col: datetime.fromisoformat(coffeeChatObj[col.name])
        start = getTime(ROOMBREAKS_START_COL)
        end = getTime(ROOMBREAKS_END_COL)

        coffeeChatTimes[room] = TimeInterval(start, end-start)
    return coffeeChatTimes

def GetCoffeeChatCapacities(cursor: SqliteDB) -> dict[str, int]:
    coffeeChatsObj = cursor.FetchAll(cursor.Q(
        [ROOM_NAME_COL, COFFEECHAT_CAPACITY_COL],
        COFFEECHAT_TABLE
    ))
    return {
        obj[ROOM_NAME_COL.name]:obj[COFFEECHAT_CAPACITY_COL.name] 
        for obj in coffeeChatsObj
    }


ATTENDEES_TABLE = createTable("attendee")
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

ATTENDEEBREAKS_TABLE = createTable("attendeeBreak")
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
        interval = TimeInterval(start, end-start)

        attendeeBreaks[name] = attendeeBreaks.get(name, []) + [interval]
    return attendeeBreaks

ATTENDEEPREFS_TABLE = createTable("attendeePreference")
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

ROOMCANDIDATES_TABLE = createTable("roomCandidate")
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

        roomCandidates[room] = roomCandidates.get(room, set()).union([att])
    return roomCandidates



COFFEECHATCANDIDATES_TABLE = createTable("coffeeChatCandidate")
COFFEECHATCANDIDATES_TABLE.CreateForeignKey(ROOM_NAME_COL, isPrimary=True)
COFFEECHATCANDIDATES_TABLE.CreateForeignKey(ATTENDEES_ID_COL, isPrimary=True)

def AddCoffeeChatCandidate(cursor: SqliteDB, roomName: str, attId: int):
    cursor.InsertIntoTable(
        COFFEECHATCANDIDATES_TABLE, {
            ROOM_NAME_COL: [roomName],
            ATTENDEES_ID_COL: [attId],
        }
    )

def GetCoffeeChatCandidates(cursor: SqliteDB) -> dict[str, set[int]]:
    ccCandidatesObj = cursor.FetchAll(cursor.Q(
        [ROOM_NAME_COL, ATTENDEES_ID_COL],
        COFFEECHATCANDIDATES_TABLE
    ))

    ccCandidates = {}
    for roomCandidateObj in ccCandidatesObj:
        room = roomCandidateObj[ROOM_NAME_COL.name]
        att = roomCandidateObj[ATTENDEES_ID_COL.name]

        ccCandidates[room] = ccCandidates.get(room, set()).union([att])
    return ccCandidates

def clearAllTables(cursor: SqliteDB):
    for table in TABLES:
        cursor.EmptyTable(table)

if __name__ == "__main__":
    WriteSchema(
        "schema.sql",
        TABLES
    )