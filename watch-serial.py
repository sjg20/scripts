#!/usr/bin/python

import os
import sys

sys.path.append('tools/patman')

import cros_subprocess
from datetime import datetime, timedelta
import telnetlib


wait_for = 'NET: Registered protocol family 2'
#wait_for = 'Brought up 4 CPUs'

# Seconds to wait
max_wait = 5

###########



boot_text = ''
watching = True

def reboot(log, str):
    global boot_text, watching

    watching = False
    cmd = ['cros_sdk', '--', 'dut-control', '-p', '7777', 'warm_reset:on', 'sleep:.2',
           'warm_reset:off']
    os.system(' '.join(cmd))
    boot_text = ''
    print str
    log.write(str)
    log.flush()


def output(stream, data):
    global boot_text, watching

    if stream == sys.stdout:
        boot_text += data
        #print data,
    if watching:
        if 'Brought up 4 CPUs' in boot_text:
            print 'OK'
            reboot()
        elif 's3c-i2c' in boot_text:
            print 'Bad'
            reboot()
    elif 'U-Boot 2013' in boot_text:
        watching = True
        boot_text = ''

def run():
    args = ['telnet', 'localhost', '4020']
    pipe = cros_subprocess.Popen(args)
    plist = pipe.CommunicateFilter(output)

def watch():
    global boot_text, watching

    sock = telnetlib.Telnet('localhost', '4020')
    log = open('log.txt', 'w')
    watching = True
    boot_text = ''
    ok = 0
    bad = 0
    deadline = datetime.now() + timedelta(seconds=max_wait)
    while True:
        str = sock.read_very_eager()
        if not str:
            if datetime.now() > deadline:
              print 'Timeout'
              bad += 1
              reboot(log, 'OK %d, Bad %d' % (ok, bad))
              deadline = datetime.now() + timedelta(seconds=max_wait)
            continue
        deadline = datetime.now() + timedelta(seconds=max_wait)
        log.write(str)
        log.flush()
        boot_text += str
        if watching:
            if wait_for in boot_text:
                log.write('\n^^^^^^^^^^^^^^^^^\n')
                ok += 1
            #elif ('s3c-i2c' in boot_text or 'ANX1120 I2C write' in boot_text or
            #      'usbcore:' in boot_text):
            #    bad += 1
            else:
                continue
            reboot(log, 'OK %d, Bad %d' % (ok, bad))
        elif 'U-Boot 2013' in boot_text:
            watching = True
            boot_text = ''

#run()
watch()
