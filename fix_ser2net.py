#!/usr/bin/env python3

"""update /etc/ser2net.yaml so that ports are as follows:

4000 - first servo AP
4001 - first servo EC
4002 - first servo Cr50 / GSC

For this to work you must name your connections servo_cpu, etc. See UARTS.

It replaces the /dev/pts/xxx lines with the correct PTS number
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
    out = subprocess.run(['cros_sdk', 'dut-control'] + names, check=True,
                         capture_output=True, encoding='utf-8').stdout

    # Convert the separate lines into a dict: key=uart, value=pty (int)
    uarts = {}
    for mat in [RE_UART.match(val) for val in out.splitlines()]:
        uarts[mat.group(1)] = int(mat.group(2))
    return uarts

def process_file(fname, uarts):
    """Read in the existing file and create a new version with the updates

    Args:
        fname (str): Filename of yaml file to read
        uarts (dict); dict of uarts:
            key: uart name, e.g. 'cpu'
            value (int): PTY number, e.g. 17
    """
    out = io.StringIO()
    cur_conn = None
    done = set()
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
                print(RE_PTS.sub(f'/dev/pts/{uarts[cur_conn]}', line), file=out)
                done.add(cur_conn)
            else:
                print(line, file=out)
    return out.getvalue(), done


def doit():
    """Update the config file"""
    uarts = get_uarts()
    out, done = process_file(FILENAME, uarts)
    subprocess.run(f"sudo cp {FILENAME} {FILENAME}~", check=True, shell=True)
    subprocess.run(f"sudo sh -c 'cat >{FILENAME}'", input=out, check=True,
                    encoding='utf-8', shell=True)

    print(f'Updated UARTs {" ".join(done)} in {FILENAME} with backup in {FILENAME}~')


if __name__ == '__main__':
    doit()
