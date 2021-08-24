from pathlib import Path
from pymodaq_plugins_daqmx.hardware.national_instruments import daq_NIDAQmx  # to be called in order to import correct
# parameters

with open(str(Path(__file__).parent.joinpath('VERSION')), 'r') as fvers:
    __version__ = fvers.read().strip()
