#!/usr/bin/env sh

echo "[DEBUG] Script started at $(date)"

QUEUEDIR="$HOME/.msmtp_queue"
LOCKFILE="$QUEUEDIR/.lock"
MAXWAIT=120

OPTIONS=$*

# eat some options that would cause msmtp to return 0 without sendmail mail
case "$OPTIONS" in
	*--help*)
	echo "$0: send mails in $QUEUEDIR"
	echo "Options are passed to msmtp"
	exit 0
	;;
	*--version*)
	echo "$0: unknown version"
	exit 0
	;;
esac

# wait for a lock that another instance has set
echo "[DEBUG] Checking lock file status: $LOCKFILE"
WAIT=0
while [ -e "$LOCKFILE" ] && [ "$WAIT" -lt "$MAXWAIT" ]; do
	sleep 1
	WAIT="$((WAIT + 1))"
done
if [ -e "$LOCKFILE" ]; then
	echo "Cannot use $QUEUEDIR: waited $MAXWAIT seconds for"
	echo "lockfile $LOCKFILE to vanish, giving up."
	echo "If you are sure that no other instance of this script is"
	echo "running, then delete the lock file."
	exit 1
fi

# change into $QUEUEDIR
cd "$QUEUEDIR" || exit 1

echo "[DEBUG] Current directory: $(pwd)"
echo "[DEBUG] Queue directory contents:"
ls -la | while read line; do echo "[DEBUG] $line"; done

# check for empty queuedir
if [ "$(echo ./*.mail)" = './*.mail' ]; then
	echo "No mails in $QUEUEDIR"
	exit 0
fi

# lock the $QUEUEDIR
echo "[DEBUG] Creating lock file: $LOCKFILE"
touch "$LOCKFILE" || exit 1
echo "[DEBUG] Lock file created successfully"

# process all mails
echo "[DEBUG] Starting mail processing loop"
for MAILFILE in *.mail; do
    echo "[DEBUG] Processing mail file: $MAILFILE"
	MSMTPFILE="$(echo $MAILFILE | sed -e 's/mail/msmtp/')"
	echo "*** Sending $MAILFILE to $(sed -e 's/^.*-- \(.*$\)/\1/' $MSMTPFILE) ..."
	if [ ! -f "$MSMTPFILE" ]; then
		echo "No corresponding file $MSMTPFILE found"
		echo "FAILURE"
		continue
	fi
	MSMTP_ARGS="$(cat "$MSMTPFILE")"
	echo "[DEBUG] Executing command: msmtp $MSMTP_ARGS < $MAILFILE"
	msmtp $MSMTP_ARGS < "$MAILFILE"
	if [ $? -eq 0 ]; then
		rm "$MAILFILE" "$MSMTPFILE"
		echo "$MAILFILE sent successfully"
	else
		echo "FAILURE"
	fi
done

# remove the lock
echo "[DEBUG] Removing lock file: $LOCKFILE"
rm -f "$LOCKFILE"
echo "[DEBUG] Lock file removed"
echo "[DEBUG] Script finished at $(date)"
exit 0
