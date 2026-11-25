from pymodaq.control_modules.move_utility_classes import comon_parameters_fun, main

from pymodaq_plugins_moke.hardware.simulated_move import SimulatedBenchMove


class DAQ_Move_MokeWavePlateSim(SimulatedBenchMove):
    """Simulated rotation mount of the half-wave plate in front of the polarising beam splitter (balance adjustment).

    The axis is the angle of the plate, in degrees. The plate rotates the polarisation by twice its angle: the two
    photodiodes of the balanced detector are balanced when the angle, counted from the (hidden) zero of the plate,
    is 22.5 deg. The offset of this zero is a setting of the balanced detector plugin.

    Compatible devices: none, this is a simulation shared with the other ``MokeXxxSim`` plugins through the
    controller (master/slave, same controller ID). Nothing was tested on a real instrument.
    Tested with PyMoDAQ 5.3.13 on Linux. No driver to install.
    """
    _axis_names = ['waveplate']
    _controller_units = 'deg'
    _epsilons = [0.01]
    _bench_attribute = 'waveplate_angle'
    _home_value = 22.5
    params = comon_parameters_fun(is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilons)


if __name__ == '__main__':
    main(__file__)
