from synchrophasor.splitter import StreamSplitter

"""
 source_ip and source_port represent data stream source (PMU)
 StreamSplitter will listen on listen_ip and listen_port for incoming
 incoming connections from PDCs."""

sp = StreamSplitter(source_ip='127.0.0.1', source_port=1410, listen_ip='127.0.0.1', listen_port=1502)

sp.run()
sp.join()
