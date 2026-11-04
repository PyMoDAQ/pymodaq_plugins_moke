import numpy as np
from pymodaq_utils.math_utils import gauss2D
from .koch import image_from_koch


class TrendList(list):
    def __init__(self, Nhistory=3):
        super().__init__()
        self._Nhistory = Nhistory

    def append(self, value):
        if len(self) > self._Nhistory:
            self.pop(0)
        super().append(value)

    def get_trend(self):
        return np.sign(np.mean(np.diff(self)))


class Hysteresis:
    def __init__(self, amplitude=1., x0=1., dx=0.2):
        self._amplitude = amplitude
        self._x0 = x0
        self._dx = dx
        self._trend = TrendList()

    def append(self, value):
        self._trend.append(value)

    def __call__(self, x: float):
        trend = self._trend.get_trend()
        if trend is None:
            trend = 1
        if trend > 0:
            x0 = self._x0
        else:
            x0 = -self._x0
        return self._amplitude * (1/2 + np.arctan((x - x0) / self._dx))


class MokeMockController:

    axis = ['current']
    Nactuators = len(axis)
    Nx = 512
    Ny = 512

    def __init__(self, positions=None, flake_size=100, degree=4, noise=0.1, amp=10):
        super().__init__()
        if positions is None:
            self.current_positions = dict(zip(self.axis, [0. for _ in range(self.Nactuators)]))
        else:
            assert isinstance(positions, list)
            assert len(positions) == self.Nactuators
            self.current_positions = positions

        self._amp = amp
        self._noise = noise
        self._flake_size = flake_size
        self._degree = degree
        self.data_mock = None
        self._histeresis = Hysteresis(amplitude=100)

    @property
    def degree(self):
        return self._degree

    @degree.setter
    def degree(self, degree):
        self._degree = degree
        self.set_Mock_data()

    @property
    def flake_size(self):
        return self._flake_size

    @flake_size.setter
    def flake_size(self, flake_size):
        self._flake_size = flake_size
        self.set_Mock_data()

    @property
    def amp(self):
        return self._amp

    @amp.setter
    def amp(self, amplitude):
        self._amp = amplitude
        self.set_Mock_data()

    @property
    def noise(self):
        return self._noise

    @noise.setter
    def noise(self, noise):
        self._noise = noise
        self.set_Mock_data()

    def check_position(self, axis=None):
        if axis is None:
            axis = self.axis[0]
        return self.current_positions[axis]

    def move_abs(self, position,  axis=None):
        if axis is None:
            axis = self.axis[0]
        delta_position = position - self.current_positions[axis]
        self.current_positions[axis] = position
        self._histeresis.append(position)

        if self.data_mock is None:
            self.data_mock = self.set_Mock_data()

    def move_rel(self, position, axis=None):
        if axis is None:
            axis = self.axis[0]
        self.current_positions[axis] += position
        self._histeresis.append(self.current_positions[axis])
        if self.data_mock is None:
            self.data_mock = self.set_Mock_data()

    def get_xaxis(self):
        return np.linspace(0, self.Nx, self.Nx, endpoint=False)

    def get_yaxis(self):
        return np.linspace(0, self.Ny, self.Ny, endpoint=False)

    def set_Mock_data(self):

        hystereris_position = self._histeresis(self.current_positions['current'])

        data = image_from_koch(degree=self._degree,
                               flake_size=(self.flake_size + hystereris_position),
                               image_size=(self.Ny, self.Nx))
        self.data_mock = self.amp * (data - (np.max(data)-np.min(data)) / 2) + \
                         np.random.random(data.shape) * self.noise
        return self.data_mock

    def get_data_output(self, data=None):
        """
        Return generated data (2D gaussian) transformed depending on the parameters
        Parameters
        ----------
        data: (ndarray) data as outputed by set_Mock_data
        Returns
        -------
        numpy nd-array
        """
        if data is None:
            data = self.set_Mock_data()
        return data
