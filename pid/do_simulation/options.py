import json
from pysrc.snippets.option import OptionCategory
from hello.pid.delay import minutes, hours, days
from hello.pid.do_simulation.doprocess import AIR_CNO, DOProcess

class PIDOps(OptionCategory):
    p = 5
    i = 5
    d = 0
    amax = 100
    amin = 0
    alpha = 1
    beta = 1
    linearity = 1
    gamma = 0
    deadband = 0
    man_request = 0
    mode = 0
    
class MFCOps(OptionCategory):
    co2_max = 1
    o2_max = 2
    n2_max = 10
    air_max = 10
    
class PlotOps(OptionCategory):
    xscale = 'auto'
    xmin = 0
    xmax = 72
    xscale_factor = 3600

class MicroProcessOps(OptionCategory): pass


class SimOps(OptionCategory):
    
    o2_pid = PIDOps()
    o2_pid.p = 2
    o2_pid.i = 10
    o2_pid.d = 0
    o2_pid.amax = 100
    o2_pid.amin = 0
    o2_pid.beta = 1
    o2_pid.linearity = 1
    o2_pid.alpha = -1
    
    n2_pid = PIDOps()
    n2_pid.p = 5
    n2_pid.i = 5
    n2_pid.d = 0
    n2_pid.amax = 90
    n2_pid.amin = 0
    n2_pid.beta = 1
    n2_pid.linearity = 1
    n2_pid.alpha = -1
    
    mfcs = MFCOps()
    mfcs.co2_max = 1
    mfcs.o2_max = 10
    mfcs.n2_max = 10
    mfcs.air_max = 10
    
    plots = PlotOps()
    plots.xscale = 'auto'
    plots.xmin = 0
    plots.xmax = 72
    plots.xscale_factor = 3600
    
    end = 10000
    initial_request_cno = (0.00, 0, 0)
    initial_pv = 90
    set_point = 40
    set_point_deadband = 1
    mode = "o2a"
    time_unit = hours
    max_iters = 3 * days

    Process = DOProcess

    # Used by DOProcess (headspace)
    main_gas = 1.0
    initial_actual_cno = AIR_CNO
    reactor_size = 80
    volume = 55
    delay = 0
    k_mult = 1.1   # Not used by Micro Process!!!
    k = None       # Not used by Micro Process!!!
    c = 0
    dc = 0
    d2c = 0

    # Used by DOProcessMicro, but not by DOProcess
    km_hs = 1  # Separate multiplier for headspace
    km_ms = 1  # Separate multiplier for microsparger
    m1 = 4.403227
    m2 = 0.500656
    m3 = 0.111072
    b  = 0.445392


class SimConfig(OptionCategory):
    simops = SimOps()
    xwindow_hrs = 20
    pause = False
    update_interval = 100
    time_factor = 200
    time_unit = 3600
    max_iters = hours * 24 * 7  # max number of iters to simulate in one graph update interval
    x_tick_interval = 1         # spacing between ticks (in hours)
    
    fig_width  = 7  # inches
    fig_height = 9 # inches

cfg = SimConfig()