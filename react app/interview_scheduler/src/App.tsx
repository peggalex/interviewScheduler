import React from 'react';
import ConfigurationPage from './Configuration';
import Icons from './Icons';
import './styles/App.css';
import './styles/Fonts.css';
import './styles/tailwindColours.css';

function App(){
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
					<button className='selected'>Configuration</button>
					<button>Schedule</button>
				</div>
			</header>
			<div>
				<ConfigurationPage/>
			</div>
		</div>
	);
}

export default App;
