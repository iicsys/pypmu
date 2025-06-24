import base64
import binascii
from struct import pack

from synchrophasor.frame import HeaderFrame, ConfigFrame2, DataFrame

cfg = ConfigFrame2(7734, 1000000, 1, "Station A", 7734, (True, True, True, True), 4, 3, 1,
                   ["VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3", "BREAKER 1 STATUS",
                    "BREAKER 2 STATUS", "BREAKER 3 STATUS", "BREAKER 4 STATUS", "BREAKER 5 STATUS",
                    "BREAKER 6 STATUS", "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                    "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS", "BREAKER D STATUS",
                    "BREAKER E STATUS", "BREAKER F STATUS", "BREAKER G STATUS"],
                   [(915527, "v"), (915527, "v"), (915527, "v"), (45776, "i")],
                   [(1, "pow"), (1, "rms"), (1, "peak")], [(0x0000, 0xffff)], 60, 22, 30,
                   1149577200, 463000)



print(str(binascii.hexlify(pack("!f", float(16))), "utf-8"))



df = DataFrame(7734, ("ok", True, "timestamp", False, False, False, 0, "<10", 0),
               [(14635, 0), (-7318, -1.1), (-7318, 1.1), (1092, 0)], 2500, 0, [100, 1000, 10000], [0x3c12], cfg,
               1149580800, 16817)
print(str(binascii.hexlify(df.convert2bytes()), "utf-8"))
print( base64.b64encode(df.convert2bytes()))

data_hex_result = str(binascii.hexlify(df.convert2bytes()), "utf-8")