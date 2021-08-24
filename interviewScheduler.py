from __future__ import annotations
from datetime import datetime, time, timedelta
from random import random, seed as setRandomSeed, sample
from typing import List

maxRating = 10
companyNames = ['Manulife', 'CAAT Pension Plan', 'Foresters Financial', 'Echelon Insurance / CCG Group', 'iA Financial Group', 'Normandin Beaudry', 'RSM Canada', 'Economical Insurance', 'Munich Re', 'Swiss Re', 'Milliman', 'Mercer Canada', 'Intact Insurance', "Ontario Teachers' Pension Plan", 'Royal and Sun Alliance (RSA)', 'KPMG Canada', 'Wawanesa Insurance', 'Canada Life', "Moody's Analytics", 'Deloitte', 'PartnerRe', 'The Co-operators', 'Desjardins', 'Northbridge Financial Corporation']
noCompanyAppointments = 12
atomicTime = timedelta(minutes=15)
randomRating = lambda: int(random()*maxRating) + 1
students = 20
candidatesFixed = 4
candidatesVariable = 8

earliestTime = timedelta(hours=9)
latestTime = timedelta(hours=12 + 6)

def timesIntersect(time1: datetime, length1: timedelta, time2: datetime, length2: timedelta):
    latestStart = max(time1, time2)
    earliestEnd = min(time1 + length1, time2 + length2)
    return latestStart < earliestEnd

class Company:

    def __init__(self, name: str):
        self.name = name
        self.rooms = []

    def addCompanyRoom(self, times: List[datetime], length: timedelta, candidates: List[Attendee]):
        self.rooms.append(CompanyRoom(self, times, length, candidates))
        return self

    def wantsAttendee(self, attendee: Attendee) -> bool:
        return any(room.wantsAttendee(attendee) for room in self.rooms)

    def hasAttendee(self, attendee: Attendee) -> bool:
        return any(room.hasAttendee(attendee) for room in self.rooms)

    def getAppointments(self) -> List[Appointment]:
        apps = []
        for room in self.rooms:
            apps.extend(room.appointments)
        return apps

    def __repr__(self) -> str:
        return self.name


def hasOtherAppsAtTime(att: Attendee, time: datetime, length: timedelta):
    if att:
        for c in companies:
            for app in c.getAppointments():
                if app.isAttendee(att) and app.intersects(time, length):
                    return True
    return False

def hasOtherAppsAtCompany(att: Attendee, company: Company):
    return company.hasAttendee(att)

class CompanyRoom:

    def __init__(self, company, times: List[datetime], length: timedelta, candidates: List[Attendee]):
        self.roomNo = len(company.rooms) + 1
        self.company = company
        self.times = times
        self.length = length
        self.candidates = set(candidates)
        self.appointments = [
            Appointment(self, time, length) for time in times
        ]

    def wantsAttendee(self, attendee: Attendee) -> bool:
        return attendee is None or attendee in self.candidates 

    def hasAttendee(self, attendee: Attendee) -> bool:
        if attendee:
            for app in self.appointments:
                if app.isAttendee(attendee):
                    return True
        return False        

    def __repr__(self) -> str:
        return f"{self.company.name} - room {self.roomNo}"
            
class TimeInterval:

    def __init__(self, time: datetime, length: timedelta):
        self.time = time
        self.length = length
        self.end = self.time + self.length

    def isIntersecting(self, timeInterval: TimeInterval):
        return timesIntersect(self.time, self.length, timeInterval.time, timeInterval.length)

    def __repr__(self):
        return (
            f"{self.time.strftime('%b %d')}: "
            + f"[{self.time.strftime('%H:%M')},{(self.length + self.time).strftime('%H:%M')}]"
        )


class Appointment(TimeInterval):

    def __init__(self, companyRoom: Company, time: datetime, length: timedelta):
        super().__init__(time, length)
        self.companyRoom = companyRoom
        self.company = self.companyRoom.company
        self.attendee = None

    def __repr__(self):
        return f"{self.company.name}-{self.companyRoom.roomNo}@{self.time.strftime('%b %d %H:%M')}"

    def isAttendee(self, attendee):
        return attendee != None and self.attendee == attendee

    def isEmpty(self):
        return self.attendee == None

    def getUtility(self):
        return self.attendee.getPref(self.company) if not self.isEmpty() else 0

    def intersects(self, time, length):
        return timesIntersect(self.time, self.length, time, length)

    def canSwap(self, attendee: Attendee):
        return attendee is None or (
            self.companyRoom.wantsAttendee(attendee) 
            and not hasOtherAppsAtTime(attendee, self.time, self.length)
            and not attendee.isBusy(self)
            and not hasOtherAppsAtCompany(attendee, self.company)
        )

    def swap(self, attendee: Attendee):
        if self.canSwap(attendee):
            self.attendee = attendee
        else:
            raise Exception('tried to swap an attendee which can\'t be swapped')

class CompanyPreference:

    def __init__(self, company: Company, pref: int):
        self.company = company
        self.pref = pref

    def __repr__(self) -> str:
        return f"{str(self.company.name)} = {self.pref}"


class Attendee:

    def __init__(self, uid: int, prefs: List[CompanyPreference], commitments: List[TimeInterval]):
        self.uid = uid
        prefs.sort(key = lambda ap: -ap.pref)
        self.prefsLst = prefs
        self.prefsDic = {p.company:p.pref for p in prefs}
        self.commitments = commitments

    def getPref(self, company) -> int:
        return self.prefsDic[company]

    def __repr__(self) -> str:
        return str(self.uid)

    def isBusy(self, timeInterval: TimeInterval) -> bool:
        return any(commit.isIntersecting(timeInterval) for commit in self.commitments)


saturday = datetime(year=2021, month=7, day=6)
sunday = saturday + timedelta(days=1)

getSomeTimes = lambda day, minutes: [
    day + timedelta(seconds = secs) 
    for secs in range(
        int(earliestTime.total_seconds()), 
        int(latestTime.total_seconds()), 
        minutes*60
    )
    if timedelta(minutes=minutes, seconds = secs) <= latestTime
]

companies = [Company(name) for name in companyNames]

attsDic = {}
attendees = []
saturdayCommitments = {'289': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '348': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '495': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '306': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '611': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '615': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '431': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '610': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '155': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '059': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '609': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '299': [TimeInterval(datetime(2021, 7, 6, 11, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 5400))], '106': [TimeInterval(datetime(2021, 7, 6, 9, 45), timedelta(0, 8100)), TimeInterval(datetime(2021, 7, 6, 14, 30), timedelta(0, 10800))], '053': [TimeInterval(datetime(2021, 7, 6, 9, 45), timedelta(0, 8100)), TimeInterval(datetime(2021, 7, 6, 13, 30), timedelta(0, 9000))], '006': [TimeInterval(datetime(2021, 7, 6, 11, 30), timedelta(0, 5400))], '001': [TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600))], '057': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 3600))], '038': [TimeInterval(datetime(2021, 7, 6, 9, 30), timedelta(0, 7200))], '499': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '580': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '564': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '123': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '619': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '584': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '205': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '185': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '8': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '167': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], '576': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))]}
sundayCommitments = {'106': [TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600))], '057': [TimeInterval(datetime(2021, 7, 7, 11, 45), timedelta(0, 4500))], '053': [TimeInterval(datetime(2021, 7, 7, 11, 30), timedelta(0, 7200)), TimeInterval(datetime(2021, 7, 7, 14, 0), timedelta(0, 7200)), TimeInterval(datetime(2021, 7, 7, 16, 30), timedelta(0, 1800))], '006': [TimeInterval(datetime(2021, 7, 7, 16, 30), timedelta(0, 1800))], '299': [TimeInterval(datetime(2021, 7, 7, 16, 30), timedelta(0, 1800))], '1': [TimeInterval(datetime(2021, 7, 7, 16, 30), timedelta(0, 1800))], '272': [TimeInterval(datetime(2021, 7, 7, 16, 30), timedelta(0, 1800))], '200': [TimeInterval(datetime(2021, 7, 7, 16, 30), timedelta(0, 1800))], '17': [TimeInterval(datetime(2021, 7, 7, 14, 0), timedelta(0, 7200)), TimeInterval(datetime(2021, 7, 7, 16, 30), timedelta(0, 1800))]}
def getPrefRow(row: str):
    if not row:
       return
    cols = row.split(',')
    uid = cols.pop(0)

    prefs = [] # List[CompanyPreference]

    companiesSpecified = set()
    for i in range(len(cols)):
        companyName = cols[-(i+1)] # -1, -2,... => 14, 13, ...
        if companyName == '0':
            continue
        company = [c for c in companies if c.name == companyName][0]
        companiesSpecified.add(company)
        prefs.append(CompanyPreference(company, i)) # 0, 1,...

    for unspecifiedCompany in (set(companies) - companiesSpecified):
        prefs.append(CompanyPreference(unspecifiedCompany, 0))

    commitments = saturdayCommitments.get(uid, []) + sundayCommitments.get(uid, [])
    attendee = Attendee(int(uid), prefs, commitments)
    attendees.append(attendee)
    attsDic[int(uid)] = attendee

with open('Student_Company_Rankings.csv', 'r', encoding='utf-8') as f:
    f.readline() # skip header
    for line in f:
        getPrefRow(line.strip().strip('\ufeff'))

setRandomSeed(12345)


companyRoomCandidates = {'Manulife-1': {608, 228, 517, 6, 306, 52, 214, 58, 539}, 'Manulife-2': {128, 5, 551, 108, 588, 53, 86, 59, 29}, 'Manulife-3': {332, 428, 303, 400, 568, 507, 189, 222}, 'Manulife-4': {259, 165, 549, 487, 616, 391, 521, 243, 373}, 'Manulife-5': {577, 293, 232, 168, 112, 273, 277, 380, 639}, 'Swiss Re-1': {66, 196, 39, 296, 585, 176, 62}, 'Swiss Re-2': {34, 293, 103, 139, 181, 222}, 'Munich Re-1': {97, 4, 293, 59, 649, 333, 400, 306, 181, 123}, 'Munich Re-2': {66, 232, 41, 10, 492, 48, 126}, 'Canada Life-1': {259, 156, 541, 534}, 'Canada Life-2': {37, 265, 556, 49, 58, 316}, 'Munich Re-3': {385, 492, 302}, 'Munich Re-4': {34, 99, 100, 228, 425, 272, 57, 219, 222, 319}, 'Wawanesa Insurance-1': {104, 51, 118, 248, 185, 25}, 'Wawanesa Insurance-2': {613, 551, 72, 202, 619, 61, 190}, 'Wawanesa Insurance-3': {616, 425, 76, 588, 593, 215, 313, 61}, 'Economical Insurance-1': {312, 7, 551, 140, 248, 185, 318, 287}, 'Economical Insurance-2': {35, 197, 9, 362, 298, 140, 45, 275, 180, 440, 316, 189}, 'Economical Insurance-3': {98, 201, 619, 653, 431, 20, 508, 381}, 'Desjardins-1': {198, 302, 276, 21, 568, 156}, 'Desjardins-2': {258, 259, 371, 636, 381, 287}, 'Intact Insurance-1': {365}, 'Intact Insurance-2': {258, 66, 551, 555, 173, 302, 17, 273, 306, 190}, 'RSM Canada-1': {420, 101, 140, 556, 302, 148, 276, 470, 407, 121, 122, 27, 381, 446}, "Moody's Analytics-1": {321, 97, 197, 552, 585, 431, 79, 623, 25, 58}, 'Milliman-1': {1, 546, 153, 100, 326, 487, 112, 466, 21, 57, 539, 156, 446, 159}, 'Deloitte-1': {259, 388, 391, 277, 407, 539, 34, 561, 312, 568, 59, 62, 333, 592, 466, 595, 596, 471, 219, 220, 97, 101, 123}, 'Echelon Insurance / CCG Group-1': {640, 99, 348}, 'Royal and Sun Alliance (RSA)-1': {197, 551, 8, 41, 555, 651, 140, 53, 313, 31}, 'KPMG Canada-1': {59, 179, 244, 189}, 'KPMG Canada-2': {568, 272, 196, 406}, 'KPMG Canada-3': {280, 53}, 'Normandin Beaudry-1': {355, 420, 451, 487, 584, 215}, 'Foresters Financial-1': {259, 517, 549, 232, 595, 53, 374, 568, 441}, 'Mercer Canada-1': {193, 354, 258, 38, 551, 400, 17, 627, 148, 470, 215, 446}, 'PartnerRe-1': {480, 97, 326, 41, 556, 52, 600, 287}, 'CAAT Pension Plan-1': {576, 388, 138, 141, 173, 17, 435, 148, 244, 372, 446}, 'iA Financial Group-1': {221, 109, 469}}
companyRoomBreaks = {'Canada Life-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Canada Life-2': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'CAAT Pension Plan-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600))], 'Deloitte-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400))], 'Desjardins-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 11, 30), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 15, 0), timedelta(0, 7200))], 'Desjardins-2': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 11, 30), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 15, 0), timedelta(0, 7200))], 'Echelon Insurance / CCG Group-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Economical Insurance-1': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], 'Economical Insurance-2': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], 'Economical Insurance-3': [TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 7200))], 'Foresters Financial-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600))], 'iA Financial Group-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Intact Insurance-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700))], 'Intact Insurance-2': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 12, 15), timedelta(0, 2700)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 12, 15), timedelta(0, 2700))], 'KPMG Canada-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400))], 'KPMG Canada-2': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400))], 'KPMG Canada-3': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400))], 'Mercer Canada-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 1800))], 'Milliman-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800))], 'Manulife-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600))], 'Manulife-2': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600))], 'Manulife-3': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600))], 'Manulife-4': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600))], 'Manulife-5': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600))], 'Munich Re-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 14, 30), timedelta(0, 1800))], 'Munich Re-2': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 14, 30), timedelta(0, 1800))], 'Munich Re-3': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 14, 30), timedelta(0, 1800))], 'Munich Re-4': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 14, 30), timedelta(0, 1800))], "Moody's Analytics-1": [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 14400)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 14400))], 'Northbridge Financial Corporation-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Normandin Beaudry-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 12, 0), timedelta(0, 3600))], "Ontario Teachers' Pension Plan-1": [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'PartnerRe-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 11, 30), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 14, 0), timedelta(0, 1800))], 'Royal and Sun Alliance (RSA)-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Royal and Sun Alliance (RSA)-2': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'RSM Canada-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 7, 9, 0), timedelta(0, 1800)), TimeInterval(datetime(2021, 7, 7, 13, 0), timedelta(0, 3600))], 'Swiss Re-1': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Swiss Re-2': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'The Co-operators-operators': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Wawanesa Insurance-1': [TimeInterval(datetime(2021, 7, 6, 13, 0), timedelta(0, 3600)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Wawanesa Insurance-2': [TimeInterval(datetime(2021, 7, 6, 10, 30), timedelta(0, 5400)), TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))], 'Wawanesa Insurance-3': [TimeInterval(datetime(2021, 7, 6, 9, 0), timedelta(0, 3600))]}
companyRoomMinutes = {'Canada Life-1': 20, 'Canada Life-2': 20, 'CAAT Pension Plan-1': 30, 'Deloitte-1': 30, 'Desjardins-1': 45, 'Desjardins-2': 45, 'Echelon Insurance / CCG Group-1': 45, 'Economical Insurance-1': 60, 'Economical Insurance-2': 30, 'Economical Insurance-3': 60, 'Foresters Financial-1': 40, 'iA Financial Group-1': 40, 'Intact Insurance-1': 45, 'Intact Insurance-2': 45, 'KPMG Canada-1': 30, 'KPMG Canada-2': 30, 'KPMG Canada-3': 30, 'Mercer Canada-1': 30, 'Milliman-1': 60, 'Manulife-1': 30, 'Manulife-2': 30, 'Manulife-3': 30, 'Manulife-4': 30, 'Manulife-5': 30, 'Munich Re-1': 30, 'Munich Re-2': 30, 'Munich Re-3': 30, 'Munich Re-4': 30, "Moody's Analytics-1": 45, 'Northbridge Financial Corporation-1': 30, 'Normandin Beaudry-1': 40, "Ontario Teachers' Pension Plan-1": 30, 'PartnerRe-1': 30, 'Royal and Sun Alliance (RSA)-1': 30, 'Royal and Sun Alliance (RSA)-2': 30, 'RSM Canada-1': 45, 'Swiss Re-1': 30, 'Swiss Re-2': 30, 'The Co-operators-operators': 30, 'Wawanesa Insurance-1': 45, 'Wawanesa Insurance-2': 30, 'Wawanesa Insurance-3': 60}

for c in companies:
    i = 1
    while True:
        roomName = f'{c.name}-{i}'
        if roomName in companyRoomCandidates:
            breaks = companyRoomBreaks.get(roomName, [])
            candidates = []
            for attId in companyRoomCandidates[roomName]:
                if attId in attsDic:
                    att = attsDic[attId]
                else:
                    att = Attendee(str(attId), [CompanyPreference(c, 0) for c in companies], [])
                    attendees.append(att)
                candidates.append(att)
            mins = companyRoomMinutes[roomName]

            times = []
            for day in [saturday, sunday]:
                secs = earliestTime.total_seconds()
                while secs < latestTime.total_seconds():
                    newTime = day + timedelta(seconds = secs)
                    newTimeInterval = TimeInterval(newTime, timedelta(minutes=mins))
                    if (day + latestTime) < newTimeInterval.end:
                        break
                    hasBreak = False
                    for b in breaks:
                        if b.isIntersecting(newTimeInterval):
                            secs += b.length.total_seconds()
                            hasBreak = True
                            break
                    if not hasBreak:
                        times.append(newTime)
                        secs += newTimeInterval.length.total_seconds()

            c.addCompanyRoom(
                times,
                timedelta(minutes=mins),
                candidates
            )
            i+=1
        else:
            break

print('done readin')

getTime = lambda day, hour, minute: day + timedelta(hours=hour, minutes=minute)

setRandomSeed(None)

# maybe shuffle

chosenAttendees = [
    a for a in attendees 
    if any(c.wantsAttendee(a) for c in companies)
]
    
def getUtility():
    return sum(sum([app.getUtility() for app in c.getAppointments()]) for c in companies)

noApps = sum(len(c.getAppointments()) for c in companies)

def getNoCompanies(att: Attendee) -> int:
    return len([c for c in companies if c.wantsAttendee(att)])

getDateStrFromApp = lambda app: app.time.isoformat()

def getNoEmptyApps(time, length):
    noEmptyApps = 0
    for c in companies:
        for app in c.getAppointments():
            if app.isEmpty() and app.intersects(time, length):
                noEmptyApps += 1
    return noEmptyApps

timeDeltaToMins = lambda time: time.total_seconds() / 60

printColLen = 12
firstColLen = 150
timeColLen = 24
timeColMinutes = 60
def printApps():
    formatCol = lambda s: s.rjust(printColLen, ' ')
    
    times = getSomeTimes(saturday, timeColMinutes) + getSomeTimes(sunday, timeColMinutes)
        #+ getSomeTimes(sunday, timeColMinutes)
    timeStrs = [t.strftime("%b %d %H:%M").center(timeColLen - 1, ' ') for t in times]

    headerRow = (firstColLen * ' ') + "|" + "|".join([formatCol(c) for c in  timeStrs]) + "|"
    print(headerRow)
    print('-'*len(headerRow))

    timeToLength = lambda time: int((timeDeltaToMins(time) / timeColMinutes) * timeColLen)

    for c in companies:
        for room in c.rooms:
            firstCol = f'{str(room)} ({",".join(str(c.uid) for c in room.candidates)})'.rjust(firstColLen, ' ')
            restOfCols = ' ' * (timeColLen * len(timeStrs))
            for app in sorted(room.appointments, key=lambda a: a.time.timestamp()):
                startIndex, i = -1, 0
                assert(min(times) <= app.time < max(times) + timedelta(minutes=timeColMinutes))
                while i < len(times):
                    if app.time == times[i]:
                        startIndex = (i * timeColLen) + timeToLength(app.time - times[i])
                        break
                    if i == len(times) - 1 or app.time < times[i+1]:
                        startIndex = (i * timeColLen) + timeToLength(app.time - times[i])
                        break
                    i += 1
                lengthIndex = timeToLength(app.length)
                endIndex = startIndex + lengthIndex
                #content = str(app.time.strftime('%H:%M')).center(lengthIndex-2, '-') if not app.isEmpty() else 'x' * (lengthIndex-2)
                content = str(app.attendee.uid).center(lengthIndex-2, '-') if not app.isEmpty() else 'x' * (lengthIndex-2)
                content = '|' + content + '|'
                assert(restOfCols[startIndex:endIndex] == (' '*len(content)))
                restOfCols = restOfCols[:startIndex] + content + restOfCols[endIndex:]

            print(firstCol + '|' + restOfCols)
            
    print('')

def canSwapBoth(app1, att1, app2, att2):
    assert(not(app1 is None and app2 is None))
    return app2 is None or app2.canSwap(att1) and (app1 is None or app1.canSwap(att2))

def swapBoth(app1, att1, app2, att2):
    assert(canSwapBoth(app1, att1, app2, att2))
    if app2:
        app2.swap(att1)
    if app1:
        app1.swap(att2)

def tryMatchEveryone(atts: List[Attendee]):

    atts = sorted(atts, key = lambda att: -len(att.commitments))
    noCompaniesCache = {a.uid: getNoCompanies(a) for a in atts}

    while True:
        changed = False

        for i in reversed(range(1, max([getNoCompanies(a) for a in atts])+1)):
            ith_atts = [a for a in atts if noCompaniesCache[a.uid]==i]
            
            while ith_atts:
                newAtt = ith_atts.pop()

                validApps = []
                for c in companies:
                    if c.wantsAttendee(newAtt):
                        for app in c.getAppointments():
                            if app.isEmpty() and app.canSwap(newAtt):
                                validApps.append(app)
                if validApps:
                    app = max(validApps, key=lambda app: (
                            getNoEmptyApps(app.time, app.length), 
                            newAtt.getPref(app.company)
                        )
                        # choose the least busy spot with the highest preference
                    )
                    app.swap(newAtt)
                    #print('free appointments:', sum([len([app for app in c.getAppointments() if app.isEmpty()]) for c in companies]))
                    changed = True
                    #printApps()

        if not changed:
            break

tryMatchEveryone(chosenAttendees)
printApps()
print(
    "candidates:", len(chosenAttendees),
    "spots:", noApps,
    "filled:", sum([len([app for app in c.getAppointments() if not app.isEmpty()]) for c in companies])
)

def printAtts():
    assigned = 0
    total = 0
    feasibleTotal = 0
    for att in sorted(chosenAttendees,key = lambda att: int(att.uid)):

        attCompaniesAccepted = [c for c in companies if c.hasAttendee(att)]
        attCompanies = [c for c in companies if c.wantsAttendee(att)]
        attCompaniesFeasible = [c for c in companies if c.wantsAttendee(att) and (c.hasAttendee(att) or any(app.isEmpty() for app in c.getAppointments()))]
        # attCompaniesFeasible excludes companies that are full

        assigned += len(attCompaniesAccepted)
        total += len(attCompanies)
        feasibleTotal += min(noCompanyAppointments, len(attCompaniesFeasible))

        attStr = (
            f'{str(att.uid).rjust(3, " ")}: '
            + f'{str([c.name + ("*" if c not in attCompaniesAccepted else "") for c in attCompanies])} '
        )
        if att.commitments:
            attStr += f'commitments: {str(att.commitments)}'
        print(attStr)

    print(f'avg appointments: {assigned/len(attendees)}/{feasibleTotal/len(attendees)}\nmatched: {assigned}/{total}\nfeasible matches: {assigned}/{feasibleTotal}')
  
printApps()
printAtts()

def getAttUtility(app, att):
    return att.prefsDic[app.company] if att and app else 0

def shouldSwap(app1, att1, app2, att2):
    canSwap = (
        (app1 is None or app1.canSwap(att2)) 
        and (app2 is None or app2.canSwap(att1))
    )
    currentUtil = getAttUtility(app1, att1) + getAttUtility(app2, att2)
    swapUtil = getAttUtility(app1, att2) + getAttUtility(app2, att1)
    return canSwap and currentUtil < swapUtil # strictly less than

def maxPref(atts):
          
    while True:

        appAtts = []
        for c in companies:
            appAtts.extend([(app, app.attendee) for app in c.getAppointments() if not app.isEmpty()])
        selectedAtts = set([att for app,att in appAtts])
        notSelectedAtts = set(atts) - selectedAtts
        appAtts.extend([(None, att) for att in notSelectedAtts])

        changed = False

        print("avg utility:", getUtility()/len(atts))
        
        i = 0
        for i in range(len(appAtts)-1):
            currentApp, currentAtt = appAtts[i]
            for j in range(i+1, len(appAtts)):
                existingApp, existingAtt = appAtts[j]
                if (currentApp is None) and (existingApp is None): continue
                if shouldSwap(currentApp, currentAtt, existingApp, existingAtt):
                    print("swapped!")
                    swapBoth(currentApp, currentAtt, existingApp, existingAtt)
                    printApps()
                    changed = True
                    break

            if changed: break
          
        if not changed: break
            
maxPref(attendees)
printApps()
print(
    "candidates:", len(chosenAttendees),
    "spots:", noApps,
    "filled:", sum([len([app for app in c.getAppointments() if not app.isEmpty()]) for c in companies])
)
#printAtts(ret)

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
                        app2.swap(None)
                        
                        if app1.canSwap(att2):
                            app1.swap(att2)
                            changed = True
                            #print(app1, "swapped", att.uid)
                            #printApps()
                            break
                        else:
                            changed2 = False

                            for k in range(i):
                                app3 = apps[k]
                                if app3.isEmpty(): continue
                                att3 = app3.attendee
                                app3.swap(None)
                                if app1.canSwap(att3) and app3.canSwap(att2):
                                    app1.swap(att3)
                                    app3.swap(att2)
                                    changed2 = True
                                    break
                                else:
                                    app3.swap(att3)

                            if not changed2:
                                app2.swap(att2)
                            else:
                                changed = True
                                break
                
        if not changed: break
            
moveToStartOfDay()
printApps()
