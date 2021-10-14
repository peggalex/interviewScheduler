from Schema import ATTENDEEBREAKS_TABLE, ATTENDEEPREFS_TABLE, ATTENDEES_TABLE, COMPANY_TABLE, INTERVIEWTIME_END_COL, INTERVIEWTIME_START_COL, INTERVIEWTIME_TABLE, ROOM_TABLE, ROOMBREAKS_TABLE, ROOMCANDIDATES_TABLE, GetAttendeeBreaks, GetAttendeePrefs, GetAttendees, GetCompanies, GetInterviewTimes, GetRoomBreaks, GetRoomCandidates, GetRooms, clearAllTables
import traceback
import logging as notFlaskLogging
from datetime import datetime, timedelta
from flask import *
from typing import Callable, Union, Optional, Any
import webbrowser

from serverUtilities import ValidationException
from os import path

from SqliteLib import Column, SqliteDB, Table
from sqlite3 import OperationalError as sqlite3Error

from interviewSchedulerFromInput import (
    parseJsonSchedule,
    readInterviewTimes, 
    readCompanyNames,
    readRoomNames,
    readRoomBreaks,
    readAttendeeNames,
    readAttendeeBreaks,
    readAttendeePrefs,
    readRoomCandidates,
    setAttendeeAndCompanies,
    getFileContents,
    run,
    trySwap
)

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
            doc = file.read().decode('ascii').strip()
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
@app.route('/getInterviewTimes', methods=['GET'])
def getInterviewTimesHandler() -> ResponseType:
    return getTableReponse(INTERVIEWTIME_TABLE)

@app.route('/setInterviewTimes', methods=['POST'])
def setInterviewTimesHandler() -> ResponseType:
    return setTable(request, readInterviewTimes, getInterviewTimesHandler)


# company names
@app.route('/getCompanyNames', methods=['GET'])
def getCompanyNamesHandler() -> ResponseType:
    return getTableReponse(COMPANY_TABLE)

@app.route('/setCompanyNames', methods=['POST'])
def setCompanyNamesHandler() -> ResponseType:
    return setTable(request, readCompanyNames, getCompanyNamesHandler)


# room names
@app.route('/getRoomNames', methods=['GET'])
def getRoomNamesHandler() -> ResponseType:
    return getTableReponse(ROOM_TABLE)

@app.route('/setRoomNames', methods=['POST'])
def setRoomNamesHandler() -> ResponseType:
    return setTable(request, readRoomNames, getRoomNamesHandler)

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
@app.route('/getRoomCandidates', methods=['GET'])
def getRoomCandidatesHandler() -> ResponseType:
    return getTableReponse(ROOMCANDIDATES_TABLE)

@app.route('/setRoomCandidates', methods=['POST'])
def setRoomCandidatesHandler() -> ResponseType:
    return setTable(request, readRoomCandidates, getRoomCandidatesHandler)


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
                'data': run(companies,attendees,GetInterviewTimes(cursor))
            }, 200
                    
        except Exception as e:
            return handleException(cursor, e)

@app.route('/swapSchedule', methods=['POST'])
def swapScheduleHandler() -> ResponseType:
    with SqliteDB() as cursor:
        try:
            data = request.get_json()['data']
            companies, atts, interviewTimes, app1, att1, app2, att2 = parseJsonSchedule(data)
            return trySwap(companies, atts, interviewTimes, app1, att1, app2, att2)
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

    webbrowser.open_new(url)

