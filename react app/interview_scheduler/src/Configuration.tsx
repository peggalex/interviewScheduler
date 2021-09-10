import React from 'react';
import Icons from './Icons';
import './styles/Configuration.css';

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
    desc: string;
    columns: IColumn[];
    dependencies: Table[];
    isLoaded: boolean;

    constructor(name: string, desc: string, columns: IColumn[], dependencies?: Table[]){
        this.name = name;
        this.desc = desc;
        this.dependencies = dependencies ?? [];
        this.columns = [];
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
}

const interviewTimesTable: Table = new Table(
    'Interview Times',
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
    'This is a list of companies participating.',
    [companyNameCol]
);

const roomNameCol: IColumn = {
    name: 'Room Name',
    type: ColumnType.STRING
}

const roomsTable: Table = new Table(
    'Company Rooms',
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
    'This is a list of rooms belonging to a company.',
    [{
        name: 'Start Time',
        type: ColumnType.DATETIME
    },
    {
        name: 'End Time',
        type: ColumnType.DATETIME,
        desc: 'must be greater than start time'
    }],
    [interviewTimesTable, roomsTable]
);



const attendeeCol: IColumn = {
    name: 'Attendee ID',
    type: ColumnType.STRING
}

const attendeeTable: Table = new Table(
    'Attendees',
    'This is a list of rooms belonging to a company.',
    [attendeeCol]
);

const attendeeBreaksTable: Table = new Table(
    'Attendee Breaks',
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
        data.append('html', file);
        
        setIsLoading(true);
        /*
        CallAPI("/addMatchHTML", RestfulType.POST, data)
        .then(({date}: {date: number}) => {
            let dateStr = new Date(date).toLocaleString("en-AU");
            if (window.confirm(`Successfully added match from: ${dateStr}, reload page?`)){
                window.location.href = "./matches";
            }
        }).catch((res)=>{
            console.log("res", res);
            alert(res["error"]);
        }).finally(()=>{
            setIsLoading(false);
        });
        */
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
        <label id="htmlUploadContainer" onClick={() => {
                table.isLoaded = true;
                updateIsLoadeds();
            }}>
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
    {table: Table, isSelected: boolean, scrollTo: (t: Table) => void, updateIsLoadeds: () => void}
){

    const shouldExpand = () => table.isDependenciesLoaded() || isSelected;

    const [isExpanded, setIsExpanded] = React.useState(shouldExpand());
    const elRef = React.useRef(null as HTMLDivElement|null);
    React.useEffect(() => {
        if (isSelected){
            elRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start'});
        }
    }, [isSelected]);
    React.useEffect(() => {
        setIsExpanded(shouldExpand());
    }, [table.isDependenciesLoaded(), isSelected]);

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

function ConfigurationPage(){

    let [selectedTable, selectTable] = React.useState(null as Table|null);

    const getIsLoadeds = () => tables.map(t => t.isLoaded);
    let [isLoadeds, setIsLoadeds] = React.useState(getIsLoadeds());
    const updateIsLoadeds = () => setIsLoadeds(getIsLoadeds());

    return <div id='configPage'>
        {tables.map(t => <TableConfig 
            key={t.name} 
            table={t} 
            isSelected={selectedTable == t} 
            scrollTo={(t: Table) => selectTable(t)}
            updateIsLoadeds={updateIsLoadeds}
        />)}
    </div>
}

export default ConfigurationPage;