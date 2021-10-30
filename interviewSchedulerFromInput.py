from __future__ import annotations
from datetime import datetime, timedelta
from typing import Callable
from parseTable import getFileContents, readAttendeeBreaks, readAttendeeNames, readAttendeePrefs, readCoffeeChat, readCoffeeChatCandidates, readCompanyNames, readInterviewTimes, readRoomBreaks, readRoomCandidates, readRoomNames, setAttendeeAndCompanies, tryToReadTable
from serverUtilities import EXCEL_DATETIME_FORMAT, Appointment, AppointmentIntersects, Attendee, Company, TimeIntervalHash, ValidationException, TimeInterval, getJsonSchedule, getNoApps, getNoNotEmptyApps, getUtility, shouldSwap, swapBoth
from Schema import *
from writeSchedule import writeSchedule
import cProfile

""" 
============
love u rach!
============
"""

def run(companies: list[Company], attendees: list[Attendee], interviewTimes: list[TimeInterval]) -> dict:
    print("start:", datetime.now().strftime("%H:%M:%S"))

    noApps = getNoApps(companies)

    print('getOverlappingApps')
    appIntersects = AppointmentIntersects(companies)

    def initEmptyAppsCache(appIntersects: AppointmentIntersects) -> dict[TimeIntervalHash, set[Appointment]]:
        return {
            timeIntHash:appSet.copy() 
            for timeIntHash,appSet 
            in appIntersects.appsAtTime.items()
        }

    def updateEmptyAppsCache(cache: dict[TimeIntervalHash, set[Appointment]], notEmptyApp: Appointment):
        cache[notEmptyApp.timeHash].remove(notEmptyApp)
        for app in cache[notEmptyApp.timeHash]:
            cache[app.timeHash] = cache[app.timeHash] - {notEmptyApp}

    def tryMatchEveryone(isCoffeeChat: bool):

        atts = [
            a for a in attendees 
            if any(c.wantsAttendee(a, isCoffeeChat) for c in companies)
        ]

        if not atts: return

        atts = sorted(atts, key = lambda att: -len(att.commitments))
        noCompaniesCache = {a.uid: a.getNoCompaniesWant(companies, isCoffeeChat) for a in atts}

        emptyAppsCache = initEmptyAppsCache(appIntersects)
        # deep copy

        while True:
            changed = False

            for i in reversed(range(1, max(noCompaniesCache.values())+1)):
                ith_atts = [a for a in atts if noCompaniesCache[a.uid]==i]
                
                while ith_atts:
                    newAtt = ith_atts.pop()

                    validApps = []
                    for c in companies:
                        if c.wantsAttendee(newAtt, isCoffeeChat):
                            for app in c.getAppointments():
                                if app.isEmpty() and app.isCoffeeChat == isCoffeeChat:
                                    if app.canSwap(newAtt, appIntersects, None):
                                        validApps.append(app)
                                    elif isCoffeeChat:
                                        pass
                    if validApps:
                        app = max(validApps, key=lambda app: (
                                len(emptyAppsCache[app.timeHash]), 
                                -newAtt.getPref(app.company)
                            )
                            # choose the least busy spot with the lowest preference
                        )
                        app.swap(newAtt, appIntersects, None)
                        updateEmptyAppsCache(emptyAppsCache, app)
                        changed = True

            if not changed:
                break

    def printStatus():
        print(
            "\tavg utility:", 
            f'{getUtility(companies)}', 
            'matched:', 
            f'{getNoNotEmptyApps(companies)}/{noApps}\n'
        )

    print('\ttryMatchEveryone')
    tryMatchEveryone(False)
    printStatus()

    def maxPref(isCoffeeChat: bool):

        appAtts = []
        for c in companies:
            for room in c.rooms:
                if isCoffeeChat and room.coffeeChat is None:
                    continue
                attsNotChosen = set(
                    room.coffeeChat.candidates if isCoffeeChat else room.candidates
                )
                for app in room.appointments:
                    if app.isCoffeeChat == isCoffeeChat:
                        appAtts.append([app, app.attendee])
                        if not app.isEmpty():
                            attsNotChosen.remove(app.attendee)
                appAtts.extend([[None, att] for att in attsNotChosen])

        while True:

            changed = False
            
            i = 0
            for i in range(len(appAtts)-1):
                currentApp, currentAtt = appAtts[i]
                for j in range(i+1, len(appAtts)):
                    existingApp, existingAtt = appAtts[j]
                    if currentAtt == existingAtt:
                        continue
                    if (currentApp is None) and (existingApp is None): continue
                    if shouldSwap(currentApp, currentAtt, existingApp, existingAtt, appIntersects):
                        swapBoth(currentApp, currentAtt, existingApp, existingAtt, appIntersects)
                        appAtts[i][1] = existingAtt
                        appAtts[j][1] = currentAtt
                        changed = True
                        break

                if changed: break
            
            if not changed: break

    print('\tmaxPref')
    maxPref(False)
    printStatus()

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
                            app2.swap(None, appIntersects, None)
                            
                            if app1.canSwap(att2, appIntersects, app2):
                                app1.swap(att2, appIntersects, app2)
                                changed = True
                                break
                            else:
                                changed2 = False

                                for k in range(i):
                                    app3 = apps[k]
                                    if app3.isEmpty(): continue
                                    att3 = app3.attendee
                                    app3.swap(None, appIntersects, None)
                                    if app1.canSwap(att3, appIntersects, app3) and app3.canSwap(att2, appIntersects, app2):
                                        app1.swap(att3, appIntersects, app3)
                                        app3.swap(att2, appIntersects, app2)
                                        changed2 = True
                                        break
                                    else:
                                        app3.swap(att3, appIntersects, None)

                                if not changed2:
                                    app2.swap(att2, appIntersects, None)
                                else:
                                    changed = True
                                    break
                    
            if not changed: break
                
    print('\tmoveToStartOfDay')
    moveToStartOfDay()
    printStatus()

    print('\tmaxPref')
    maxPref(False)
    printStatus()

    print('\ntryMatchEveryone coffee chat')
    tryMatchEveryone(True)
    printStatus()

    print('\tmaxPref coffee chat')
    maxPref(True)
    printStatus() 

    print("stop:", datetime.now().strftime("%H:%M:%S"))

    return getJsonSchedule(
        companies, 
        attendees, 
        interviewTimes
    )

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
                (readCoffeeChat, 'coffeeChatList.csv'),
                (readAttendeeNames, 'attendeesList.csv'),
                (readAttendeeBreaks, 'attendeeBreaksList.csv'),
                (readAttendeePrefs, 'attendeePreferencesList.csv'),
                (readRoomCandidates, 'roomCandidatesList.csv'),
                (readCoffeeChatCandidates, 'coffeeChatCandidatesList.csv')
            ]:
                func(getFileContents(filename), cursor)
        else:
            for func, tableName in [
                (readInterviewTimes, 'interview times list'),
                (readCompanyNames, 'company list'),
                (readRoomNames, 'room list'),
                (readCoffeeChat, 'coffee chat list'),
                (readRoomBreaks, 'room breaks list'),
                (readAttendeeNames, 'attendees list'),
                (readAttendeeBreaks, 'attendee breaks list'),
                (readAttendeePrefs, 'attendee preferences list'),
                (readRoomCandidates, 'room candidates list'),
                (readCoffeeChatCandidates, 'coffee chat candidates list')
            ]:
                tryToReadTable(cursor, func, tableName)

        companies = []
        attendees = []
        setAttendeeAndCompanies(cursor, companies, attendees)

        print('done readin')

        #cProfile.run('run(companies, attendees, GetInterviewTimes(cursor))')
        print('creating schedule...')
        run(companies, attendees, GetInterviewTimes(cursor))
        filename = f"Interview Schedule {datetime.now().isoformat()[:-7].replace(':', '.')}.csv"
        writeSchedule(filename, companies)
        print(f"wrote schedule to file '{filename}'")