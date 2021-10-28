import { strictEqual } from 'assert';
import React from 'react';
import Icons from './Icons';
import './styles/Schedule.css';
import { CallAPI, CallAPIJson, RestfulType } from './Utilities';

interface IAttendee {
    commitments: IInterval[];
    prefs: {[company: string]: number};
}

interface IInterval {
    start: string;
    end: string;
}

class Interval {
    start: Date;
    end: Date;
    lengthMins: number;

    constructor(start: Date, end: Date){
        this.start = start;
        this.end = end;
        this.lengthMins = (+end - +start) / 1000 / 60;
    }

    static fromStr(intervalStr: IInterval): Interval {
        return new Interval(
            new Date(intervalStr.start),
            new Date(intervalStr.end)
        )
    }
}

interface IAppointment extends IInterval {
    att?: number;
    room: string;
}

class Appointment {
    att?: number;
    companyName: string;
    roomName: string;
    iApp: IAppointment;

    constructor(att: number, companyName: string, roomName: string, iApp: IAppointment){
        this.att = att;
        this.companyName = companyName;
        this.roomName = roomName;
        this.iApp = iApp;
    }
}

interface IRoom {
    apps: IAppointment[];
    candidates: number[];
}

interface ISchedule {
    attendees: {[attId: number]: IAttendee};
    companies: {[companyName: string]: {[roomName: string]: IRoom}};
    interviewTimes: IInterval[];
    totalUtility: number;
    noAppointments: number;
    noAttendeesChosen: number;
}

function addHours(date: Date, hours: number): Date {
    let newDate = new Date(date);
    newDate.setHours(date.getHours() + hours);
    return newDate
}

function getHeadings(schedule: ISchedule): Date[]{
    let interviewTimes = schedule.interviewTimes.map(
        time => Interval.fromStr(time)
    );

    let headings = [];
    for (let interval of interviewTimes){
        for (let t = interval.start; t < interval.end; t = addHours(t, 1)){
            headings.push(t);
        }
    }
    return headings;
}

const dateToTimeStr = (date: Date) => new Intl.DateTimeFormat(
    'en-US', 
    { hour: 'numeric', minute: 'numeric', hour12: true }
).format(date);


function dateToStr(date: Date){
    let time = dateToTimeStr(date);
    let month = new Intl.DateTimeFormat('en-US', { month: 'short'}).format(date);
    let day = date.getDate();
    return `${month} ${day}, ${time}`;
}

var ATT_TO_APPS: {[att: number]: Appointment[]} = {};
var ROOM_TO_COMPANY: {[room: string]: string} = {};
var ATT_TO_ROOMS: {[att: number]: Set<string>} = {};
var ATT_TO_BREAKS = {};

var DRAGGING_APP: {
    app: string|null, 
    room: string|null, 
    att: string|null, 
    time: string|null
} = {
    'app': null,
    'room': null,
    'att': null,
    'time': null
}

function ScheduleCompany(
    {schedule, swapFunc}: 
    {schedule: ISchedule, swapFunc: (app1?: Object, att1?: number, app2?: Object, att2?: number) => void}
){
    let headings = getHeadings(schedule);
    ATT_TO_APPS = {}; // empty out prev
    ATT_TO_ROOMS = {};
    ROOM_TO_COMPANY = {};

    //const attKey = 'att', timeKey = 'time', roomKey = 'room', appKey = 'app';

    function dragApp(ev: React.DragEvent<HTMLDivElement>) {
        console.log('draggin');

        let el = ev.target as any;
        let attStr = el.dataset.att;
        let timeStr = el.dataset.time;
        let roomStr = el.dataset.room;
        let appStr = el.dataset.app;

        /*ev.dataTransfer!.setData(attKey, attStr ?? '');
        ev.dataTransfer!.setData(timeKey, timeStr ?? '');
        ev.dataTransfer!.setData(roomKey, roomStr ?? '');        
        ev.dataTransfer!.setData(appKey, appStr ?? '');*/

        DRAGGING_APP.att = attStr ?? '';
        DRAGGING_APP.time = timeStr ?? '';
        DRAGGING_APP.room = roomStr ?? '';
        DRAGGING_APP.app = appStr ?? '';

        document.querySelectorAll(
            `#scheduleCompany tbody tr:not([data-room='${roomStr}'])`
        ).forEach(row => {
            row.classList.add('fadeRoom');
        });
    }

    function dropApp(ev: React.DragEvent<HTMLDivElement>) {
        console.log('droppin');
        ev.preventDefault();

        let el = ev.currentTarget;
        let attStr = el.dataset.att;
        let timeStr = el.dataset.time;
        let roomStr = el.dataset.room;
        let appStr = el.dataset.app;

        /*let otherAttStr = ev.dataTransfer!.getData(attKey);
        let otherTimeStr = ev.dataTransfer!.getData(timeKey);
        let otherRoomStr = ev.dataTransfer!.getData(roomKey);
        let otherAppStr = ev.dataTransfer!.getData(appKey);*/

        let otherAttStr = DRAGGING_APP.att;
        let otherTimeStr = DRAGGING_APP.time;
        let otherRoomStr = DRAGGING_APP.room;
        let otherAppStr = DRAGGING_APP.app;

        let room = roomStr || otherRoomStr;

        let [att1, att2] = [attStr, otherAttStr].map(s => s ? parseInt(s) : undefined);
        let [app1, app2] = [appStr, otherAppStr].map(s => s ? JSON.parse(s) : undefined);

        let getAppStr = (att?: number, time?: string|null) => `${att ? `Attendee ${att}` : 'Appointment'}${time ? ` @ ${time}` : ''}`;

        if (!att1 && !app1){
            
        }
        if (window.confirm(
                (!att1 && !app1) ? 
                `Are you sure you want to move ${getAppStr(att2, otherTimeStr)} out of the schedule (to the extra column) for ${room}?` : 
                `Are you sure you want to swap ${getAppStr(att2, otherTimeStr)} with ${getAppStr(att1, timeStr)} for ${room}?`
            )){
            console.log('hi');
            swapFunc(app1, att1, app2, att2);
        }
    }

    function allowDrop(ev: any) {

        let el = ev.target;
        let attStr = el.dataset.att;
        let timeStr = el.dataset.time;
        let roomStr = el.dataset.room;
        let appStr = el.dataset.app;

        let otherAttStr = DRAGGING_APP.att;
        let otherTimeStr = DRAGGING_APP.time;
        let otherRoomStr = DRAGGING_APP.room;
        let otherAppStr = DRAGGING_APP.app;

        if (!(
            (!timeStr && !otherTimeStr) ||
            (timeStr == otherTimeStr) ||
            (roomStr != otherRoomStr) ||
            (!attStr && !otherAttStr) ||
            (!appStr && !otherAppStr)
        )){
            // if these conditions are false, allow drag by preventDefault
            ev.preventDefault();
        }
    }

    function dragAppEnd(ev: any){
        document.querySelectorAll("#scheduleCompany tbody tr.fadeRoom").forEach(row => {
            row.classList.remove('fadeRoom');
        });
    }

    return <div id='scheduleCompany'>
        <table>
            <thead><tr>
                <th id='roomNameCol'>Room Name</th>
                {headings.map((time, i) => 
                    <th key={i}>{dateToStr(time)}</th>
                )}
                <th id='extra'>Extra</th>
            </tr></thead>
            <tbody>
                {Object.entries(schedule.companies).map(([companyName, rooms]) => {
                    return Object.entries(rooms).map(([roomName, room]) => {

                        let timeToApp: {[time: number]: IAppointment[]} = {}
                        let i = 0;
                        for (let app of room.apps) {
                            let interval = Interval.fromStr(app);

                            for (;i < headings.length && addHours(headings[i], 1) <= interval.start; i++){}

                            timeToApp[+headings[i]] = timeToApp[+headings[i]] || [];
                            timeToApp[+headings[i]].push(app);
                        }
                        let candidatesNotSelected = new Set(room.candidates);
                        for (let attId of room.candidates){
                            console.log('att:', attId, 'company:', companyName);
                            ATT_TO_ROOMS[attId] = ATT_TO_ROOMS[attId] || new Set();
                            ATT_TO_ROOMS[attId].add(roomName);
                            ROOM_TO_COMPANY[roomName] = companyName;
                        }
                        /* as we iterate over apps, remove attendees who are selected */
                        return <tr data-room={roomName}>
                            <td>{roomName}</td>
                            {headings.map(heading => <td key={+heading}>{
                                (timeToApp[+heading] || []).map(app => {
                                    if (app.att != null){
                                        candidatesNotSelected.delete(app.att);
                                        ATT_TO_APPS[app.att] = ATT_TO_APPS[app.att] || [];
                                        ATT_TO_APPS[app.att].push(new Appointment(app.att, companyName, roomName, app));
                                    }
                                    let interval = Interval.fromStr(app);
                                    let lengthPercent = (interval.lengthMins / 60) * 100;
                                    let startPercent = (interval.start.getMinutes() / 60) * 100;
                                    let att = app.att == null ? null : schedule.attendees[app.att!];
                                    
                                    return <div 
                                        className="appContainer centerAll" style={{
                                            left: `${startPercent}%`,
                                            width: `${lengthPercent}%`
                                        }}
                                        key={roomName + interval.toString()}
                                    >
                                        <div
                                            data-att={app.att}
                                            data-time={dateToTimeStr(interval.start)} 
                                            data-room={roomName} 
                                            data-app={JSON.stringify(app as Object)}
                                            className={`app col centerAll ${app.att ? '' : 'empty'}`} 
                                            draggable={app.att != null}
                                            onDragStart={dragApp} 
                                            onDragEnd={dragAppEnd}
                                            onDrop={dropApp} 
                                            onDragOver={allowDrop}
                                        >
                                            <div className='appLength'>{interval.lengthMins}m</div>
                                            <span className='appAtt'>{app.att || '?'}</span>
                                            <span className='appTime'>{dateToTimeStr(interval.start)}</span>
                                            <span className='appPref'>{att == null ? null : `pref: ${att?.prefs[companyName]}`}</span>
                                        </div>
                                    </div>
                                })
                            }</td>)}
                            <td><div className="row">
                                <div className="appContainer notSelected centerAll">
                                    <div 
                                        className={`app removeApp col centerAll`} 
                                        data-room={roomName} 
                                        onDrop={dropApp} 
                                        onDragOver={allowDrop}
                                    >
                                        <span className='appAtt'>remove</span>
                                    </div>
                                </div>
                                {Array.from(candidatesNotSelected).map(attId => {
                                    let att = schedule.attendees[attId];
                                    return <div key={attId} className="appContainer notSelected centerAll">
                                        <div 
                                            className={`app col centerAll`} 
                                            draggable 
                                            data-att={attId} 
                                            data-room={roomName} 
                                            onDragStart={dragApp} 
                                            onDragEnd={dragAppEnd}
                                            onDrop={dropApp} 
                                            onDragOver={allowDrop}
                                        >
                                            <span className='appPref'>pref: {att.prefs[companyName]}</span>
                                            <span className='appAtt'>{attId}</span>
                                        </div>
                                    </div>
                                })}
                            </div></td>
                        </tr>
                    })
                })}
            </tbody>
        </table>
    </div>
}


function ScheduleAttendees(
        {schedule,}: 
        {schedule: ISchedule}
    ){

    let headings = getHeadings(schedule);

    return <div id='scheduleAttendee'>
        <table>
            <thead><tr>
                <th id='roomNameCol'>Attendee</th>
                {headings.map((time, i) => 
                    <th key={i}>{dateToStr(time)}</th>
                )}
                <th id='extra'>Extra</th>
            </tr></thead>
            <tbody>
                {Object.entries(schedule.attendees).map(([attIdStr, att]) => {
                    let timeToApp: {[time: number]: Appointment[]} = {};
                    let timeToBreak: {[time: number]: Interval[]} = {};
                    let attId = parseInt(attIdStr); // ts considers keys as string
                    if ((ATT_TO_ROOMS[attId] || new Set()).size == 0) return;
                    let i = 0;
                    let apps = ATT_TO_APPS[attId] || [];
                    apps.sort((a,b) => +Interval.fromStr(a.iApp).start - +Interval.fromStr(b.iApp).start)
                    for (let app of apps) {
                        let interval = Interval.fromStr(app.iApp);

                        for (;i < headings.length && addHours(headings[i], 1) <= interval.start; i++){}

                        timeToApp[+headings[i]] = timeToApp[+headings[i]] || [];
                        timeToApp[+headings[i]].push(app);
                    }
                    i = 0;
                    for (let breakStr of att.commitments) {
                        let interval = Interval.fromStr(breakStr);

                        for (;i < headings.length && addHours(headings[i], 1) <= interval.start; i++){}

                        timeToBreak[+headings[i]] = timeToBreak[+headings[i]] || [];
                        timeToBreak[+headings[i]].push(interval);
                    }
                    let roomsNotSelected = new Set(ATT_TO_ROOMS[attId]); 
                    /* as we iterate over apps, remove companies who are selected */
                    return <tr>
                        <td>{attId}</td>
                        {headings.map(heading =><td key={+heading}>{
                            (timeToBreak[+heading] || []).map(interval => {
                                let lengthPercent = (interval.lengthMins / 60) * 100;
                                let startPercent = (interval.start.getMinutes() / 60) * 100;
                                return <div 
                                    data-app={`${dateToStr(interval.start)} ${dateToStr(interval.end)}`} 
                                    className="appContainer centerAll" style={{
                                        left: `${startPercent}%`,
                                        width: `${lengthPercent}%`
                                    }}
                                    key={attId + interval.toString()}
                                >
                                    <div className={`app col centerAll ${'empty'}`}>
                                        <div className='appLength'>{interval.lengthMins}m</div>
                                        <span className='appPref'></span>
                                        <span className='appAtt'>{'break'}</span>
                                        <span className='appTime'>{dateToTimeStr(interval.start)}</span>
                                    </div>
                                </div>
                            })
                        }{
                            (timeToApp[+heading] || []).map(app => {
                                if (app.att != null){
                                    roomsNotSelected.delete(app.roomName);
                                }
                                let interval = Interval.fromStr(app.iApp);
                                let lengthPercent = (interval.lengthMins / 60) * 100;
                                let startPercent = (interval.start.getMinutes() / 60) * 100;
                                let att = app.att == null ? null : schedule.attendees[app.att!];
                                return <div 
                                    data-app={`${dateToStr(interval.start)} ${dateToStr(interval.end)}`} 
                                    className="appContainer centerAll" style={{
                                        left: `${startPercent}%`,
                                        width: `${lengthPercent}%`
                                    }}
                                    key={attId + interval.toString()}
                                >
                                    <div className={`app col centerAll ${app.att ? '' : 'empty'}`}>
                                        <div className='appLength'>{interval.lengthMins}m</div>
                                        <span className='appAtt' title={app.roomName}>{app.roomName}</span>
                                        <span className='appTime'>{dateToTimeStr(interval.start)}</span>
                                        <span className='appPref'>{att == null ? null : `pref: ${att?.prefs[app.companyName]}`}</span>
                                    </div>
                                </div>
                            })
                        }</td>)}
                        <td><div className="row">{Array.from(roomsNotSelected).map(roomName => {
                            return <div key={attId} className="appContainer notSelected centerAll">
                                <div className={`app col centerAll`}>
                                    <span className='appPref'>pref: {att.prefs[ROOM_TO_COMPANY[roomName]]}</span>
                                    <span className='appAtt'>{ROOM_TO_COMPANY[roomName]}</span>
                                </div>
                            </div>
                        })}</div></td>
                    </tr>
                })}
            </tbody>
        </table>
    </div>
}

function SchedulePage(){

    let [scheduleObj, setScheduleObj] = React.useState(null as ISchedule|null);
    const [isLoading, setIsLoading] = React.useState(false);

	let gen = () => {
        setIsLoading(true);
		CallAPI(
            '/generateSchedule', 
            RestfulType.GET
        ).then(({data}: {data: ISchedule}) => {
            setScheduleObj(data);
		}).catch((res)=>{
			console.log("res", res);
			alert(res["error"]);
		}).finally(()=>setIsLoading(false));
	}

	let swap = (app1?: Object, att1?: number, app2?: Object, att2?: number) => {
        setIsLoading(true);
		CallAPIJson('/swapSchedule', RestfulType.POST, {
            'data': {
                ...(scheduleObj as Object),
                'app1': app1 ?? null,
                'att1': att1 ?? null,
                'app2': app2 ?? null,
                'att2': att2 ?? null
            }
        }).then(({data}: {data: ISchedule}) => {
            setScheduleObj(data);
		}).catch((res)=>{
			console.log("res", res);
			alert(res["error"]);
		}).finally(()=>setIsLoading(false));
	}

	let writeSchedule = () => {
        setIsLoading(true);
		CallAPIJson(
            '/writeSchedule', 
            RestfulType.POST, 
            {'data': scheduleObj}
        ).then(({data: {filename}}: {data: {filename: string}}) => {
            alert(`written to file: '${filename}' in your app directory`);
		}).catch((res)=>{
			console.log("res", res);
			alert(res["error"]);
		}).finally(()=>setIsLoading(false));
	}

    return <div id='schedulePage' className='col centerCross'>
        <button id='generateButt' className='row centerAll' onClick={gen}>
            {Icons.Generate}<p>generate schedule</p>
        </button>
        {scheduleObj==null ? (isLoading ? <div className="loader"></div> : null) :
            <div>
                <div id='schedulesStats' className='row center'>
                    <p>Total Utility: <span>{scheduleObj.totalUtility}</span></p>
                    <p>Appointments Filled: <span>{scheduleObj.noAttendeesChosen}/{scheduleObj.noAppointments}</span></p>
                </div>
                <div id='schedules'>
                    <ScheduleCompany schedule={scheduleObj} swapFunc={swap}/>
                    <ScheduleAttendees schedule={scheduleObj}/>
                </div>
                <button onClick={writeSchedule}>write schedule</button>
            </div>
        }
    </div>
}

export default SchedulePage;