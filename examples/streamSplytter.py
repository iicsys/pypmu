from synchrophasor.splitter import StreamSplytter

"""
 source_ip and source_port represent data stream source (PMU)
 StreamSplytter will listen on listen_ip and listen_port for incoming
 incoming connections from PDCs."""

sp = StreamSplytter(source_ip='127.0.0.1', source_port=1410, listen_ip='127.0.0.1', listen_port=1502)

sp.run()
sp.join()
