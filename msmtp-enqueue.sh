#!/usr/bin/env bash

QUEUEDIR=$HOME/.msmtp_queue

# Set secure permissions on created directories and files
umask 077

# Change to queue directory (create it if necessary)
if [ ! -d "$QUEUEDIR" ]; then
	mkdir -p "$QUEUEDIR" || exit 1
fi
cd "$QUEUEDIR" || exit 1

# Create new unique filenames of the form
# MAILFILE:  ccyy-mm-dd-hh.mm.ss[-x].mail
# MSMTPFILE: ccyy-mm-dd-hh.mm.ss[-x].msmtp
# where x is a consecutive number only appended if you send more than one
# mail per second.
BASE="`date +%Y-%m-%d-%H.%M.%S`"
if [ -f "$BASE.mail" -o -f "$BASE.msmtp" ]; then
	TMP="$BASE"
	i=1
	while [ -f "$TMP-$i.mail" -o -f "$TMP-$i.msmtp" ]; do
		i=`expr $i + 1`
	done
	BASE="$BASE-$i"
fi
MAILFILE="$BASE.mail"
MSMTPFILE="$BASE.msmtp"

# Write command line to $MSMTPFILE
echo "$@" > "$MSMTPFILE" || exit 1

# Write the mail to $MAILFILE
cat > "$MAILFILE" || exit 1

# If we are online, run the queue immediately.
# Use Google's DNS server to check internet connectivity
# Comment next line (and uncomment line after) to use real connectivity check
# ping -c 1 -t 1 nonexistentdomain.example.com > /dev/null 2>&1
ping -c 1 -t 2 8.8.8.8 > /dev/null
if [ $? -eq 0 ]; then
	# Use full path to the runqueue script to ensure it can be found
	$HOME/.mutt/msmtp-runqueue.sh > /dev/null &
fi

exit 0
