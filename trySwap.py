from __future__ import annotations
from serverUtilities import Appointment, AppointmentIntersects, Attendee, Company, ValidationException, TimeInterval, canSwapBoth, getJsonSchedule, swapBoth
from Schema import *

def trySwap(
            companies: list[Company], 
            attendees: list[Attendee], 
            interviewTimes: list[TimeInterval],
            app1: Optional[Appointment], 
            att1: Optional[Attendee], 
            app2: Optional[Appointment], 
            att2: Optional[Attendee]
        ) -> dict:
        
    appIntersects = AppointmentIntersects(companies)

    if not canSwapBoth(app1, att1, app2, att2, appIntersects):
        reason1 = None if app1 is None else app1.cantSwapReason(att2, appIntersects, app2)
        reason2 = None if app2 is None else app2.cantSwapReason(att1, appIntersects, app1)
        reason = reason1 or reason2
        raise ValidationException(f'Could not swap: {reason}')

    swapBoth(app1, att1, app2, att2, appIntersects)
    return getJsonSchedule(
        companies, 
        attendees, 
        interviewTimes
    )