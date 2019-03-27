from ctypes import *
import mmap
import random
import time

import numpy as np
import pandas as pd
import sys
import time
import math
import socket
import random

TESTING = False # Set to false when ran on test server

class CoreInfo(Structure):
    _fields_ = [
        ('numLPs',      c_ulonglong),
        ('lpBusyMask',  c_ulonglong),
        ('numHvCores',  c_ulonglong)
    ]

if not TESTING:
    filename = "Global\\HvmMmapFile"
    shm = mmap.mmap(0, sizeof(CoreInfo), filename)
    coreInfo = CoreInfo.from_buffer(shm)

t_start_monitor = t_start_update = time.time()
prev_num_busy_lp = 0
num_busy_lp_list = [] 
first_time = 1
total_lp = 32 
pred_peak = total_cpu = total_lp #TODO: use LP or PP?
t_monitor = 50*1e-6 # 50us in sec
t_update = 10*1e-3 # 10ms in sec

# set up connection with VW daemon
host = 'localhost'
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (host, port)
s.connect(server_address)

while True:
    #***************** cpu monitoring window ********************
    # read from shared memory
    t_elapsed_monitor = time.time() - t_start_monitor # time elapsed in sec
    if t_elapsed_monitor > t_monitor: # or if shared memory updated by hvm agent
        # log cpu utilization 
        if not TESTING:
            num_busy_lp_list.append(coreInfo.numLPs) #TODO
        else:
            num_busy_lp_list.append(10) 
    #************************************************************


    #***************** cpu peak update window *******************
    t_elapsed_update = time.time() - t_start_update 
    if t_elapsed_update > t_update: 
        observed_peak = np.max(num_busy_lp_list)
        # update model if not first feature
        if first_time:
            first_time = 0
        else:
            def cost_function(label, pred_label, true_label, offset):
                if label < true_label:
                    # underestimate: higher cost
                    cost = true_label - label
                else:
                    # overestimate: lower cost
                    cost = -total_cpu + label - true_label
                return (cost, offset) 
            labelStr = ''
            for j in range(1, total_cpu+1):
                cost, tmp = cost_function(j, pred_peak, observed_peak, 0)
                labelStr += '{0}:{1} '.format(j, cost)
            msg = labelStr + vw_features
            s.sendall(msg)
            data = s.recv(1024)
            
        # compute features
        core_list = num_busy_lp_list
        core_dist = [np.mean(core_list), np.std(core_list), np.min(core_list), np.max(core_list), np.median(core_list)]
        num_busy_lp_list = [] # reset log
        features = core_dist
        vw_features = ""
        featureVals = [str(x) for x in features]
        DIST_SUMMARY = ['average', 'std-dev', 'min', 'max', 'median']
        NAMESPACES = [('busy-cores-prev-interval', DIST_SUMMARY)]
        j = 0
        for namespace,featureNames in NAMESPACES:
            vw_features += "|{0} ".format(namespace)
            if type(featureNames) is list:
                for featureName in featureNames:
                    vw_features += "{0}:{1} ".format(featureName, float(featureVals[j]))
                    j += 1
            else:
                vw_features += "{0}:{1} ".format(featureName, float(featureVals[j]))
                j += 1
        vw_features += "\n"
       
        # make prediction 
        msg = vw_features
        s.sendall(msg)
        data = s.recv(1024)
        pred_peak = int(data.strip())

        # write to shared memory
        if not TESTING:
            coreInfo.numHvCores = pred_peak # TODO: convert to LP??
        else:
            print pred_peak
    #************************************************************

    
