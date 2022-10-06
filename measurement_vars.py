def init():
    global incr_vars  # For incrementing the progress bar.
    incr_vars = []
    global ex_vars  # For saving the experiment data.
    ex_vars = []
    global send_sweep  # For updating the plot in sweep measurements.
    send_sweep = []
    global send_transient  # For updating the plot in transient measurements.
    send_transient = []
    global stop_ex  # For interrupting measurements. (TODO: explain)
    stop_ex = False
    global ex_finished
    ex_finished = False
    global abort_ex
    abort_ex = False  # Complementing stop_ex, if this is True then ex_vars is also updated.