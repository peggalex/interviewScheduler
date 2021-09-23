import React from 'react';
import ConfigurationPage from './Configuration';
import SchedulePage from './Schedule';
import Icons from './Icons';
import './styles/App.css';
import './styles/Fonts.css';
import './styles/tailwindColours.css';

function App(){

	let [configPageSelected, setConfigPageSelected] = React.useState(true);

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
						onClick={() => setConfigPageSelected(false)}
					>Schedule</button>
				</div>
			</header>
			<div>
				{configPageSelected ? <ConfigurationPage/> : <SchedulePage/>}
			</div>
		</div>
	);
}

export default App;
