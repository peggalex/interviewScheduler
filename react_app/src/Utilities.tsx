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