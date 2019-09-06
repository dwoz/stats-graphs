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
import argparse
from random import random, randint
from pyrrd.rrd import DataSource, RRA, RRD
import psutil

KEEP_GOING = True
rrd_file = 'process_memory.rrd'
graph_file = 'process_memory.png'

parser = argparse.ArgumentParser()
parser.add_argument(
    'pid',
    help='The process id to graph',
    type=int,
)
parser.add_argument(
    '--graph-name',
    help='The name put on the graph produced',
    default='Process Memory',
)
parser.add_argument(
    '--children',
    help='Include the memory usage of all decendent processes',
    default=False,
    action='store_true',
)

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


def pid_memory(pid):
    try:
        proc = psutil.Process(pid)
        mem_info = proc.memory_info()
    except psutil.NoSuchProcess:
        return 0, 0
    return mem_info.vms / 1024, mem_info.rss / 1024


def walk_children(pid):
    try:
        proc = psutil.Process(pid)
        for sub_proc in proc.children():
            yield sub_proc.pid
            for sub_pid in walk_children(sub_proc.pid):
                yield sub_pid
    except psutil.NoSuchProcess:
        pass

def pid_and_subs_memory(pid):
    vsz, rss = pid_memory(pid)
    if vsz == 0 and rss == 0:
        return vsz, rss
    for child_pid in walk_children(pid):
        if pid:
            try:
                c_vsz, c_rss = pid_memory(child_pid)
            except psutil.NoSuchProcess:
                continue
            vsz += c_vsz
            rss += c_rss
    return vsz, rss


def sigint_handler(signal, frame):
    global KEEP_GOING
    KEEP_GOING = False

def main():
    ns = parser.parse_args()
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
        if ns.children:
            vsz, rss = pid_and_subs_memory(ns.pid)
        else:
            vsz, rss = pid_memory(ns.pid)
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
        ns.graph_name,
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
