#!/bin/bash
if test -z "$(docker images -q sched:latest)"; then
	echo "building..."
	docker build --tag sched .
	echo "...built"
else
	echo "already built"
fi
echo "starting up"
docker run -p 4000:4000 sched &
sleep 2.5
open http://localhost:4000


