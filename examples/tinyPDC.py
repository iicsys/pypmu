from synchrophasor.pdc import Pdc
from synchrophasor.frame import DataFrame
from matplotlib.pyplot import plot,show
import socket
"""
tinyPDC will connect to pmu_ip:pmu_port and send request
for header message, configuration and eventually
to start sending measurements.
"""


if __name__ == "__main__":

    pdc = Pdc(pdc_id=7, pmu_ip=socket.gethostbyname("rasp"), pmu_port=10000)
    pdc.logger.setLevel("DEBUG")

    pdc.run()  # Connect to PMU

    # header = pdc.get_header()  # Get header message from PMU
    config = pdc.get_config()  # Get configuration from PMU

    pdc.start()  # Request to start sending measurements
    timestamps=[]
    for i in range(100):

        data = pdc.get()  # Keep receiving data

        if type(data) == DataFrame:
            print(data.get_measurements())


        if not data:
            break


