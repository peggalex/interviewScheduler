import { strictEqual } from 'assert';
import React from 'react';
import Icons from './Icons';
import './styles/Schedule.css';
import { CallAPI, RestfulType } from './Utilities';

enum ColumnType {
    STRING,
    INT,
    DATETIME
}

function ColumnTypeToStr(colType: ColumnType){
    switch (colType){
        case ColumnType.STRING:
            return 'string';
        case ColumnType.INT:
            return 'integer';
        case ColumnType.DATETIME:
            return 'datetime';
        default:
            throw Error(`unhandled col type for colTypeToStr(): ${ColumnType}`);
    }
}

interface IColumn{
    name: string;
    type: ColumnType;
    desc?: string;
    table?: Table;
}

class Table{
    name: string;
    endpoint: string;
    desc: string;
    columns: IColumn[];
    values: string[][];
    dependencies: Table[];
    isLoaded: boolean;

    constructor(name: string, endpoint: string, desc: string, columns: IColumn[], dependencies?: Table[]){
        this.name = name;
        this.endpoint = endpoint;
        this.desc = desc;
        this.dependencies = dependencies ?? [];
        this.columns = [];
        this.values = [];
        this.isLoaded = false;
        for (let col of columns){
            this.addColumn(col);
        }
    }

    addColumn(col: IColumn){
        this.columns.push(col);
        col.table = col.table ?? this; 
        /* if this col doesn't have a table, add this one as their table */
        return this;
    }

    isDependenciesLoaded(){
        return this.dependencies.every(t => t.isLoaded);
    }

    addValues(values: string[][]){
        if (values.some(r => r.length != this.columns.length)){
            alert('incorrect length of return table');
            throw Error('incorrect length of return table');
        }
        this.values = values;
        this.isLoaded = true;
    }
}

const interviewTimesTable: Table = new Table(
    'Interview Times',
    'readInterviewTimes',
    'This is a list of valid times for interviews.',
    [
        {
            name: 'Start Time',
            type: ColumnType.DATETIME
        },
        {
            name: 'End Time',
            type: ColumnType.DATETIME,
            desc: 'must be greater than start time'
        },
    ]
);

const companyNameCol: IColumn = {
    name: 'Company Name',
    type: ColumnType.STRING
}

const companiesTable: Table = new Table(
    'Companies',
    'readCompanyNames',
    'This is a list of companies participating.',
    [companyNameCol]
);

const roomNameCol: IColumn = {
    name: 'Room Name',
    type: ColumnType.STRING
}

const roomsTable: Table = new Table(
    'Company Rooms',
    'readRoomNames',
    'This is a list of company rooms.',
    [companyNameCol, roomNameCol, {
        name: 'Length',
        type: ColumnType.INT,
        desc: 'in minutes'
    }],
    [companiesTable]
);

const roomBreaksTable: Table = new Table(
    'Room Breaks',
    'readRoomBreaks',
    'This is a list of rooms belonging to a company.',
    [
        roomNameCol,
        {
            name: 'Start Time',
            type: ColumnType.DATETIME
        },
        {
            name: 'End Time',
            type: ColumnType.DATETIME,
            desc: 'must be greater than start time'
        }
    ],
    [interviewTimesTable, roomsTable]
);



const attendeeCol: IColumn = {
    name: 'Attendee ID',
    type: ColumnType.STRING
}

const attendeeTable: Table = new Table(
    'Attendees',
    'readAttendeeNames',
    'This is a list of rooms belonging to a company.',
    [attendeeCol]
);

const attendeeBreaksTable: Table = new Table(
    'Attendee Breaks',
    'readAttendeeBreaks',
    'This is a list of rooms belonging to a company.',
    [attendeeCol,
    {
        name: 'Start Time',
        type: ColumnType.DATETIME
    },
    {
        name: 'End Time',
        type: ColumnType.DATETIME,
        desc: 'must be greater than start time'
    }],
    [interviewTimesTable, attendeeTable]
);

const attendeePrefsTable: Table = new Table(
    'Attendee Preferences',
    'readAttendeePrefs',
    'This is a list of rooms belonging to a company.',
    [attendeeCol, companyNameCol,
    {
        name: 'Preference',
        type: ColumnType.INT,
        desc: 'the larger the better'
    }],
    [attendeeTable]
);

const roomCandidatesTable: Table = new Table(
    'Room Candidates',
    'readRoomCandidates',
    'This is a list of rooms belonging to a company.',
    [roomNameCol, attendeeCol],
    [roomsTable, attendeeTable]
);
const tables: Table[] = [
    interviewTimesTable,
    companiesTable,
    roomsTable,
    roomBreaksTable,
    attendeeTable,
    attendeeBreaksTable,
    attendeePrefsTable,
    roomCandidatesTable
];



function FileUpload({table, updateIsLoadeds}: {table: Table, updateIsLoadeds: () => void}): JSX.Element{
    const fileRef = React.useRef(null as HTMLInputElement|null);
    const [isLoading, setIsLoading] = React.useState(false);
    const [fileName, setFileName] = React.useState("");

    async function sendFile(){
        let fileElement = fileRef.current;
        if (fileElement == null){
            return;
        }
        let files = fileElement.files;

        if (files == null || files.length == 0) {
            fileElement.setCustomValidity("Please select file");
            return fileElement.reportValidity();
        } else {
            fileElement.setCustomValidity("");
        }
        let file = files[0];        
        
        var data = new FormData();
        data.append('table', file);
        
        setIsLoading(true);
        
        CallAPI(`/${table.endpoint}`, RestfulType.POST, data)
        .then(({data}: {data: string[][]}) => {
            table.addValues(data);
            alert(`Uploaded table: ${table.name}`);
            updateIsLoadeds();
        }).catch((res)=>{
            console.log("res", res);
            alert(res["error"]);
        }).finally(()=>{
            setIsLoading(false);
        });
    }

    function onFileChange(){
        let fileElement = fileRef.current;
        if (fileElement == null){
            return;
        }
        let files = fileElement.files;

        if (files != null && 0 < files.length) {
            setFileName(files[0].name);    
            sendFile();  
        } else {
            setFileName("");      
        }
    }

    return isLoading ? <div className="loader"></div> : <>
        <label id="htmlUploadContainer">
            <input 
                onChange={onFileChange} 
                ref={fileRef} 
                name="file" 
                accept=".csv" 
                type="file"
            />
            <div id="htmlUpload" className="col centerCross clickable whiteWhenHovered">
                <div className="row centerCross">
                    {Icons.Upload} 
                    <p>choose file</p>
                </div>
                <p>(.csv)</p>
            </div>
        </label>
        <p><i>{fileName == "" ? "No file selected" : fileName}</i></p>
    </>
}

function ColumnConfig({table, col}: {table: Table, col: IColumn}){

    let descs = [ColumnTypeToStr(col.type)];
    if (table != col.table){
        descs.push(`must be defined in the ${col.table!.name} table`)
    }
    if (col.desc){
        descs.push(col.desc);
    }

    return <div className='column'>
        <b>{col.name}</b> • {descs.join(', ')}
    </div>
}

function TableConfig(
    {table, isSelected, scrollTo, updateIsLoadeds}: 
    {table: Table, isSelected: boolean, scrollTo: (t: Table|null) => void, updateIsLoadeds: () => void}
){

    const shouldExpand = () => table.isDependenciesLoaded();

    const [isExpanded, setIsExpanded] = React.useState(shouldExpand());
    const elRef = React.useRef(null as HTMLDivElement|null);
    React.useEffect(() => {
        if (isSelected){
            elRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start'});
        }
        setIsExpanded(true);
        scrollTo(null);
    }, [isSelected]);
    React.useEffect(() => {
        setIsExpanded(shouldExpand());
    }, [table.isDependenciesLoaded()]);

    return <div ref={elRef} className='table'>
        <div className='tableHeader row clickable' onClick={() => setIsExpanded(!isExpanded)}>
            <div className='tableChevronContainer'>
                {isExpanded ? Icons.ChevronDown : Icons.ChevronUp}
            </div>
            <h2 className='centerAll'>{table.name}</h2>
            <div className='spacer'></div>
            <div className='tableAvailability centerAll'>
                {table.isDependenciesLoaded() ? 
                    (table.isLoaded ? Icons.CheckMark : Icons.PlusSign) : 
                    Icons.CrossSign
                }
            </div>
        </div>
        {!isExpanded ? null : <div className='tableConfig col'>
            <div className='tableDesc'>
                <p>{table.desc}</p>
            </div>
            {table.dependencies.length == 0 ? null : <div className='tableDependencies'>
                <h3>Depends on:</h3>
                <ul>
                    {table.dependencies.map((t,i) => <li 
                        className='dependency row centerCross clickable'
                        onClick={() => scrollTo(t)}
                        key={i}
                    >
                        <p>{t.name} table</p>
                        <div className='dependencyIcon row centerCross'>
                            {t.isLoaded ? Icons.CheckMark : Icons.CrossSign}
                        </div>
                    </li>)}
                </ul>
            </div>}
            <div className='tableColumns'>
                <h3>Columns:</h3>
                <ul>
                    {table.columns.map((c, i) => <li key={i}><ColumnConfig table={table} col={c}/></li>)}
                </ul>
            </div>
            <div className='tableUpload col centerCross'>
                <FileUpload table={table} updateIsLoadeds={updateIsLoadeds}/>
            </div>
        </div>}
    </div>
}

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

class Room {
    companyName: string;
    roomName: string;

    constructor(company: string, room: string){
        this.companyName = company;
        this.roomName = room;
    }
}

interface ISchedule {
    attendees: {[attId: number]: IAttendee};
    companies: {[companyName: string]: {[roomName: string]: IRoom}};
    interviewTimes: IInterval[];
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

function ScheduleCompany(
    {schedule}: 
    {schedule: ISchedule}
){
    let headings = getHeadings(schedule);
    ATT_TO_APPS = {}; // empty out prev
    ATT_TO_ROOMS = {};
    ROOM_TO_COMPANY = {};

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
                        let length = 30;
                        let candidatesNotSelected = new Set(room.candidates);
                        for (let attId of room.candidates){
                            console.log('att:', attId, 'company:', companyName);
                            ATT_TO_ROOMS[attId] = ATT_TO_ROOMS[attId] || new Set();
                            ATT_TO_ROOMS[attId].add(roomName);
                            ROOM_TO_COMPANY[roomName] = companyName;
                        }
                        /* as we iterate over apps, remove attendees who are selected */
                        return <tr>
                            <td>{roomName}</td>
                            {headings.map(heading => <td key={+heading}>{
                                (timeToApp[+heading] || []).map(app => {
                                    if (app.att != null){
                                        candidatesNotSelected.delete(app.att);
                                        ATT_TO_APPS[app.att] = ATT_TO_APPS[app.att] || [];
                                        ATT_TO_APPS[app.att].push(new Appointment(app.att, companyName, roomName, app));
                                    }
                                    let interval = Interval.fromStr(app);
                                    length = interval.lengthMins;
                                    let lengthPercent = (interval.lengthMins / 60) * 100;
                                    let startPercent = (interval.start.getMinutes() / 60) * 100;
                                    let att = app.att == null ? null : schedule.attendees[app.att!];
                                    return <div 
                                        data-app={`${dateToStr(interval.start)} ${dateToStr(interval.end)}`} 
                                        className="appContainer centerAll" style={{
                                            left: `${startPercent}%`,
                                            width: `${lengthPercent}%`
                                        }}
                                        key={roomName + interval.toString()}
                                    >
                                        <div className={`app col centerAll ${app.att ? '' : 'empty'}`}>
                                            <div className='appLength'>{interval.lengthMins}m</div>
                                            <span className='appPref'>{att == null ? null : `pref: ${att?.prefs[companyName]}`}</span>
                                            <span className='appAtt'>{app.att || '?'}</span>
                                            <span className='appTime'>{dateToTimeStr(interval.start)}</span>
                                        </div>
                                    </div>
                                })
                            }</td>)}
                            <td><div className="row">{Array.from(candidatesNotSelected).map(attId => {
                                let att = schedule.attendees[attId];
                                return <div key={attId} className="appContainer notSelected centerAll">
                                    <div className={`app col centerAll`}>
                                        <span className='appPref'>pref: {att.prefs[companyName]}</span>
                                        <span className='appAtt'>{attId}</span>
                                    </div>
                                </div>
                            })}</div></td>
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

    return <div id='scheduleCompany'>
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
                                        <span className='appPref'>{att == null ? null : `pref: ${att?.prefs[app.companyName]}`}</span>
                                        <span className='appAtt'>{app.roomName}</span>
                                        <span className='appTime'>{dateToTimeStr(interval.start)}</span>
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
        
	let gen = () => {
		CallAPI(`/generateSchedule`, RestfulType.GET)
		.then(({data}: {data: ISchedule}) => {
            setScheduleObj(data);
			alert(`Generated schedule`);
		}).catch((res)=>{
			console.log("res", res);
			alert(res["error"]);
		});
	}

    let attToApp: {[attId: number]: IAppointment[]} = {};

    return <div id='schedulePage' className='col centerCross'>
        <button onClick={gen}>generate schedule</button>
        {scheduleObj==null ? null :
            <div id='schedules'>
                <ScheduleCompany schedule={scheduleObj}/>
                <ScheduleAttendees schedule={scheduleObj}/>
            </div>
        }
    </div>
}

export default SchedulePage;