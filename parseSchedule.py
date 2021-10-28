from datetime import datetime
from typing import Optional
from serverUtilities import Company, CompanyPreference, Attendee, TimeInterval, Appointment, ValidationException

def parseJsonSchedule(data: dict) -> tuple[
        list[Company], 
        list[Attendee], 
        list[TimeInterval]
    ]:

    attendeesJson, companiesJson = data['attendees'], data['companies']

    interviewTimes = [TimeInterval.fromStr(t['start'], t['end']) for t in data['interviewTimes']]

    companyNameToCompany = {}
    for companyName in companiesJson.keys():
        companyNameToCompany[companyName] = Company(companyName)

    attendeeIdToAttendee = {}
    for attIdStr, attendeeJson in attendeesJson.items():
        attId = int(attIdStr)
        prefs = [
            CompanyPreference(companyNameToCompany[companyName], pref)
            for companyName, pref in attendeeJson['prefs'].items()
        ]
        commitments = [TimeInterval.fromStr(c['start'], c['end']) for c in attendeeJson['commitments']]
        attendeeIdToAttendee[attId] = Attendee(attId, prefs, commitments)

    for companyName, company in companyNameToCompany.items():
        for roomName, roomJson in companiesJson[companyName].items():
            times = [TimeInterval.fromStr(app['start'], app['end']) for app in roomJson['apps']]
            candidates = [attendeeIdToAttendee[attId] for attId in roomJson['candidates']]
            company.addCompanyRoom(roomName, times, candidates)

            assert(len(roomJson['apps']) == len(company.rooms[-1].appointments))
            for i in range(len(roomJson['apps'])):
                att = roomJson['apps'][i]['att']
                if att is not None:
                    company.rooms[-1].appointments[i].attendee = attendeeIdToAttendee[att]

    return (
        list(companyNameToCompany.values()),
        list(attendeeIdToAttendee.values()), 
        interviewTimes
    )

def parseJsonSwapSchedule(data: dict) -> tuple[
        list[Company], 
        list[Attendee], 
        list[TimeInterval],
        Optional[Appointment], 
        Optional[Attendee], 
        Optional[Appointment], 
        Optional[Attendee]
    ]:

    companies, attendees, interviewTimes = parseJsonSchedule(data)

    attendeeIdToAttendee = {att.uid:att for att in attendees}
    companyNameToCompany = {c.name:c for c in companies}

    def getApp(appJson: dict) -> Optional[Appointment]:
        if appJson is None:
            return None

        for company in companies:
            for room in company.rooms:
                if room.name == appJson['room']:
                    for app in room.appointments:
                        if app.time == datetime.fromisoformat(appJson['start']):
                            # datetime equality does not need to be the same object
                            return app
        raise ValidationException('what the hey?')

    getAttId = lambda attId: attendeeIdToAttendee[attId] if attId is not None else None

    appAttKeys = ['app1', 'att1', 'app2', 'att2']
    app1Json, att1Id, app2Json, att2Id = [data.get(k, None) for k in appAttKeys]

    att1, att2 = [getAttId(attId) for attId in (att1Id, att2Id)]
    app1, app2 = [getApp(j) for j in [app1Json, app2Json]]
    ValidationException.throwIfFalse(att1 != att2)
    ValidationException.throwIfFalse(
        all(
            app is None or app.attendee == att 
            for app,att in ((app1, att1), (app2, att2))
        ),
        'if app and att is defined, app.att = att must be true'
    )
    ValidationException.throwIfFalse(
        any(app is not None for app in (app1, app2)),
        'must be at least one app'
    )
    ValidationException.throwIfFalse(
        any(att is not None for att in (att1, att2)),
        'must be at least one att'
    )

    return (
        companies,
        attendees,
        interviewTimes,
        app1,
        att1,
        app2,
        att2
    )