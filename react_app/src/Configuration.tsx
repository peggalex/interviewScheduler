import React from 'react';
import Icons from './Icons';
import './styles/Configuration.css';
import { CallAPIToJson, ColumnType, ColumnTypeToStr, IColumn, RestfulType, Table, TableData, tables } from './Utilities';

function FormatColumn(col: string, colType: ColumnType){
    switch (colType){
        case ColumnType.STRING:
        case ColumnType.INT:
            return col;
        case ColumnType.DATETIME:
            let date = new Date(Date.parse(col));
            let month = date.toLocaleString('default', { month: 'short' });
            let mins = date.getMinutes().toString().padStart(2, '0');
            return `${month} ${date.getDate()}, ${date.getHours()}:${mins}`;
        default:
            throw Error(`unhandled col type for FormatColumn(): ${ColumnType}`);
    }
}

const getLocalStorageKey = (table: Table) => `filename|${table.name}`;
const getDefaultFilename = (table: Table, tableData: TableData) => {
    if (!table.isLoaded(tableData)){
        return "";
    }
    const localStorageKey = getLocalStorageKey(table);
    return localStorage.getItem(localStorageKey) ?? "<unknown filename>";
}

function FileUpload({table, tableData, updateTableData, isLoading, setIsLoading}: {
    table: Table, 
    tableData: TableData, 
    updateTableData: () => void,
    isLoading: boolean,
    setIsLoading: (isLoading: boolean) => void
}): JSX.Element {
    const fileRef = React.useRef(null as HTMLInputElement|null);
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
        
        CallAPIToJson(
            `/set${table.endpoint}`, 
            RestfulType.POST, data
        ).then(({data}: {data: string[][]}) => {
            alert(`Uploaded table: ${table.name}`);
            setFileName(file.name);
            localStorage.setItem(getLocalStorageKey(table), file.name); 
            updateTableData();
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
            sendFile();  
        } else {
            setFileName("");      
        }
    }

    React.useEffect(() => {
        setFileName(getDefaultFilename(table, tableData))
    }, [JSON.stringify(tableData)]);

    let buttWorks = table.isDependenciesLoaded(tableData);

    return isLoading ? <div className="loader"></div> : <>
        <label id="htmlUploadContainer">
            <input 
                onChange={onFileChange} 
                ref={fileRef} 
                name="file" 
                accept=".csv" 
                type="file"
                disabled={!buttWorks}
            />
            <div id="htmlUpload" className={`col centerCross clickable whiteWhenHovered ${buttWorks ? "" : "disabled"}`}>
                <div className="row centerCross">
                    {Icons.Upload} 
                    <p>choose file</p>
                </div>
                <p>(.csv)</p>
            </div>
        </label>
        <p><i>
            {
                buttWorks ? 
                    (fileName == "" ? "No file selected" : fileName) : 
                    "dependencies not loaded"
            }
        </i></p>
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
    {table, isSelected, scrollTo, tableData, updateTableData}: 
    {table: Table, isSelected: boolean, scrollTo: (t: Table|null) => void, tableData: TableData, updateTableData: () => void}
){
    const [values, setValues] = React.useState(table.getValues(tableData));
    const [isLoading, setIsLoading] = React.useState(false);

    const shouldExpand = (t: Table) => t.isDependenciesLoaded(tableData);
    const [isExpanded, setIsExpanded] = React.useState(shouldExpand(table));

    const elRef = React.useRef(null as HTMLDivElement|null);
    React.useEffect(() => {
        if (isSelected){
            elRef.current?.scrollIntoView({behavior: 'smooth', block: 'start'});
        }
        setIsExpanded(true);
        scrollTo(null);
    }, [isSelected]);

    React.useEffect(() => {
        setIsExpanded(shouldExpand(table));
    }, [shouldExpand(table)]);

    React.useEffect(() => {
        setValues(table.getValues(tableData));
    }, [JSON.stringify(table.getValues(tableData))]);

    return <div ref={elRef} className='table'>
        <div className='tableHeader row clickable' onClick={() => setIsExpanded(!isExpanded)}>
            <div className='tableChevronContainer'>
                {isExpanded ? Icons.ChevronDown : Icons.ChevronUp}
            </div>
            <h2 className='centerAll'>{table.name}</h2>
            <div className='spacer'></div>
            <div className='tableAvailability centerAll'>
                {table.isDependenciesLoaded(tableData) ? 
                    (table.isLoaded(tableData) ? Icons.CheckMark : Icons.PlusSign) : 
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
                            {t.isLoaded(tableData) ? Icons.CheckMark : Icons.CrossSign}
                        </div>
                    </li>)}
                </ul>
            </div>}
            <div className='tableColumns'>
                <h3>Columns:</h3>
                <ul>
                    {table.columns.map((c, i) => 
                        <li key={i}><ColumnConfig table={table} col={c}/></li>
                    )}
                </ul>
            </div>
            <div className='tableUpload col centerCross'>
                <FileUpload 
                    table={table} 
                    tableData={tableData} 
                    updateTableData={updateTableData} 
                    isLoading={isLoading} 
                    setIsLoading={setIsLoading}
                />
                {!isLoading && table.isLoaded(tableData) ? <div className='tableTable'>
                    <table>
                        <thead><tr>
                            {table.columns.map((c, i) => 
                                <th key={i}>{c.name}</th>
                            )}
                        </tr></thead>
                        <tbody>{values.map((r, i) => 
                            <tr key={i}>{r.map((c, k) => 
                                <td key={k}>
                                    {FormatColumn(c, table.columns[k].type)}
                                </td>
                            )} </tr>
                        )}</tbody>
                    </table>
                </div> : null}
            </div>
        </div>}
    </div>
}

function ConfigurationPage(
        {tableData, updateTableData}: 
        {tableData: TableData, updateTableData: () => void}
    ){

    let [selectedTable, selectTable] = React.useState(null as Table|null);

    return <div id='configPage'>
        {tables.map(t => <TableConfig 
            key={t.name} 
            table={t} 
            isSelected={selectedTable == t} 
            scrollTo={(t: Table|null) => selectTable(t)}
            tableData={tableData}
            updateTableData={updateTableData}
        />)}
    </div>
}

export default ConfigurationPage;