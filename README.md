# Python Synchrophasor Module #

Synchrophasor module represents implementation of IEEE C37.118.2
standard in Python. `synchrophasor` module is still in development phase
but we have few very interesting tools.

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

* Clone this repository 
`git clone https://github.com/sstevan/synchrophasor.git` or
* Download this repository as `.zip` file and extract or
* ~~Install using `pip`~~ or
* Use [PyCharm](https://www.jetbrains.com/pycharm/) to clone this repo.


Add `synchrophasor` folder to `PYTHONPATH`:


* If you're using GNU/Linux or Mac OS X add `synchrophasor` folder 
(located inside repo folder) to your `$PYTHONPATH` like this:

`export PYTHONPATH="${PYTHONPATH}:/path_to/synchrophasor/synchrophasor" >> ~/.bashrc`

* If you're using Windows switch to GNU/Linux and check previous
solution or
* Add module folder following this [tutorial](https://docs.python.org/2/using/windows.html#excursus-setting-environment-variables) or
* ~~If you've installed it using `pip` it's already there or~~
* If you've cloned repository using PyCharm - PyCharm will handle it 
for you.


### Running the tests ###

Right now we have only one test for frame encapsulation validation. You
can check it like this:
```
python tests/validate_frames.py
```
If you have Python 3 installed alongside with Python 2 you should try
like this:
```
python3 tests/validate_frames.py
```

If ```AssertionError``` is **not** shown you're good to go!


## Usage - What we have so far? ##

Inside examples folder you will find few useful examples that utilize
`synchrophasor` module.

### TinyPMU ###

With only few lines of code you can bring up PMU simulator which will
send constant phasor measurements to connected PDCs. 

```
from synchrophasor.pmu import Pmu


pmu = Pmu(port=1410, ip="127.0.0.1")

pmu.set_configuration()  # This will load default PMU configuration specified in IEEE C37.118.2 - Annex D (Table D.2)
pmu.set_header()  # This will load default header message "Hello I'm tinyPMU!"

pmu.run()  # PMU starts listening for incoming connections

while True:
    if pmu.clients:  # Check if there is any connected PDCs
        pmu.send(pmu.ieee_data_sample)  # Sending sample data frame specified in IEEE C37.118.2 - Annex D (Table D.1)

pmu.join()

```

### TinyPDC ###

Here's an example of very simple PDC. tinyPDC supports only one 
connection to PMU and still cannot understand measurements or
configuration but with your help we can learn tinyPDC to read 
Data Frames and Configuration Frames

```
from synchrophasor.pdc import Pdc

pdc = Pdc(pdc_id=7, pmu_ip='127.0.0.1', pmu_port=1410)

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

### StreamSplitter ###

Possible practical use of synchrophasor module would be data-stream
splitter. In case you need to send phasor measurements to multiple
destinations following 4 lines of code will do it:

```
from synchrophasor.splitter import StreamSplitter

sp = StreamSplitter(source_ip='127.0.0.1', source_port=1410, listen_ip='127.0.0.1', listen_port=1502)
sp.run()
sp.join()
```

## We don't have it yet? :( ##

Since `synchrophasor` module is in early development phase we're
missing few very important things.

* We don't have Configuration Frame version 1 and version 3 implemented
but Configuration Frame version 2 is working just fine.
* We don't have `convert2frame()` methods for converting raw bytes
into `DataFrame` or `ConfigFrame`. We do have it for `CommandFrame` and
`HeaderFrame`.
* We don't have UDP connection supported yet but TCP looks like it's
working as it should

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

* [IEEE C37.118](http://smartgridcenter.tamu.edu/resume/pdf/1/SynPhasor_std.pdf)