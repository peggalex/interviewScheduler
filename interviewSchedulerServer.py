from Schema import ATTENDEEBREAKS_TABLE, ATTENDEEPREFS_TABLE, ATTENDEES_TABLE, COFFEECHAT_TABLE, COFFEECHATCANDIDATES_TABLE, COMPANY_TABLE, COMPANYROOM_TABLE, CONVENTIONTIME_TABLE, INTERVIEWCANDIDATES_TABLE, ROOMBREAKS_TABLE, ROOMINTERVIEW_TABLE, GetCompanyRooms, GetConventionTimes
import traceback
import logging as notFlaskLogging
from datetime import datetime
from flask import *
from typing import Callable, Any

from serverUtilities import ValidationException
from os import path

from SqliteLib import Column, SqliteDB, Table
from sqlite3 import OperationalError as sqlite3Error

from parseTable import (
    readCoffeeChat,
    readCoffeeChatCandidates,
    readConventionTimes,
    readInterviewCandidates,
    readRoomInterviews,
    readRoomBreaks,
    readAttendeeNames,
    readAttendeeBreaks,
    readAttendeePrefs,
    setAttendeeAndCompanies,  
)

from parseSchedule import (
    parseJsonSchedule,
    parseJsonSwapSchedule,
)

from writeSchedule import writeSchedule
from trySwap import trySwap
from interviewSchedulerFromInput import run

notFlaskLogging.basicConfig(level=notFlaskLogging.DEBUG)
app = Flask(__name__, static_folder='./react_app/build/static', template_folder="./react_app/build")

ResponseType = tuple[dict[str, Any], int]

def handleException(cursor: SqliteDB, e: Exception) -> ResponseType:
    """ Roleback cursor, return 400 if validation error else 500 """

    lastQuery = cursor.lastQuery # save before rollback
    cursor.Rollback()
    traceback.print_exc()

    if type(e) == ValidationException:
        return {"error": f"{str(e)}"}, 400
    else:
        errorMsg = f"Server Error: {str(type(e))} -- {str(e)}"
        if type(e) == sqlite3Error:
            errorMsg += f"\n\tlast query: {lastQuery}"
        return {"error": errorMsg}, 500

def setTable(request, setFunc: Callable[[str, SqliteDB], None], getFunc: Callable[[], ResponseType]) -> ResponseType:
    """ Parse file from request, pass to setFunc, return getFunc """

    with SqliteDB() as cursor:
        try:
            fileKey = 'table'
            ValidationException.throwIfFalse(
                fileKey in request.files,
                'No file in request'
            )

            file = request.files[fileKey]
            ValidationException.throwIfFalse(
                file.filename != '',
                "No file selected"
            )

            ext = file.filename.split(".")[-1]
            ValidationException.throwIfFalse(
                ext == 'csv',
                "Wrong file extension (must be .csv)"
            )

            #doc = quopri.decodestring(file.read()).decode("latin")
            doc = file.read().decode('utf-8').strip()
            setFunc(doc, cursor)
            #return {'data': [line.split(',') for line in doc.split('\n')][1:]}, 200
            return getFunc()

        except Exception as e:
            return handleException(cursor, e)

def getTableReponse(table: Table) -> ResponseType:
    """ Get table, return reponse obj, handle exceptions """

    with SqliteDB() as cursor:
        try:
            table = cursor.FetchAll(cursor.Q(table.GetColumns(), table))
            return {'data': [list(x.values()) for x in table]}, 200 # no need for keys
        except Exception as e:
            return handleException(cursor, e)


# interview times
@app.route('/getConventionTimes', methods=['GET'])
def getConventionTimesHandler() -> ResponseType:
    return getTableReponse(CONVENTIONTIME_TABLE)

@app.route('/setConventionTimes', methods=['POST'])
def setConventionTimesHandler() -> ResponseType:
    return setTable(request, readConventionTimes, getConventionTimesHandler)


# company names
@app.route('/getCompanyRooms', methods=['GET'])
def getCompanyRoomsHandler() -> ResponseType:
    return getTableReponse(COMPANYROOM_TABLE)

@app.route('/setCompanyRooms', methods=['POST'])
def setCompanyNamesHandler() -> ResponseType:
    return setTable(request, GetCompanyRooms, getCompanyRoomsHandler)


# room names
@app.route('/getRoomInterviews', methods=['GET'])
def getRoomInterviewsHandler() -> ResponseType:
    return getTableReponse(ROOMINTERVIEW_TABLE)

@app.route('/setRoomInterviews', methods=['POST'])
def setRoomInterviewsHandler() -> ResponseType:
    return setTable(request, readRoomInterviews, getRoomInterviewsHandler)


# room breaks
@app.route('/getRoomBreaks', methods=['GET'])
def getRoomBreaksHandler() -> ResponseType:
    return getTableReponse(ROOMBREAKS_TABLE)

@app.route('/setRoomBreaks', methods=['POST'])
def setRoomBreaksHandler() -> ResponseType:
    return setTable(request, readRoomBreaks, getRoomBreaksHandler)


# attendee names
@app.route('/getAttendeeNames', methods=['GET'])
def getAttendeeNamesHandler() -> ResponseType:
    return getTableReponse(ATTENDEES_TABLE)

@app.route('/setAttendeeNames', methods=['POST'])
def setAttendeeNamesHandler() -> ResponseType:
    return setTable(request, readAttendeeNames, getAttendeeNamesHandler)


# attendee breaks
@app.route('/getAttendeeBreaks', methods=['GET'])
def getAttendeeBreaksHandler() -> ResponseType:
    return getTableReponse(ATTENDEEBREAKS_TABLE)

@app.route('/setAttendeeBreaks', methods=['POST'])
def setAttendeeBreaksHandler() -> ResponseType:
    return setTable(request, readAttendeeBreaks, getAttendeeBreaksHandler)


# attendee prefs
@app.route('/getAttendeePrefs', methods=['GET'])
def getAttendeePrefsHandler() -> ResponseType:
    return getTableReponse(ATTENDEEPREFS_TABLE)

@app.route('/setAttendeePrefs', methods=['POST'])
def setAttendeePrefsHandler() -> ResponseType:
    return setTable(request, readAttendeePrefs, getAttendeePrefsHandler)


# room candidates
@app.route('/getInterviewCandidates', methods=['GET'])
def getInterviewCandidatesHandler() -> ResponseType:
    return getTableReponse(INTERVIEWCANDIDATES_TABLE)

@app.route('/setInterviewCandidates', methods=['POST'])
def setInterviewCandidatesHandler() -> ResponseType:
    return setTable(request, readInterviewCandidates, getInterviewCandidatesHandler)


# coffee chats
@app.route('/getCoffeeChats', methods=['GET'])
def getCoffeeChatsHandler() -> ResponseType:
    return getTableReponse(COFFEECHAT_TABLE)

@app.route('/setCoffeeChats', methods=['POST'])
def setCoffeeChatsHandler() -> ResponseType:
    return setTable(request, readCoffeeChat, getCoffeeChatsHandler)


# coffee chat candidates
@app.route('/getCoffeeChatCandidates', methods=['GET'])
def getCoffeeChatCandidatesHandler() -> ResponseType:
    return getTableReponse(COFFEECHATCANDIDATES_TABLE)

@app.route('/setCoffeeChatCandidates', methods=['POST'])
def setCoffeeChatCandidatesHandler() -> ResponseType:
    return setTable(request, readCoffeeChatCandidates, getCoffeeChatCandidatesHandler)



@app.route('/generateSchedule', methods=['GET'])
def generateScheduleHandler() -> ResponseType:
    companies = []
    attendees = []

    with SqliteDB() as cursor:
        try:
            setAttendeeAndCompanies(
                cursor,
                companies=companies,
                attendees=attendees
            )

            return {
                'data': run(companies,attendees,GetConventionTimes(cursor))
            }, 200
                    
        except Exception as e:
            return handleException(cursor, e)

@app.route('/swapSchedule', methods=['POST'])
def swapScheduleHandler() -> ResponseType:
    with SqliteDB() as cursor:
        try:
            data = request.get_json()['data']
            return {"data": trySwap(*parseJsonSwapSchedule(data))}, 200
        except Exception as e:
            return handleException(cursor, e)

@app.route('/writeSchedule', methods=['POST'])
def writeScheduleHandler() -> ResponseType:
    with SqliteDB() as cursor:
        try:
            data = request.get_json()['data']
            companies, atts, interviewTimes = parseJsonSchedule(data)
            filename = f"Interview Schedule {datetime.now().isoformat()[:-7].replace(':', '.')}.csv"
            writeSchedule(filename, companies)
            return {'data': {'filename': filename}}, 200
        except Exception as e:
            return handleException(cursor, e)


@app.route('/images/<filename>')
def getImagesEndpoint(filename) -> ResponseType:

    return send_from_directory(
        path.join(app.root_path, 'react_app/build'),
        filename
    )

@app.route('/')
@app.errorhandler(404)   
def index(e = None) -> ResponseType:
    return render_template('index.html')

if __name__=="__main__":
    print('starting server...')

    '''
    readInterviewTimes(getFileContents('interviewDays.csv'), interviewTimes)
    readCompanyNames(getFileContents('companyList.csv'), companyNames)
    readRoomNames(getFileContents('companyRoomsList.csv'), companyNames, companyRoomNames, roomLengths, roomNames)
    readRoomBreaks(getFileContents('companyBreakList.csv'), interviewTimes, roomNames, companyRoomBreaks)
    readAttendeeNames(getFileContents('attendeesList.csv'), attendeeIDs)
    readAttendeeBreaks(getFileContents('attendeeBreaksList.csv'), interviewTimes, attendeeIDs, attendeeBreaks)
    readAttendeePrefs(getFileContents('attendeePreferencesList.csv'), companyNames, attendeeIDs, attendeePreferences)
    readRoomCandidates(getFileContents('roomCandidatesList.csv'), roomNames, attendeeIDs, roomCandidates)
    '''

    url = "0.0.0.0:4000"

    app.run(
        "0.0.0.0", 
        debug=True, 
        port=4000
    )
