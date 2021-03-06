CREATE TABLE IF NOT EXISTS interviewTime(
	timestamp INTEGER  NOT NULL,
	start DATETIME  NOT NULL,
	end DATETIME  NOT NULL,
	PRIMARY KEY (start)
);

CREATE TABLE IF NOT EXISTS company(
	timestamp INTEGER  NOT NULL,
	companyName VARCHAR(50)  NOT NULL,
	PRIMARY KEY (companyName)
);

CREATE TABLE IF NOT EXISTS companyRoom(
	timestamp INTEGER  NOT NULL,
	companyName VARCHAR(50)  NOT NULL,
	roomName VARCHAR(50)  NOT NULL,
	PRIMARY KEY (roomName),
	FOREIGN KEY (companyName) REFERENCES company(companyName) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS roomInterview(
	timestamp INTEGER  NOT NULL,
	roomName VARCHAR(50)  NOT NULL,
	length INTEGER  NOT NULL,
	start DATETIME  NOT NULL,
	end DATETIME  NOT NULL,
	PRIMARY KEY (roomName),
	FOREIGN KEY (roomName) REFERENCES companyRoom(roomName) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS roomBreak(
	timestamp INTEGER  NOT NULL,
	roomName VARCHAR(50)  NOT NULL,
	start DATETIME  NOT NULL,
	end DATETIME  NOT NULL,
	PRIMARY KEY (roomName, start),
	FOREIGN KEY (roomName) REFERENCES companyRoom(roomName) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS roomCoffeeChat(
	timestamp INTEGER  NOT NULL,
	roomName VARCHAR(50)  NOT NULL,
	capacity INTEGER  NOT NULL,
	start DATETIME  NOT NULL,
	end DATETIME  NOT NULL,
	PRIMARY KEY (roomName),
	FOREIGN KEY (roomName) REFERENCES companyRoom(roomName) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attendee(
	timestamp INTEGER  NOT NULL,
	attendeeID INTEGER  NOT NULL,
	attendeeName VARCHAR(50)  NOT NULL,
	PRIMARY KEY (attendeeID)
);

CREATE TABLE IF NOT EXISTS attendeeBreak(
	timestamp INTEGER  NOT NULL,
	attendeeID INTEGER  NOT NULL,
	start DATETIME  NOT NULL,
	end DATETIME  NOT NULL,
	PRIMARY KEY (attendeeID, start),
	FOREIGN KEY (attendeeID) REFERENCES attendee(attendeeID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attendeePreference(
	timestamp INTEGER  NOT NULL,
	attendeeID INTEGER  NOT NULL,
	companyName VARCHAR(50)  NOT NULL,
	preference INTEGER  NOT NULL,
	PRIMARY KEY (attendeeID, companyName),
	FOREIGN KEY (attendeeID) REFERENCES attendee(attendeeID) ON DELETE CASCADE,
	FOREIGN KEY (companyName) REFERENCES company(companyName) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interviewCandidate(
	timestamp INTEGER  NOT NULL,
	roomName VARCHAR(50)  NOT NULL,
	attendeeID INTEGER  NOT NULL,
	PRIMARY KEY (roomName, attendeeID),
	FOREIGN KEY (roomName) REFERENCES companyRoom(roomName) ON DELETE CASCADE,
	FOREIGN KEY (attendeeID) REFERENCES attendee(attendeeID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS coffeeChatCandidate(
	timestamp INTEGER  NOT NULL,
	roomName VARCHAR(50)  NOT NULL,
	attendeeID INTEGER  NOT NULL,
	preference INTEGER  NOT NULL,
	PRIMARY KEY (roomName, attendeeID),
	FOREIGN KEY (roomName) REFERENCES companyRoom(roomName) ON DELETE CASCADE,
	FOREIGN KEY (attendeeID) REFERENCES attendee(attendeeID) ON DELETE CASCADE
);