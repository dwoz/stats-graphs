# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)
import re
import os
import signal
import sys
import time
import subprocess
import datetime
from random import random, randint
from pyrrd.rrd import DataSource, RRA, RRD

KEEP_GOING = True
rrd_file = 'process_memory.rrd'
graph_file = 'process_memory.png'


def memory(pid):
    #/bin/ps --no-headers -o size,rss -p 1677
    command = ['ps', '--no-headers', '-o', 'vsz,rss', '--pid', pid]
    try:
        ps = subprocess.check_output(command)
    except subprocess.CalledProcessError:
        vsz, rss = 0, 0
    else:
        vsz, rss = [int(_) for _ in ps.strip().split()]
    return vsz, rss


def sigint_handler(signal, frame):
    global KEEP_GOING
    KEEP_GOING = False

def main():
    if len(sys.argv) == 1:
        print("pid needed")
        sys.exit(1)
    elif len(sys.argv) > 3:
        print("Too many args")
        sys.exit()
    elif len(sys.argv) == 3:
        pid = sys.argv[1]
        graph_name = sys.argv[2]
    else:
        graph_name = 'Memory Usage'
        pid = sys.argv[1]
    signal.signal(signal.SIGINT, sigint_handler)
    dss = [
        DataSource(dsName='vsz', dsType='GAUGE', heartbeat=2),
        DataSource(dsName='rss', dsType='GAUGE', heartbeat=2)
    ]
    rras = [
        RRA(cf='AVERAGE', xff=0.5, steps=10, rows=1000),
        #RRA(cf='AVERAGE', xff=0.5, steps=1, rows=100)
        RRA(cf='LAST', xff=0.5, steps=1, rows=100000)
    ]
    try:
		os.remove(rrd_file)
		os.remove(graph_file)
    except OSError:
		pass
    rrd = RRD(rrd_file, ds=dss, rra=rras, step=1)
    rrd.create()
    start = time.time()
    print("Starting at %d." % start)
    while KEEP_GOING:
        vsz, rss = memory(pid)
        #print("sample {} {}".format(size, rss))
        if vsz == 0 and rss == 0:
            break
        rrd.bufferValue(time.time(), vsz, rss)
        rrd.update()
        time.sleep(1)
    end = time.time()
    print("Sampling finishes: %d." % end)
   #  #rrdtool fetch foo.rrd AVERAGE --end=now --start=now-50s
   #  command = [
   #      'rrdtool',
   #  	'fetch',
   #      rrd_file,
   #      'AVERAGE',
   #      '--end',
   #      str(int(end)),
   #      '--start',
   #      str(int(start))
   #  ]
   #  ps = subprocess.Popen(command)
   #  ps.wait()
   #CDEF:mem_used_x=mem_used,1024,\* \
   #LINE2:mem_used_x#D7CC00:mem_used
    command = [
        'rrdtool',
        'graph',
        '--title',
        graph_name,
        graph_file,
        '--start',
        str(int(start)),
        '--end',
        str(int(end)),
   #     'DEF:vsz={}:vsz:AVERAGE'.format(rrd_file),
        'DEF:rss={}:rss:AVERAGE'.format(rrd_file),
   #     'CDEF:vsz_k=vsz,1024,*',
        'CDEF:rss_k=rss,1024,*',
   #     'LINE:vsz_k#4287f5:Virtual',
        'LINE:rss_k#42d7f5:Residential',
    ]
    ps = subprocess.check_output(command)
    print(ps)
    sys.exit(0)


def epoch():
    timenow=datetime.datetime.utcnow()
    secondssince = (timenow-datetime.datetime(1970, 1, 1)).total_seconds()
    return  int((secondssince + 30.5)/60)*60

if __name__ == '__main__':
    main()
