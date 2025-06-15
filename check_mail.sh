#!/bin/sh
#op inject -i ~/.mbsyncrc.tpl -o ~/.mbsyncrc

#STATE=`nmcli networking connectivity`
#
#if [ $STATE = 'full' ]
#then
#    #~/bin/msmtp-runqueue.sh
#    /usr/local/bin/msmtpq
#    ~/.mutt/msmtp-runqueue.sh
#    /opt/homebrew/bin/mbsync -a
#    /usr/local/bin/notmuch new
#    /usr/local/bin/notmuch compact
#    exit 0
#fi
#echo "No internet connection."
#exit 0

 #previous script
 ~/.mutt/msmtp-runqueue.sh
    #~/.mutt/msmtp
    /opt/homebrew/bin/mbsync -a
    /opt/homebrew/bin/notmuch new
    /opt/homebrew/bin/notmuch compact

#rm ~/.mbsyncrc
#~/Documents/Coding/offlineimap/offlineimap.py
