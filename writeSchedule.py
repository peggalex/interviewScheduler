from serverUtilities import EXCEL_DATETIME_FORMAT, Appointment, Company

def writeSchedule(filename: str, companies: list[Company]):
    apps: list[Appointment] = []
    for company in companies:
        apps.extend([a for a in company.getAppointments() if not a.isEmpty()])
    apps.sort(key = lambda a: (a.company.name, a.companyRoom.name, a.time))
    with open(filename, 'w') as f:
        writeCSVLine = lambda lst: f.write(','.join(lst) + '\n')

        writeCSVLine(['ASNA ID', 'Name', 'Company', 'Is Coffee Chat?', 'Start Time', 'End Time'])
        for app in apps:
            writeCSVLine([
                str(app.attendee.uid), 
                app.attendee.name,
                app.companyRoom.name, 
                str(app.isCoffeeChat()),
                app.time.strftime(EXCEL_DATETIME_FORMAT), 
                app.end.strftime(EXCEL_DATETIME_FORMAT)
            ])