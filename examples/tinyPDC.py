from synchrophasor.pdc import Pdc
from synchrophasor.frame import DataFrame
import pickle
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
    i=0
    while True:

        data = pdc.get()  # Keep receiving data

        if type(data) == DataFrame:
            data=data.get_measurements()
            i+=1
            timestamps.append(data['time'])

        if not data:
            continue
        if i==240:
            break

    pdc.stop()
    pdc.quit()
    with open("timestamps","wb+")as handle:
        pickle.dump(timestamps,handle)
