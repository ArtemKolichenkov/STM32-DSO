"""
    Oscilloscope project
"""
from __future__ import division
from PyQt4 import QtGui, QtCore
import design
import sys
import re
import pyqtgraph as pg
import numpy as np
import settings
import serial   
from scipy.signal import blackmanharris
from parabolic import parabolic
import cPickle as pickle

# Initializing configuration object
config = settings.Config()
# Initializing Channel objects for 1st and 2nd channel and setting default parameters
channel_1 = settings.Channel(is_on=True, color='y')
channel_2 = settings.Channel(is_on=False, color='r')

# Initializing Logic objects for logic channels and setting default parameters
logic_channel_0 = settings.LogicChannel(
    is_on=True, color=(255, 255, 255), y_offset=-3.98)
logic_channel_1 = settings.LogicChannel(
    is_on=True, color=(255, 255, 0), y_offset=-3.6)
logic_channel_2 = settings.LogicChannel(
    is_on=True, color=(0, 255, 0), y_offset=-3.22)
logic_channel_3 = settings.LogicChannel(
    is_on=True, color=(0, 0, 255), y_offset=-2.84)
logic_channel_4 = settings.LogicChannel(
    is_on=True, color=(255, 0, 255), y_offset=-2.46)
logic_channel_5 = settings.LogicChannel(
    is_on=True, color=(255, 0, 0), y_offset=-2.08)
logic_channel_6 = settings.LogicChannel(
    is_on=True, color=(0, 255, 255), y_offset=-1.7)
logic_channel_7 = settings.LogicChannel(
    is_on=True, color=(255, 165, 0), y_offset=-1.32)

# Putting logic channels into a list for better code management
logic_channels = [logic_channel_0, logic_channel_1, logic_channel_2, logic_channel_3,
                  logic_channel_4, logic_channel_5, logic_channel_6, logic_channel_7]


def freq_from_fft(channel, fs):
    """
    Estimate frequency from peak of FFT.

    Parameters
    ----------
    channel : Channel object
        Channel to be processed
    fs : int
        Sampling rate

    """
    # Compute Fourier transform of windowed signal
    windowed = channel.signal * blackmanharris(len(channel.signal))
    f = np.fft.rfft(windowed)
    channel.fft_y = np.abs(f)  # amplitude spectrum
    channel.fft_x = np.fft.rfftfreq(channel.signal.size, 1 / fs)
    # Find the peak and interpolate to get a more accurate peak
    i = np.argmax(abs(f))
    true_i = parabolic(np.log(abs(f)), i)[0]

    # Convert to equivalent frequency
    return fs * true_i / len(windowed)


""" Oscilloscope screen related functions are below """


def show_fft_dialog():
    """
    Shows dialog box for FFT and sets curve inside of it.
    """
    fft_dialog = FFTDialog()
    fft_curve = fft_dialog.fft_plot.getPlotItem()
    vb = fft_curve.vb
    fft_curve.plot(channel_1.fft_x[:505], channel_1.fft_y[:505] / 10, pen='w')
    vLine = pg.InfiniteLine(angle=90, movable=False)
    hLine = pg.InfiniteLine(angle=0, movable=False)
    fft_curve.addItem(vLine, ignoreBounds=True)
    fft_curve.addItem(hLine, ignoreBounds=True)
    bottom_axis = fft_curve.getAxis('bottom')
    bottom_axis.setTicks([
        [(1000, '1 kHz'), (50000, '50 kHz'), (100000, '100 kHz'), (200000, '200 kHz'),
         (300000, '300 kHz'), (400000, '400 kHz'), (500000, '500 kHz'), (600000, '600 kHz'),
         (700000, '700 kHz'), (800000, '800 kHz'), (900000, '900 kHz'), (1000000, '1 MHZ')
         ],
        []])
    vb.setLimits(yMin=-20, yMax=400)
    vb.setLimits(xMin=-20000, xMax=1070000)
    label = fft_dialog.freq_label

    def mouseMoved(evt):
        pos = evt[0]  # using signal proxy turns original arguments into a tuple
        if fft_curve.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            frequency = int(mousePoint.x())
            if frequency > 1000000:
                frequency = frequency / 1000000
                label.setText("f=%.3F MHz" % frequency)
            elif frequency > 10000:
                frequency = frequency / 1000
                label.setText("f=%.3F kHz" % frequency)
            else:
                label.setText("f=%.3F Hz" % frequency)
            vLine.setPos(mousePoint.x())
            hLine.setPos(mousePoint.y())
    proxy = pg.SignalProxy(fft_curve.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)
    fft_dialog.exec_()


def plot_fft():
    fft_curve = form.the_plot.plot(pen='w')
    fft_curve.setPos(0, -3.9)
    fft_curve.setData(np.array(range(0, len(channel_1.fft_x)))
                      * (1000 / 1800), channel_1.fft_y / 350)


def acquire_signal(channel):
    """
    Captures data for corresponding channel and makes simple measurements.

    Parameters
    ----------
    channel : Channel object
        Channel where data will be saved.
    """
    def make_measurements(channel, sample_rate):
        channel.max_v = channel.signal.max()
        channel.rms = np.sqrt(np.mean(channel.signal ** 2))
        channel.ptp = np.ptp(channel.signal)
        channel.freq = freq_from_fft(channel, sample_rate)

    if config.original_timescale['value'] <= 0.00005:
        sample_rate = settings.SAMPLE_RATES[0.00005]
    else:
        sample_rate = settings.SAMPLE_RATES[config.original_timescale['value']]

    stm32 = serial.Serial('COM3', 115200) # Baud rate does not matter here since it is not real com port but USB
    stm32.close()
    stm32.open()
    signal_array = np.zeros(7200)
    incoming_data = stm32.read(size=7200)
    for i, x in enumerate(incoming_data):
        # converting 8bit values back to voltages (assuming stable 3.3v supply)
        signal_array[i] = ord(x) * 0.012890625 - 1.65
    
    channel.signal = signal_array

    make_measurements(channel, sample_rate)


def acquire_logic():
    """
    Acquires logic channels data.
    """
    for channel in logic_channels:
        if channel.is_on:
            stm32 = serial.Serial('COM3', 115200) # Baud rate does not matter here since it is not real com port but USB
            stm32.close()
            stm32.open()
            signal_array = np.zeros(1800)
            incoming_data = stm32.read(size=1800)
            for i, x in enumerate(incoming_data):
                signal_array[i] = ord(x)
            channel.signal = signal_array


def plot_logic():
    """
    Plots logic channels onto display.
    """
    def plot_logic_channel(channel):
        channel.curve = form.the_plot.plot(pen=channel.color)
        if config.original_timescale['value'] < 0.00005:
            channel.curve.setPos(
                -((1000 * (0.00005 / config.original_timescale['value']) / 2) - 500), channel.y_offset)
            channel.curve.setData(np.array(range(0, len(channel.signal)))
                                  * (1000 / (config.sample_points / (0.00005 / config.original_timescale['value']))), channel.signal / 4)
        else:
            channel.curve.setPos(
                0, channel.y_offset)
            channel.curve.setData(np.array(range(0, len(channel.signal)))
                                  * (1000 / config.sample_points), channel.signal / 4)
        channel.original_curve = channel.curve.getData()[0]

    for channel in logic_channels:
        if channel.is_on:
            plot_logic_channel(channel)


def update_screen():
    '''
    Updates the oscilloscope screen with new data.
    '''

    def plot_channel(channel):
        channel.curve = form.the_plot.plot(pen=channel.color)
        if config.original_timescale['value'] < 0.00005:
            channel.curve.setPos(
                -((1000 * (0.00005 / config.original_timescale['value']) / 2) - 500), (config.vertical_bounds[1] / 400) * form.vpos_one_slider.value())
            channel.curve.setData(np.array(range(0, len(channel.signal)))
                                  * (1000 / (config.sample_points / (0.00005 / config.original_timescale['value']))), channel.signal)
        else:
            channel.curve.setPos(
                0, (config.vertical_bounds[1] / 400) * form.vpos_one_slider.value())
            channel.curve.setData(np.array(range(0, len(channel.signal)))
                                  * (1000 / config.sample_points), channel.signal)
        channel.original_curve = channel.curve.getData()[0]

    stm32 = serial.Serial('COM3', 115200) # Baud rate does not matter here since it is not real com port but USB
    stm32.close()
    stm32.open()

    if channel_1.is_on and channel_2.is_on:
        stm32.write(b'110')
        acquire_signal(channel_1)
        acquire_signal(channel_2)
        plot_channel(channel_1)
        plot_channel(channel_2)
        vertical_position_changed(channel_1, form.vpos_one_slider, form.vpos_one_value_label)
        vertical_position_changed(channel_2, form.vpos_two_slider, form.vpos_two_value_label)
    elif channel_1.is_on:
        stm32.write(b'100')
        acquire_signal(channel_1)
        plot_channel(channel_1)
        update_measurements()
        vertical_position_changed(channel_1, form.vpos_one_slider, form.vpos_one_value_label)
    else:
        stm32.write(b'010')
        acquire_signal(channel_2)
        plot_channel(channel_2)
        vertical_position_changed(channel_2, form.vpos_two_slider, form.vpos_two_value_label)

    if config.logic_on:
        stm32.write(b'001')
        acquire_logic()
        plot_logic()


def move_horizontal(self):
    '''
    Moves the oscilloscope screen when interacting with horizontal scrollbar.
    '''
    form.the_plot.setXRange(0 + self * 100, 1000 + self * 100, padding=0)


def logic_onoff(logic):
    """
    Turns on logic channels and changes display accordingly.

    Parameters
    ----------
    logic : boolean
        State of logic channels (on/off). Set automatically from GUI event.
    """
    config.logic_on = logic
    if not logic:
        clear_logic_screen()
        form.logic_button.setText("Logic OFF")
    if logic:
        plot_logic()
        form.logic_button.setText("Logic ON")
    check_if_all_channels_off()


def clear_logic_screen():
    """
    Removes logic channels curves from the display.
    """
    for channel in logic_channels:
        form.the_plot.removeItem(channel.curve)


def logic_channel_onoff(checkbox, channel):
    """
    Disables/Enables logic channel.
    Parameters
    ----------
    checkbox : QCheckBox object
        The checkbox that was changed
    channel : LogicChannel object
        LogicChannel instance for corresponding channel

    """
    channel.is_on = checkbox.isChecked()


""" Buttons events for Functions menu are below """


def single():
    '''
    Takes a single snapshot of a signal.
    The length of snapshot is the sample window currently used (or several windows if it is less than 1000 points).
    '''

    clear_screen()
    update_screen()


def clear_screen():
    '''
    Clears oscilloscope screen and erases the data stored in Channel.curve.
    '''
    form.the_plot.removeItem(channel_1.curve)
    channel_1.curve = None

    form.the_plot.removeItem(channel_2.curve)
    channel_2.curve = None

    clear_logic_screen()
    for channel in logic_channels:
        channel.curve = None
        channel.signal = np.array([])


""" Channel controll GUI functions are below """


def ch1_on_off(self):
    """
    Turns on channel_1 object and updates GUI.
    Parameters
    ----------
    self : boolean
        ON/OFF state of channel. Set up automatically from GUI event.
    """
    if self:
        channel_1.is_on = True
        update_GUI()
    else:
        channel_1.is_on = False
        update_GUI()

    check_if_all_channels_off()


def ch2_on_off(self):
    """
    Turns on channel_2 object and updates GUI.

    Parameters
    ----------
    self : boolean
        ON/OFF state of channel. Set up automatically from GUI event.
    """
    if self:
        channel_2.is_on = True
        update_GUI()
    else:
        channel_2.is_on = False
        update_GUI()

    check_if_all_channels_off()


def check_if_all_channels_off():
    """
    Checks if all channels turned off and updates GUI accordingly.
    """
    if not channel_1.is_on and not channel_2.is_on and not config.logic_on:
        form.single_button.setEnabled(False)
        form.run_button.setEnabled(False)
    else:
        form.single_button.setEnabled(True)
        form.run_button.setEnabled(True)


def time_resolution_changed(self):
    """
    Zooms in and out when time resolution changed
    """
    def plot_resized_channel(channel, multiplier):
        if config.original_timescale['value'] < 0.00005:
            channel.curve.setPos(-((1000 * (0.00005 /
                                            config.original_timescale['value']) * multiplier / 2) - 500), 0)
        else:
            channel.curve.setPos(500 - ((1000 * multiplier) / 2), 0)
        channel.curve.setData(channel.original_curve * multiplier, channel.curve.getData()[1])

    def plot_resized_logic_channel(channel, multiplier):
        if config.original_timescale['value'] < 0.00005:
            channel.curve.setPos(-((1000 * (0.00005 /
                                            config.original_timescale['value']) * multiplier / 2) - 500), 0)
        else:
            channel.curve.setPos(500 - ((1000 * multiplier) / 2), channel.y_offset)
        channel.curve.setData(channel.original_curve * multiplier, channel.curve.getData()[1])

    config.current_timescale['value'] = form.hscale_select.itemData(
        form.hscale_select.currentIndex()).toPyObject()

    # Displaying the Max Frequency value
    update_GUI()

    # Determining multiplier for zooming in and out at signal
    multiplier = config.original_timescale['value'] / config.current_timescale['value']

    # Initialize the new curve array with zoomed in and out values
    if channel_1.curve and channel_2.curve:
        plot_resized_channel(channel_1, multiplier)
        plot_resized_channel(channel_2, multiplier)
    elif channel_1.curve:
        plot_resized_channel(channel_1, multiplier)
    elif channel_2.curve:
        plot_resized_channel(channel_2, multiplier)
    else:
        pass
    vertical_position_changed(channel_1, form.vpos_one_slider, form.vpos_one_value_label)
    vertical_position_changed(channel_2, form.vpos_two_slider, form.vpos_two_value_label)

    if config.logic_on:
        for channel in logic_channels:
            plot_resized_logic_channel(channel, multiplier)


def voltage_changed(channel, new_scale):
    """
    Zooms in and out when voltage resolution changed

    Parameters
    ----------
    channel : Channel object
        Corresponding channel for which the vertical resolution has changed.
    new_scale : QComboBox object
        Combobox from which the new value is taken
    """
    def plot_resized_channel(multiplier):
        channel.curve.setData(channel.curve.getData()[0], channel.signal * multiplier)

    channel.voltage_scale = int(re.search(r'\d+', str(new_scale.currentText())).group(0))
    is_mv = re.search(r'mV', str(new_scale.currentText()))
    if is_mv:
        voltage_multiplier = 1 / (channel.voltage_scale / 1000)
        channel.voltage_mv = True
    else:
        voltage_multiplier = 1 / channel.voltage_scale
        channel.voltage_mv = False
    if channel.curve:
        plot_resized_channel(voltage_multiplier)
    trigger_position_changed(form.trigger_level_slider.value())


def vertical_position_changed(channel, slider, label):
    """
    Moves signal curve up and down according to slider position.

    Parameters
    ----------
    channel : Channel object
        Corresponding channel for which the vertical position has changed.
    slider : QSlider object
        Slider from which the new value is taken
    label: QLabel object
        Label below the slider (to update text readout)
    """
    if channel.curve:
        channel.curve.setPos(channel.curve.pos()[
            0], (config.vertical_bounds[1] / 400) * slider.value())
    label.setText(
        str((config.vertical_bounds[1] / (config.vertical_bounds[1] * 100)) * slider.value()) + " div")


def vertical_zero(channel_number):
    """
    Centers signal vertically.

    Parameters
    ----------
    channel_number : int
        Channel (number 1 or 2) which needs to be centered vertically.
    """
    if channel_number == 1:
        form.vpos_one_slider.setValue(0)
    else:
        form.vpos_two_slider.setValue(0)


""" Trigger related functions are below """


def holdoff_value_changed(self):
    """
    Changes holdoff value and updates GUI.

    Parameters
    ----------
    self : int
        The time value. Set up automatically from GUI event.
    """
    if config.holdoff_suffix == "ns":
        config.holdoff_time = self
        if config.holdoff_time == 1000:
            config.holdoff_time = 1
            config.holdoff_suffix = "us"
            form.holdoff_spinBox.setSuffix("us")
            form.holdoff_spinBox.setValue(1.0)
    elif config.holdoff_suffix == "us":
        config.holdoff_time = self
        if self < 1:
            config.holdoff_time = 999.9
            config.holdoff_suffix = "ns"
            form.holdoff_spinBox.setValue(999.9)
            form.holdoff_spinBox.setSuffix("ns")
        if config.holdoff_time == 1000.0:
            config.holdoff_time = 1
            config.holdoff_suffix = "ms"
            form.holdoff_spinBox.setSuffix("ms")
            form.holdoff_spinBox.setValue(1.0)
    elif config.holdoff_suffix == "ms":
        config.holdoff_time = self
        if self < 1:
            config.holdoff_time = 999.9
            config.holdoff_suffix = "us"
            form.holdoff_spinBox.setValue(999.9)
            form.holdoff_spinBox.setSuffix("us")


def trigger_show(show):
    """
    Shows/hides trigger line on the display.

    Parameters
    ----------
    show : boolean
        Enable/Disable trigger display. Set up automatically from GUI event.
    """
    if show:
        form.show_button.setText('Hide')
        config.trigger_curve = form.the_plot.plot(
            [8, 10000], [form.trigger_level_slider.value() / 100, form.trigger_level_slider.value() / 100], pen=settings.TRIGGER_PEN,  symbolBrush=(119, 172, 48), symbolPen='w', symbol='t2', symbolSize=14)
    else:
        form.show_button.setText('Show')
        form.the_plot.removeItem(config.trigger_curve)
        config.trigger_curve = None


def toggle_trigger_channel(self):
    """
    Selects trigger channel (1 or 2).
    """
    if form.trigger_source_ch1.isChecked():
        config.trigger_source = 1
    else:
        config.trigger_source = 2
    trigger_position_changed(form.trigger_level_slider.value())


def trigger_position_changed(level):
    """
    Sets up new trigger value and updates GUI (trigger line).

    Parameters
    ----------
    level : int
        Enable/Disable trigger display. Set up automatically from GUI event.
    """
    config.trigger_level = level
    if config.trigger_curve:
        config.trigger_curve.setData([8, 10000], [level / 100, level / 100])
    if config.trigger_source == 1:
        voltage_level = config.trigger_level * (channel_1.voltage_scale * 0.01)
        mv_adjust = channel_1.voltage_mv
    else:
        voltage_level = config.trigger_level * (channel_2.voltage_scale * 0.01)
        mv_adjust = channel_2.voltage_mv
    if mv_adjust:
        if abs(voltage_level) > 1000:
            form.trigger_level_value_label.setGeometry(QtCore.QRect(14, 160, 53, 13))
        if abs(voltage_level) < 100:
            form.trigger_level_value_label.setGeometry(QtCore.QRect(22, 160, 47, 13))
        else:
            form.trigger_level_value_label.setGeometry(QtCore.QRect(17, 160, 47, 13))
        form.trigger_level_value_label.setText(str(voltage_level) + "mV")
    else:
        form.trigger_level_value_label.setGeometry(QtCore.QRect(29, 160, 35, 13))
        form.trigger_level_value_label.setText(str(voltage_level) + "V")


def update_measurements():
    """
    Updates GUI for measurements section.
    """
    form.readout_one.setText("CH1_Vpp: " + "%.3f V" % channel_1.ptp)
    form.readout_two.setText("CH1_Freq: " + "%.3f Hz" % channel_1.freq)
    form.readout_three.setText("CH1_Vrms: " + "%.3f V" % channel_1.rms)
    form.readout_four.setText("CH1_Vmax: " + "%.3f V" % channel_1.max_v)
    form.readout_eight.setText("CH2_Vmax: " + "%.3f V" % channel_2.max_v)


def update_GUI():
    """
    General GUI update routine.
    """
    def disable_channel_1():
        form.vpos_one_slider.setEnabled(False)
        form.vpos_one_center_button.setEnabled(False)
        form.vscale_one_select.setEnabled(False)
        form.probe_one_1_1.setEnabled(False)
        form.probe_one_1_10.setEnabled(False)
        form.sps_one_label.setText("-----")

    def disable_channel_2():
        form.vpos_two_slider.setEnabled(False)
        form.vpos_two_center_button.setEnabled(False)
        form.vscale_two_select.setEnabled(False)
        form.probe_two_1_1.setEnabled(False)
        form.probe_two_1_10.setEnabled(False)
        form.sps_two_label.setText("-----")

    def enable_channel_1():
        form.vpos_one_slider.setEnabled(True)
        form.vpos_one_center_button.setEnabled(True)
        form.vscale_one_select.setEnabled(True)
        form.probe_one_1_1.setEnabled(True)
        form.probe_one_1_10.setEnabled(True)

    def enable_channel_2():
        form.vpos_two_slider.setEnabled(True)
        form.vpos_two_center_button.setEnabled(True)
        form.vscale_two_select.setEnabled(True)
        form.probe_two_1_1.setEnabled(True)
        form.probe_two_1_10.setEnabled(True)

    if channel_1.is_on and channel_2.is_on:
        # Enable all
        # Divide by 2
        enable_channel_1()
        enable_channel_2()
        # UPDATE SPS FOR BOTH CHANNELS
    elif channel_1.is_on:
        # output ch1
        # hide ch2
        disable_channel_2()
        enable_channel_1()
        if config.current_timescale['value'] <= 0.00005:
            form.sps_one_label.setText(settings.MAX_FREQUENCIES[0.00005] + "\nat 7200000 SPS")
        else:
            form.sps_one_label.setText(
                settings.MAX_FREQUENCIES[config.current_timescale['value']] + "\nat " + str(settings.SAMPLE_RATES[config.current_timescale['value']]) + " SPS")
    elif channel_2.is_on:
        # output ch2
        # hide ch1
        disable_channel_1()
        enable_channel_2()
        if config.current_timescale['value'] <= 0.00005:
            form.sps_two_label.setText(settings.MAX_FREQUENCIES[0.00005] + "\nat 7200000 SPS")
        else:
            form.sps_two_label.setText(
                settings.MAX_FREQUENCIES[config.current_timescale['value']] + "\nat " + str(settings.SAMPLE_RATES[config.current_timescale['value']]) + " SPS")
    else:
        disable_channel_1()
        disable_channel_2()


class Oscilloscope(QtGui.QMainWindow, design.Ui_MainWindow):
    """
    Main window configuration and initialization.
    """

    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)

        # Initial oscilloscope screen configuration.

        # Binding PlotWidget 'plot' to class variable 'the_plot'
        self.the_plot = self.plot
        # Hiding the default PlotWidget buttons
        self.the_plot.hideButtons()
        # Setting the range of a ViewBox
        self.the_plot.setRange(rect=None, xRange=(
            0, 1000), yRange=(-4, 4), padding=0, update=True, disableAutoRange=True)
        # Hiding left axis (we draw our own in center)
        self.the_plot.hideAxis('left')
        # Hiding bottom axis (we draw our own in center)
        self.the_plot.hideAxis('bottom')

        zero_line_x = [-9000, 10000]  # Zero axis X coordinates
        zero_line_y = [0, 0]  # Zero axis Y coordinates
        self.the_plot.plot(zero_line_x, zero_line_y, pen=settings.DASHED_PEN)  # Plotting zero axis

        center_line_x = [500, 500]  # Vertical center axis X coordinates
        center_line_y = [-4, 4]  # Vertical center axis Y coordinates
        # Plotting center axis
        center_curve = self.the_plot.plot(
            center_line_x, center_line_y, pen=settings.DASHED_PEN)
        # Adding center line to grid array inside configuration object
        config.grid.append(center_curve)

        # Plotting the grid that is used to divide screen into sections (for voltage and time axes)
        x = -9000
        while x < 10000:
            gridLine_x = [x, x]
            gridLine_y = [-4, 4]
            if x == 500:
                pass
            else:
                grid_curve = self.the_plot.plot(
                    gridLine_x, gridLine_y, pen=settings.GRID_PEN)
                config.grid.append(grid_curve)
            x = x + 100
        y = -4
        while y < 4:
            gridLine_x = [-9000, 10000]
            gridLine_y = [y, y]
            if y == 0:
                pass
            else:
                grid_curve = self.the_plot.plot(
                    gridLine_x, gridLine_y, pen=settings.GRID_PEN)
                config.grid.append(grid_curve)
            y = y + 1

        # Trigger load from config
        if config.trigger_source == 1:
            self.trigger_source_ch1.setChecked(True)
        else:
            self.trigger_source_ch2.setChecked(True)

        # Signal conncetions
        # self.run_button.clicked.connect(run)
        self.single_button.clicked.connect(single)
        self.logic_button.clicked.connect(logic_onoff)
        self.logic_settings_button.clicked.connect(self.show_logic_dialog)
        self.FFT_button.clicked.connect(show_fft_dialog)
        self.clear_button.clicked.connect(clear_screen)
        self.horizontal_scroll_bar.valueChanged.connect(move_horizontal)
        self.hscale_select.currentIndexChanged.connect(
            time_resolution_changed)
        self.vscale_one_select.currentIndexChanged.connect(
            lambda: voltage_changed(channel_1, form.vscale_one_select))
        self.vscale_two_select.currentIndexChanged.connect(
            lambda: voltage_changed(channel_2, form.vscale_two_select))
        self.holdoff_spinBox.valueChanged.connect(holdoff_value_changed)
        self.vpos_one_slider.valueChanged.connect(
            lambda: vertical_position_changed(channel_1, form.vpos_one_slider, form.vpos_one_value_label))
        self.vpos_two_slider.valueChanged.connect(lambda: vertical_position_changed(
            channel_2, form.vpos_two_slider, form.vpos_two_value_label))
        self.vpos_one_center_button.clicked.connect(lambda: vertical_zero(1))
        self.vpos_two_center_button.clicked.connect(lambda: vertical_zero(2))
        self.ch1_checkbox.stateChanged.connect(ch1_on_off)
        self.ch2_checkbox.stateChanged.connect(ch2_on_off)
        self.trigger_source_ch1.toggled.connect(toggle_trigger_channel)
        self.trigger_source_ch2.toggled.connect(toggle_trigger_channel)
        self.trigger_level_slider.valueChanged.connect(trigger_position_changed)
        self.show_button.clicked.connect(trigger_show)

    def show_logic_dialog(self):
        dialog = LogicDialog(self)
        dialog.exec_()


def clickable(widget):
    """
    Enables clicking events on QLabel object (or any object that does not support click signals)
    """
    class Filter(QtCore.QObject):

        clicked = QtCore.pyqtSignal()

        def eventFilter(self, obj, event):

            if obj == widget:
                if event.type() == QtCore.QEvent.MouseButtonRelease:
                    if obj.rect().contains(event.pos()):
                        self.clicked.emit()
                        return True

            return False

    filter = Filter(widget)
    widget.installEventFilter(filter)
    return filter.clicked


class LogicDialog(QtGui.QDialog, design.Ui_LogicDialog):
    """
    Logic channels configuration window.
    """

    def __init__(self, parent=None):
        super(self.__class__, self).__init__()
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowSystemMenuHint)
        self.restoreSettings()
        self.logic0_checkbox.stateChanged.connect(
            lambda: logic_channel_onoff(self.logic0_checkbox, logic_channel_0))
        self.logic1_checkbox.stateChanged.connect(
            lambda: logic_channel_onoff(self.logic1_checkbox, logic_channel_1))
        self.logic2_checkbox.stateChanged.connect(
            lambda: logic_channel_onoff(self.logic2_checkbox, logic_channel_2))
        self.logic3_checkbox.stateChanged.connect(
            lambda: logic_channel_onoff(self.logic3_checkbox, logic_channel_3))
        self.logic4_checkbox.stateChanged.connect(
            lambda: logic_channel_onoff(self.logic4_checkbox, logic_channel_4))
        self.logic5_checkbox.stateChanged.connect(
            lambda: logic_channel_onoff(self.logic5_checkbox, logic_channel_5))
        self.logic6_checkbox.stateChanged.connect(
            lambda: logic_channel_onoff(self.logic6_checkbox, logic_channel_6))
        self.logic7_checkbox.stateChanged.connect(
            lambda: logic_channel_onoff(self.logic7_checkbox, logic_channel_7))
        clickable(self.logic_color_label_0).connect(
            lambda: self.color_picker(self.logic_color_label_0, logic_channel_0))
        clickable(self.logic_color_label_1).connect(
            lambda: self.color_picker(self.logic_color_label_1, logic_channel_1))
        clickable(self.logic_color_label_2).connect(
            lambda: self.color_picker(self.logic_color_label_2, logic_channel_2))
        clickable(self.logic_color_label_3).connect(
            lambda: self.color_picker(self.logic_color_label_3, logic_channel_3))
        clickable(self.logic_color_label_4).connect(
            lambda: self.color_picker(self.logic_color_label_4, logic_channel_4))
        clickable(self.logic_color_label_5).connect(
            lambda: self.color_picker(self.logic_color_label_5, logic_channel_5))
        clickable(self.logic_color_label_6).connect(
            lambda: self.color_picker(self.logic_color_label_6, logic_channel_6))
        clickable(self.logic_color_label_7).connect(
            lambda: self.color_picker(self.logic_color_label_7, logic_channel_7))

    def color_picker(self, channel_label, channel):
        color = QtGui.QColorDialog.getColor()
        channel.color = (color.red(), color.green(), color.blue())
        plot_logic()
        channel_label.setStyleSheet(
            'background-color: %s; border:1px solid' % color.name())

    def saveSettings(self):
        """
        Saves configuration for logic channels.
        """
        config.logic_settings = {}
        for child in self.children():
            name = child.objectName()
            if not name:
                continue
            if isinstance(child, QtGui.QCheckBox):
                config.logic_settings[name] = child.isChecked()
            elif isinstance(child, QtGui.QLabel):
                config.logic_settings[name] = child.styleSheet()

    def restoreSettings(self):
        """
        Restores previous logic channels configuration.
        """
        for child in self.children():
            name = child.objectName()
            if name not in config.logic_settings:
                continue
            if isinstance(child, QtGui.QCheckBox):
                child.setChecked(config.logic_settings[name])
            elif isinstance(child, QtGui.QLabel):
                child.setStyleSheet(config.logic_settings[name])

    def closeEvent(self, event):
        self.saveSettings()


class FFTDialog(QtGui.QDialog, design.Ui_FFTDialog):
    """
    FFT window configurations.
    """

    def __init__(self, parent=None):
        super(self.__class__, self).__init__()
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowSystemMenuHint)


app = QtGui.QApplication(sys.argv)
form = Oscilloscope()
form.showMaximized()
# Initical display configurations
# Trigger valueChanged for spinBox, because reasons
form.holdoff_spinBox.setValue(100.0)
update_GUI()  # why is it here? delete?
trigger_position_changed(form.trigger_level_slider.value())
app.exec_()

sys.exit(1)  # If this executes - there was an error
