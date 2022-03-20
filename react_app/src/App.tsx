import React from 'react';
import ConfigurationPage from './Configuration';
import SchedulePage from './Schedule';
import Icons from './Icons';
import './styles/App.css';
import './styles/Fonts.css';
import './styles/tailwindColours.css';
import { CallAPIToJson, RestfulType, Table, TableData, tables } from './Utilities';

function App(){

	let [configPageSelected, setConfigPageSelected] = React.useState(true);
	let [canGenerate, setCanGenerate] = React.useState(false);

    let tableDataInit: TableData = {};
    for (let table of tables){
        tableDataInit[table.name] = [];
    }
    let [tableData, setTableData] = React.useState(tableDataInit);

    async function getData(table: Table): Promise<string[][]>{
        return CallAPIToJson(`/get${table.endpoint}`, RestfulType.GET)
            .then(({data}: {data: string[][]}) => data)
            .catch((res)=>{
                console.log("res", res);
                alert(res["error"]);
                return [];
            });
    }

    async function updateTableData(){
		const newTable: TableData  = {};
        for (let table of tables){
            newTable[table.name] = await getData(table);
        }
        setTableData(newTable);
    }

    React.useEffect(() => {updateTableData()}, []); // call once on init

	React.useEffect(() => {
		let canGenerate = true;
		for (let table of tables){
			if (table.mandatory && !table.isLoaded(tableData)){
				canGenerate = false;
				break;
			}
		}
		setCanGenerate(canGenerate);	
	}, [tableData])

	return (
		<div>
			<header>
				<div id='banner' className="row">
					<div id='calendarContainer' className='centerAll'>
						{Icons.Calendar}
					</div>
					<div id='titleContainer' className='spacer centerCross'>
						<h1 id=''>Interview Scheduling Tool</h1>
					</div>
				</div>
				<div id='navButtons' className='centerAll'>
					<button 
						className={configPageSelected ? 'selected' : ''}
						onClick={() => setConfigPageSelected(true)}
					>Configuration</button>
					<button
						className={configPageSelected ? '' : 'selected'}
						disabled={!canGenerate}
						title={canGenerate ? '' : 'mandatory tables not uploaded'}
						onClick={() => setConfigPageSelected(false)}
					>Schedule</button>
				</div>
			</header>
			<div>
				{configPageSelected ? <ConfigurationPage tableData={tableData} updateTableData={updateTableData}/> : <SchedulePage/>}
			</div>
		</div>
	);
}

export default App;
