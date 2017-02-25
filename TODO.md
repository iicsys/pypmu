# To-Do list #

This to-do list will help us to set priorities and define future work.  

## Must Have ##

* ~~Implement `recv_all` if command is to long for buffer.~~
* ~~Implement `convert2frame()` methods for DataFrame and ConfigFrame.~~
* ~~Implement PDC methods - *getters*.~~
* ~~Upload to `pip`.~~
* ~~Well, well, we might implement StreamSplitter with `Pdc()` and `Pmu()`?~~
* ~~Calculate SOC if not defined in `__init()__` function.~~
* ~~Check phasor values list length using data format (`PHASOR_NUM`).~~
* ~~Check analog values list length using data format (`ANALOG_NUM`).~~
* ~~Check digital values list length using data format (`DIGITAL_NUM`).~~
* ~~Check flags when setting time base.~~

## Good to Have ##

* Read data frames from CSV file.
* Simple GUI for PMU.
* Use *Network Time Protocol* for time measuring.
* Refactor masks using binary literals for easier reading
* `extended2int()` method should try to convert to bytes 
* `set_phasor_num()`, `set_analog_num()`, `set_digital_num()` should be 
one method - easier for maintenance.
* ~~`convert2frame()` should inherit methods from CommonFrame for decoding
 message.~~ 
* User defined analog units.
* Handler for user defined commands (when custom command arrives 
what to do).
* Add delay offset parameter to adjust exact number of Data frames 
per second.
* Make only one module with both PMU and PDC functionality utilizing
Queue as incoming and outgoing stack.