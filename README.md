# pyPMU - Python Synchrophasor Module #

Synchrophasor module represents implementation of IEEE C37.118.2
standard in Python. `synchrophasor` module is still in development phase
but we have a few very interesting tools.

### Notes: 

##### - Latest Alpha release: v1.0.0-alpha
##### - We need some beta testers!

## Getting Started ##

Synchrophasor module is made to be easy to install and run.

### Prerequisites ###

You will need `python3` to run module correctly. Check 
your Python version:
```
python --version
```
If you're using Python 2 version you can install [Python 3](https://www.python.org/downloads/) alongside with
Python 2. 

### Installing ###

* Install using `pip` for Python 3: `pip3 install synchrophasor`

* You can download this project as `zip` file and extract it or clone it
using git `git clone https://github.com/iicsys/pypmu.git` and then run 
`python3 setup.py install` inside project folder.

### Running the tests ###

Right now we only have one test for frame encapsulation validation. You
can check it like this:
```
python3 tests/validate_frames.py
```

If ```AssertionError``` is **not** shown you're good to go!


## Usage - What do we have so far? ##

Inside examples folder you will find a few useful examples that utilize
`synchrophasor` module.

### StreamSplitter ###

Possible practical use of the synchrophasor module would be data-stream
splitter. In case you need to send phasor measurements to multiple
destinations following 4 lines of code will do it:

```
from synchrophasor.splitter import StreamSplitter

sp = StreamSplitter(source_ip="127.0.0.1", source_port=1410, listen_ip="127.0.0.1", listen_port=1502)
sp.run()
```


### TinyPMU ###

With only few lines of code you can bring up a PMU simulator which will
send constant phasor measurements to connected PDCs. 

```
from synchrophasor.pmu import Pmu


pmu = Pmu(ip="127.0.0.1", port=1410)

pmu.set_configuration()  # This will load default PMU configuration specified in IEEE C37.118.2 - Annex D (Table D.2)
pmu.set_header()  # This will load default header message "Hello I'm tinyPMU!"

pmu.run()  # PMU starts listening for incoming connections

while True:
    if pmu.clients:  # Check if there is any connected PDCs
        pmu.send(pmu.ieee_data_sample)  # Sending sample data frame specified in IEEE C37.118.2 - Annex D (Table D.1)

pmu.join()

```

### TinyPDC ###

Here's an example of a very simple PDC. tinyPDC supports only one 
connection to a PMU and still cannot understand measurements or
configuration but with your help we can learn tinyPDC to read 
Data Frames and Configuration Frames

```
from synchrophasor.pdc import Pdc

pdc = Pdc(pdc_id=7, pmu_ip="127.0.0.1", pmu_port=1410)

pdc.run()  # Connect to PMU

header = pdc.get_header()  # Get header message from PMU
config = pdc.get_config()  # Get configuration from PMU

pdc.start()  # Request to start sending measurements

while True:
    data = pdc.get()  # Keep receiving data
    if not data:
        pdc.quit()  # Close connection
        break
```

## Applications ##

If you really don't want to know what is inside of these scripts we've 
prepared applications for you inside `apps` folder.

Make them executable like this:

`chmod +x splytter.py`

Then you can ask for help like this and you will find usage example
there:

`./splytter --help`

### splytter ###

If you don't want to bother writing your own script for stream splitter
you can run `splytter` application like this:

`
./splytter.py -i 10 -sip 127.0.0.1 -sp 1410 -lip 127.0.0.1 -lp 9991'
`

### pmy ###

If you need a PMU simulator for a network test or something like that you
can run the `pmy` application which will send constant data frames to all
connected PDCs:

`
./pmy.py -i 511 -ip 127.0.0.1 -p 1995 -r 30'
`
## We don't have it yet? :( ##

Since `synchrophasor` module is in early development phase we're
missing a few very important things.

* We don't have UDP connection supported yet but TCP looks like it's
working as it should.
* We don't have Configuration Frame 3 implemented.
* We don't have out-of-the-box data stream aggregation for PDC.

If you feel like you could help us, with testing or developing please
do not hesitate to contact us: <stevan.sandi@gmail.com> or
<tp0x45@gmail.com>.

## Contributing ##

1. Please check [TODO.md](TODO.md) to find out where you can help us.
2. Fork this repo.
3. Create new branch: `git checkout -b fixing-your-stupid-bug`
4. Commit changes: `git commit -m 'There you go! Fixed your stupid bug.'`
5. Push changes to the branch: `git push origin fixing-your-stupid-bug` 
6. Submit pull request.

## Credits ##

* [Tomo Popovic](https://me.linkedin.com/in/tomopopovic) - `synchrophasor` module project leader.
* [Bozo Krstajic](https://me.linkedin.com/in/bozo-krstajic-b503b51) - `synchrophasor` module project adviser.
* [Stevan Sandi](https://me.linkedin.com/in/sstevan) - `synchrophasor` module project developer.

## License ##

Please check [LICENSE.txt](LICENSE.txt).

## References ##

* C37.118.2-2011 - IEEE Standard for Synchrophasor Data Transfer for Power Systems,  [>>](http://standards.ieee.org/findstds/standard/C37.118.2-2011.html)
 
## Citations ##

_If you use the pyPMU code for your research, please cite the following publication:_

* S. Sandi, T. Popovic, "pyPMU – Open Source Python Package for Synchrophasor Data Transfer", IEEE 24th Telecommunications Forum (TELFOR), Belgrade, Serbia, Nov 22-23

* S. Sandi, T. Popovic, B. Krstajic, "Python Implementation of IEEE C37.118 Communication Protocol", Journal of Electrical Engineering, Faculty of Electrical Engineering, University, Podgorica, Montenegro, Vol. 21, No. 1, December 2015, pp 108-117
