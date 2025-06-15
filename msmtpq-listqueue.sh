#!/usr/bin/env bash

QUEUEDIR=$HOME/.msmtp_queue

for i in $QUEUEDIR/*.mail; do
	if [ -f "$i" ]; then
		egrep -s --colour=never -h '(^From:|^To:|^Subject:)' "$i"
		echo " "
	else
		echo "No mail in queue"
		break
	fi
done
