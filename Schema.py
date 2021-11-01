from SqliteLib import *
from typing import DefaultDict
from datetime import datetime
from serverUtilities import CoffeeChat, TimeInterval
from os import remove

TABLES: list[DatedTable] = []
def createTable(name: str) -> DatedTable:
    if name in [t.name for t in TABLES]:
        raise Exception(f'duplicate name: {name}')
    table = DatedTable(name)
    TABLES.append(table)
    return table

CONVENTIONTIME_TABLE = createTable("interviewTime")
CONVENTIONTIME_START_COL = CONVENTIONTIME_TABLE.CreateColumn("start", DATETIME_TYPE, isPrimary=True)
CONVENTIONTIME_END_COL = CONVENTIONTIME_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddConventionTime(cursor: SqliteDB, timeInt: TimeInterval):
    cursor.InsertIntoTable(
        CONVENTIONTIME_TABLE, {
            CONVENTIONTIME_START_COL: [timeInt.time], 
            CONVENTIONTIME_END_COL: [timeInt.end]
        }
    )

def GetConventionTimes(cursor: SqliteDB) -> list[TimeInterval]:
    conventionTimesObj = cursor.FetchAll(cursor.Q(
        [CONVENTIONTIME_START_COL, CONVENTIONTIME_END_COL],
        CONVENTIONTIME_TABLE
    ))
    conventionTimes = []
    for timeObj in conventionTimesObj:
        getTime = lambda col: datetime.fromisoformat(timeObj[col.name])
        start = getTime(CONVENTIONTIME_START_COL)
        end = getTime(CONVENTIONTIME_END_COL)
        conventionTimes.append(TimeInterval(start, end-start))
    conventionTimes.sort(key = lambda t: t.time)
    return conventionTimes

COMPANY_TABLE = createTable("company")
COMPANY_COMPANYNAME_COL = COMPANY_TABLE.CreateColumn("companyName", VarCharType(50), isPrimary=True)

COMPANYROOM_TABLE = createTable("companyRoom")
COMPANYROOM_TABLE.CreateForeignKey(COMPANY_COMPANYNAME_COL, isPrimary=False)
COMPANYROOM_ROOMNAME_COL = COMPANYROOM_TABLE.CreateColumn("roomName", VarCharType(50), isPrimary=True)

def AddCompanyRoom(cursor: SqliteDB, companyName: str, roomName: str):
    if (not cursor.Exists(cursor.Q(
        [COMPANY_COMPANYNAME_COL], 
        COMPANY_TABLE,
        {COMPANY_COMPANYNAME_COL: companyName}
    ))):
        cursor.InsertIntoTable(COMPANY_TABLE, {COMPANY_COMPANYNAME_COL: [companyName]})

    cursor.InsertIntoTable(
        COMPANYROOM_TABLE, {
            COMPANY_COMPANYNAME_COL: [companyName],
            COMPANYROOM_ROOMNAME_COL: [roomName]
        }
    )

def GetCompanyRooms(cursor: SqliteDB) -> dict[str, str]:
    roomsObj = cursor.FetchAll(cursor.Q(
        [COMPANY_COMPANYNAME_COL, COMPANYROOM_ROOMNAME_COL],
        COMPANYROOM_TABLE
    ))

    rooms = {}
    for roomObj in roomsObj:
        companyName = roomObj[COMPANY_COMPANYNAME_COL.name]
        roomName = roomObj[COMPANYROOM_ROOMNAME_COL.name]
        rooms[companyName] = rooms.get(companyName, []) + [roomName]

    return rooms

ROOMINTERVIEW_TABLE = createTable("roomInterview")
ROOMINTERVIEW_TABLE.CreateForeignKey(COMPANYROOM_ROOMNAME_COL, isPrimary=True)
ROOMINTERVIEW_LENGTH_COL = ROOMINTERVIEW_TABLE.CreateColumn("length", INTEGER_TYPE)
ROOMINTERVIEW_START_COL = ROOMINTERVIEW_TABLE.CreateColumn("start", DATETIME_TYPE)
ROOMINTERVIEW_END_COL = ROOMINTERVIEW_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddRoom(cursor: SqliteDB, roomName: str, roomLen: str, interval: TimeInterval):
    cursor.InsertIntoTable(
        ROOMINTERVIEW_TABLE, {
            COMPANYROOM_ROOMNAME_COL: [roomName],
            ROOMINTERVIEW_LENGTH_COL: [roomLen],
            ROOMINTERVIEW_START_COL: [interval.time],
            ROOMINTERVIEW_END_COL: [interval.end]
        }
    )

def GetRoomsWithInterview(cursor: SqliteDB) -> set[str]:
    return set([
        r[COMPANYROOM_ROOMNAME_COL.name] 
        for r in cursor.FetchAll(cursor.Q(
            [COMPANYROOM_ROOMNAME_COL],
            ROOMINTERVIEW_TABLE
        ))
    ])

def GetRoomLengths(cursor: SqliteDB) -> dict[str, int]:
    return {
        r[COMPANYROOM_ROOMNAME_COL.name]:r[ROOMINTERVIEW_LENGTH_COL.name] 
        for r in cursor.FetchAll(cursor.Q(
            [COMPANYROOM_ROOMNAME_COL, ROOMINTERVIEW_LENGTH_COL],
            ROOMINTERVIEW_TABLE
        ))
    }

def GetRoomIntervals(cursor: SqliteDB) -> dict[str, TimeInterval]:
    roomIntervalsObj = cursor.FetchAll(cursor.Q(
        [COMPANYROOM_ROOMNAME_COL, ROOMINTERVIEW_START_COL, ROOMINTERVIEW_END_COL],
        ROOMINTERVIEW_TABLE
    ))
    roomIntervals = {}
    for timeObj in roomIntervalsObj:
        getTime = lambda col: datetime.fromisoformat(timeObj[col.name])
        room = timeObj[COMPANYROOM_ROOMNAME_COL.name]
        start = getTime(CONVENTIONTIME_START_COL)
        end = getTime(CONVENTIONTIME_END_COL)

        roomIntervals[room] = (TimeInterval(start, end-start))
    return roomIntervals

ROOMBREAKS_TABLE = createTable("roomBreak")
ROOMBREAKS_TABLE.CreateForeignKey(COMPANYROOM_ROOMNAME_COL, isPrimary=True)
ROOMBREAKS_START_COL = ROOMBREAKS_TABLE.CreateColumn("start", DATETIME_TYPE, isPrimary=True)
ROOMBREAKS_END_COL = ROOMBREAKS_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddRoomBreak(cursor: SqliteDB,roomName: str, timeInt: TimeInterval):
    cursor.InsertIntoTable(
        ROOMBREAKS_TABLE, {
            COMPANYROOM_ROOMNAME_COL: [roomName],
            ROOMBREAKS_START_COL: [timeInt.time],
            ROOMBREAKS_END_COL: [timeInt.end]
        }
    )

def GetRoomBreaks(cursor: SqliteDB) -> dict[str, list[TimeInterval]]:
    roomBreaksObj = cursor.FetchAll(cursor.Q(
        [COMPANYROOM_ROOMNAME_COL, ROOMBREAKS_START_COL, ROOMBREAKS_END_COL],
        ROOMBREAKS_TABLE
    ))  

    roomBreaks = {}
    for roomBreakObj in roomBreaksObj:
        name = roomBreakObj[COMPANYROOM_ROOMNAME_COL.name]
        getTime = lambda col: datetime.fromisoformat(roomBreakObj[col.name])
        start = getTime(ROOMBREAKS_START_COL)
        end = getTime(ROOMBREAKS_END_COL)
        timeInt = TimeInterval(start, end-start)

        roomBreaks[name] = roomBreaks.get(name, []) + [timeInt]
    return roomBreaks


COFFEECHAT_TABLE = createTable("roomCoffeeChat")
COFFEECHAT_TABLE.CreateForeignKey(COMPANYROOM_ROOMNAME_COL, isPrimary=True)
COFFEECHAT_CAPACITY_COL = COFFEECHAT_TABLE.CreateColumn("capacity", INTEGER_TYPE)
COFFEECHAT_START_COL = COFFEECHAT_TABLE.CreateColumn("start", DATETIME_TYPE)
COFFEECHAT_END_COL = COFFEECHAT_TABLE.CreateColumn("end", DATETIME_TYPE)

def AddCoffeeChat(cursor: SqliteDB, roomName: str, capacity: str, interval: TimeInterval):
    cursor.InsertIntoTable(
        COFFEECHAT_TABLE, {
            COMPANYROOM_ROOMNAME_COL: [roomName],
            COFFEECHAT_CAPACITY_COL: [capacity],
            COFFEECHAT_START_COL: [interval.time],
            COFFEECHAT_END_COL: [interval.end]
        }
    )

def GetCoffeeChatTimes(cursor: SqliteDB) -> dict[str, TimeInterval]:
    coffeeChatsObj = cursor.FetchAll(cursor.Q(
        [COMPANYROOM_ROOMNAME_COL, COFFEECHAT_START_COL, COFFEECHAT_END_COL],
        COFFEECHAT_TABLE
    ))

    coffeeChatTimes = {}
    for coffeeChatObj in coffeeChatsObj:
        room = coffeeChatObj[COMPANYROOM_ROOMNAME_COL.name]
        getTime = lambda col: datetime.fromisoformat(coffeeChatObj[col.name])
        start = getTime(ROOMBREAKS_START_COL)
        end = getTime(ROOMBREAKS_END_COL)

        coffeeChatTimes[room] = TimeInterval(start, end-start)
    return coffeeChatTimes

def GetCoffeeChatCapacities(cursor: SqliteDB) -> dict[str, int]:
    coffeeChatsObj = cursor.FetchAll(cursor.Q(
        [COMPANYROOM_ROOMNAME_COL, COFFEECHAT_CAPACITY_COL],
        COFFEECHAT_TABLE
    ))
    return {
        obj[COMPANYROOM_ROOMNAME_COL.name]:obj[COFFEECHAT_CAPACITY_COL.name] 
        for obj in coffeeChatsObj
    }


ATTENDEES_TABLE = createTable("attendee")
ATTENDEES_ID_COL = ATTENDEES_TABLE.CreateColumn("attendeeID", INTEGER_TYPE, isPrimary=True)
ATTENDEES_NAME_COL = ATTENDEES_TABLE.CreateColumn("attendeeName", VarCharType(50))

def AddAttendee(cursor: SqliteDB, attendeeId: str, name: str):
    cursor.InsertIntoTable(
        ATTENDEES_TABLE, {
            ATTENDEES_ID_COL: [attendeeId],
            ATTENDEES_NAME_COL: [name]
        }
    )

def GetAttendees(cursor: SqliteDB) -> set[str]:
    return set((
        c[ATTENDEES_ID_COL.name]
        for c in cursor.FetchAll(cursor.Q(
            [ATTENDEES_ID_COL],
            ATTENDEES_TABLE,
            orderBys=[ATTENDEES_ID_COL]
        ))
    ))
    
def GetAttendeeNames(cursor: SqliteDB) -> dict[str, str]:
    return {
        c[ATTENDEES_ID_COL.name]:c[ATTENDEES_NAME_COL.name] 
        for c in cursor.FetchAll(cursor.Q(
            [ATTENDEES_ID_COL, ATTENDEES_NAME_COL],
            ATTENDEES_TABLE,
            orderBys=[ATTENDEES_ID_COL]
        ))
    }

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
ATTENDEEPREFS_TABLE.CreateForeignKey(COMPANY_COMPANYNAME_COL, isPrimary=True)
ATTENDEEBREAKS_PREF_COL = ATTENDEEPREFS_TABLE.CreateColumn("preference", INTEGER_TYPE)

def AddAttendeePref(cursor: SqliteDB, attendeeId: str, companyName: str, pref: str):
    cursor.InsertIntoTable(
        ATTENDEEPREFS_TABLE, {
            ATTENDEES_ID_COL: [attendeeId],
            COMPANY_COMPANYNAME_COL: [companyName],
            ATTENDEEBREAKS_PREF_COL: [pref]
        }
    )

def GetAttendeePrefs(cursor: SqliteDB) -> dict[str, dict[str, int]]:
    attsPrefsObj = cursor.FetchAll(cursor.Q(
        [ATTENDEES_ID_COL, COMPANY_COMPANYNAME_COL, ATTENDEEBREAKS_PREF_COL],
        ATTENDEEPREFS_TABLE
    ))
    
    attsPrefs = {}
    for attPrefObj in attsPrefsObj:
        att = attPrefObj[ATTENDEES_ID_COL.name]
        company = attPrefObj[COMPANY_COMPANYNAME_COL.name]
        pref = attPrefObj[ATTENDEEBREAKS_PREF_COL.name]
        attPref = attsPrefs.get(att, {})
        attPref[company] = pref
        attsPrefs[att] = attPref
    return attsPrefs

INTERVIEWCANDIDATES_TABLE = createTable("interviewCandidate")
INTERVIEWCANDIDATES_TABLE.CreateForeignKey(COMPANYROOM_ROOMNAME_COL, isPrimary=True)
INTERVIEWCANDIDATES_TABLE.CreateForeignKey(ATTENDEES_ID_COL, isPrimary=True)

def AddInterviewCandidate(cursor: SqliteDB, roomName: str, attendeeId: str):
    cursor.InsertIntoTable(
        INTERVIEWCANDIDATES_TABLE, {
            COMPANYROOM_ROOMNAME_COL: [roomName],
            ATTENDEES_ID_COL: [attendeeId]
        }
    )

def GetInterviewCandidates(cursor: SqliteDB) -> dict[str, set[str]]:
    roomCandidatesObj = cursor.FetchAll(cursor.Q(
        [COMPANYROOM_ROOMNAME_COL, ATTENDEES_ID_COL],
        INTERVIEWCANDIDATES_TABLE
    ))

    roomCandidates = {}
    for roomCandidateObj in roomCandidatesObj:
        room = roomCandidateObj[COMPANYROOM_ROOMNAME_COL.name]
        att = roomCandidateObj[ATTENDEES_ID_COL.name]

        roomCandidates[room] = roomCandidates.get(room, set()).union([att])
    return roomCandidates



COFFEECHATCANDIDATES_TABLE = createTable("coffeeChatCandidate")
COFFEECHATCANDIDATES_TABLE.CreateForeignKey(COMPANYROOM_ROOMNAME_COL, isPrimary=True)
COFFEECHATCANDIDATES_TABLE.CreateForeignKey(ATTENDEES_ID_COL, isPrimary=True)

def AddCoffeeChatCandidate(cursor: SqliteDB, roomName: str, attId: int):
    cursor.InsertIntoTable(
        COFFEECHATCANDIDATES_TABLE, {
            COMPANYROOM_ROOMNAME_COL: [roomName],
            ATTENDEES_ID_COL: [attId],
        }
    )

def GetCoffeeChatCandidates(cursor: SqliteDB) -> dict[str, set[int]]:
    ccCandidatesObj = cursor.FetchAll(cursor.Q(
        [COMPANYROOM_ROOMNAME_COL, ATTENDEES_ID_COL],
        COFFEECHATCANDIDATES_TABLE
    ))

    ccCandidates = {}
    for roomCandidateObj in ccCandidatesObj:
        room = roomCandidateObj[COMPANYROOM_ROOMNAME_COL.name]
        att = roomCandidateObj[ATTENDEES_ID_COL.name]

        ccCandidates[room] = ccCandidates.get(room, set()).union([att])
    return ccCandidates

def clearAllTables(cursor: SqliteDB): 
    for table in TABLES:
        cursor.EmptyTable(table)

if __name__ == "__main__":
    try:
        remove(DB_FILENAME)
    except FileNotFoundError: 
        pass
    finally:
        WriteSchema(
            "schema.sql",
            TABLES
        )