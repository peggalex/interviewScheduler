from Schema import GetInterviewTimes, clearAllTables
import traceback
import logging as notFlaskLogging
from datetime import datetime, timedelta
from flask import *
from typing import Callable
import webbrowser

from serverUtilities import ValidationException
from os import path

from SqliteLib import SqliteDB
from sqlite3 import OperationalError as sqlite3Error

from interviewSchedulerFromInput import (
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
    run
)

interviewTimes = []

companyNames = set()

companyRoomNames = {}
roomLengths = {}
roomNames = set()

companyRoomBreaks = {}

attendeeIDs = set()

attendeeBreaks = {}

attendeePreferences = {}

roomCandidates = {}

tables = [interviewTimes, companyNames, companyRoomNames, roomLengths, roomNames, companyRoomBreaks, attendeeIDs, attendeeBreaks, attendeePreferences]

notFlaskLogging.basicConfig(level=notFlaskLogging.DEBUG)
app = Flask(__name__, static_folder='./react_app/build/static', template_folder="./react_app/build")

def handleException(cursor: SqliteDB, e: Exception):
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

def readRequest(request, func: Callable):
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

            func(doc, cursor)

            return {'data': [line.split(',') for line in doc.split('\n')][1:]}, 200

        except Exception as e:
            return handleException(cursor, e)

@app.route('/readInterviewTimes', methods=['POST'])
def readInterviewTimesHandler():
    return readRequest(request, readInterviewTimes)

@app.route('/readCompanyNames', methods=['POST'])
def readCompanyNamesHandler():
    return readRequest(request, readCompanyNames)

@app.route('/readRoomNames', methods=['POST'])
def readRoomNamesHandler():
    return readRequest(request, readRoomNames)

@app.route('/readRoomBreaks', methods=['POST'])
def readRoomBreaksHandler():
    return readRequest(request, readRoomBreaks)

@app.route('/readAttendeeNames', methods=['POST'])
def readAttendeeNamesHandler():
    return readRequest(request, readAttendeeNames)

@app.route('/readAttendeeBreaks', methods=['POST'])
def readAttendeeBreaksHandler():
    return readRequest(request, readAttendeeBreaks)

@app.route('/readAttendeePrefs', methods=['POST'])
def readAttendeePrefsHandler():
    return readRequest(request, readAttendeePrefs)

@app.route('/readRoomCandidates', methods=['POST'])
def readRoomCandidatesHandler():
    return readRequest(request, readRoomCandidates)

@app.route('/generateSchedule', methods=['GET'])
def generateScheduleHandler():
    companies = []
    attendees = []

    with SqliteDB() as cursor:
        try:
            setAttendeeAndCompanies(
                cursor,
                companies=companies,
                attendees=attendees
            )
            run(GetInterviewTimes(cursor),companies,attendees)

            return {
                'data': {
                    'companies': {c.name: c.toJson() for c in companies},
                    'attendees': {a.uid: a.toJson() for a in attendees},
                    'interviewTimes': [t.toJson() for t in GetInterviewTimes(cursor)]
                }
            }, 200
                    
        except Exception as e:
            companies.clear()
            attendees.clear()

            return handleException(cursor, e)

@app.route('/images/<filename>')
def getImagesEndpoint(filename):

    return send_from_directory(
        path.join(app.root_path, 'react_app/build'),
        filename
    )

@app.route('/')
@app.errorhandler(404)   
def index(e = None):
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

