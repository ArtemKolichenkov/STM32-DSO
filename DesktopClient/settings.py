"""
    This file contains various constants,
    flags and testing stuff.
"""

from PyQt4 import QtCore
import pyqtgraph as pg
import numpy as np

# SAMPLE_POINTS_100NS_DIV = 7
# SAMPLE_POINTS_200NS_DIV = 14
# SAMPLE_POINTS_500NS_DIV = 36
# SAMPLE_POINTS_1US_DIV = 72
# SAMPLE_POINTS_2US_DIV = 144
# SAMPLE_POINTS_5US_DIV = 360
# SAMPLE_POINTS_10US_DIV = 720
# SAMPLE_POINTS_20US_DIV = 1440
# SAMPLE_POINTS_50US_DIV = 3600
# SAMPLE_POINTS_100US_DIV = 7200
# SAMPLE_POINTS_200US_DIV = 14400
# SAMPLE_POINTS_500US_DIV = 36000
# SAMPLE_POINTS_1MS_DIV = 72000
# SAMPLE_POINTS_2MS_DIV = 144000
SAMPLE_RATE_50US_AND_DOWN = 7200000
SAMPLE_RATE_100US = 3600000
SAMPLE_RATE_200US = 1800000
SAMPLE_RATE_500US = 720000
SAMPLE_RATE_1MS = 360000
SAMPLE_RATE_2MS = 180000
SAMPLE_RATE_5MS = 72000
SAMPLE_RATE_10MS = 36000
SAMPLE_RATE_20MS = 18000
SAMPLE_RATE_50MS = 7200
SAMPLE_RATE_100MS = 3600
SAMPLE_RATE_200MS = 1800
SAMPLE_RATE_500MS = 720
SAMPLE_RATE_1S = 360

SAMPLE_RATES = {0.00005: SAMPLE_RATE_50US_AND_DOWN, 0.0001: SAMPLE_RATE_100US,
                0.0002: SAMPLE_RATE_200US, 0.0005: SAMPLE_RATE_500US,
                0.001: SAMPLE_RATE_1MS, 0.002: SAMPLE_RATE_2MS,
                0.005: SAMPLE_RATE_5MS, 0.01: SAMPLE_RATE_10MS,
                0.02: SAMPLE_RATE_20MS, 0.05: SAMPLE_RATE_50MS,
                0.1: SAMPLE_RATE_100MS, 0.2: SAMPLE_RATE_200MS,
                0.5: SAMPLE_RATE_500MS, 1.0: SAMPLE_RATE_1S}

MAX_FREQUENCIES = {0.00005: '~1 MHz', 0.0001: '360 kHz',
                   0.0002: "180 kHz", 0.0005: "72 kHz",
                   0.001: '36 kHz', 0.002: "18 kHz",
                   0.005: '7.2 kHz', 0.01: '3.6 kHz',
                   0.02: '1.8 kHz', 0.05: '720 Hz',
                   0.1: '360 Hz', 0.2: '180 Hz',
                   0.5: '72 Hz', 1.0: '36 Hz'}


class Channel:

    def __init__(self, is_on=None, current_time_value=None,
                 voltage_scale=None, original_time_index=None,
                 original_voltage_index=None, original_voltage_value=None,
                 signal=None, curve=None, original_curve=None,
                 color=None, voltage_mv=None, max_v=None, rms=None,
                 ptp=None, freq=None, fft_x=None, fft_y=None):
        self.is_on = is_on if is_on is not None else False
        self.color = color if color is not None else 'y'
        self.signal = signal if signal is not None else np.array([])
        self.voltage_scale = voltage_scale if voltage_scale is not None else 1
        self.voltage_mv = False
        self.original_voltage_index = original_voltage_index if original_voltage_index is not None else 7
        self.original_voltage_value = original_voltage_value if original_voltage_value is not None else 1
        self.curve = curve if curve is not None else None
        self.original_curve = original_curve if original_curve is not None else None
        self.max_v = max_v if max_v is not None else 0
        self.rms = rms if rms is not None else 0
        self.ptp = ptp if ptp is not None else 0
        self.freq = freq if freq is not None else 0
        self.fft_x = fft_x if fft_x is not None else None
        self.fft_y = fft_y if fft_y is not None else None


class LogicChannel:

    def __init__(self, is_on, color, curve=None, original_curve=None, signal=None, y_offset=None):
        self.is_on = True
        self.color = color
        self.curve = curve
        self.signal = signal if signal is not None else np.array([])
        self.original_curve = original_curve if original_curve is not None else None
        self.y_offset = y_offset


class Config:
    """
        All free-floating variables are now under Config object
    """

    def __init__(self):
        self.grid = []
        self.vertical_bounds = [-4, 4]
        self.is_running = False
        self.holdoff_time = 100
        self.holdoff_suffix = "ns"
        self.current_timescale = {'index': 8, 'value': 0.00005}
        self.original_timescale = {'index': 8, 'value': 0.00005}
        self.trigger_level = 0
        self.trigger_source = 1
        self.trigger_curve = None
        self.logic_on = False
        self.logic_settings = {}
        self.sample_points = 4909


# CONSTANTS
GRID_PEN = pg.mkPen((255, 255, 255, 130), width=1,
                    style=QtCore.Qt.CustomDashLine)
GRID_PEN.setDashPattern([1, 3, 1, 3])
TRIGGER_PEN = pg.mkPen((0, 255, 0, 180), width=1,
                       style=QtCore.Qt.CustomDashLine)
TRIGGER_PEN.setDashPattern([6, 4])
DASHED_PEN = pg.mkPen('w', width=1, style=QtCore.Qt.CustomDashLine)
DASHED_PEN.setDashPattern([2, 5, 2, 5])
