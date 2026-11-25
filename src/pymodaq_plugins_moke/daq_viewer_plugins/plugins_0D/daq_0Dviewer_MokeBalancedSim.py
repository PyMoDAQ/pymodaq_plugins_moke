import numpy as np

from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter
from pymodaq_utils.utils import ThreadCommand
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins

from pymodaq_plugins_moke.hardware.simulated_bench import MokeBench, MODELS

LABELS = ['diode_A', 'diode_B', 'difference', 'sum']

# setting name -> (bench settings group, attribute, factor from the displayed unit to the bench unit)
BENCH_PARAMETERS = {
    'model': ('sample', 'model', 1), 'hk': ('sample', 'hk', 1.), 'hc': ('sample', 'hc', 1.),
    'width': ('sample', 'width', 1.), 'easy_polar': ('sample', 'easy_polar', 1.),
    'easy_azimuth': ('sample', 'easy_azimuth', 1.), 'kerr_polar': ('sample', 'kerr_polar', 1e-3),
    'kerr_long': ('sample', 'kerr_long', 1e-3), 'kerr_trans': ('sample', 'kerr_trans', 1e-3),
    'polarization': ('sample', 'polarization', 1), 'kerr_s_over_p': ('sample', 'kerr_s_over_p', 1.),
    'power': ('optics', 'power', 1.), 'reflectivity': ('optics', 'reflectivity', 1.),
    'responsivity': ('optics', 'responsivity', 1.), 'gain': ('optics', 'gain', 1e3),
    'waveplate_zero': ('optics', 'waveplate_zero', 1.),
    'imperfections_enabled': ('imperfections', 'enabled', 1),
    'shot_noise': ('imperfections', 'shot_noise', 1),
    'electronic_noise': ('imperfections', 'electronic_noise', 1),
    'electronic_noise_rms': ('imperfections', 'electronic_noise_rms', 1e-6),
    'laser_noise': ('imperfections', 'laser_noise', 1),
    'laser_noise_rms': ('imperfections', 'laser_noise_rms', 1e-2),
    'imbalance': ('imperfections', 'imbalance', 1),
    'imbalance_percent': ('imperfections', 'imbalance_percent', 1.),
    'faraday': ('imperfections', 'faraday', 1), 'faraday_slope': ('imperfections', 'faraday_slope', 1e-6),
    'drift': ('imperfections', 'drift', 1), 'drift_amplitude': ('imperfections', 'drift_amplitude', 1e-3),
    'drift_period': ('imperfections', 'drift_period', 1.),
}


def _num(title, name, value, **kwargs):
    return {'title': title, 'name': name, 'type': 'float', 'value': value, **kwargs}


def _check(title, name, value):
    return {'title': title, 'name': name, 'type': 'bool', 'value': value}


class DAQ_0DViewer_MokeBalancedSim(DAQ_Viewer_base):
    """Simulated balanced detection of a MOKE bench: two photodiodes behind a polarising beam splitter.

    Emits one 0D dataset with four channels in V: ``diode_A``, ``diode_B``, ``difference`` and ``sum``. The signal
    depends on the instruments of the shared simulated bench (magnet field, half-wave plate angle, sample
    rotation, angle of incidence) that are controlled by the ``MokeXxxSim`` actuator plugins, on the settings of
    the simulated sample and optics, and on optional imperfections. The Kerr rotation is deliberately not
    computed here: ``difference / (2 * sum)`` gives it (in rad) near the balance, an extension or an analysis does
    that for any digitiser. No semantic annotation either.

    Compatible devices: none, this is a simulation. Nothing was tested on a real instrument.
    Tested with PyMoDAQ 5.3.13 on Linux. No driver to install.
    """
    params = comon_parameters + [
        {'title': 'Sample:', 'name': 'sample', 'type': 'group', 'children': [
            {'title': 'Magnetisation model:', 'name': 'model', 'type': 'list', 'limits': MODELS, 'value': MODELS[0],
             'tip': 'Stoner-Wohlfarth: vector magnetisation, uniaxial anisotropy. tanh: scalar loop along the easy axis'},
            _num('Anisotropy field Hk (mT):', 'hk', 40., min=0.1, tip='Stoner-Wohlfarth: switching field along the easy axis'),
            _num('Coercive field (mT):', 'hc', 15., min=0., tip='tanh model'),
            _num('Switching width (mT):', 'width', 4., min=0.01, tip='tanh model'),
            _num('Easy axis from the normal (deg):', 'easy_polar', 0.),
            _num('Easy axis azimuth (deg):', 'easy_azimuth', 0.),
            _num('Polar Kerr rotation (mrad):', 'kerr_polar', 0.5, tip='At saturation, magnetisation along +z'),
            _num('Longitudinal Kerr rotation (mrad):', 'kerr_long', 0.3,
                 tip='At saturation and 90 deg incidence, magnetisation along +x; scales as sin(incidence)'),
            _num('Transverse reflectivity change (1e-3):', 'kerr_trans', 1.,
                 tip='Intensity change at saturation, magnetisation along +y, p polarisation only'),
            {'title': 'Polarisation:', 'name': 'polarization', 'type': 'list', 'limits': ['p', 's'], 'value': 'p'},
            _num('Kerr s / p ratio:', 'kerr_s_over_p', 1., tip='Simple model: the rotation in s polarisation is this factor times that in p'),
        ]},
        {'title': 'Optics and detection:', 'name': 'optics', 'type': 'group', 'children': [
            _num('Power on the sample (mW):', 'power', 1., min=0.),
            _num('Sample reflectivity:', 'reflectivity', 0.5, min=0., max=1.),
            _num('Photodiode responsivity (A/W):', 'responsivity', 0.5, min=0.),
            _num('Amplifier gain (kV/A):', 'gain', 1., min=0.),
            _num('Waveplate zero offset (deg):', 'waveplate_zero', 0.,
                 tip='Hidden defect: the plate zero is not where its scale says, find the balance by looking for a zero difference'),
            _num('Integration time (ms):', 'integration', 10., min=0.01, tip='Sets the detection bandwidth, 1 / (2 t), for the shot noise'),
        ]},
        {'title': 'Imperfections:', 'name': 'imperfections', 'type': 'group', 'children': [
            _check('Enabled', 'imperfections_enabled', True),
            _check('Shot noise', 'shot_noise', True),
            _check('Electronic noise', 'electronic_noise', True),
            _num('  rms per channel (uV):', 'electronic_noise_rms', 20., min=0.),
            _check('Laser intensity noise', 'laser_noise', True),
            _num('  rms (%):', 'laser_noise_rms', 0.1, min=0., tip='Common to both diodes, rejected by the balance except when unbalanced'),
            _check('Gain imbalance A/B', 'imbalance', False),
            _num('  gain difference (%):', 'imbalance_percent', 2.),
            _check('Faraday rotation of the optics', 'faraday', False),
            _num('  slope (urad/mT):', 'faraday_slope', 5.),
            _check('Slow drift of the polarisation', 'drift', False),
            _num('  amplitude (mrad):', 'drift_amplitude', 0.2, min=0.),
            _num('  period (s):', 'drift_period', 60., min=0.1),
        ]},
    ]

    def ini_attributes(self):
        self.controller: MokeBench = None

    def ini_detector(self, controller=None):
        if self.is_master:
            self.controller = MokeBench()
        else:
            self.controller = controller
        for name in BENCH_PARAMETERS:
            self._forward(self._find(name))
        self.dte_signal_temp.emit(self._dte(np.zeros(len(LABELS))))
        return 'Simulated balanced detection of the MOKE bench, no hardware', True

    def close(self):
        if self.is_master and self.controller is not None:
            self.controller.close()

    def _find(self, name: str) -> Parameter:
        for group in ('sample', 'optics', 'imperfections'):
            if name in self.settings.child(group).names:
                return self.settings.child(group, name)
        raise KeyError(name)

    def _forward(self, param: Parameter):
        group, attribute, factor = BENCH_PARAMETERS[param.name()]
        value = param.value() if factor == 1 and not isinstance(param.value(), float) else param.value() * factor
        self.controller.set_parameter(group, attribute, value)

    def commit_settings(self, param: Parameter):
        if param.name() in BENCH_PARAMETERS:
            self._forward(param)

    @staticmethod
    def _dte(values) -> DataToExport:
        return DataToExport('MokeBalanced', data=[DataFromPlugins(
            name='MokeBalanced', data=[np.array([v]) for v in values], dim='Data0D', labels=LABELS, units='V')])

    def grab_data(self, Naverage=1, **kwargs):
        t_int = self.settings['optics', 'integration'] * 1e-3
        reads = [self.controller.read_diodes(t_int) for _ in range(max(int(Naverage), 1))]
        values = [float(np.mean([r[label] for r in reads])) for label in LABELS]
        self.dte_signal.emit(self._dte(values))

    def stop(self):
        return ''


if __name__ == '__main__':
    main(__file__)
