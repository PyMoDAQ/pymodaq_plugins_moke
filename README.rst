pymodaq_plugins_moke
####################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_moke.svg
   :target: https://pypi.org/project/pymodaq_plugins_moke/
   :alt: Latest Version

.. image:: https://github.com/PyMoDAQ/pymodaq_plugins_moke/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/PyMoDAQ/pymodaq_plugins_moke/actions/workflows/tests.yml

PyMoDAQ plugins for magneto-optical Kerr effect (MOKE) measurements at CEMES: the macro bench (a photodetector
and an electromagnet) and the micro bench (Kerr microscope with a camera and LED illumination).

This branch targets **PyMoDAQ 5.3.x** (Python 3.11 to 3.14).

Authors
=======

* Sebastien Weber (sebastien.weber@cemes.fr)

Instruments
===========

Below is the list of instruments included in this plugin

Actuators
+++++++++

* **Current**: current of the electromagnet, through a National Instruments analog output (needs ``pymodaq_plugins_daqmx``)
* **CurrentMock**: simulated version of the above, with a magnetic hysteresis
* **LedDC4104**: Thorlabs DC4104 four-channel LED driver of the Kerr microscope

Viewer0D
++++++++

* **ReadCurrent**: reads the electromagnet current on a National Instruments analog input

Viewer1D
++++++++

* **MokeMacro**: detection of the macro MOKE bench

Viewer2D
++++++++

* **MOKEGrabber**: Andor sCMOS camera of the Kerr microscope (needs ``pymodaq_plugins_andor``)
* **MOKEMockGrabber**: simulated Kerr microscope image, with a magnetic hysteresis


Extensions
==========

* **MicroMOKE**: acquisition of Kerr microscope images with the sequence of LED illuminations


Installation instructions
=========================

* PyMoDAQ 5.3.7 or later.
* The National Instruments and Andor drivers are needed by the plugins that use them (see ``pymodaq_plugins_daqmx``
  and ``pymodaq_plugins_andor``).


Development
===========

* Install your plugin in editable mode: ``pip install -e .``
* Check it, without any hardware: ``check_plugin`` (and ``pytest``)
* If you use an AI coding assistant, point it to ``AGENTS.md``: it describes the patterns to follow for instrument
  plugins, Dashboard extensions (``CustomExt``, whenever instruments are involved) and standalone apps
  (``CustomApp``, only if no instruments are needed).
