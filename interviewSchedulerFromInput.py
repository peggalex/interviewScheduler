from __future__ import annotations
from datetime import datetime, timedelta
from typing import Callable

from parseTable import getFileContents, readAttendeeBreaks, readAttendeeNames, readAttendeePrefs, readCoffeeChat, readCoffeeChatCandidates, readCompanyRoomNames, readConventionTimes, readInterviewCandidates, readRoomBreaks, readRoomInterviews, setAttendeeAndCompanies, tryToReadTable
from serverUtilities import EXCEL_DATETIME_FORMAT, Appointment, AppointmentIntersects, Attendee, Company, TimeIntervalHash, ValidationException, TimeInterval, canSwapBoth, getJsonSchedule, getNoApps, getNoNotEmptyApps, getUtility, shouldSwap, swapBoth, trySwapBoth
from Schema import *
from writeSchedule import writeSchedule
import cProfile

def getAttToMaxRank(companies: list[Company], attendees: list[Attendee], isCoffeeChat: bool):
    attToMaxRank = {a:0 for a in attendees}
    if isCoffeeChat:
        for att in attendees:
            for c in companies:
                for r in c.rooms:
                    if r.wantsAttendee(att, True):
                        attToMaxRank[att] = max(
                            r.coffeeChat.companyPref(att), 
                            attToMaxRank[att]
                        )
    return attToMaxRank


def run(companies: list[Company], attendees: list[Attendee], conventionTimes: list[TimeInterval]) -> dict:
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

        #atts = sorted(atts, key = lambda att: len(att.commitments), reverse=True)
        #noCompaniesCache = {a.uid: a.getNoCompaniesWant(companies, isCoffeeChat) for a in atts}

        attToNoMaxRank = getAttToMaxRank(companies, attendees, isCoffeeChat)
        
        attToCompaniesAttending = {a:0 for a in atts}
        for company in companies:
            for app in company.getAppointments():
                if not app.isEmpty() and app.isCoffeeChat() == isCoffeeChat:
                    prev = attToCompaniesAttending.get(app.attendee, 0)
                    attToCompaniesAttending[app.attendee] = prev + 1

        attToNoCompaniesInvited = {a: a.getNoCompaniesWant(companies, isCoffeeChat) for a in atts}

        emptyAppsCache = initEmptyAppsCache(appIntersects)
        # deep copy

        while True:
            changed  = False

            atts = sorted(
                atts, 
                key = lambda att: (
                    attToNoMaxRank[att],
                    attToCompaniesAttending[att],
                    attToNoCompaniesInvited[att],
                    -len(att.commitments)
                )
            )
            for newAtt in atts:

                validApps: list[Appointment] = []
                for c in companies:
                    if c.wantsAttendee(newAtt, isCoffeeChat):
                        for app in c.getAppointments():
                            if app.isEmpty() and app.isCoffeeChat() == isCoffeeChat:
                                if app.canSwap(newAtt, appIntersects, None):
                                    validApps.append(app)
                                elif isCoffeeChat:
                                    # a little logic to handle coffee chats overlapping with apps
                                    appAtTime = appIntersects.getOtherAppAtTime(newAtt, app)
                                    if appAtTime is None or appAtTime.isCoffeeChat():
                                        continue
                                    for appAtTimeSwap in appAtTime.companyRoom.appointments:
                                        if appAtTimeSwap in (app, appAtTime) or appAtTimeSwap.attendee == newAtt:
                                            continue
                                        if trySwapBoth(appAtTime, appAtTime.attendee, appAtTimeSwap, appAtTimeSwap.attendee, appIntersects):
                                            print('\t\tswapped out a coffee chat blocker')
                                            if app.canSwap(newAtt, appIntersects, None):
                                                print('\t\tcoffee chat added after blocker swapped')
                                                validApps.append(app)
                                            break


                if validApps:
                    appMaxKey = lambda app: (
                        (
                            len(emptyAppsCache[app.timeHash]), 
                            -app.getUtility(newAtt),
                            -len(app.companyRoom.coffeeChat.candidates),
                            -app.companyRoom.coffeeChat.capacity,
                        ) if isCoffeeChat else (
                            len(emptyAppsCache[app.timeHash]), 
                            -len(app.companyRoom.candidates),
                            -len(app.companyRoom.times),
                            -app.getUtility(newAtt)
                        )
                    )
                    app = max(validApps, key=lambda app: appMaxKey(app))
                        # choose the least busy spot with the lowest preference
                    app.swap(newAtt, appIntersects, None)
                    attToCompaniesAttending[newAtt] += 1
                    updateEmptyAppsCache(emptyAppsCache, app)
                    changed = True

            if not changed:
                break

    def printStatus():
        print(
            "\tutility:", 
            f'{getUtility(companies)}', 
            'matched:', 
            f'{getNoNotEmptyApps(companies)}/{noApps}\n'
        )

    print('\ttryMatchEveryone')
    tryMatchEveryone(False)
    printStatus()

    def minRank(isCoffeeChat: bool):

        appAtts = []
        for c in companies:
            for room in c.rooms:
                if isCoffeeChat and room.coffeeChat is None:
                    continue
                attsNotChosen = set(
                    room.coffeeChat.candidates if isCoffeeChat else room.candidates
                )
                for app in room.appointments:
                    if app.isCoffeeChat() == isCoffeeChat:
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
                    if all(a is None for a in (currentAtt, existingAtt)): continue
                    if all(a is None for a in (currentApp, existingApp)): continue
                    
                    """
                    if any(app1 and att1 and not app2
                        for app1,att1,app2,att2 in (
                            (currentApp, currentAtt, existingApp, existingAtt), 
                            (existingApp, existingAtt, currentApp, currentAtt)
                        )
                    ): continue
                    # this condition will increase expected rank (bad), but it will help
                    # preserve the heuristic of tryMatchEveryone, 
                    # foremost enabling people to have at least 1 interview
                    """

                    if shouldSwap(currentApp, currentAtt, existingApp, existingAtt, appIntersects):
                        swapBoth(currentApp, currentAtt, existingApp, existingAtt, appIntersects)
                        appAtts[i][1] = existingAtt
                        appAtts[j][1] = currentAtt
                        changed = True
                        break

                if changed: break
            
            if not changed: break

    print('\tminRank')
    minRank(False)
    printStatus()

    def moveToStartOfDay():
            
        while True:
            changed = False
            for c in companies:

                apps = sorted(
                    (a for a in c.getAppointments() if not a.isCoffeeChat()), 
                    key=lambda app: app.time.timestamp()
                )

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

    print('\tminRank')
    minRank(False)
    printStatus()

    print('\n\ttryMatchEveryone coffee chat')
    tryMatchEveryone(True)
    printStatus()

    print('\tminRank coffee chat')
    minRank(True)
    printStatus() 

    print("stop:", datetime.now().strftime("%H:%M:%S"))

    return getJsonSchedule(
        companies, 
        attendees, 
        conventionTimes
    )

debugging = True

if __name__ == "__main__":
    with SqliteDB() as cursor:
        clearAllTables(cursor)

        if debugging:
            for func, filename in [
                (readConventionTimes, 'interviewDays.csv'),
                (readCompanyRoomNames, 'companyRoomList2.csv'),
                (readRoomInterviews, 'roomInterviewList.csv'),
                (readRoomBreaks, 'companyBreakList.csv'),
                (readCoffeeChat, 'coffeeChatList.csv'),
                (readAttendeeNames, 'attendeesList3.csv'),
                (readAttendeeBreaks, 'attendeeBreaksList.csv'),
                (readAttendeePrefs, 'attendeePreferencesList.csv'),
                (readInterviewCandidates, 'roomCandidatesList.csv'),
                (readCoffeeChatCandidates, 'coffeeChatCandidatesList2.csv')
            ]:
                func(getFileContents(filename), cursor)
        else:
            for func, tableName in [
                (readConventionTimes, 'convention times list'),
                (readCompanyRoomNames, 'company rooms list'),
                (readRoomInterviews, 'room interview list'),
                (readCoffeeChat, 'coffee chat list'),
                (readRoomBreaks, 'room breaks list'),
                (readAttendeeNames, 'attendees list'),
                (readAttendeeBreaks, 'attendee breaks list'),
                (readAttendeePrefs, 'attendee preferences list'),
                (readInterviewCandidates, 'interview candidates list'),
                (readCoffeeChatCandidates, 'coffee chat candidates list')
            ]:
                tryToReadTable(cursor, func, tableName)

        companies = []
        attendees = []
        setAttendeeAndCompanies(cursor, companies, attendees)

        print('done readin')

        #cProfile.run('run(companies, attendees, GetConventionTimes(cursor))')
        
        print('creating schedule...')
        run(companies, attendees, GetConventionTimes(cursor))
        filename = f"Interview Schedule {datetime.now().isoformat()[:-7].replace(':', '.')}.csv"
        writeSchedule(filename, companies)
        print(f"wrote schedule to file '{filename}'")
        