from ctypes import *
import mmap
import random
import time

class CoreInfo(Structure):
    _fields_ = [
        ('numLPs',      c_ulonglong),
        ('lpBusyMask',  c_ulonglong),
        ('numHvCores',  c_ulonglong)
    ]


filename = "Global\\HvmMmapFile"
shm = mmap.mmap(0, sizeof(CoreInfo), filename)
coreInfo = CoreInfo.from_buffer(shm)


while True:
    print("numLPs: ", coreInfo.numLPs)
    print("lpBusyMask: ", format(coreInfo.lpBusyMask, '08x'))
    print("numHvCores: ", coreInfo.numHvCores)
    print("=======")

    coreInfo.numHvCores = random.randrange(10)

    time.sleep(2)
