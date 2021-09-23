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
    att?: IAttendee;
    room: string;
}

interface IRoom {
    apps: IAppointment[];
    candidates: number[];
}

interface ISchedule {
    attendees: {[attId: number]: IAttendee};
    companies: {[companyName: string]: IRoom[]};
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


function dateToStr(date: Date){
    let time = new Intl.DateTimeFormat(
        'en-US', 
        { hour: 'numeric', minute: 'numeric', hour12: true }
    ).format(date);
    let month = new Intl.DateTimeFormat('en-US', { month: 'short'}).format(date);
    let day = date.getDate();
    return `${month} ${day}, ${time}`;
}

function ScheduleCompany({schedule}: {schedule: ISchedule}){

    let headings = getHeadings(schedule);

    return <div id='scheduleCompany'>
        <table>
            <thead><tr>
                <th>Room Name</th>
                {headings.map((time, i) => 
                    <th key={i}>{dateToStr(time)}</th>
                )}
            </tr></thead>
            <tbody>
                {Object.entries(schedule.companies).map(
                    ([_, rooms]: [_: string, rooms: IRoom[]]) => {
                        console.log('rooms', rooms);
                        return Object.entries(rooms).map(([roomName, room]: [roomName: string, room: IRoom]) => {

                            let timeToDate: {[time: number]: IAppointment[]} = {}
                            let i = 0;
                            for (let app of room.apps) {
                                let interval = Interval.fromStr(app);

                                for (;addHours(headings[i], 1) <= interval.start; i++){}

                                timeToDate[+headings[i]] = timeToDate[+headings[i]] || [];
                                timeToDate[+headings[i]].push(app);
                            }

                            return <tr>
                                <td>{roomName}</td>
                                {headings.map(heading => <td key={+heading}>{(
                                    timeToDate[+heading] || []).map(
                                        app => {
                                            let interval = Interval.fromStr(app);
                                            let lengthPercent = (interval.lengthMins / 60) * 100;
                                            let startPercent = (interval.start.getMinutes() / 60) * 100;
                                            return <div data-app={`${dateToStr(interval.start)} ${dateToStr(interval.end)}`} className="appContainer centerAll" style={{
                                                left: `${startPercent}%`,
                                                width: `${lengthPercent}%`
                                            }}>
                                                <div className="app centerAll">
                                                    {app.att}
                                                </div>
                                            </div>
                                        }
                                    )
                                }</td>
                            )}</tr>
                        })
                    }
                )}
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
            console.log('times:', data.interviewTimes);
			alert(`Generated schedule`);
		}).catch((res)=>{
			console.log("res", res);
			alert(res["error"]);
		});
	}

    return <div id='schedulePage' className='col centerCross'>
        <button onClick={gen}>generate schedule</button>
        {scheduleObj==null ? null :
            <div id='schedules'>
                <ScheduleCompany schedule={scheduleObj}/>
            </div>
        }
    </div>
}

export default SchedulePage;