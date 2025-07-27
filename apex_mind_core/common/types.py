from enum import Enum

class HardwareOpType(Enum):
    GpuCompute = 0
    FileRead = 1
    FileWrite = 2
    SensorRead = 3
    NetworkRequest = 4
    CameraCapture = 5
