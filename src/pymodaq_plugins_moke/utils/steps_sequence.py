import numpy as np

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtWidgets import QWidget
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.scanner import TableModelSequential
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import pymodaq_ptypes as ptypes
from pymodaq.daq_utils.parameter import utils as putils


class TableViewCustom(QtWidgets.QTableView):
    """
        ============== ===========================
        *Attributes**    **Type**
        *valuechanged*   instance of pyqt Signal
        *QtWidgets*      instance of QTableWidget
        ============== ===========================
    """

    valueChanged = QtCore.Signal(list)
    add_data_signal = QtCore.Signal(int)
    remove_row_signal = QtCore.Signal(int)

    def __init__(self, menu=False):
        super().__init__()
        self.setmenu(menu)

    def setmenu(self, status):
        if status:
            self.menu = QtWidgets.QMenu()
            self.menu.addAction('Add new', self.add)
            self.menu.addAction('Remove selected row', self.remove)
            self.menu.addAction('Clear all', self.clear)
            self.menu.addSeparator()
        else:
            self.menu = None

    def clear(self):
        self.model().clear()

    def add(self):
        self.add_data_signal.emit(self.currentIndex().row())

    def remove(self):
        self.remove_row_signal.emit(self.currentIndex().row())

    def data_has_changed(self, topleft, bottomright, roles):
        self.valueChanged.emit([topleft, bottomright, roles])

    def get_table_value(self):
        """

        """
        return self.model()

    def set_table_value(self, data_model):
        """

        """
        try:
            self.setModel(data_model)
            self.model().dataChanged.connect(self.data_has_changed)
        except Exception as e:
            pass

    def contextMenuEvent(self, event):
        if self.menu is not None:
            self.menu.exec(event.globalPos())


class TableModelSequential(gutils.TableModel):
    def __init__(self, data, **kwargs):
        header = ['Start', 'Stop', 'Step']
        editable = [True, True, True]
        self.default_row = [0., 1., 0.1]
        super().__init__(data, header=header, editable=editable, show_checkbox=True, **kwargs)

    def __repr__(self):
        return f'{self.__class__.__name__} from module {self.__class__.__module__}'

    def validate_data(self, row, col, value):
        """
        make sure the values and signs of the start, stop and step values are "correct"
        Parameters
        ----------
        row: (int) row within the table that is to be changed
        col: (int) col within the table that is to be changed
        value: (float) new value for the value defined by row and col

        Returns
        -------
        bool: True is the new value is fine (change some other values if needed) otherwise False
        """
        start = self.data(self.index(row, 0), QtCore.Qt.DisplayRole)
        stop = self.data(self.index(row, 1), QtCore.Qt.DisplayRole)
        step = self.data(self.index(row, 2), QtCore.Qt.DisplayRole)
        isstep = False
        if col == 0:  # the start
            start = value
        elif col == 1:  # the stop
            stop = value
        elif col == 2:  # the step
            isstep = True
            step = value

        if np.abs(step) < 1e-12 or start == stop:
            return False
        if np.sign(stop - start) != np.sign(step):
            if isstep:
                self._data[row][1] = -stop
            else:
                self._data[row][2] = -step
        return True

    @QtCore.Slot(int)
    def add_data(self, row, data=None):
        if data is not None:
            self.insert_data(row, [float(d) for d in data])
        else:
            self.insert_data(row, self.default_row)

    @QtCore.Slot(int)
    def remove_data(self, row):
        self.remove_row(row)

    def load_txt(self):
        fname = gutils.select_file(start_path=None, save=False, ext='*')
        if fname is not None and fname != '':
            while self.rowCount(self.index(-1, -1)) > 0:
                self.remove_row(0)

            data = np.loadtxt(fname)
            if len(data.shape) == 1:
                data = data.reshape((data.size, 1))
            self.set_data_all(data)

    def save_txt(self):
        fname = gutils.select_file(start_path=None, save=True, ext='dat')
        if fname is not None and fname != '':
            np.savetxt(fname, self.get_data_all(), delimiter='\t')


class ItemDelegate(QtWidgets.QAbstractItemDelegate):
    def createEditor(self, parent: QWidget, option: 'QStyleOptionViewItem', index: QtCore.QModelIndex) -> QWidget:
        pass

    def setEditorData(self, editor: QWidget, index: QtCore.QModelIndex) -> None:
        pass

    def setModelData(self, editor: QWidget, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex) -> None:
        pass


class StepsSequencer(gutils.CustomApp):

    positions_signal = QtCore.Signal(np.ndarray)
    params = [dict(title='Npts', name='npts', type='int', readonly=True),
              dict(title='', label='Send Points', name='send_points', type='bool_push'),
              dict(title='Steps', name='table', type='table_view', delegate=gutils.SpinBoxDelegate, menu=True)]

    def __init__(self, dockarea):
        super().__init__(dockarea)

        self._table_model = None
        self._table_view = None

        self.setup_table_view()
        self.update_model()

    def connect_things(self):
        pass

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        pass

    def setup_docks(self):
        '''
        subclass method from CustomApp
        '''
        self.dock = gutils.Dock('Steps Sequencer', size=(350, 350))
        self.dockarea.addDock(self.dock, 'left')
        self.dock.addWidget(self.settings_tree, 10)

    def emit_positions(self):
        self.positions_signal.emit(np.transpose(np.array([self.update_steps_calculation()])))

    def setup_table_view(self):
        self._table_view = putils.get_widget_from_tree(self.settings_tree, ptypes.TableViewCustom)[0]
        styledItemDelegate = QtWidgets.QStyledItemDelegate()
        styledItemDelegate.setItemEditorFactory(gutils.SpinBoxDelegate(decimals=6))
        self._table_view.setItemDelegate(styledItemDelegate)

        #self._table_view.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self._table_view.horizontalHeader().setStretchLastSection(True)
        self._table_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self._table_view.setSelectionMode(QtWidgets.QTableView.SingleSelection)

        self._table_view.setDragEnabled(True)
        self._table_view.setDropIndicatorShown(True)
        self._table_view.setAcceptDrops(True)
        self._table_view.viewport().setAcceptDrops(True)
        self._table_view.setDefaultDropAction(QtCore.Qt.MoveAction)
        self._table_view.setDragDropMode(QtWidgets.QTableView.InternalMove)
        self._table_view.setDragDropOverwriteMode(False)

    def update_model(self):
        Nseqs = 1
        default_row = [0., 1., 0.1]
        init_data = [default_row for _ in range(Nseqs)]
        self._table_model = TableModelSequential(init_data)
        self.settings.child('table').setValue(self._table_model)

        self._table_view.add_data_signal[int].connect(self._table_model.add_data)
        self._table_view.remove_row_signal[int].connect(self._table_model.remove_data)
        self._table_view.load_data_signal.connect(self._table_model.load_txt)
        self._table_view.save_data_signal.connect(self._table_model.save_txt)

    def value_changed(self, param):
        if param.name() == 'table':
            self.evaluate_nsteps()
        elif param.name() == 'send_points':
            if param.value():
                self.emit_positions()
                param.setValue(False)

    def evaluate_nsteps(self):
        Nsteps = 1
        for ind, data in enumerate(self._table_model.raw_data):
            if self._table_model.is_checked(ind):
                Nsteps += int((data[1] - data[0]) / data[2])
        self.settings.child('npts').setValue(Nsteps)

    def update_steps_calculation(self):
        init = False
        values = np.array([])
        for ind, data in enumerate(self._table_model.raw_data):
            if not init and self._table_model.is_checked(ind):
                values = utils.linspace_step(*data)
                init = True
            elif self._table_model.is_checked(ind):
                values = np.concatenate((values, utils.linspace_step(*data)))
        return values

    @property
    def view(self):
        return self._table_view


def print_positions(positions: np.ndarray):
    print(positions)
    print(f'the shape is {positions.shape} and the size {positions.size}')


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    dockarea = gutils.DockArea()
    prog = StepsSequencer(dockarea)
    prog.positions_signal.connect(print_positions)
    dockarea.show()
    sys.exit(app.exec_())


if __name__ == '__main__':

    main()
