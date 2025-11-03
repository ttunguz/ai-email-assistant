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
    
    # Apply tagging rules first (before inbox tag to avoid conflicts)
    /opt/homebrew/bin/notmuch tag +newsletter -- folder:theory/INBOX AND '(' from:newsletters OR from:substack OR from:mailchimp OR subject:newsletter OR subject:unsubscribe OR from:bloomberg.com OR from:news.bloomberg.com OR from:techcrunch.com OR from:pitchbook.com OR from:coinbase.com OR from:fortune.com OR from:theinformation.com OR from:hex.tech OR from:calypsoai.com OR from:ycombinator.com OR from:pointer.io OR from:nekuda.org OR from:dowjones.com OR from:getbreakout.ai OR from:harmonic.ai OR from:braintrustdata.com OR from:venture5.com OR from:email.insider.com OR from:theneurondaily.com ')'
    /opt/homebrew/bin/notmuch tag +automated -- folder:theory/INBOX AND NOT tag:newsletter AND '(' from:noreply OR from:no-reply OR from:donotreply OR from:notifications ')'
    /opt/homebrew/bin/notmuch tag +receipts -- folder:theory/INBOX AND '(' from:receipts OR subject:receipt OR subject:invoice OR from:uber OR from:lyft ')'
    /opt/homebrew/bin/notmuch tag +asana -- folder:theory/INBOX AND '(' from:asana OR subject:asana OR from:notifications@asana.com ')'
    /opt/homebrew/bin/notmuch tag +calendar -- folder:theory/INBOX AND '(' from:calendar OR subject:invitation OR subject:meeting ')'
    /opt/homebrew/bin/notmuch tag +github -- folder:theory/INBOX AND '(' from:github OR from:notifications@github ')'
    /opt/homebrew/bin/notmuch tag +notion -- folder:theory/INBOX AND '(' from:notion OR subject:notion ')'
    /opt/homebrew/bin/notmuch tag +theory -- folder:theory/INBOX AND '(' to:theory.ventures OR from:theory.ventures ')'
    /opt/homebrew/bin/notmuch tag +important -- folder:theory/INBOX AND '(' from:john OR from:lauren OR from:art OR from:spencer OR from:kristin ')'
    /opt/homebrew/bin/notmuch tag +portfolio -- folder:theory/INBOX AND '(' subject:portfolio OR subject:investment OR subject:fundraising ')'
    /opt/homebrew/bin/notmuch tag +personal -- folder:theory/INBOX AND '(' to:tomasz.tunguz@gmail.com OR from:family OR from:friends ')'

    # Tag emails in INBOX folder (only those not auto-archived)
    /opt/homebrew/bin/notmuch tag +inbox -- folder:theory/INBOX AND NOT '(' tag:automated OR tag:receipts OR tag:asana ')'
    
    /opt/homebrew/bin/notmuch compact

#rm ~/.mbsyncrc
#~/Documents/Coding/offlineimap/offlineimap.py
