import { strictEqual } from 'assert';
import React from 'react';
import internal from 'stream';
import Icons from './Icons';
import './styles/Schedule.css';
import { CallAPIToJson, CallAPIJsonToJson, RestfulType, CallAPIJsonToDownloadCSV } from './Utilities';

interface IAttendee {
    name: string;
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
    isCoffeeChat: boolean;
    room: string;
}

class Appointment {
    att?: number;
    companyName: string;
    roomName: string;
    interval: Interval;
    isCoffeeChat: boolean;
    iApp: IAppointment;

    constructor(att: number|undefined, companyName: string, roomName: string, iApp: IAppointment){
        this.att = att;
        this.companyName = companyName;
        this.roomName = roomName;
        this.interval = Interval.fromStr(iApp);
        this.isCoffeeChat = iApp.isCoffeeChat;
        this.iApp = iApp;
    }
}
interface ICoffeeChat extends IInterval {
    candidates: number[];
    capcaity: number;
}

interface IRoom {
    apps: IAppointment[];
    candidates: number[];
    coffeeChat?: ICoffeeChat;
}

interface ISchedule {
    attendees: {[attId: number]: IAttendee};
    companies: {[companyName: string]: {[roomName: string]: IRoom}};
    conventionTimes: IInterval[];
    totalUtility: number;
    noAppointments: number;
    noAppointmentsNotEmpty: number;
    noAttendeeesChosen: number;
    varNoAppointments: number;
}

function addHours(date: Date, hours: number): Date {
    let newDate = new Date(date);
    newDate.setHours(date.getHours() + hours);
    return newDate
}

function getHeadings(schedule: ISchedule): Date[]{
    let conventionTimes = schedule.conventionTimes.map(
        time => Interval.fromStr(time)
    );

    let headings = [];
    for (let interval of conventionTimes){
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
var ATT_TO_INTERVIEWROOMS: {[att: number]: Set<string>} = {};
var ATT_TO_COFFEECHATROOMS: {[att: number]: Set<string>} = {};
var ROOM_TO_COFFEECHATAPPS: {[room: string]: Appointment[]} = {};

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
    {schedule: ISchedule, swapFunc: (isCoffeeChat: boolean, app1?: Object, att1?: number, app2?: Object, att2?: number) => void}
){
    let headings = getHeadings(schedule);
    ATT_TO_APPS = {}; // empty out prev
    ATT_TO_INTERVIEWROOMS = {};
    ATT_TO_COFFEECHATROOMS = {};

    ROOM_TO_COMPANY = {};
    ROOM_TO_COFFEECHATAPPS = {};

    function dragInterviewApp(ev: React.DragEvent<HTMLDivElement>) {
        console.log('draggin');

        let el = ev.target as any;
        let attStr = el.dataset.att;
        let timeStr = el.dataset.time;
        let roomStr = el.dataset.room;
        let appStr = el.dataset.app;

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

    function dropInterviewApp(ev: React.DragEvent<HTMLDivElement>) {
        console.log('droppin');
        ev.preventDefault();

        let el = ev.currentTarget;
        let attStr = el.dataset.att;
        let timeStr = el.dataset.time;
        let roomStr = el.dataset.room;
        let appStr = el.dataset.app;

        let otherAttStr = DRAGGING_APP.att;
        let otherTimeStr = DRAGGING_APP.time;
        let otherRoomStr = DRAGGING_APP.room;
        let otherAppStr = DRAGGING_APP.app;

        let room = roomStr || otherRoomStr;

        let [att1, att2] = [attStr, otherAttStr].map(s => s ? parseInt(s) : undefined);
        let [app1, app2] = [appStr, otherAppStr].map(s => s ? JSON.parse(s) : undefined);

        let getAppStr = (att?: number, time?: string|null) => `${att ? `Attendee ${att}` : 'Appointment'}${time ? ` @ ${time}` : ''}`;

        if (window.confirm(
                (!att1 && !app1) ? 
                `Are you sure you want to move ${getAppStr(att2, otherTimeStr)} out of the schedule (to the extra column) for ${room}?` : 
                `Are you sure you want to swap ${getAppStr(att2, otherTimeStr)} with ${getAppStr(att1, timeStr)} for ${room}?`
            )){
            console.log('hi');
            swapFunc(false, app1, att1, app2, att2);
        }
    }

    function allowInterviewDrop(ev: any) {

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

    function dragInterviewAppEnd(ev: any){
        document.querySelectorAll("#scheduleCompany tbody tr.fadeRoom").forEach(row => {
            row.classList.remove('fadeRoom');
        });
    }

    return <><h2>Interviews</h2><div id='scheduleCompany' className="scheduleTableContainer">
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

                        let timeToApp: {[time: number]: Appointment[]} = {};
                        let addedInCoffeeChat = false;
                        let i = 0;

                        ROOM_TO_COMPANY[roomName] = companyName;

                        let candidatesNotSelected = new Set(room.candidates);
                        for (let attId of room.candidates){
                            ATT_TO_INTERVIEWROOMS[attId] = ATT_TO_INTERVIEWROOMS[attId] || new Set();
                            ATT_TO_INTERVIEWROOMS[attId].add(roomName);
                        }
                        if (room.coffeeChat){
                            for (let attId of room.coffeeChat.candidates){
                                ATT_TO_COFFEECHATROOMS[attId] = ATT_TO_COFFEECHATROOMS[attId] || new Set();
                                ATT_TO_COFFEECHATROOMS[attId].add(roomName);
                            } 
                        }
                        /* as we iterate over apps, remove attendees who are selected */
                        for (let iApp of room.apps) {
                            let app = new Appointment(iApp.att, companyName, roomName, iApp);
                            if (app.att != null){
                                if (!app.isCoffeeChat){
                                    candidatesNotSelected.delete(app.att);
                                }
                                ATT_TO_APPS[app.att] = [...(ATT_TO_APPS[app.att] || []), app];
                            }
                            if (app.isCoffeeChat){
                                ROOM_TO_COFFEECHATAPPS[roomName] = [...(ROOM_TO_COFFEECHATAPPS[roomName] || []), app];
                                if (addedInCoffeeChat){
                                    continue; // only use one coffee chat
                                } else {
                                    addedInCoffeeChat = true;
                                }
                            }
                            let interval = app.interval;

                            for (;i < headings.length && addHours(headings[i], 1) <= interval.start; i++){}

                            timeToApp[+headings[i]] = timeToApp[+headings[i]] || [];
                            timeToApp[+headings[i]].push(app);
                        }
                        return <tr data-room={roomName}>
                            <td>{roomName}</td>
                            {headings.map(heading => <td key={+heading}>{
                                (timeToApp[+heading] || []).map(app => {
                                    let interval = app.interval;
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
                                            data-att={app.isCoffeeChat ? null : app.att}
                                            data-time={dateToTimeStr(interval.start)} 
                                            data-room={roomName} 
                                            data-app={app.isCoffeeChat ? null : JSON.stringify(app.iApp as Object)}
                                            className={`app col centerAll ${app.att ? '' : 'empty'} ${app.isCoffeeChat ? 'cc' : ''}`} 
                                            draggable={app.att != null && !app.isCoffeeChat}
                                            onDragStart={app.isCoffeeChat ? ()=>{} : dragInterviewApp} 
                                            onDragEnd={app.isCoffeeChat ? ()=>{} : dragInterviewAppEnd}
                                            onDrop={app.isCoffeeChat ? ()=>{} : dropInterviewApp} 
                                            onDragOver={app.isCoffeeChat ? ()=>{} : allowInterviewDrop}
                                        >
                                            {app.isCoffeeChat ? <div className='ccIcon'>{Icons.Coffee}</div> : null}
                                            <div className='appLength'>{interval.lengthMins}m</div>
                                            <span className='appAtt'>{app.isCoffeeChat ? 'coffee chat' : app.att || '?'}</span>
                                            <span className='appTime'>{dateToTimeStr(interval.start)}</span>
                                            <span className='appPref'>{att == null || app.isCoffeeChat ? null : `pref: ${att?.prefs[companyName]}`}</span>
                                        </div>
                                    </div>
                                })
                            }</td>)}
                            <td><div className="row centerCross">
                                <div className="appContainer notSelected centerAll">
                                    <div 
                                        className={`app removeApp col centerAll`} 
                                        data-room={roomName} 
                                        onDrop={dropInterviewApp} 
                                        onDragOver={allowInterviewDrop}
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
                                            onDragStart={dragInterviewApp} 
                                            onDragEnd={dragInterviewAppEnd}
                                            onDrop={dropInterviewApp} 
                                            onDragOver={allowInterviewDrop}
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
    </div></>
}

function ScheduleCoffeeChat(
    {schedule, swapFunc}: 
    {schedule: ISchedule, swapFunc: (isCoffeeChat: boolean, app1?: Object, att1?: number, app2?: Object, att2?: number) => void}
){
    function dragCCApp(ev: React.DragEvent<HTMLDivElement>) {
        console.log('draggin');

        let el = ev.target as any;
        let attStr = el.dataset.att;
        let timeStr = el.dataset.time;
        let roomStr = el.dataset.room;
        let appStr = el.dataset.app;

        DRAGGING_APP.att = attStr ?? '';
        DRAGGING_APP.time = timeStr ?? '';
        DRAGGING_APP.room = roomStr ?? '';
        DRAGGING_APP.app = appStr ?? '';

        document.querySelectorAll(
            `#scheduleCoffeeChat tbody tr:not([data-room='${roomStr}'])`
        ).forEach(row => {
            row.classList.add('fadeRoom');
        });
    }

    function dropCCApp(ev: React.DragEvent<HTMLDivElement>) {
        console.log('droppin');
        ev.preventDefault();

        let el = ev.currentTarget;
        let attStr = el.dataset.att;
        let timeStr = el.dataset.time;
        let roomStr = el.dataset.room;
        let appStr = el.dataset.app;

        let otherAttStr = DRAGGING_APP.att;
        let otherTimeStr = DRAGGING_APP.time;
        let otherRoomStr = DRAGGING_APP.room;
        let otherAppStr = DRAGGING_APP.app;

        let room = roomStr || otherRoomStr;

        let [att1, att2] = [attStr, otherAttStr].map(s => s ? parseInt(s) : undefined);
        let [app1, app2] = [appStr, otherAppStr].map(s => s ? JSON.parse(s) : undefined);

        let getAppStr = (att?: number, time?: string|null) => `${att ? `Attendee ${att}` : 'Appointment'}${time ? ` @ ${time}` : ''}`;

        if (window.confirm(
                (!att1 && !app1) ? 
                `Are you sure you want to move ${getAppStr(att2, otherTimeStr)} out of the schedule (to the extra column) for ${room}?` : 
                `Are you sure you want to swap ${getAppStr(att2, otherTimeStr)} with ${getAppStr(att1, timeStr)} for ${room}?`
            )){
            console.log('hi');
            swapFunc(true, app1, att1, app2, att2);
        }
    }

    function allowCCDrop(ev: any) {

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

    function dragCCAppEnd(ev: any){
        document.querySelectorAll("#scheduleCoffeeChat tbody tr.fadeRoom").forEach(row => {
            row.classList.remove('fadeRoom');
        });
    }

    return <><h2>Coffee Chats</h2><div id='scheduleCoffeeChat' className="scheduleTableContainer">
        <table>
            <thead><tr>
                <th id='roomNameCol'>Room Name</th>
                <th>Appointments</th>
                <th id='extra'>Extra</th>
            </tr></thead>
            <tbody>
                {Object.entries(schedule.companies).map(([companyName, rooms]) => {
                    return Object.entries(rooms).map(([roomName, room]) => {
                        let cc = room.coffeeChat;
                        if (cc == null){
                            return null;
                        }        
                        let interval = Interval.fromStr(cc);    
                        
                        let candidatesNotSelected = new Set(cc.candidates);
                        return <tr data-room={roomName}>
                            <td className="ccRowLabel">
                                <p className="ccRoomName">{roomName}</p>
                                <p className="ccRoomDate">({dateToStr(interval.start)}, {dateToStr(interval.end)})</p>
                            </td>
                            <td><div className="row centerCross">{room.apps.map(app => {
                                if (!app.isCoffeeChat){ 
                                    return null; 
                                }
                                let att = app.att == null ? null : schedule.attendees[app.att!];
                                if (att != null){
                                    candidatesNotSelected.delete(app.att!);
                                }
                                return <div className="appContainer centerAll">
                                    <div
                                        data-att={app.att}
                                        data-time={dateToTimeStr(interval.start)} 
                                        data-room={roomName} 
                                        data-app={JSON.stringify(app as Object)}
                                        className={`app col centerAll ${app.att ? '' : 'empty'} cc`} 
                                        draggable={app.att != null}
                                        onDragStart={dragCCApp} 
                                        onDragEnd={dragCCAppEnd}
                                        onDrop={dropCCApp} 
                                        onDragOver={allowCCDrop}
                                    >
                                        <div className='ccIcon'>{Icons.Coffee}</div>
                                        <div className='appLength'>{interval.lengthMins}m</div>
                                        <span className='appAtt'>{app.att || '?'}</span>
                                        <span className='appTime'>{dateToTimeStr(interval.start)}</span>
                                        <span className='appPref'>{app.att == null ? null : `pref: ${att?.prefs[companyName]}`}</span>
                                    </div>
                                </div>
                            })}</div></td>
                            <td><div className="row centerCross">
                                <div className="appContainer notSelected centerAll">
                                    <div 
                                        className={`app removeApp col centerAll cc`} 
                                        data-room={roomName} 
                                        onDrop={dropCCApp} 
                                        onDragOver={allowCCDrop}
                                    >
                                        <span className='appAtt'>remove</span>
                                    </div>
                                </div>
                                {Array.from(candidatesNotSelected).map(attId => {
                                    let att = schedule.attendees[attId];
                                    return <div key={attId} className="appContainer notSelected centerAll">
                                        <div 
                                            className={`app col centerAll cc`} 
                                            draggable 
                                            data-att={attId} 
                                            data-room={roomName} 
                                            onDragStart={dragCCApp} 
                                            onDragEnd={dragCCAppEnd}
                                            onDrop={dropCCApp} 
                                            onDragOver={allowCCDrop}
                                        >   
                                            <div className='ccIcon'>{Icons.Coffee}</div>
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
    </div></>
}

function ScheduleAttendees(
        {schedule,}: 
        {schedule: ISchedule}
    ){

    let headings = getHeadings(schedule);

    return <><h2>Attendees</h2><div id='scheduleAttendee' className="scheduleTableContainer">
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
                    if ((
                        (ATT_TO_INTERVIEWROOMS[attId] || new Set()).size + 
                        (ATT_TO_COFFEECHATROOMS[attId] || new Set()).size) == 0
                    ){
                        return;
                    }

                    let apps = ATT_TO_APPS[attId] || [];
                    apps.sort((a,b) => +Interval.fromStr(a.iApp).start - +Interval.fromStr(b.iApp).start);

                    let interviewRoomsNotSelected = new Set(ATT_TO_INTERVIEWROOMS[attId]);
                    let coffeeChatRoomsNotSelected = new Set(ATT_TO_COFFEECHATROOMS[attId]);
                    let i = 0;
                    for (let app of apps) {
                        if (app.att != null){
                            let roomsNotSelected = app.isCoffeeChat ? coffeeChatRoomsNotSelected : interviewRoomsNotSelected;
                            roomsNotSelected.delete(app.roomName);
                        }
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
                    /* as we iterate over apps, remove companies who are selected */
                    return <tr>
                        <td>{attId}. {att.name}</td>
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
                                    <div className={`app col centerAll ${app.att ? '' : 'empty'} ${app.isCoffeeChat ? 'cc' : ''}`}>
                                        {app.isCoffeeChat ? <div className='ccIcon'>{Icons.Coffee}</div> : null}
                                        <div className='appLength'>{interval.lengthMins}m</div>
                                        <span className='appAtt' title={app.roomName}>{app.roomName}</span>
                                        <span className='appTime'>{dateToTimeStr(interval.start)}</span>
                                        <span className='appPref'>{att == null ? null : `pref: ${att?.prefs[app.companyName]}`}</span>
                                    </div>
                                </div>
                            })
                        }</td>)}
                        <td><div className="row">{[false, true].map(isCoffeeChat => {
                            let roomsNotSelected = isCoffeeChat ? coffeeChatRoomsNotSelected : interviewRoomsNotSelected;
                            return Array.from(roomsNotSelected).map(roomName => (
                                <div key={attId} className="appContainer notSelected centerAll">
                                    <div className={`app col centerAll ${isCoffeeChat ? 'cc' : ''}`}>
                                        {isCoffeeChat ? <div className='ccIcon'>{Icons.Coffee}</div> : null}
                                        <span className='appPref'>pref: {att.prefs[ROOM_TO_COMPANY[roomName]]}</span>
                                        <span className='appAtt'>{ROOM_TO_COMPANY[roomName]}</span>
                                    </div>
                                </div>
                            )
                        )})}</div></td>
                    </tr>
                })}
            </tbody>
        </table>
    </div></>
}

function SchedulePage(){

    let [scheduleObj, setScheduleObj] = React.useState(null as ISchedule|null);
    const [isLoading, setIsLoading] = React.useState(false);

	let gen = () => {
        setIsLoading(true);
		CallAPIToJson(
            '/generateSchedule', 
            RestfulType.GET
        ).then(({data}: {data: ISchedule}) => {
            setScheduleObj(data);
		}).catch((res)=>{
			console.log("res", res);
			alert(res["error"]);
		}).finally(()=>setIsLoading(false));
	}

	let swap = (isCoffeeChat: boolean, app1?: Object, att1?: number, app2?: Object, att2?: number) => {
        setIsLoading(true);
		CallAPIJsonToJson('/swapSchedule', RestfulType.POST, {
            'data': {
                ...(scheduleObj as Object),
                'app1': app1 ?? null,
                'att1': att1 ?? null,
                'app2': app2 ?? null,
                'att2': att2 ?? null,
                'isCoffeeChat': isCoffeeChat
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
		CallAPIJsonToDownloadCSV(
            '/writeSchedule', 
            RestfulType.POST, 
            {'data': scheduleObj}
        ).finally(()=>setIsLoading(false));
	}

    return <div id='schedulePage' className='col centerCross'>
        <button id='generateButt' className='row centerAll' onClick={gen}>
            {Icons.Generate}<p>generate schedule</p>
        </button>
        {isLoading ? <div className="loader"></div> : (scheduleObj==null ? null :
            <div className="col centerCross">
                <div id='schedulesStats' className='row center'>
                    <p>Appointments Filled: <span>{scheduleObj.noAppointmentsNotEmpty}/{scheduleObj.noAppointments}</span></p>
                    <p>Avg No. Appointments: <span>{(scheduleObj.noAppointmentsNotEmpty/scheduleObj.noAttendeeesChosen).toFixed(2)}</span></p>
                    <p>Var of No. Appointments: <span>{scheduleObj.varNoAppointments.toFixed(2)}</span></p>
                    <p>Average Rank: <span>{(
                        scheduleObj.totalUtility/scheduleObj.noAppointmentsNotEmpty).toFixed(2)
                    }</span></p>
                </div>
                <div id='schedules'>
                    <ScheduleCompany schedule={scheduleObj} swapFunc={swap}/>
                    <ScheduleCoffeeChat schedule={scheduleObj} swapFunc={swap}/>
                    <ScheduleAttendees schedule={scheduleObj}/>
                </div>
                <button id="writeScheduleButt" className='row centerAll' onClick={writeSchedule}>
                    {Icons.Edit}<p>write schedule</p>
                </button>
            </div>
        )}
    </div>
}

export default SchedulePage;