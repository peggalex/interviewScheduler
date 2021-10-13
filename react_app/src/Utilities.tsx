import React from 'react';

export const EnumArray = (e: any): string[] => 
    Object.values(e).filter((s: any) => isNaN(s)) as string[];


export enum RestfulType {
    POST,
    GET,
    PUT
}

export async function CallAPI(
    url: string, 
    method: RestfulType, 
    body: any = null,
    headers: any = {}
): Promise<any> {
	url = url.replace(/[ \t\n]/g, ''); // get rid of empty spaces and newlines
    var fullUrl = `${process.env.PUBLIC_URL || './'}/${url}`;
	return new Promise(async (resolve, reject) => {
        fetch(fullUrl, {
            method: RestfulType[method],
            body: body,
            headers: headers
        }).then(async (response) => {
            if (!response.ok){
                reject(await response.json());
            } else {
                resolve(await response.json());
            }
        });
	});
}

export const CallAPIJson = async (
    url: string,
    method: RestfulType,
    body: Object
) => CallAPI(
    url, 
    method, 
    JSON.stringify(body),
    {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
);


//https://stackoverflow.com/questions/1322732/convert-seconds-to-hh-mm-ss-with-javascript
export const secsToHMS = (secs: number): string => {
    const hourInSecs = 60*60;
    let dateStr = new Date(secs * 1000).toISOString();
    const endIndex = 19;
    let len = 8;
    if (secs < hourInSecs) len -= 3;
    return dateStr.substr(endIndex - len, len);
};

export enum ColumnType {
    STRING,
    INT,
    DATETIME
}

export function ColumnTypeToStr(colType: ColumnType){
    switch (colType){
        case ColumnType.STRING:
            return 'string';
        case ColumnType.INT:
            return 'integer';
        case ColumnType.DATETIME:
            return 'datetime';
        default:
            throw Error(`unhandled col type for ColumnTypeToStr(): ${ColumnType}`);
    }
}

export interface IColumn{
    name: string;
    type: ColumnType;
    desc?: string;
    table?: Table;
}

export type TableData = {[tableName: string]: string[][]};

export const tables: Table[] = [];

export class Table{
    name: string;
    endpoint: string;
    desc: string;
    columns: IColumn[];
    mandatory: boolean;
    dependencies: Table[];

    constructor(name: string, endpoint: string, desc: string, columns: IColumn[], mandatory: boolean, dependencies?: Table[]){
        tables.push(this);
        this.name = name;
        this.endpoint = endpoint;
        this.desc = desc;
        this.mandatory = mandatory;
        this.dependencies = dependencies ?? [];
        this.columns = [];
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

    getValues(tableData: TableData){
        return tableData[this.name];
    }

    isDependenciesLoaded(tableData: TableData){
        return this.dependencies.every(t => t.isLoaded(tableData));
    }

    isLoaded(tableData: TableData){
        return 0 < (tableData[this.name]?.length ?? -1);
    }
}

const interviewTimesTable: Table = new Table(
    'Interview Times',
    'InterviewTimes',
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
    ],
    true
);

const companyNameCol: IColumn = {
    name: 'Company Name',
    type: ColumnType.STRING
}

const companiesTable: Table = new Table(
    'Companies',
    'CompanyNames',
    'This is a list of companies participating.',
    [companyNameCol],
    true
);

const roomNameCol: IColumn = {
    name: 'Room Name',
    type: ColumnType.STRING
}

const roomsTable: Table = new Table(
    'Company Rooms',
    'RoomNames',
    'This is a list of company rooms.',
    [companyNameCol, roomNameCol, {
        name: 'Length',
        type: ColumnType.INT,
        desc: 'in minutes'
    },    
    {
        name: 'Start Time',
        type: ColumnType.DATETIME
    },
    {
        name: 'End Time',
        type: ColumnType.DATETIME,
        desc: 'must be greater than start time'
    }],
    true,
    [companiesTable, interviewTimesTable]
);

const roomBreaksTable: Table = new Table(
    'Room Breaks',
    'RoomBreaks',
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
    false,
    [interviewTimesTable, roomsTable]
);

const attendeeCol: IColumn = {
    name: 'Attendee ID',
    type: ColumnType.STRING
}

const attendeeTable: Table = new Table(
    'Attendees',
    'AttendeeNames',
    'This is a list of rooms belonging to a company.',
    [attendeeCol],
    true
);

const attendeeBreaksTable: Table = new Table(
    'Attendee Breaks',
    'AttendeeBreaks',
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
    false,
    [interviewTimesTable, attendeeTable]
);

const attendeePrefsTable: Table = new Table(
    'Attendee Preferences',
    'AttendeePrefs',
    'This is a list of rooms belonging to a company.',
    [attendeeCol, companyNameCol,
    {
        name: 'Preference',
        type: ColumnType.INT,
        desc: 'the larger the better'
    }],
    true,
    [attendeeTable]
);

const roomCandidatesTable: Table = new Table(
    'Room Candidates',
    'RoomCandidates',
    'This is a list of rooms belonging to a company.',
    [roomNameCol, attendeeCol],
    true,
    [roomsTable, attendeeTable]
);