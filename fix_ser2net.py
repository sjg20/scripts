#!/usr/bin/env python3

"""Automate port mapping so you can telnet to Chromebook UARTs

This updates /etc/ser2net.yaml so that ports are mapped correctly and you can
use 'telnet localhost 4000' to access the AP UART, for example.

It replaces the /dev/pts/xxx lines with the correct PTS number.

To use this, do 'sudo apt install ser2net' then add something like this to the
end of /etc/ser2net.yaml :

connection: &servo_cpu
    accepter: telnet,localhost,4000
    enable: on
    options:
      banner: *banner
      kickolduser: true
    connector: serialdev,
              /dev/pts/17,
              115200n81,nobreak

connection: &servo_ec
    accepter: telnet,localhost,4001
    enable: on
    options:
      banner: *banner
      kickolduser: true
    connector: serialdev,
              /dev/pts/15,
              115200n81,nobreak

connection: &servo_cr50
    accepter: telnet,localhost,4002
    enable: on
    options:
      banner: *banner
      kickolduser: true
    connector: serialdev,
              /dev/pts/13,
              115200n81,nobreak
"""

import io
import re
import subprocess
import sys

# Parse 'cpu_uart_pty:/dev/pts/17' to extract cpu and 17
RE_UART = re.compile(r'^([a-z0-9]*).*:/dev/pts/(.*)')

# UARTs we want to update
UARTS = ['cpu', 'ec', 'cr50']

# Filename to update
FILENAME = '/etc/ser2net.yaml'

RE_CONN = re.compile(r'connection: &servo_(.*)')
RE_PTS = re.compile(r'/dev/pts/[0-9]*')

def get_uarts():
    """Get the PTYs for each uart we are interested in

    Return:
        dict of uarts:
            key: uart name, e.g. 'cpu'
            value (int): PTY number, e.g. 17
    """
    names = [f'{u}_uart_pty' for u in UARTS]

    # This emits lines like 'cpu_uart_pty:/dev/pts/17'
    out = subprocess.run(['cros_sdk', 'dut-control'] + names, check=False,
                         capture_output=True, encoding='utf-8')
    if out.returncode:
        print(out.stderr, file=sys.stderr)
        sys.exit(1)

    # Convert the separate lines into a dict: key=uart, value=pty (int)
    uarts = {}
    for mat in [RE_UART.match(val) for val in out.stdout.splitlines()]:
        uarts[mat.group(1)] = int(mat.group(2))
    return uarts

def process_file(fname, uarts):
    """Read in the existing file and create a new version with the updates

    Args:
        fname (str): Filename of yaml file to read
        uarts (dict); dict of uarts:
            key: uart name, e.g. 'cpu'
            value (int): PTY number, e.g. 17

    Returns:
        tuple:
            str: New contents of file
            found: dict of actions taken:
                key: uart name, e.g. 'cpu'
                value (bool): True if changed, False if already correct
    """
    out = io.StringIO()
    cur_conn = None
    found = {}
    with open(fname, encoding='utf-8') as inf:
        for line in inf.read().splitlines():
            m_conn = RE_CONN.match(line)
            m_pts = RE_PTS.search(line)
            if m_conn:
                cur_conn = m_conn.group(1)
                if cur_conn not in uarts:
                    print(f'Ignoring unknown uart {cur_conn}', file=sys.stderr)
            if m_pts:
                if not cur_conn:
                    print(f'Ignoring {line} with unknown connection',
                        file=sys.stderr)
                new_line = RE_PTS.sub(f'/dev/pts/{uarts[cur_conn]}', line)
                print(new_line, file=out)
                found[cur_conn] = new_line != line
            else:
                print(line, file=out)
    return out.getvalue(), found


def doit():
    """Update the config file

    Return:
        int: exit code (0 for sucess, 1 for error)"""
    uarts = get_uarts()
    out, found = process_file(FILENAME, uarts)
    if not found:
        print(f'No suitable connections found in {FILENAME} - please check docs')
        return 1

    updated = [key for key, val in found.items() if val]
    if updated:
        subprocess.run(f"sudo cp {FILENAME} {FILENAME}~", check=True, shell=True)

        # Use sh inside the shell command so that the redirect is done as root
        subprocess.run(f"sudo sh -c 'cat >{FILENAME}'", input=out, check=True,
                        encoding='utf-8', shell=True)

        print(f'Updated UARTs {" ".join(updated)} in {FILENAME} with backup in {FILENAME}~')

        # Restart the daemon so that the changes take effect
        subprocess.run('sudo systemctl restart ser2net', check=True, shell=True)
    else:
        print(f'Not updated, UARTs {" ".join(found.keys())} are correct in {FILENAME}')
    return 0


if __name__ == '__main__':
    sys.exit(doit())
