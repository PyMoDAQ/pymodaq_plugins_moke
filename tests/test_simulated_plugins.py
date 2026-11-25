"""Behaviour of the simulated MOKE plugins as the Dashboard drives them, with the harness of PyMoDAQ.

The magnet, half-wave plate, sample rotation and goniometer actuators and the balanced detector share one bench:
the first plugin initialised is the master and the others receive its controller (slaves)."""
import numpy as np
import pytest

from pymodaq.utils.plugin_testing import (make_actuator, make_detector, move_abs_and_wait, move_rel_and_wait,
                                          move_home_and_wait, grab_and_wait, assert_units)

from pymodaq_plugins_moke.daq_move_plugins.daq_move_MokeMagnetSim import DAQ_Move_MokeMagnetSim
from pymodaq_plugins_moke.daq_move_plugins.daq_move_MokeWavePlateSim import DAQ_Move_MokeWavePlateSim
from pymodaq_plugins_moke.daq_move_plugins.daq_move_MokeSampleRotationSim import DAQ_Move_MokeSampleRotationSim
from pymodaq_plugins_moke.daq_move_plugins.daq_move_MokeGoniometerSim import DAQ_Move_MokeGoniometerSim
from pymodaq_plugins_moke.daq_viewer_plugins.plugins_0D.daq_0Dviewer_MokeBalancedSim import (
    DAQ_0DViewer_MokeBalancedSim, LABELS)

ACTUATORS = {DAQ_Move_MokeMagnetSim: 'mT', DAQ_Move_MokeWavePlateSim: 'deg',
             DAQ_Move_MokeSampleRotationSim: 'deg', DAQ_Move_MokeGoniometerSim: 'deg'}


def set_setting(plugin, path, value):
    """Change a setting as the module does: set the value, then let the plugin apply it (commit_settings)"""
    param = plugin.settings.child(*path)
    param.setValue(value)
    plugin.commit_settings(param)


@pytest.fixture
def bench_plugins():
    """All the plugins on one bench: the magnet is the master, the others are slaves"""
    magnet = make_actuator(DAQ_Move_MokeMagnetSim, tau=1.)  # 1 ms response time, fast tests
    plugins = [magnet]
    for cls in (DAQ_Move_MokeWavePlateSim, DAQ_Move_MokeSampleRotationSim, DAQ_Move_MokeGoniometerSim):
        plugins.append(make_actuator(cls, controller=magnet.controller))
    detector = make_detector(DAQ_0DViewer_MokeBalancedSim, controller=magnet.controller)
    plugins.append(detector)
    yield magnet, plugins[1:-1], detector
    for plugin in reversed(plugins):
        plugin.close()


@pytest.mark.parametrize('cls, unit', list(ACTUATORS.items()))
def test_each_actuator_moves_and_reports_its_unit(cls, unit):
    actuator = make_actuator(cls)
    assert actuator.initialized
    pos = move_abs_and_wait(actuator, 10.)
    assert pos.units == unit
    assert pos.value(unit) == pytest.approx(10., abs=0.6)
    pos = move_rel_and_wait(actuator, 2.)
    assert pos.value(unit) == pytest.approx(12., abs=0.6)
    actuator.close()


def test_home_positions():
    magnet = make_actuator(DAQ_Move_MokeMagnetSim, tau=1.)
    move_abs_and_wait(magnet, 30.)
    assert move_home_and_wait(magnet).value('mT') == pytest.approx(0., abs=0.6)
    waveplate = make_actuator(DAQ_Move_MokeWavePlateSim)
    move_abs_and_wait(waveplate, 5.)
    assert move_home_and_wait(waveplate).value('deg') == pytest.approx(22.5, abs=0.02)


def test_all_plugins_share_one_controller(bench_plugins):
    magnet, others, detector = bench_plugins
    assert all(p.controller is magnet.controller for p in others)
    assert detector.controller is magnet.controller


def test_slaves_do_not_close_the_shared_bench(bench_plugins):
    magnet, others, detector = bench_plugins
    others[0].close()
    detector.close()
    assert not magnet.controller.closed


def test_detector_returns_four_channels_in_volts(bench_plugins):
    _, _, detector = bench_plugins
    dte = grab_and_wait(detector)
    assert len(dte) == 1
    assert dte[0].labels == LABELS
    assert dte[0].dim.name == 'Data0D'
    assert_units(dte, 'V')


def test_hysteresis_loop_through_the_plugins(bench_plugins):
    magnet, _, detector = bench_plugins
    set_setting(detector, ('imperfections', 'imperfections_enabled',), False)
    set_setting(detector, ('sample', 'model',), 'tanh')
    fields = np.concatenate([np.linspace(-60, 60, 13), np.linspace(60, -60, 13)])
    signal = []
    for field in fields:
        move_abs_and_wait(magnet, field)
        data = grab_and_wait(detector)
        signal.append(float(data.get_data_from_full_name('MokeBalanced/MokeBalanced').data[2][0]))
    signal = np.array(signal)
    up, down = signal[:13], signal[13:][::-1]
    assert up[0] < 0 < up[-1]
    assert up[6] * down[6] < 0  # the remanent state depends on the history


def test_waveplate_balances_the_detection(bench_plugins):
    _, (waveplate, *_), detector = bench_plugins
    set_setting(detector, ('imperfections', 'imperfections_enabled',), False)
    set_setting(detector, ('optics', 'waveplate_zero',), 3.)
    move_abs_and_wait(waveplate, 22.5)
    unbalanced = grab_and_wait(detector)[0].data
    move_abs_and_wait(waveplate, 25.5)
    balanced = grab_and_wait(detector)[0].data
    assert abs(balanced[2][0]) < abs(unbalanced[2][0])


def test_settings_reach_the_bench(bench_plugins):
    magnet, _, detector = bench_plugins
    set_setting(detector, ('sample', 'hk',), 55.)
    set_setting(detector, ('imperfections', 'laser_noise_rms',), 0.5)  # in %
    set_setting(detector, ('imperfections', 'electronic_noise_rms',), 30.)  # in uV
    assert magnet.controller.sample.hk == 55.
    assert magnet.controller.imperfections.laser_noise_rms == pytest.approx(5e-3)
    assert magnet.controller.imperfections.electronic_noise_rms == pytest.approx(30e-6)
    set_setting(magnet, ('tau',), 200.)
    assert magnet.controller.field_tau == pytest.approx(0.2)


def test_detector_alone_works_as_master():
    detector = make_detector(DAQ_0DViewer_MokeBalancedSim)
    assert detector.initialized
    dte = grab_and_wait(detector)
    assert dte[0].labels == LABELS
    detector.close()
