#!/usr/bin/env python3

import signal
import sys
import os
import subprocess
import gi
import threading

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify

APPINDICATOR_ID = ''
indicator = None

instanceName = ''

filePath = os.path.dirname(os.path.abspath(__file__))
unknownEmblem = filePath + '/images/emblems/emblem-dropbox-selsync.png'
idleEmblem = filePath + '/images/emblems/dropbox-icon.png'
syncingEmblem = filePath + '/images/emblems/emblem-dropbox-syncing.png'

threadHandle = None

def build_menu(title):
    menu = gtk.Menu()

    item_title = gtk.MenuItem(title)
    menu.append(item_title)

    item_quit = gtk.MenuItem('Quit')
    item_quit.connect('activate', quit)
    menu.append(item_quit)
    
    item_status = gtk.MenuItem('Status')
    item_status.connect('activate', status)
    menu.append(item_status)

    menu.show_all()
    return menu

def status(_):
    global instanceName
    notify.Notification.new('Dropbox sync status', \
            get_dropbox_status(instanceName), None).show()

def quit(source):
    stop_dropbox_docker(instanceName)
    notify.uninit()
    gtk.main_quit()

def start_dropbox_docker(instanceName):
    ret = 0
    try:
        ret = subprocess.check_call( \
                ['docker', 'start', '{0}'.format(instanceName)])
    except subprocess.CalledProcessError as e:
        print(e.output)
    return ret

def stop_dropbox_docker(instanceName):
    try:
        subprocess.check_call( \
                ['docker', 'stop', '{0}'.format(instanceName)])
    except subprocess.CalledProcessError as e:
        print(e.output)

            
def get_dropbox_status(instanceName):
    ret = ""
    try:
        ret = subprocess.check_output( \
                ['docker', \
                'exec', \
                '-ti', \
                '{0}'.format(instanceName), \
                'dropbox', \
                'status']) \
                .decode("utf-8")
    except subprocess.CalledProcessError as e:
        print(e.output)
    return ret

def timed_status_check(instanceName):
    global indicator
    global threadHandle
    
    statusString = get_dropbox_status(instanceName)
    print(statusString)

    nextCheck = 5.0
    if('Up to date' in statusString):
        set_icon(indicator, idleEmblem)
        nextCheck = 30
    elif('Syncing' in statusString):
        set_icon(indicator, syncingEmblem)
    else:
        set_icon(indicator, unknownEmblem)
    
    threadHandle = threading.Timer(nextCheck, timed_status_check, [instanceName])
    threadHandle.daemon = True
    threadHandle.start()

def set_icon(indicator, iconPath=idleEmblem):
    indicator.set_icon(os.path.abspath(iconPath))

def main():
    global instanceName
    global APPINDICATOR_ID
    global indicator
    global threadHandle

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if(len(sys.argv) != 2):
        print('Error - no dropbox instance name passed')
        sys.exit()
    else:
        instanceName = sys.argv[1]
        APPINDICATOR_ID = instanceName + '-appind'
        print('Dropbox instance {0}'.format(instanceName))

    indicator = appindicator.Indicator.new( \
            APPINDICATOR_ID, \
            os.path.abspath(syncingEmblem), \
            appindicator.IndicatorCategory.APPLICATION_STATUS)
    indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
    indicator.set_title('Dropbox in docker container {0}'.format(instanceName))
    indicator.set_menu(build_menu(instanceName))

    notify.init(APPINDICATOR_ID)

    start_dropbox_docker(instanceName)

    timed_status_check(instanceName)
 
    gtk.main()
    threadHandle.cancel()
    print('Dropbox instance {0} closed'.format(instanceName))

if __name__ == "__main__":
    main()
