import { rejects } from 'assert';
import React from 'react';

export const EnumArray = (e: any): string[] => 
    Object.values(e).filter((s: any) => isNaN(s)) as string[];


export enum RestfulType {
    POST,
    GET,
    PUT
}

export function CallAPIToJson(
    url: string, 
    method: RestfulType, 
    body: any = null,
    headers: any = {}
): Promise<any> {
    return new Promise((resolve, reject) => 
        CallAPI(url, method, body, headers)
            .then(async (response) => {
                if (!response.ok){
                    reject(await response.json());
                } else {
                    resolve(await response.json());
                }
            })
    );
}

export function CallAPIJsonToDownloadCSV(
    url: string, 
    method: RestfulType, 
    json: any = null,
): Promise<void> {
    return new Promise((resolve, reject) => {
        CallAPI(url, method, JSON.stringify(json), {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        .then(async (res) => {
            if (!res.ok){
                reject(alert(await res.json()))
            } else {
                let mimetype = res.headers.get('Content-Type')!;
                let filename = /.+filename="([^"]+)"/g.exec(
                    res.headers.get('Content-Disposition')!
                )![1];

                download(
                    mimetype, 
                    await res.text(),
                    filename
                );
                resolve();
            }
        })
    });

}

export function CallAPI(
    url: string, 
    method: RestfulType, 
    body: any = null,
    headers: any = {}
): Promise<Response> {
	url = url.replace(/[ \t\n]/g, ''); // get rid of empty spaces and newlines
    var fullUrl = `${process.env.PUBLIC_URL || './'}/${url}`;
	return fetch(fullUrl, {
        method: RestfulType[method],
        body: body,
        headers: headers
	});
}

export const CallAPIJsonToJson = async (
    url: string,
    method: RestfulType,
    body: Object
) => CallAPIToJson(
    url, 
    method, 
    JSON.stringify(body),
    {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
);

function download(mimetype: string, data: string, filename: string) {
    const link = document.createElement("a");
    link.href = `data:${mimetype},${encodeURIComponent(data)}`;
    link.download = filename;
    link.click();
}

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

const conventionTimesTable: Table = new Table(
    'Convention Times',
    'ConventionTimes',
    'This is a list of valid times for the convention.',
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

const roomNameCol: IColumn = {
    name: 'Room Name',
    type: ColumnType.STRING
}


const companyRoomsTable: Table = new Table(
    'Company Rooms',
    'CompanyRooms',
    'This is a list of companies participating, and their rooms.',
    [companyNameCol, roomNameCol],
    true
);


const roomInterviewsTable: Table = new Table(
    'Room Interviews',
    'RoomInterviews',
    'This is a list of rooms with interviews.',
    [roomNameCol, {
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
    [conventionTimesTable, companyRoomsTable]
);

const roomBreaksTable: Table = new Table(
    'Room Breaks',
    'RoomBreaks',
    'This is a list of room breaks.',
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
    [companyRoomsTable]
);

const attendeeCol: IColumn = {
    name: 'Attendee ID',
    type: ColumnType.STRING
}

const attendeeTable: Table = new Table(
    'Attendees',
    'AttendeeNames',
    'This is a list of attendees (students attending ASNA).',
    [attendeeCol, {
        name: "Attendee Name",
        type: ColumnType.STRING
    }],
    true
);

const attendeeBreaksTable: Table = new Table(
    'Attendee Breaks',
    'AttendeeBreaks',
    'This is a list of attendee breaks.',
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
    [conventionTimesTable, attendeeTable]
);

const attendeePrefsTable: Table = new Table(
    'Attendee Preferences',
    'AttendeePrefs',
    'This is a list of the preferences an attendee has for a company.',
    [attendeeCol, companyNameCol,
    {
        name: 'Preference',
        type: ColumnType.INT,
        desc: 'must be positive, the smaller the better'
    }],
    true,
    [attendeeTable, companyRoomsTable]
);

const interviewCandidatesTable: Table = new Table(
    'Interview Candidates',
    'InterviewCandidates',
    'This is a list of interview candidates.',
    [roomNameCol, attendeeCol],
    true,
    [companyRoomsTable, roomInterviewsTable, attendeeTable]
);

const coffeeChatsTable: Table = new Table(
    'Coffee Chats',
    'CoffeeChats',
    'This is a list of room coffee chats.',
    [roomNameCol, 
    {
        name: "Capacity",
        type: ColumnType.INT,
        desc: "must be positive"
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
    false,
    [conventionTimesTable, companyRoomsTable]
);

const coffeeChatsCandidatesTable: Table = new Table(
    'Coffee Chat Candidates',
    'CoffeeChatCandidates',
    'This is a list of room coffee chats candidates, and the rank the company ascribes that candidate.',
    [roomNameCol, attendeeCol, {
        name: 'Rank',
        type: ColumnType.INT,
        desc: 'must be positive, the smaller the better'
    }],
    false,
    [attendeeTable, companyRoomsTable, coffeeChatsTable]
);