#!/bin/bash
if test -z "$(docker images -q sched:latest)"; then
	echo "building..."
	docker build --tag sched .
	echo "...built"
else
	echo "already built"
fi
if test -z "$(lsof -i:4000)"; then
	echo "starting up"
	docker run -p 4000:4000 sched &
else
	echo "already started"
fi
sleep 2
open http://localhost:4000


