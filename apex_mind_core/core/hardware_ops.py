from enum import Enum

class HardwareOpType(Enum):
    FileRead = 1
    FileWrite = 2
    NetworkRequest = 3
    GpuCompute = 4

class HardwareOp:
    def __init__(self, op_type: HardwareOpType):
        self.op_type = op_type
        self.path = ""   # For file operations
        self.url = ""    # For network requests
        self.shader_code = ""  # For GPU ops
        self.data = b""  # For write operations and GPU data
