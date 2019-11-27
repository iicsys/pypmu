from synchrophasor.frame import *
from synchrophasor.pmu import Pmu
import random

"""
pyPMU is custom configured PMU simulator. Code below represents
PMU described in IEEE C37.118.2 - Annex D.
"""


if __name__ == "__main__":

    pmu = Pmu(ip="", port=10000,method='udp')
    pmu.logger.setLevel("DEBUG")

    ph_v_conversion = int(300000.0 / 32768 * 100000)  # Voltage phasor conversion factor
    ph_i_conversion = int(15000.0 / 32768 * 100000)  # Current phasor conversion factor
    cfg = ConfigFrame2(7,  # PMU_ID
                       1000000,  # TIME_BASE
                       1,  # Number of PMUs included in data frame
                       "Station A",  # Station name
                       7734,  # Data-stream ID(s)
                       (True, True, True, True),  # Data format - Check ConfigFrame2 set_data_format()
                       3,  # Number of phasors
                       1,  # Number of analog values
                       1,  # Number of digital status words
                       ["VA", "VB", "VC", "ANALOG1", "BREAKER 1 STATUS",
                        "BREAKER 2 STATUS", "BREAKER 3 STATUS", "BREAKER 4 STATUS", "BREAKER 5 STATUS",
                        "BREAKER 6 STATUS", "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                        "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS", "BREAKER D STATUS",
                        "BREAKER E STATUS", "BREAKER F STATUS", "BREAKER G STATUS"],  # Channel Names
                       [(0, "v"), (0, "v"),
                        (0, "v")],  # Conversion factor for phasor channels - (float representation, not important)
                       [(1, "pow")],  # Conversion factor for analog channels
                       [(0x0000, 0xffff)],  # Mask words for digital status words
                       60,  # Nominal frequency
                       1,  # Configuration change count
                       240)  # Rate of phasor data transmission)

    hf = HeaderFrame(7,  # PMU_ID
                     "Hello I'm nanoPMU!")  # Header Message

    pmu.set_configuration(cfg)
    pmu.set_header(hf)

    pmu.run()

    import time
    samples=240
    PERIOD=1/samples
    firstIter=True

    

    while True:
        if pmu.clients:
            if firstIter:
                while (n:=time.time())%1!=0:
                    continue
                next1 = n + PERIOD
                firstIter=False
            
            pmu.send_data(phasors=[(random.uniform(215.0, 240.0), random.uniform(-0.1, 0.3)),
                                   (random.uniform(215.0, 240.0), random.uniform(1.9, 2.2)),
                                   (random.uniform(215.0, 240.0), random.uniform(3.0, 3.14))],
                          analog=[9.91],
                          digital=[0x0001])
            delay = -1.0
            missed = 0

            while delay < 0.0:

                delay = next1 - time.time()

                next1 += PERIOD

                missed += 1

            if missed > 1:
                print("missed {} appointments.".format(missed - 1))

            time.sleep(delay)

    pmu.join()