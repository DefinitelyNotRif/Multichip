import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
from tkinter import messagebox
from tkinter import simpledialog
from tkinter.colorchooser import askcolor

from ttkthemes import ThemedTk
import csv
import os
from re import split
import logging
import traceback
import threading
import psutil
import pyvisa
from datetime import date, timedelta
import ast
from functools import partial
from win32com.client import Dispatch
from visualization import *
from datamanager import *
from measurements import *
import measurement_vars
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import to_hex, to_rgb
from Arduino import Arduino


def do_nothing():
    pass


def strf(s):
    """
    Rounds the float represented by the string s, to 5 significant digits.
    """
    return '%.5g'%s


class TkExceptionHandler:  # I don't know what this does, but apparently it's crucial.
    def __init__(self, func, subst, widget):
        self.func = func
        self.subst = subst
        self.widget = widget

    def __call__(self, *args):
        if self.subst:
            args = self.subst(*args)
        return self.func(*args)


tk.CallWrapper = TkExceptionHandler

logging.basicConfig(filename="logs.log", level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')  # Set the format to use in logs.txt
# trans_buttons_list, active_list = [], [[False] * 4 for i in range(8)] * 8  # For future use
param_list = ["d", "jg", "bg"]  # The parameters for the sweeps (drain first).
drain_smus = []  # Lists the SMUs connected to the drains (e.g. ["SMU2", ...]).
device_names = ['' for i in range(4)]  # Lists the names of each of the (up to) four devices.
trans_names = [['' for i in range(4)] for j in range(4)]    # Lists the names of each of the transistors.
                                                            # Each row corresponds to a different device.
active_trans = []  # [[False for i in range(4)] for j in range(4)]  # True if the transistor is selected.
pinno = {}  # The dictionary that maps each Arduino digital output to an index in the range 0-15.
global meas_type    # 'char'/'exposure'/'transient'. Determines the type of the last measurement, for the "Use data from
meas_type = ''      # last exp." option.
vth_funcs = ['Constant', 'Linear extrapolation']
measurement_vars.stop_ex = False  # This is explained in open_measurement_window()
current_id = -1  # The highest ID out of the existing experiments. Is the global definition even necessary?!
version = '0.4.1'
err_msg = ''  # Error message for when the SPA isn't connected or services aren't running
suppress_errors = True  # If True, doesn't show errors if the SPA/Arduino aren't connected. For debugging purposes.
# limit_time = True  # If True, transient measurements will run until the defined total time has elapsed. Otherwise,
                    # they will perform the defined number of measurements, even though it will take much longer.


# def strf(x):
#     """
#     Returns the string str(x), rounded to avoid float errors.
#     :param x:
#     :return:
#     """
#

def reset_spa():
    """"
    Resets all the SMUs to 0V. This function is called whenever the program is closed, even by an error.
    """
    b1500 = AgilentB1500("GPIB0::18::INSTR", read_termination='\r\n', write_termination='\r\n', timeout=60000)
    b1500.initialize_all_smus()
    b1500.data_format(21, mode=1)
    for smu in b1500.smu_references:
        smu.enable()  # enable SMU
        smu.adc_type = 'HRADC'  # set ADC to high-resoultion ADC
        smu.meas_range_current = '1 nA'
        smu.meas_op_mode = 'COMPLIANCE_SIDE'
        smu.force('Voltage', 'Auto Ranging', 0)


def open_trans_selection():
    """
    Opens and builds the transistor selection window. The left frame lists all active drain SMUs, and allows toggling
    them on or off. The right frame allows activation of each of the transistors, as well as setting the names of the
    devices and transistors.
    When the user clicks "Confirm", the transistor states, names and device names are saved in their respective global
    variables, as well as in data/transistor_data.csv.
    """

    def confirm_trans():
        """
        Closes the window and updates trans_list.
        """
        global trans_names, device_names, active_trans, drain_smus, stv_smu2, stv_smu3, stv_smu4
        nonlocal stvs_dev_names, stvs_trans_names

        for i in range(4):
            device_names = [s.get() for s in stvs_dev_names]
            trans_names[i] = [s.get() for s in stvs_trans_names[i]]
        towrite = [[str(b) for b in row] for row in active_trans]
        towrite.append(device_names)
        for i in range(4):
            towrite.append(trans_names[i])
        towrite.append(drain_smus)
        towrite.append([s.get() for s in [stv_smu2, stv_smu3, stv_smu4]])
        # print(towrite)
        with open('data/transistor_data.csv', 'w', newline='') as f:
            csv_writer = writer(f)
            csv_writer.writerows(towrite)
        selection_window.grab_release()
        selection_window.destroy()

    def activate_trans(row, col):
        global active_trans
        nonlocal btns_select
        if active_trans[row][col]:
            btns_select[row][col].config(bg='red')
            active_trans[row][col] = False
        else:
            btns_select[row][col].config(bg='green')
            active_trans[row][col] = True

    def activate_dev(row):
        """
        Toggles all the transistors in a device on or off. If only some of them are on, it turns them all off.
        :param row: The device to be handled.
        """
        global active_trans, drain_smus
        nonlocal btns_select
        turnon = not any(active_trans[row])
        bgcol = 'green' if turnon else 'red'
        for col in range(4):
            if len(drain_smus) > col:
                btns_select[row][col].config(bg=bgcol)
                active_trans[row][col] = turnon

    global device_names, trans_names, active_trans, drain_smus
    global board
    if not board and not suppress_errors:
        messagebox.showerror('', 'Please connect the Arduino controller and reopen the program.')
        return

    selection_window = tk.Toplevel(window)
    selection_window.geometry("800x600")
    selection_window.title("Select Transistors")
    selection_window.grab_set()  # Always on top
    selection_window.rowconfigure(0, weight=1)
    selection_window.columnconfigure(0, weight=1)
    frm_selection = ttk.Frame(selection_window)  # Contains all the contents of the window (to match styles)
    frm_selection.grid(row=0, column=0, sticky="nsew")
    frm_selection.rowconfigure(1, weight=1)
    frm_selection.columnconfigure(1, weight=3)
    frm_selection.columnconfigure(2, weight=1)

    btns_select = []  # A nested list of buttons - each row is a device, each column is a transistor position.
    ttk.Label(frm_selection, text="Active transistors: ").grid(row=0, column=1, sticky="nsw", padx=10, pady=10)
    frm_transgrid = ttk.Frame(frm_selection, relief=tk.SUNKEN)
    frm_transgrid.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=10, pady=10)
    frm_transgrid.rowconfigure([0, 1], weight=1)
    frm_transgrid.columnconfigure([0, 1], weight=1)
    device_frames = []  # A 2x2 grid of frames, each one containing the four transistors in its respective device
    stvs_dev_names = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]  # The device names
    ents_dev_names = []  # The entryboxes that contain these names
    stvs_trans_names = [[tk.StringVar() for i in range(4)] for j in range(4)]   # A nested list of StringVars, that contain the names of each transistor.
                            # (Ordered by their device)
    ents_trans_names = []  # Their entryboxes
    for i in range(4):
        device_frames.append(ttk.Frame(frm_transgrid, relief=tk.RAISED, borderwidth=2))
        device_frames[-1].grid(row=i//2, column=i % 2, sticky='nsew')
        device_frames[-1].rowconfigure([2, 4], weight=1)  # 0 - dev name. 1, 3 - trans names. 2, 4 - buttons.
        device_frames[-1].columnconfigure([0, 1], weight=1)
        ttk.Label(device_frames[-1], text=f"Device name \n(chamber #{i+1}): ").grid(row=0, column=0, sticky="nsw", pady=5, padx=10)
        stvs_dev_names[i].set(device_names[i])
        ents_dev_names.append(ttk.Entry(device_frames[-1], textvar=stvs_dev_names[i], width=10))
        ents_dev_names[-1].grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
        btns_select.append([])
        ents_trans_names.append([])
        for j in range(4):
            stvs_trans_names[i][j].set(trans_names[i][j])
            ents_trans_names[-1].append(ttk.Entry(device_frames[-1], textvariable=stvs_trans_names[i][j], width=5))
            ents_trans_names[-1][-1].grid(row=(j//2)*2+1, column=j % 2, sticky="ns", padx=5, pady=(5, 0))
            btns_select[-1].append(tk.Button(device_frames[-1], text='', bg='red'))
            btns_select[-1][-1].grid(row=(j//2)*2+2, column=j % 2, sticky="nsew", padx=5, pady=(0, 5))
            btns_select[-1][-1].config(command=lambda xi=i, xj=j: activate_trans(xi, xj))
            if active_trans[i][j]:
                btns_select[-1][-1].config(bg='green')
            if len(drain_smus) > j:
                btns_select[-1][-1].config(text=drain_smus[j])
            else:
                btns_select[-1][-1].config(bg='gray', state=tk.DISABLED)
                ents_trans_names[-1][-1].config(state=tk.DISABLED)

    frm_sel_smus = ttk.Frame(frm_selection, relief=tk.SUNKEN)
    frm_sel_smus.grid(row=0, column=0, rowspan=2, sticky='nsew')
    frm_sel_smus.rowconfigure([0, 1, 2], weight=1)
    frm_sel_smus.columnconfigure([0, 1], weight=1)
    ttk.Label(frm_sel_smus, text="Chambers: \n(Click to toggle)").grid\
        (row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
    btns_trans_smus = []
    for i in range(4):
        btns_trans_smus.append(ttk.Button(frm_sel_smus))
        btns_trans_smus[-1].grid(row=i//2+1, column=i % 2, sticky="nsew", padx=5, pady=50)
        btns_trans_smus[-1].config(text=f"Chamber #{i + 1}")
        btns_trans_smus[-1].config(command=lambda row=i: activate_dev(row))
        # for j in range(4):
        #     if len(drain_smus) <= j:
        #         btns_trans_smus[-1].config(text="(None)")
        #         btns_trans_smus[-1].config(state=tk.DISABLED)
        #         for b in btns_select[i]:
        #             b.config(state=tk.DISABLED, bg='gray')
        #         ents_dev_names[i].config(state=tk.DISABLED)
        #         for e in ents_trans_names[i]:
        #             e.config(state=tk.DISABLED)

    btn_confirm = ttk.Button(frm_selection, text="Confirm", command=lambda: confirm_trans())
    btn_confirm.grid(row=0, column=2, sticky="nsew", padx=10, pady=10, ipadx=10)


# def callback(var):
#     content = var.get()


def set_var_name(num, s):
    """
    When a variable name is changed from the "SMUs" tab, the dropmenus in the "Sweep" and "Transient" tabs must update
    as well. The corresponding label in the "Transient" tab (before the entrybox holding its value) is also changed.
    :param num: The variable form which the function was called (1=var1, 2=var2), according to tab_smus.
    :param s: The StringVar corresponding to the variable.
    """
    global stv_var1, stv_var2, stv_var3, stv_name1, stv_name2, stv_name3, stv_name, param_list  # Bad global refs?!
    if type(s) == str:  # For the case where we're updating the const by loading a config
        v = s
    else:
        v = s.get()
    param_list[num - 1] = v  # Update param_list
    # Update both dropdown lists
    m1 = drp_name1["menu"]
    m1.delete(0, "end")
    for x in param_list:
        m1.add_command(label=x, command=lambda i=x: stv_name1.set(i))

    m2 = drp_name2["menu"]
    m2.delete(0, "end")
    for x in param_list:
        m2.add_command(label=x, command=lambda i=x: stv_name2.set(i))

    m3 = drp_name["menu"]
    m3.delete(0, "end")
    for x in param_list:
        m3.add_command(label=x, command=lambda i=x: stv_name.set(i))
    global stv_name
    stv_name.set(param_list[0])  # Reset the dropmenu in the "Transient" tab so that the user won't try to measure
        # a nonexistent variable

    # Update the corresponding name StringVar - Whichever one is not in the updated param_list.
    # if not from_sweep:
    for x in [stv_name1, stv_name2]:
        if x.get() not in param_list:
            x.set(v)
    if split('\(|\)', stv_name3.get())[1] not in param_list:
        stv_name3.set("Constant variable (" + v + "): ")
    # Update the corresponding label in the "Transient" tab
    global lbls_tnames
    lbls_tnames[num-1]["text"] = "V({}): ".format(param_list[num-1])


def update_table(t):
    """
    Updates the table in the "Analysis" tab, by re-reading central.csv.
    :param t: The table to be updated. For some reason, I couldn't just use the table as a global variable...
    """
    if control_tabs.tab(control_tabs.select(), "text") == "Analysis":  # Only update the table if you're going to see it
        with open("data/central.csv", newline='') as f:  # Get the new experiment list
            csv_reader = reader(f)
            existing_data = list(csv_reader)
        t.delete(*t.get_children())  # Reset the table
        t["column"] = [*existing_data[0][0:2], "Experiment type", *existing_data[0][2:]]  # Prepare headers
        t["show"] = "headings"
        widths = [44, 79, 115, 63, 39, 120, 58, 83, 111, 69, 76, 98, 100, 70, 0, 176]  # Prepare widths
        for col in t["column"]:  # Set the headers
            t.heading(col, text=col)
        for i in range(len(t["columns"])):  # Set column widths
            t.column(t["columns"][i], width=widths[i], stretch=False)
        # The experiment type and variable order are determined by the abbreviation (e.g. 'JBD'), but there still
        # needs to be a readable representation of the experiment type for the user. Therefore:
        for row in existing_data[1:]:  # Determine the experiment type from the abbreviation saved in the file
            extype = 'Other'  # Not supposed to stay like this.
            abbr = row[-2]
            if len(abbr) == 2:
                extype = 'Transient'
            elif len(abbr) == 3:
                extype = 'Exposure'
            else:
                if abbr[0] == 'C':
                    extype = 'Characteristic'
                elif abbr[0] == 'T':
                    extype = 'Periodic sweep'
            t.insert("", "end", values=[*row[:2], extype, *row[2:]])


def extract_var_letter(s):
    """
    Turns a variable name (e.g. 'jg') into a single letter for the abbreviation.
    :param s: The variable name
    :return: The corresponding letter
    """
    if 'J' in s.upper():
        return 'J'
    if 'B' in s.upper():
        return 'B'
    if 'D' in s.upper():
        return 'D'
    if 'T' in s.upper():
        return 'T'
    return ''


def set_labels(lvars, extract=False):
    """
    Sets the labels (globals label_prim, label_sec, label_const) for the analysis graphs, based on the current
    experiment's abbreviation.
    Transient measurements: TX where X is the measured current.
    Characteristics: CXYZ where X is the primary variable, Y is the secondary and Z is the constant.
    Exposure: XYZ, same as above.
    Trans. sweeps: TXYZ where X is the primary variable, and both Y and Z are constant.
    """
    global label_prim, label_sec, label_const
    if extract:  # We get a list of three strings, turn it into a 3-char string
        var_order = ''.join([extract_var_letter(x) for x in lvars])
    else:  # We get a three-letter string (already extracted).
        var_order = lvars
    raise_error = False  # Will become true if any of the letters are invalid
    if len(var_order) >= 3:
        p, s, c = tuple(var_order[-3:])
        match p:
            case 'J':
                label_prim = "$V_{JG} (V)$"
            case 'B':
                label_prim = "$V_{BG} (V)$"
            case 'D':
                label_prim = "$V_{D} (V)$"
            case _:
                raise_error = True
        match s:
            case 'J':
                label_sec = "$V_{JG} (V)$"
            case 'B':
                label_sec = "$V_{BG} (V)$"
            case 'D':
                label_sec = "$V_{D} (V)$"
            case _:
                raise_error = True
        match c:
            case 'J':
                label_const = "$V_{JG}$"
            case 'B':
                label_const = "$V_{BG}$"
            case 'D':
                label_const = "$V_{D}$"
            case _:
                raise_error = True
        if var_order[0] == 'T':  # If it's a periodic sweep, var_sec is effectively the time.
            label_sec = "Time (sec)"
        elif var_order[0] != 'C' and len(var_order) == 4:  # CXXX and TXXX are the only legal 4-letter abbreviations
            raise_error = True
    elif len(var_order) == 2:  # If it's a transient measurement, the labels don't really matter... Still undecided about this
        if not var_order[0] == 'T':
            raise_error = True
        else:
            label_prim = "Time (sec)"
            match var_order[1]:  # TODO: Which label should I use?! Maybe I don't even need to set it?
                case 'J':
                    label_sec = "$V_{JG}$"
                case 'B':
                    label_sec = "$V_{BG}$"
                case 'D':
                    label_sec = "$V_{D}$"
                case _:
                    raise_error = True
    if raise_error:
        tk.messagebox.showerror('', "Error: Invalid variable order!")


def hacky_no_spa_1(w):
    """
    If the SPA isn't connected or can't be detected, we need to get an error message - but raising it before setting up
    the tabs messes them up, and raising it afterwards also causes problems (don't remember what it was). I might have
    forgotten parts of the problem by now, it probably also had to do with the fact that you shouldn't use tkinter in
    a thread, and that the SPA connection attempt MUST be done in one (to prevent freezing).
    The dumb solution: Start a thread that sleeps for half a second, letting the window set itself up, then generate
    and event that's bound to a function (outside the thread) that raises the messagebox.
    :param w:
    :return:
    """
    time.sleep(0.5)
    w.event_generate("<<no-spa>>", when="tail")


def hacky_no_spa_2():
    if not suppress_errors:
        messagebox.showerror('SPA not connected', err_msg)
    pass


def get_service(name):
    """
    Returns the specified service, or None if it doesn't exist.
    :param name: The name of the service.
    :return: The service object itself, or None.
    """
    service = None
    try:
        service = psutil.win_service_get(name)
        service = service.as_dict()
    except Exception as ex:
        # raise psutil.NoSuchProcess if no service with such name exists
        print(str(ex))

    return service


def open_measurement_window(p_prim, stv_linlog1, is_transient=False, for_testing=False):  # p_prim is a list if sweep, string if transient
    """
    Opens the measurement window, which includes the graph, progressbar, and accompanying text.
    :param p_prim: Information about the primary variable, to be displayed in the labels. If the experiment is a sweep
            it's the whole p_prim list (to set the xlims), if the experiment is transient it's just the variable name.
    :param stv_linlog1: To determine the initial yscale.
    :param is_transient: To determine the xlims.
    :param for_testing: If True, the window was opened by the "Test Color Scheme" button. Therefore, some of the
    elements don't need to be displayed.
    """
    def close():
        measurement_vars.stop_ex = False  # Just in case it didn't happen in the measurements file
        measurement_vars.ex_finished = False
        window_load.destroy()

    def close_prep():
        """
        Hacky workaround to close the experiment window and also stop the experiment itself:
        - Set the global variable stop_ex to True
        - The measurement function detects this and raises an event in the exp. window (while also resetting stop_ex)
        - The event is bound to a function that simply closes the window.
        """
        if for_testing:  # There is no actual measurement taking place
            close()
        else:
            lbl_progress["text"] = "Closing (once the sweep is done)... "
            window_load.title("Closing...")
            if measurement_vars.ex_finished:  # If the measurement has already finished
                window_load.destroy()
                measurement_vars.stop_ex = False  # Just in case
                measurement_vars.ex_finished = False
            else:
                measurement_vars.stop_ex = True

    window_load = tk.Toplevel()
    window_load.title("Running measurement")
    window_load.rowconfigure(0, weight=1)
    window_load.columnconfigure(0, weight=1)
    # window_load.overrideredirect(True)  # What is this?
    window_load.protocol("WM_DELETE_WINDOW", lambda: close_prep())  # Properly finish the measurements before closing!
    window_load.geometry("800x600+0+0")
    frm_load = ttk.Frame(window_load)
    frm_load.grid(row=0, column=0, sticky="nsew")
    frm_load.rowconfigure(2, weight=1, minsize=300)
    frm_load.columnconfigure(0, weight=1)
    if not for_testing:
        if is_transient:
            ttk.Label(frm_load, text="Measuring current...").grid(row=0, column=0, columnspan=3,
                                                                                sticky="nsw")
        else:
            ttk.Label(frm_load, text="Measuring sweep...").grid(row=0, column=0, columnspan=3,
                                                                                sticky="nsw")
        stv_ex_linlog = tk.StringVar(value=stv_linlog1.get())  # Determines the yscale
        stv_ex_curr = tk.StringVar(value='n')  # Shows/hides the additional currents (jg, bg, s)
        chk_linlog = ttk.Checkbutton(frm_load, text="Logarithmic scale", variable=stv_ex_linlog,
                                     onvalue="Logarithmic", offvalue="Linear")
        chk_linlog.grid(row=1, column=0, sticky="nsw")
        chk_currents = ttk.Checkbutton(frm_load, text="Show additional currents", variable=stv_ex_curr, onvalue='y',
                                       offvalue='n')
        chk_currents.grid(row=1, column=2, sticky="nsw")
    fig = plt.Figure()
    ax = fig.add_subplot(111)
    ax2 = ax.twinx()
    ax3 = ax.twinx()
    ax4 = ax.twinx()
    # Make some space between the three right axes
    ax3.spines["right"].set_position(("axes", 1.2))
    ax4.spines["right"].set_position(("axes", 1.4))
    ax3.get_yaxis().get_offset_text().set_position((1.2, 5.0))
    ax4.get_yaxis().get_offset_text().set_position((1.4, 5.0))
    if not is_transient:  # If it's a sweep, we can set the xlims from the start
        ax.set_xlim([p_prim[1], p_prim[2]])
    if stv_linlog1.get() == 'Logarithmic':
        ax.set_yscale('log')
        ax2.set_yscale('log')
        ax3.set_yscale('log')
        ax4.set_yscale('log')
    # The additional currents are initially hidden
    ax2.set_visible(False)
    ax3.set_visible(False)
    ax4.set_visible(False)
    # Set a different color for each current
    global color_d1, color_g1, color_g2, color_src
    ax.spines["left"].set_edgecolor(color_d1)
    ax2.spines["right"].set_edgecolor(color_g1)
    ax3.spines["right"].set_edgecolor(color_g2)
    ax4.spines["right"].set_edgecolor(color_src)
    ax.tick_params(axis='y', colors=color_d1)
    ax2.tick_params(axis='y', colors=color_g1)
    ax3.tick_params(axis='y', colors=color_g2)
    ax4.tick_params(axis='y', colors=color_src)
    ax.yaxis.label.set_color(color_d1)
    ax2.yaxis.label.set_color(color_g1)
    ax3.yaxis.label.set_color(color_g2)
    ax4.yaxis.label.set_color(color_src)

    bar = FigureCanvasTkAgg(fig, frm_load)  # Embed the graph in the window
    bar.get_tk_widget().grid(row=2, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

    if not for_testing:
        prb = ttk.Progressbar(frm_load, orient="horizontal", mode="determinate")
        prb.grid(row=3, column=0, columnspan=3, padx=5, pady=10, sticky="ew")
        lbl_progress = ttk.Label(frm_load, text="Starting measurement...")
        lbl_progress.grid(row=4, column=0, sticky="nsw")
        btn_ex_abort = ttk.Button(frm_load, text="Abort and save")
        btn_ex_abort.grid(row=4, column=1, sticky="nsew", padx=5, pady=5)
        btn_ex_end = ttk.Button(frm_load, text="Finish", state=tk.DISABLED)
        btn_ex_end.grid(row=4, column=2, sticky="nsew", padx=5, pady=5)

    window_load.grab_set()  # Always on top
    window_load.bind("<<close-window>>", lambda e: close())
    if for_testing:
        window_load.title("Color Scheme Test")
        return ax, ax2, ax3, ax4, bar
    else:
        return window_load, fig, lbl_progress, chk_linlog, stv_ex_linlog, chk_currents, btn_ex_end, btn_ex_abort, prb, \
               ax, ax2, ax3, ax4, bar  # These objects will be referred to at runtime


def safe_quit():  # To prevent the program from running after the window is closed...
    window.quit()
    window.destroy()


def init_channels_tab():
    def update_drains_label(s):
        """
        Sets lbl_drains to show the SMUs that are not currently used as gate or source SMUs.
        Triggered whenever one of the drp_smu#s is changed, only if they're all already set!
        Also updates drain_smus.
        :param s: The StringVar from which the function was called.
        """
        global drain_smus, active_trans
        used_smus = [stv_smu2, stv_smu3, stv_smu4]  # So they're included in locals()
        for s in used_smus:
            if s.get() == "(None)":
                used_smus.remove(s)
        try:
            temp_smus = [x for x in smu_list]
            for s in used_smus:  # Remove the SMUs that are "taken"
                if s.get() == '':  # Don't do anything
                    return
                temp_smus.remove(s.get())
            lbl_drains["text"] = ', '.join(temp_smus)  # e.g. "SMU2, SMU5"
            if len(drain_smus) != 0:  # Ignore the initial run
                active_trans = [[False for j in range(4)] for i in range(4)]
            drain_smus = temp_smus
            stv_smu1.set(drain_smus[0])  # TEMPORARILY - only use the first SMU, until simultaneous measurements are implemented.
        except ValueError:  # Trying to remove an SMU that has already been removed, i.e. the same one was selected twice.
            temp_smus_error = [x for x in smu_list]  # Re-list all the SMUs
            temp_smus_error.append("(None)")  # If it's selected it'll be removed; if not, it'll be ignored, since
            # we take temp_smus_error[0] in the end.
            for stv in [*drain_smus, *set([x.get() for x in used_smus])]:  # Should be missing one name
                temp_smus_error.remove(stv)  # So that only the missing name remains in temp_smus_error
            window.after(1, s.set, temp_smus_error[0])  # Reset the stv the user tried to change

    # Choose which SMUs will be used and assign a variable to each.
    tab_channels.rowconfigure([*range(4)], weight=1)
    tab_channels.columnconfigure([*range(4)], weight=1)
    global smu_list
    global b1500
    if spa_connected:
        smu_list = list(b1500.smu_names.values())  # "SMU1", "SMU2", etc
    else:
        smu_list = ["SMU1", "SMU2", "SMU3", "SMU4", "SMU5", "SMU6"]  # Just a placeholder.
    ttk.Label(tab_channels, text="Drain SMUs: ").grid(row=0, column=0, sticky="nse")
    ttk.Label(tab_channels, text="Gate SMUs: ").grid(row=1, column=0, sticky="nse")
    ttk.Label(tab_channels, text="Ground SMU: ").grid(row=3, column=0, sticky="nse")
    global stv_smu1, stv_smu2, stv_smu3, stv_smu4
    stv_smu1 = tk.StringVar(name='stv_smu1')
    stv_smu2 = tk.StringVar(name='stv_smu2')
    stv_smu3 = tk.StringVar(name='stv_smu3')
    stv_smu4 = tk.StringVar(name='stv_smu4')
    # The stv_smu#s represent the used SMUs, in the order shown in the tab (i.e. stv_smu2 is the top gate SMU).
    # Starts from 2 in case I'd want to bring back a StringVar for the drain...
    # for s in [stv_smu2, stv_smu3, stv_smu4]:
    #     s.trace("w", lambda *args: update_drains_label(s))

    stv_smu2.trace("w", lambda *args: update_drains_label(stv_smu2))
    stv_smu3.trace("w", lambda *args: update_drains_label(stv_smu3))
    stv_smu4.trace("w", lambda *args: update_drains_label(stv_smu4))

    # drp_smu1 = ttk.OptionMenu(tab_channels, stv_smu1, None, *smu_list)
    # drp_smu1.grid(row=0, column=1, sticky="ew")
    # drp_smu1.configure(state="disabled")

    lbl_drains = ttk.Label(tab_channels)
    lbl_drains.grid(row=0, column=1, sticky="w", padx=10)

    drp_smu2 = ttk.OptionMenu(tab_channels, stv_smu2, None, *smu_list)
    drp_smu2.grid(row=1, column=1, sticky="w", padx=10, ipadx=20)
    # drp_smu2.configure(state="disabled")
    drp_smu3 = ttk.OptionMenu(tab_channels, stv_smu3, None, *smu_list)
    drp_smu3.grid(row=2, column=1, sticky="w", padx=10, ipadx=20)
    # drp_smu3.configure(state="disabled")
    drp_smu4 = ttk.OptionMenu(tab_channels, stv_smu4, None, *smu_list, "(None)")
    drp_smu4.grid(row=3, column=1, sticky="w", padx=10, ipadx=20)
    # drp_smu4.configure(state="disabled")
    # l = len(smu_list)  # Maybe only allow operation with >4 SMUs?
    # if l == 0:
    #     messagebox.showerror('', "No SMUs detected!")
    # if l >= 1:
    #     stv_smu1.set(smu_list[0])
    #     drp_smu1.configure(state="normal")
    # if l >= 2:
    #     stv_smu2.set(smu_list[1])
    #     drp_smu2.configure(state="normal")
    # if l >= 3:
    #     stv_smu3.set(smu_list[2])
    #     drp_smu3.configure(state="normal")
    # if l >= 4:
    #     stv_smu4.set(smu_list[3])
    #     drp_smu4.configure(state="normal")

    # Temporarily:
    # stv_smu1.set("SMU1")
    # stv_smu2.set("SMU5")
    # stv_smu3.set("SMU6")
    # stv_smu4.set("SMU4")

    with open('data/transistor_data.csv', newline='') as f:
        csv_reader = reader(f)
        temp_lst = list(csv_reader)
    # stv_smu1.set(temp_lst[9][0])  # Is this necessary...?
    stv_smu2.set(temp_lst[10][0])
    stv_smu3.set(temp_lst[10][1])
    stv_smu4.set(temp_lst[10][2])

    ttk.Label(tab_channels, text="Variable name: ").grid(row=0, column=2, sticky="nse")
    ttk.Label(tab_channels, text="Variable name: ").grid(row=1, column=2, sticky="nse")
    ttk.Label(tab_channels, text="Variable name: ").grid(row=2, column=2, sticky="nse")
    global stv_var1, stv_var2, stv_var3
    stv_var1 = tk.StringVar(value="d")
    stv_var2 = tk.StringVar(value="jg")
    stv_var3 = tk.StringVar(value="bg")
    ent_var1 = ttk.Entry(tab_channels, textvariable=stv_var1, width=10)
    ent_var1.grid(row=0, column=3, sticky="w", padx=10)
    ent_var1.bind("<FocusOut>", lambda e: set_var_name(1, stv_var1))  # See the definition of set_var_name() for info
    ent_var2 = ttk.Entry(tab_channels, textvariable=stv_var2, width=10)
    ent_var2.grid(row=1, column=3, sticky="w", padx=10)
    ent_var2.bind("<FocusOut>", lambda e: set_var_name(2, stv_var2))
    ent_var3 = ttk.Entry(tab_channels, textvariable=stv_var3, width=10)
    ent_var3.grid(row=2, column=3, sticky="w", padx=10)
    ent_var3.bind("<FocusOut>", lambda e: set_var_name(3, stv_var3))

    # Temporarily, until I implement SMU flexibility:
    # for x in [drp_smu1, drp_smu2, drp_smu3, drp_smu4, ent_var1, ent_var2, ent_var3]:
    #     x.configure(state=tk.DISABLED)


def init_sweep_tab():
    # Set up sweep and exposure measurements.
    def enable_step_n(x):
        """
        If both "Start" and "Stop" are filled in, and the latter is greater, enable the "Step" and "No. of steps"
        entryboxes. Otherwise, disable them.
        :param x: 1 for the primary variable, 2 for the secondary variable.
        """
        if x == 1:
            start = ent_start1.get()
            stop = ent_stop1.get()
            try:
                if start != '' and stop != '':  # Both are filled in
                    if suffix(stop) > suffix(start):  # The range is positive
                        if stv_step1.get() == '':  # If the entryboxes are empty, enable them.
                            ent_step1.config(state="normal")
                            ent_n1.config(state="normal")
                        else:  # If the entryboxes are filled (and only the range is changed), update the step.
                            update_step_n(stv_n1, 'n', 1)
                else:  # If the range cannot be defined, disable step and n.
                    ent_step1.config(state="disabled")
                    ent_n1.config(state="disabled")
                    stv_step1.set('')
                    stv_n1.set('')
                    # set_text(ent_step1, stv_step1, '')
                    # set_text(ent_n1, stv_n1, '')
            except ValueError:  # If the "Start" or "Stop" values are invalid
                ent_step1.config(state="disabled")
                ent_n1.config(state="disabled")
                stv_step1.set('')
                stv_n1.set('')
                # set_text(ent_step1, stv_step1, '')
                # set_text(ent_n1, stv_n1, '')
        elif x == 2:  # Same for the second column.
            start = ent_start2.get()
            stop = ent_stop2.get()
            try:
                if start != '' and stop != '':
                    if float(stop) > float(start):
                        if stv_step2.get() == '':
                            ent_step2.config(state="normal")
                            ent_n2.config(state="normal")
                        else:
                            update_step_n(stv_n2, 'n', 2)
                else:
                    ent_step2.config(state="disabled")
                    ent_n2.config(state="disabled")
                    stv_step2.set('')
                    stv_n2.set('')
                    # set_text(ent_step2, stv_step2, '')
                    # set_text(ent_n2, stv_n2, '')
            except ValueError:
                ent_step2.config(state="disabled")
                ent_n2.config(state="disabled")
                stv_step2.set('')
                stv_n2.set('')
                # set_text(ent_step2, stv_step2, '')
                # set_text(ent_n2, stv_n2, '')

    def update_step_n(var, t, num):
        """
        When "Step" or "No. of steps" are changed, the other value must update accordingly. This may also trigger when
        changeing the voltage range (stop-start).
        :param var: The StringVar of the entry that called the function.
        :param t: 'step' or 'n', according to the caller.
        :param num: 1 or 2, according to the column (primary or secondary variable).
        """
        if len(var.get()) > 0:  # To avoid errors. I don't think letting the user leave an entry blank could cause
            # problems, because it won't let them run measurements anyways.
            try:
                x = suffix(var.get())
                if num == 1:
                    rng = suffix(ent_stop1.get()) - suffix(ent_start1.get())  # The voltage range
                    if t == 'step':  # Update n. But since it needs to be an integer, update step too right afterwards!
                        if x == 0:  # To prevent zero division errors
                            stv_n1.set('1')
                            # set_text(ent_n1, stv_n1, '1')
                            return
                        newn = round(rng / x + 1)
                        stv_n1.set(strf(newn))
                        stv_step1.set(strf(rng / (newn - 1)))
                        # set_text(ent_n1, stv_n1, str(newn))
                        # set_text(ent_step1, stv_step1, str(rng / (newn - 1)))
                    if t == 'n':  # Update step
                        if x == 1:  # To define single-sweep measurements
                            stv_step1.set('0')
                            # set_text(ent_step1, stv_step1, '0')
                            return
                        if x == 0:  # To prevent zero division errors
                            return
                        stv_step1.set(strf(rng / (x - 1)))
                        # set_text(ent_step1, stv_step1, str(rng / (x - 1)))
                if num == 2:
                    rng = suffix(ent_stop2.get()) - suffix(ent_start2.get())
                    if t == 'step':
                        if x == 0:  # Here this special case matters: only one sweep, therefore n=1 and step is
                            # undefined (but set to 0 here - this isn't sent to the SPA anyways).
                            stv_n2.set('1')
                            # set_text(ent_n2, stv_n2, '1')
                            return
                        newn = round(rng / x + 1)
                        stv_n2.set(strf(newn))
                        stv_step2.set(strf(rng / (newn - 1)))
                        # set_text(ent_n2, stv_n2, str(newn))
                        # set_text(ent_step2, stv_step2, str(rng / (newn - 1)))
                    if t == 'n':
                        if x == 1:
                            stv_step2.set('0')
                            # set_text(ent_step2, stv_step2, '0')
                            return
                        if x == 0:
                            return
                        stv_step2.set(strf(rng / (x - 1)))
                        # set_text(ent_step2, stv_step2, str(rng / (x - 1)))
            except (ValueError, ZeroDivisionError) as e:
                print(e)
                return

    def update_const(other_stv):
        """
        After setting the name of the primary or secondary variable, the constant variable's name must also be updated.
        If the primary and secondary variable names are the same, one must be changed (and then the constant is
        updated).
        :param other_stv: The StringVar of the dropmenu from which the function was NOT called, i.e. the one that wasn't
        just changed.
        """
        try:
            global param_list, stv_name1, stv_name2, stv_name3
            if stv_name1.get() != '' and stv_name2.get() != '':  # If both variables have been defined
                if stv_name1.get() == stv_name2.get():  # If they're the same, change the one the user didn't just set.
                    for i in param_list:  # Find the first variable other than the one that the dropmenus are set to,
                        if other_stv.get() != i:  # and set it as the other variable.
                            other_stv.set(i)
                            break
                p = [i for i in param_list]  # Set the constant to the only variable that isn't "taken".
                # print("1: {}, 2: {}".format(stv_name1.get(), stv_name2.get()))
                p.remove(stv_name1.get())
                p.remove(stv_name2.get())
                stv_name3.set("Constant variable (" + p[0] + "): ")
        except Exception as e:  # This function was so problematic, I had to make a separate error case for it
            tb = str(traceback.format_exc())
            messagebox.showerror('', "An error has occurred while updating the variables.")
            logging.error("UPDATE_CONST() ERROR: " + str(e) + ". Traceback: " + str(tb))

    def save_config(edit=False):
        """
        Check if all the entryboxes are filled in, and if all the values that are supposed to be numeric indeed are.
        Then, save the configuration to configs_s.csv, or overwrite an existing row.
        :param edit: False to add a new row, True to overwrite an existing row.
        """
        try:
            if len(split('\(|\)', stv_name3.get())) < 3:  # There is nothing between the parentheses for the const. variable
                messagebox.showerror('', "Please choose the primary and secondary variables!")
                return
            params = [stv_savename.get(), stv_op.get(), stv_gas.get(), stv_conc.get(), stv_carr.get(), stv_atm.get(),
                      stv_dev.get(), stv_dec.get(), stv_thick.get(), stv_temp.get(), stv_hum.get(), stv_name1.get(),
                      stv_linlog1.get(), stv_start1.get(), stv_stop1.get(), stv_step1.get(), stv_n1.get(), stv_comp1.get(),
                      stv_name2.get(), stv_start2.get(), stv_stop2.get(), stv_step2.get(), stv_n2.get(), stv_comp2.get(),
                      split('\(|\)', stv_name3.get())[1], stv_const.get(), stv_const_comp.get(), stv_hold.get(),
                      stv_delay.get(), stv_var1.get(), stv_var2.get(), stv_var3.get()]
            for i in params:  # Check that all the entryboxes are filled in
                if i == '':
                    messagebox.showerror('', "Please fill out all the parameters (including the info on the left)!")
                    return
            for i in [*params[13:18], *params[19:24], *params[25:-3]]:  # Check that the relevant values are numeric
                try:
                    suffix(i)
                except ValueError:
                    messagebox.showerror('', "The following parameters must be numeric: Start, Stop, Step, No. of steps, "
                                             "Compliance, Constant variable value.")
                    return
            if not edit:  # Save
                with open("data/configs_s.csv", newline='') as f:  # Check if the name already exists
                    csv_reader = reader(f)
                    for row in list(csv_reader)[1:]:
                        if row[0] == stv_savename.get():
                            messagebox.showerror('', "Configuration name already exists!")
                            return
                with open("data/configs_s.csv", "a+", newline='') as f:  # Write a new line with the params
                    csv_writer = writer(f)
                    csv_writer.writerow(params)
                menu = drp_load["menu"]  # Add it to the menu
                options = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)]
                options.append(params[0])  # Clear the dropmenu and re-add the options including the new one
                menu.delete(0, "end")
                for s in options:
                    menu.add_command(label=s, command=tk._setit(stv_loadname, s))
                messagebox.showinfo('', 'Configuration saved. ')
            else:  # Edit
                with open("data/configs_s.csv", newline='') as f:  # Get the existing configs
                    csv_reader = reader(f)
                    loadouts = list(csv_reader)
                same_name = [row[0] == stv_savename.get() for row in loadouts]  # True on the row we need to edit, False otherwise
                if not any(same_name):  # Trying to edit a config that doesn't exist
                    messagebox.showerror('', "Configuration name does not exist!")
                    return
                with open("data/configs_s.csv", "w", newline='') as f:
                    csv_writer = writer(f)
                    for row in loadouts:
                        if row[0] == stv_savename.get():
                            csv_writer.writerow(params)
                        else:
                            csv_writer.writerow(row)
                messagebox.showinfo('', 'Configuration edited. ')
        except PermissionError as e:
            tb = str(traceback.format_exc())
            if 'used by another process' in tb:
                messagebox.showerror('', "The configuration list is open in another program. Please close it and "
                                         "try again.")
            else:  # Just in case
                messagebox.showerror('', "Permission error: Please make sure the configuration list is not open in "
                                         "another program.")
            return

    def load_config():
        """
        Loads the selected configuration into all the entryboxes.
        """
        global stv_name1, stv_name2, stv_name, param_list
        with open("data/configs_s.csv", newline='') as f:
            csv_reader = reader(f)
            for row in list(csv_reader)[1:]:
                if row[0] == stv_loadname.get():  # For the row that corresponds to the selected config:
                    # Fill out the entryboxes (and update param_list)
                    # param_list = row[-3:]
                    stv_op.set(row[1])
                    stv_gas.set(row[2])
                    stv_conc.set(row[3])
                    stv_carr.set(row[4])
                    stv_atm.set(row[5])
                    stv_dev.set(row[6])
                    stv_dec.set(row[7])
                    stv_thick.set(row[8])
                    stv_temp.set(row[9])
                    stv_hum.set(row[10])
                    # param_list[0] = row[-3]
                    # stv_name1.set(row[11])
                    stv_linlog1.set(row[12])
                    stv_start1.set(row[13])
                    stv_stop1.set(row[14])
                    stv_step1.set(row[15])
                    stv_n1.set(row[16])
                    stv_comp1.set(row[17])
                    # param_list[1] = row[-2]
                    # stv_name2.set(row[18])
                    stv_start2.set(row[19])
                    stv_stop2.set(row[20])
                    stv_step2.set(row[21])
                    stv_n2.set(row[22])
                    stv_comp2.set(row[23])
                    stv_const.set(row[25])
                    stv_const_comp.set(row[26])
                    stv_hold.set(row[27])
                    stv_delay.set(row[28])
                    # stv_name3.set("Constant variable (" + row[24] + "): ")
                    # param_list[2] = row[-1]

                    # Now we must update param_list and the stv_name#s. However, whenever one of the latter is changed,
                    # it triggers update_const(), which requires param_list to match the stv_name#s except for the one
                    # that was just updated. Therefore, we need to update the elements of param_list in the order of the
                    # stv_name#s!!
                    names = [row[11], row[18], row[24]]  # Corresponding to stv_name1, stv_name2 and stv_name3.
                    new_params = row[-3:]  # Corresponding to the order of the new param_list.
                    # A for loop would be clunky because of stv_name3's unique format...
                    param_list[new_params.index(names[0])] = names[0]
                    stv_name1.set(names[0])
                    param_list[new_params.index(names[1])] = names[1]
                    stv_name2.set(names[1])
                    param_list[new_params.index(names[2])] = names[2]
                    stv_name3.set("Constant variable ({}): ".format(names[2]))


                    stv_var1.set(row[-3])
                    stv_var2.set(row[-2])
                    stv_var3.set(row[-1])
                    # set_var_name(1, stv_name1, True)
                    # set_var_name(2, stv_name2, True)
                    # set_var_name(3, row[24], True)

                    # Update the dropmenus
                    m1 = drp_name1["menu"]
                    m1.delete(0, "end")
                    for x in param_list:
                        m1.add_command(label=x, command=lambda i=x: stv_name1.set(i))
                    m2 = drp_name2["menu"]
                    m2.delete(0, "end")
                    for x in param_list:
                        m2.add_command(label=x, command=lambda i=x: stv_name2.set(i))
                    m3 = drp_name["menu"]
                    m3.delete(0, "end")
                    for x in param_list:
                        m3.add_command(label=x, command=lambda i=x: stv_name.set(i))
                    # Update the corresponding label in the "Transient" tab
                    global lbls_tnames
                    for i in range(3):
                        lbls_tnames[i]["text"] = "V({}): ".format(param_list[i])
                    # Update the chosen value in the transient dropmenu to the drain SMU
                    stv_name.set(param_list[0])
                    return

    def delete_config():
        """
        Deletes the selected configuration.
        """
        if tk.messagebox.askyesno('', "Are you sure you want to delete this configuration?"):
            try:
                del_id = stv_loadname.get()  # The name of the config to be deleted
                with open("data/configs_s.csv", newline='') as f:  # Get the existing configs
                    csv_reader = reader(f)
                    existing_data = list(csv_reader)
                with open("data/configs_s.csv", "w", newline='') as f:   # Write them back, except for the one that will
                    csv_writer = writer(f)                              # be deleted
                    for row in existing_data:
                        if row[0] != del_id:
                            csv_writer.writerow(row)
                menu = drp_load["menu"]  # Update the dropmenu
                options = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)]  # Get the options as a list
                options.remove(del_id)
                menu.delete(0, "end")  # Delete everything and rewrite them without the deleted option
                for s in options:
                    menu.add_command(label=s, command=tk._setit(stv_loadname, s))
                stv_loadname.set('')  # Reset the chosen config, since the one that was previously chosen no longer exists
                messagebox.showinfo('', 'Configuration deleted.')
            except PermissionError as e:
                tb = str(traceback.format_exc())
                if 'used by another process' in tb:
                    messagebox.showerror('', "The configuration list is open in another program. Please close it and "
                                             "try again.")
                else:  # Just in case
                    messagebox.showerror('', "Permission error: Please make sure the configuration list is not open in "
                                             "another program.")
                return

    def run_characteristic():
        """
        Runs a characteristic measurement - that is, several I-V sweeps (on the primary variable), each with a
        different value for the secondary variable.
        """
        def increment(evt):
            """
            Increments the progressbar and updates the progress label.
            :param: val: The portion of the progressbar that should be full (between 0 and 1).
            :param: v: The value (voltage) of the secondary variable in the current sweep.
            :param: devid: The index of the device that had just been measured. If it is 4, the "Initializing"
            message should be displayed. If it is 5, the "Measurement Complete" message should be displayed.
            """
            global device_names
            val, v, devid = tuple(measurement_vars.incr_vars)
            if devid == 4:
                lbl_progress["text"] = "Initializing..."
            elif devid == 5:
                lbl_progress["text"] = f"Measurement complete ({p_sec[0]}={v}V)."
            else:
                lbl_progress["text"] = f"Measuring ({device_names[devid]}, {p_sec[0]}={v}V)..."
            prb["value"] = val * 100
            if val == 1:
                btn_ex_end["state"] = tk.NORMAL

        def add_sweep(evt):
            """
            Adds a sweep to the plot.
            :param: v1: The primary variable of the sweep. (list)
            :param: v2: The secondary variable value of the sweep that is being added (voltage or time).
                        Currently unused. (float)
            :param: i: The currents measured from the sweep. (list of 3-19 lists)
            """
            global drain_colors, color_g1, color_g2, color_src
            v1, v2, i = tuple(measurement_vars.send_sweep)
            secondary_col = -3 if show_src else -2
            y1 = i[:secondary_col]  # Only the drains
            y2 = i[secondary_col]
            y3 = i[secondary_col+1]
            if show_src:
                y4 = i[-1]

            for n, y in enumerate(y1):
                ax.plot(v1, y, color=drain_colors[n])
            ax2.plot(v1, y2, color_g1)
            ax3.plot(v1, y3, color_g2)
            if show_src:
                ax4.plot(v1, y4, color_src)
            bar.draw()

        def linlog():
            """
            Updates the graph based on the state of the linear/logarithmic chechbox.
            """
            if chk_linlog.instate(['selected']):
                ax.set_yscale('log')
                ax2.set_yscale('log')
                ax3.set_yscale('log')
                ax4.set_yscale('log')
            else:
                ax.set_yscale('linear')
                ax2.set_yscale('linear')
                ax3.set_yscale('linear')
                ax4.set_yscale('linear')
            bar.draw()

        def additional_currents():
            """
            Shows/hides the three additional currents (jg, bg, s).
            """
            if chk_currents.instate(['selected']):
                ax2.set_visible(True)
                ax3.set_visible(True)
                if show_src:
                    ax4.set_visible(True)
                    fig.subplots_adjust(right=0.65)  # Make room for the new right axes
                else:
                    fig.subplots_adjust(right=0.75)
            else:
                ax2.set_visible(False)
                ax3.set_visible(False)
                ax4.set_visible(False)
                fig.subplots_adjust(right=0.9)  # But here the graph can take the entire right side
            bar.draw()

        def finish_sweep(aborted=False):
            """
            Closes the window, extracts the final measurement data, and saves the experiment.
            :param: ex_v1: The primary variable. (list)
            :param: ex_v2: The secondary variable. (list)
            :param: ex_i: The measured DRAIN currents. (list of lists, with a size
                            of len(ex_v2) x len(ex_v1))
            :param: aborted: True if the function was called via the "Abort" button, False if it was called via the
            "Finish" button.
            """
            if aborted:  # Let close() close the window, after the experiment has ended.
                lbl_progress["text"] = "Closing (once the sweep is done)... "
                window_load.title("Closing...")
                if measurement_vars.ex_finished:  # If the measurement has already finished
                    window_load.grab_release()
                    window_load.destroy()
                    measurement_vars.stop_ex = False  # Just in case
                    measurement_vars.ex_finished = False
                else:  # The current sweep must be allowed to finish
                    measurement_vars.abort_ex = True
                    measurement_vars.stop_ex = True
            else:  # If called from the "Finish" button, the window can close normally.
                window_load.grab_release()
                window_load.destroy()
            # # Reset these variables, just in case
            # measurement_vars.stop_ex = False
            # measurement_vars.ex_finished = False
            if len(measurement_vars.ex_vars) == 3:  # To avoid unpacking an empty list after aborting
                ex_v1, ex_v2, ex_i = tuple(measurement_vars.ex_vars)  # Extract the measurement data
                i_to_save = [[x for row in [meas[i] for meas in ex_i] for x in row] for i in range(len(ex_i[0]))]
                # Explanation:
                # - i iterates over the drains (ex_i[0] is simply the first measurement (sec voltage), and its
                # length is the number of columns = drains).
                # - [meas[i] for meas in ex_i] takes the i-th column of each measurement (sec voltage).
                # - The list wrapping it simply flattens it, so it is the same length as meas_prim and meas_sec.
                # In the end, we get a nested list, where each inner list corresponds to a different drain.
                print(i_to_save)

                global meas_prim, meas_sec, meas_i0, meas_ia, meas_order, meas_type
                meas_prim = np.tile(ex_v1[0], len(ex_v2))  # Convert the variable data into spreadsheet format
                meas_sec = np.repeat(ex_v2, len(ex_v1[0]))
                meas_i0 = i_to_save[-1]  # Only take the last drain!
                meas_ia = []
                run_vars = [p_prim[0], p_sec[0], p_other[0]]  # Variable names, to determine their order
                meas_order = ''.join([extract_var_letter(x) for x in run_vars])
                meas_order = 'C' + meas_order
                set_labels(meas_order)
                meas_type = 'char'  # For the "Use data from last experiment" option

                names = [f"V({stv_name2.get()})", f"V({stv_name1.get()})",
                         "I ({})".format(split('\(|\)', stv_name3.get())[1])]
                # The parameters in the order defined in add_experiment() (see the function definition).
                info = [date.today().strftime("%d/%m/%y"), stv_op.get(), stv_gas.get(), stv_conc.get(), stv_carr.get(),
                        stv_atm.get(), '', '', stv_dec.get(), stv_thick.get(), stv_temp.get(), stv_hum.get()]
                index = 0
                with open("data/central.csv", newline='') as f:  # Determine the ID of the new experiment
                    csv_reader = reader(f)
                    ids = [int(row[0]) for row in list(csv_reader)[1:]]
                if len(ids) != 0:
                    index = max(ids) + 1

                ordered_names = [trans_names[row][col] for row in range(4) for col in range(4)
                                 if active_trans[row][col]]  # The names of the active transistors only
                ordered_devs = [device_names[row] for row in range(4) for col in range(4)
                                if active_trans[row][col]]  # The corresponding device of each transistor

                for i in range(len(i_to_save)):  # For each drain
                    data_to_save = [list(x) for x in zip(meas_sec, meas_prim, i_to_save[i])]  # "Transpose" the rows
                    data_to_save = [names, *data_to_save]  # Add a row for the variable names
                    params_to_file = [index, *info, meas_order, '']
                    params_to_file[7] = ordered_devs[i]  # TODO: Check if these work!!
                    params_to_file[8] = ordered_names[i]
                    add_experiment(*params_to_file, data_to_save)
                    index += 1

        measurement_vars.incr_vars = []     # Reset the variables that are used to communicate between measurements.py
        measurement_vars.ex_vars = []       # and this file
        measurement_vars.send_sweep = []

        global drain_smus, stv_smu2, stv_smu3, stv_smu4, stv_name1, stv_name2, stv_name3, active_trans, board, pinno
        # Check that all the required entryboxes are filled in
        check_params = [stv_op.get(), stv_gas.get(), stv_conc.get(), stv_carr.get(), stv_atm.get(),
                        stv_dev.get(), stv_dec.get(), stv_thick.get(), stv_temp.get(), stv_hum.get(), stv_name1.get(),
                        stv_linlog1.get(), stv_start1.get(), stv_stop1.get(), stv_step1.get(), stv_n1.get(),
                        stv_comp1.get(), stv_name2.get(), stv_start2.get(), stv_stop2.get(), stv_step2.get(),
                        stv_n2.get(), stv_comp2.get(), stv_const.get(), stv_const_comp.get(), stv_hold.get(),
                        stv_delay.get()]
        for i in check_params:
            if i == '':
                messagebox.showerror('', "Please fill out all the parameters (including the info on the left)!")
                # Now set the focus on the entrybox that needs to be filled in.
                for f in tab_sweep.winfo_children():  # Find all entry widgets in the tab
                    for w in f.winfo_children():
                        if w.winfo_class() == "TEntry":
                            if w.get() == '':  # Focus on it if it's blank
                                w.focus()
                                return
                return  # Juuust in case.
        for i in [*check_params[12:17], *check_params[18:]]:
            # These are the parameters that must be numeric: start1, stop1, step1, n1, comp1, start2, stop2, step2,
            # n2, comp2, const, const comp, hold, delay.
            try:
                suffix(i)
            except ValueError:
                messagebox.showerror('', "The following parameters must be numeric: Start, Stop, Step, No. of steps, "
                                         "Compliance, Constant variable value.")
                return
        if not any([any(x) for x in active_trans]):  # Check that at least one SMU is selected.
            messagebox.showerror('', "Please select at least one SMU.")
            return
        try:  # Make sure the SMUs are properly detected.
            smu_name_list = [*[x for x in drain_smus], stv_smu2.get(), stv_smu3.get(), stv_smu4.get()]
            if len(smu_name_list) > len(set(smu_name_list)):    # This means the SMUs aren't unique (at least one is
                                                                # selected twice!)
                messagebox.showerror('', "Please make sure all the SMUs (in the 'Channels' tab) are different!")
                return
        except Exception as e:
            messagebox.showerror('', "Something's wrong with the SMUs (\"" + e + "\").")
            tb = traceback.format_exc()
            logging.error(str(e) + ". Traceback: " + str(tb))
        try:  # TODO: Redundant?!?!?! Why did I do it this way?
            global param_list
            # Gather and arrange the variables required for the measurement
            p_prim = [stv_name1.get(), *[suffix(x) for x in [stv_start1.get(), stv_stop1.get(), stv_step1.get(),
                                                             stv_n1.get(), stv_comp1.get()]]]
            p_sec = [stv_name2.get(), *[suffix(x) for x in [stv_start2.get(), stv_stop2.get(), stv_step2.get(),
                                                            stv_n2.get(), stv_comp2.get()]]]
            p_other = [split('\(|\)', stv_name3.get())[1], suffix(stv_const.get()), suffix(stv_const_comp.get()),
                       suffix(stv_hold.get()), suffix(stv_delay.get()), param_list]
            p_smus = [drain_smus, stv_smu2.get(), stv_smu3.get(), stv_smu4.get()]
            if p_prim[0] == '' or p_sec[0] == '':
                messagebox.showerror('', "Both variable names must be filled in.")
                return
        except ValueError:  # If any of the suffix() calls fail
            messagebox.showerror('', "The following parameters must be numeric: Start, Stop, Step, No. of steps, "
                                     "Compliance, Constant variable value.")
            return

        window_load, fig, lbl_progress, chk_linlog, stv_ex_linlog, chk_currents, btn_ex_end, btn_ex_abort, prb, ax, ax2,\
        ax3, ax4, bar = open_measurement_window(p_prim, stv_linlog1)  # Open the measurement window, return the objects
                                                                      # that will be dynamically changed
        ax.set_ylabel("I ({})".format(param_list[0]))
        ax2.set_ylabel("I ({})".format(param_list[1]))
        ax3.set_ylabel("I ({})".format(param_list[2]))
        ax4.set_ylabel("I (Source)")
        # If the source SMU wasn't set, hide the axis (and don't add its sweeps)
        show_src = stv_smu4.get() == "(None)"
        ax4.set_visible(show_src)
        bar.draw()

        # Set the drain colors based on the number of active drains
        global drain_colors, color_d1, color_d2
        num_drains = len([x for row in active_trans for x in row if x])  # The number of active drains
        drain_colors.clear()
        color_diff = [y-x for x,y in zip(color_d1, color_d2)]
        for i in range(num_drains):
            drain_colors[i] = tuple([color_d1[j]+color_diff[j]*i/(num_drains-1) for j in range(3)])

        # Bind the commands to the checkboxes and buttons
        chk_linlog["command"] = linlog
        chk_currents["command"] = additional_currents
        btn_ex_abort["command"] = lambda: finish_sweep(True)
        btn_ex_end["command"] = finish_sweep  # .bind() doesn't work, because it still works when the button is disabled
        # Bind the events for communication with measurements.py
        window_load.bind("<<prb-increment>>", increment)
        window_load.bind("<<add-sweep>>", add_sweep)

        measurement_vars.ex_finished = False
        global b1500
        # Start the measurement in a thread, so the window can update in real time
        th = threading.Thread(target=sweep, args=(b1500, [p_prim, p_sec, p_other, p_smus, active_trans],
                                                  window_load, show_src, board, pinno), daemon=True)
        th.start()

    def run_exposure():
        """
        Runs an exposure measurement: A characteristic, then either a transient or a periodic sweep, and then another
        characteristic. The idea is that the gas flow starts during the second measurements, and the characteristics
        represent the I-V curves when the device is fully exposed or not exposed at all.
        Transient = The current of the constant variable as a function of time (though all four currents are saved).
        Periodic sweep = An I-V sweep, at a fixed value of the secondary variable, at set time intervals.
        """
        def start_exposure():
            """
            This is for the measurement itself. Everything outside start_exposure() but inside run_exposure() (bad name
            choice, I know) has to do with the window that opens beforehand.
            """
            def increment(evt):
                """
                Increments the progressbar and updates the progress label.
                The progress label's text depends on the measurement type (see inc_type).
                :param: val: The portion of the progressbar that should be full (between 0 and 1).
                :param: v: The value (voltage) of the secondary variable in the current sweep.
                :param: after: Whether the progress update is right before or right after performing a sweep, just for the
                                progress label.
                :param: inc_type: Whether the current measurement is a sweep (either a characteristic or a periodic
                sweep), or a transient measurement.
                """
                global inc_type
                if inc_type == 'sweep':
                    val, v, devid = tuple(measurement_vars.incr_vars)  # TODO: Remove v?
                    if devid == 4:
                        lbl_progress["text"] = "Initializing..."
                    elif devid == 5:
                        lbl_progress["text"] = f"Measurement complete."
                    else:
                        lbl_progress["text"] = f"Measuring ({device_names[devid]})..."
                    prb["value"] = val * 100
                    if val == 1:
                        btn_ex_end["state"] = tk.NORMAL
                elif inc_type == 'transient':
                    val = measurement_vars.incr_vars
                    prb["value"] = val * 100
                    lbl_progress["text"] = "Measuring..."
                    if val == 1:
                        btn_ex_end["state"] = tk.NORMAL
                        lbl_progress["text"] = "Measurement complete. "

            def add_sweep(evt):
                """
                Adds a sweep to the plot.
                :param: v1: The primary variable of the sweep. (list)
                :param: v2: The secondary variable value of the sweep that is being added (voltage or time).
                            Currently unused. (float)
                :param: i: The currents measured from the sweep. (list of 3-19 lists)
                """
                global drain_colors, color_g1, color_g2, color_src
                v1, v2, i = tuple(measurement_vars.send_sweep)
                secondary_col = -3 if show_src else -2
                y1 = i[:secondary_col]  # Only the drains
                y2 = i[secondary_col]
                y3 = i[secondary_col + 1]
                if show_src:
                    y4 = i[-1]

                for n, y in enumerate(y1):
                    ax.plot(v1, y, color=drain_colors[n])
                ax2.plot(v1, y2, color_g1)
                ax3.plot(v1, y3, color_g2)
                if show_src:
                    ax4.plot(v1, y4, color_src)
                bar.draw()

            def add_spot(evt):
                """
                Adds a spot measurement to the graph, for each of the four currents. (used in transient experiments)
                Note that the "parameters" represent the entire experiment, not just the new spot measurement.
                :param: x: The time measurements.
                :param: y1-y4: The four currents. y1 is the drain current, y2 and y3 are the gate currents, and y4 is
                the source current.
                """
                global drain_colors, color_g1, color_g2, color_src
                data = measurement_vars.send_transient
                x = data[0]
                secondary_col = -3 if show_src else -2  # To take the last 3 columns if the source SMU is active,
                # or 2 otherwise.
                y1s = data[1:secondary_col]
                y2 = data[secondary_col]
                y3 = data[secondary_col + 1]
                if show_src:
                    y4 = data[-1]
                s = ax.get_yscale()  # To reset it to the same value after the axis is cleared
                ax.clear()
                ax2.clear()
                ax3.clear()
                ax4.clear()
                for i, y in enumerate(y1s):
                    ax.plot(x, y, color=drain_colors[i])
                ax2.plot(x, y2, color_g1)
                ax3.plot(x, y3, color_g2)
                if show_src:
                    ax4.plot(x, y4, color_src)
                ax.set_yscale(s)
                ax2.set_yscale(s)
                ax3.set_yscale(s)
                ax4.set_yscale(s)
                if chk_currents.instate(['selected']):  # Re-resize the plot and reposition the right axes
                    # fig.subplots_adjust(right=0.65)
                    ax3.spines.right.set_position(("axes", 1.2))
                    ax4.spines.right.set_position(("axes", 1.4))
                    ax3.get_yaxis().get_offset_text().set_position((1.2, 5.0))
                    ax4.get_yaxis().get_offset_text().set_position((1.4, 5.0))
                ax.set_ylabel("I ({})".format(param_list[0]))
                ax2.set_ylabel("I ({})".format(param_list[1]))
                ax3.set_ylabel("I ({})".format(param_list[2]))
                ax4.set_ylabel("I (Source)")
                ax.set_xlabel("t (sec)")
                bar.draw()

            def linlog():
                """
                Updates the graph based on the state of the linear/logarithmic chechbox.
                """
                if chk_linlog.instate(['selected']):
                    ax.set_yscale('log')
                    ax2.set_yscale('log')
                    ax3.set_yscale('log')
                    ax4.set_yscale('log')
                else:
                    ax.set_yscale('linear')
                    ax2.set_yscale('linear')
                    ax3.set_yscale('linear')
                    ax4.set_yscale('linear')
                bar.draw()

            def additional_currents():
                """
                Shows/hides the three additional currents (jg, bg, s).
                """
                if chk_currents.instate(['selected']):
                    ax2.set_visible(True)
                    ax3.set_visible(True)
                    ax3.spines.right.set_position(("axes", 1.2))
                    ax3.get_yaxis().get_offset_text().set_position((1.2, 5.0))
                    if show_src:
                        ax4.set_visible(True)
                        ax4.spines.right.set_position(("axes", 1.4))
                        ax4.get_yaxis().get_offset_text().set_position((1.4, 5.0))
                        fig.subplots_adjust(right=0.65)
                    else:
                        fig.subplots_adjust(right=0.75)
                else:
                    ax2.set_visible(False)
                    ax3.set_visible(False)
                    ax4.set_visible(False)
                    fig.subplots_adjust(right=0.9)
                bar.draw()

            def finish_first(aborted=False):
                """
                Clear the plot, temporarily store the experiment results, set up the next measurement and start it.
                :param: ex_v1: The primary variable. (list)
                :param: ex_v2: The secondary variable. (list)
                :param: ex_i: The measured current (for the CONSTANT variable!). (list of lists, with a size
                                of len(ex_v2) x len(ex_v1))
                :param: aborted: True if called via the "Abort" button. In this case, the window should close and the
                results should be saved as a characteristic.
                """
                if len(measurement_vars.ex_vars) == 3:  # To avoid unpacking an empty list after aborting
                    ex_v1, ex_v2, ex_i = tuple(measurement_vars.ex_vars)
                    i_to_save = [[x for row in [meas[i] for meas in ex_i] for x in row] for i in range(len(ex_i[0]))]
                    # See explanation in run_characteristic -> finish_sweep
                    global meas_prim, meas_sec, meas_i0, meas_ia, meas_order, exp_drains
                    # exp_drains is only used here - to save all of the drain currents temporarily, in order to
                    # permanently save them in finish_third.
                    meas_prim = np.tile(ex_v1[0], len(ex_v2))
                    meas_sec = np.repeat(ex_v2, len(ex_v1[0]))
                    meas_i0 = i_to_save[-1]  # Only take the last drain!
                    exp_drains = [x for x in i_to_save]
                    if aborted:  # Let close() close the window, after the experiment has ended.
                        lbl_progress["text"] = "Closing (once the sweep is done)... "
                        window_load.title("Closing...")
                        if measurement_vars.ex_finished:  # If the measurement has already finished
                            window_load.grab_release()
                            window_load.destroy()
                            measurement_vars.stop_ex = False  # Just in case
                            measurement_vars.ex_finished = False
                        else:  # The current sweep must be allowed to finish
                            measurement_vars.abort_ex = True
                            measurement_vars.stop_ex = True
                        meas_ia = []
                        # For the record, the following snipped is copied from run_characteristic():
                        run_vars = [p_prim[0], p_sec[0], p_other[0]]  # Variable names, to determine their order
                        meas_order = ''.join([extract_var_letter(x) for x in run_vars])
                        meas_order = 'C' + meas_order
                        set_labels(meas_order)
                        global meas_type
                        meas_type = 'char'  # For the "Use data from last experiment" option
                        names = [f"V({stv_name2.get()})", f"V({stv_name1.get()})",
                                 "I ({})".format(split('\(|\)', stv_name3.get())[1])]
                        # The parameters in the order defined in add_experiment() (see the function definition).
                        temp_info = [s.get() for s in [stv_op, stv_gas, stv_conc, stv_carr, stv_atm, stv_dec,
                                                       stv_thick, stv_temp, stv_hum]]
                        # Because check_params was changed, so we can't use it in the next line
                        info = [date.today().strftime("%d/%m/%y"), *temp_info[:5], '', '', *temp_info[5:]]
                        index = 0
                        with open("data/central.csv", newline='') as f:  # Determine the ID of the new experiment
                            csv_reader = reader(f)
                            ids = [int(row[0]) for row in list(csv_reader)[1:]]
                        if len(ids) != 0:
                            index = max(ids) + 1

                        ordered_names = [trans_names[row][col] for row in range(4) for col in range(4)
                                         if active_trans[row][col]]  # The names of the active transistors only
                        ordered_devs = [device_names[row] for row in range(4) for col in range(4)
                                        if active_trans[row][col]]  # The corresponding device of each transistor

                        for i in range(len(i_to_save)):
                            data_to_save = [list(x) for x in zip(meas_sec, meas_prim, i_to_save[i])]  # "Transpose"
                            data_to_save = [names, *data_to_save]  # Add a row for the variable names
                            params_to_file = [index, *info, meas_order, '']  # Add the experiment
                            params_to_file[7] = ordered_devs[i]  # TODO: Check if these work!!
                            params_to_file[8] = ordered_names[i]
                            add_experiment(*params_to_file, data_to_save)
                            index += 1

                    else:  # Save the data temporarily, and proceed to the next experiment.
                        # The experiment will only be saved once "ia" is obtained.
                        # Clear the plot, re-resize it and reposition the right axes
                        ax.clear()
                        ax2.clear()
                        ax3.clear()
                        ax4.clear()
                        if chk_currents.instate(['selected']):
                            ax3.spines.right.set_position(("axes", 1.2))
                            ax4.spines.right.set_position(("axes", 1.4))
                            ax3.get_yaxis().get_offset_text().set_position((1.2, 5.0))
                            ax4.get_yaxis().get_offset_text().set_position((1.4, 5.0))
                        ax.set_ylabel("I ({})".format(param_list[0]))
                        ax2.set_ylabel("I ({})".format(param_list[1]))
                        ax3.set_ylabel("I ({})".format(param_list[2]))
                        ax4.set_ylabel("I (Source)")
                        bar.draw()

                        prb["value"] = 0  # Reset the progressbar
                        if inv_ex_type.get() == 0:  # If the second measurement is transient, set inc_type so that increment()
                            global inc_type         # can handle the progressbar accordingly. TODO: No longer necessary?
                            inc_type = 'transient'
                            ax.set_xlabel("t (sec)")  # Also change the x-axis label.
                        else:
                            ax.set_xlabel("V({}) (V)".format(p_prim[0]))  # If it's a periodic sweep, the label should stay the same.

                        measurement_vars.incr_vars = []     # Reset the variables that are used to communicate between
                        measurement_vars.ex_vars = []       # measurements.py and this file
                        measurement_vars.send_sweep = []
                        measurement_vars.send_transient = []
                        measurement_vars.ex_finished = False

                        global b1500, stv_s_timegroup
                        # Start the appropriate measurement
                        if inv_ex_type.get() == 0:
                            if inv_ex_limit.get() == 1:
                                limit_time = True
                            else:
                                limit_time = False
                            th2 = threading.Thread(target=transient,
                                                   args=(b1500, [param_list, p_voltages, p_comps, p_time_params, p_smus,
                                                                 active_trans], window_load, limit_time,
                                                     int(stv_s_timegroup.get()), show_src, board, pinno), daemon=True)
                        else:
                            th2 = threading.Thread(target=transient_sweep, args=(b1500, [p_prim, [stv_name2.get(),
                                                      suffix(stv_ex_sweepvar.get()), suffix(stv_ex_s_comp.get()),
                                                      suffix(stv_ex_s_n.get()), suffix(stv_ex_s_between.get())],
                                                      p_other, p_smus, active_trans], window_load, show_src, board,
                                                      pinno), daemon=True)
                        btn_ex_end["state"] = tk.DISABLED  # Disable the finish button!
                        linlog()  # Just in case...?
                        btn_ex_abort["command"] = lambda: finish_second(True)
                        btn_ex_end["command"] = finish_second  # Can't use bind() or else it'll be clickable while disabled
                        th2.start()

            def finish_second(aborted=False):
                """
                Clear the plot, save this experiment's results, and set up the second sweep of the exposure experiment.
                :param: measurement_vars.ex_vars:
                - If the measurement is transient: The time and currents of each spot measurement. (list of lists of
                length 4-20).
                - If it's a periodic sweep: [ex_v1, ex_v2, ex_i] as defined in finish_first().
                :param: aborted: True if called via the "Abort" button. In this case, the window should close, the
                results of the first measurement should be saved as a characteristic, and the second measurement should
                then be saved as a transient/periodic sweep.
                """
                global meas_prim, meas_sec, meas_i0, meas_ia, meas_order, meas_type, exp_drains
                info = [date.today().strftime("%d/%m/%y"), stv_op.get(), stv_gas.get(), stv_conc.get(), stv_carr.get(),
                        stv_atm.get(), '', '', stv_dec.get(), stv_thick.get(), stv_temp.get(), stv_hum.get()]
                # As defined in add_experiment().

                if aborted:  # Let close() close the window, after the experiment has ended.
                    lbl_progress["text"] = "Closing (once the sweep is done)... "
                    window_load.title("Closing...")
                    if measurement_vars.ex_finished:  # If the measurement has already finished
                        window_load.grab_release()
                        window_load.destroy()
                        measurement_vars.stop_ex = False  # Just in case
                        measurement_vars.ex_finished = False
                    else:  # The current sweep must be allowed to finish
                        measurement_vars.abort_ex = True
                        measurement_vars.stop_ex = True

                    # Save the first measurement
                    meas_ia = []
                    # For the record, the following snipped is copied from run_characteristic():
                    run_vars = [p_prim[0], p_sec[0], p_other[0]]  # Variable names, to determine their order
                    meas_order = ''.join([extract_var_letter(x) for x in run_vars])
                    meas_order = 'C' + meas_order
                    set_labels(meas_order)
                    global meas_type
                    meas_type = 'char'  # For the "Use data from last experiment" option
                    names = [f"V({stv_name2.get()})", f"V({stv_name1.get()})",
                             "I ({})".format(split('\(|\)', stv_name3.get())[1])]
                    index = 0
                    with open("data/central.csv", newline='') as f:  # Determine the ID of the new experiment
                        csv_reader = reader(f)
                        ids = [int(row[0]) for row in list(csv_reader)[1:]]
                    if len(ids) != 0:
                        index = max(ids) + 1

                    ordered_names = [trans_names[row][col] for row in range(4) for col in range(4)
                                     if active_trans[row][col]]  # The names of the active transistors only
                    ordered_devs = [device_names[row] for row in range(4) for col in range(4)
                                    if active_trans[row][col]]  # The corresponding device of each transistor

                    for i in range(len(exp_drains)):
                        data_to_save = [list(x) for x in zip(meas_sec, meas_prim, exp_drains[i])]  # "Transpose"
                        data_to_save = [names, *data_to_save]  # Add a row for the variable names
                        params_to_file = [index, *info, meas_order, '']  # Add the experiment
                        params_to_file[7] = ordered_devs[i]  # TODO: Check if these work!!
                        params_to_file[8] = ordered_names[i]
                        add_experiment(*params_to_file, data_to_save)
                        index += 1

                # Handle the second measurement
                secondary_col = -3 if show_src else -2  # Take the last drain +3 columns if the source SMU is active, or
                # 2 columns otherwise.
                index = 0
                with open("data/central.csv", newline='') as f:  # Find the last index and set the new one
                    csv_reader = reader(f)
                    ids = [int(row[0]) for row in list(csv_reader)[1:]]
                if len(ids) != 0:
                    index = max(ids) + 1
                ordered_names = [trans_names[row][col] for row in range(4) for col in range(4)
                                 if active_trans[row][col]]  # The names of the active transistors only
                ordered_devs = [device_names[row] for row in range(4) for col in range(4)
                                if active_trans[row][col]]  # The corresponding device of each transistor

                if len(measurement_vars.ex_vars) != 0:
                    if inv_ex_type.get() == 0:  # Transient
                        data_to_save = measurement_vars.ex_vars  # Rows of length (num_drains+4)
                        data_to_analyze = [list(x) for x in zip(*data_to_save)]  # (num_drains+4) columns
                        data_to_analyze = [data_to_analyze[0],
                                           *data_to_analyze[secondary_col - 1:]]  # 4/5 columns (uses the LAST drain)
                        # data_to_save = [names, *data_to_save]
                        meas_order = 'T' + extract_var_letter(p_time_params[0])     # The second letter is the primary
                                                                                    # variable of the sweep
                        set_labels(meas_order)
                        meas_prim = data_to_analyze[0]
                        meas_i0 = data_to_analyze[1]  # TODO: Is this correct?
                        for i in range(1,
                                       len(data_to_save[0]) + secondary_col):  # Save each of the experiments separately
                            sliced = [[row[0], row[i], *row[secondary_col:]] for row in data_to_save]
                            sliced = [names, *sliced]
                            params_to_file = [index, *info, meas_order, '']
                            params_to_file[7] = ordered_devs[i]  # TODO: Check if these work!!
                            params_to_file[8] = ordered_names[i]
                            add_experiment(*params_to_file, sliced)
                            index += 1

                    elif inv_ex_type.get() == 1:  # Periodic sweep
                        # meas_type = 'char'
                        names = ['t', stv_name1.get(), 'I']
                        ex_v1, ex_v2, ex_i = tuple(measurement_vars.ex_vars)
                        i_to_save = [[x for row in [meas[i] for meas in ex_i] for x in row] for i in
                                     range(len(ex_i[0]))]
                        temp_prim = np.tile(ex_v1[0], len(ex_v2))  # Convert the sweep voltages into spreadsheet format
                        temp_sec = np.repeat(ex_v2, len(ex_v1[0]))
                        run_vars = [p_prim[0], p_sec[0], p_other[0]]
                        meas_order = ''.join([extract_var_letter(x) for x in run_vars])  # Get the abbreviation
                        meas_order = 'T' + meas_order  # Add 'T' to denote that it's a periodic sweep
                        set_labels(meas_order)

                        for i in range(len(i_to_save)):  # For each drain
                            data_to_save = [list(x) for x in
                                            zip(temp_sec, temp_prim, i_to_save[i])]  # "Transpose" the rows
                            data_to_save = [names, *data_to_save]  # Add a row for the variable names
                            params_to_file = [index, *info, meas_order, '']
                            params_to_file[7] = ordered_devs[i]  # TODO: Check if these work!!
                            params_to_file[8] = ordered_names[i]
                            add_experiment(*params_to_file, data_to_save)
                            index += 1

                if not aborted:
                    # Reset the graph
                    ax.clear()
                    ax2.clear()
                    ax3.clear()
                    ax4.clear()
                    if chk_currents.instate(['selected']):  # Re-resize the graph area and reposition the right axes
                        ax3.spines.right.set_position(("axes", 1.2))
                        ax4.spines.right.set_position(("axes", 1.4))
                        ax3.get_yaxis().get_offset_text().set_position((1.2, 5.0))
                        ax4.get_yaxis().get_offset_text().set_position((1.4, 5.0))
                    ax.set_ylabel("I ({})".format(param_list[0]))
                    ax2.set_ylabel("I ({})".format(param_list[1]))
                    ax3.set_ylabel("I ({})".format(param_list[2]))
                    ax4.set_ylabel("I (Source)")
                    ax.set_xlabel("V({}) (V)".format(p_prim[0]))
                    bar.draw()
                    for a in [ax, ax2, ax3, ax4]:  # Since the next measurement is a characteristic, we can set the xlims
                        a.set_xlim(p_prim[1], p_prim[2])    # in advance.
                    prb["value"] = 0  # Reset the progressbar
                    global inc_type
                    inc_type = 'sweep'
                    measurement_vars.incr_vars = []     # Reset the variables that are used to communicate between
                    measurement_vars.ex_vars = []       # measurements.py and this file
                    measurement_vars.send_sweep = []
                    measurement_vars.send_transient = []
                    measurement_vars.ex_finished = False
                    # Set up and start the third measurement
                    th3 = threading.Thread(target=sweep, args=(b1500, [p_prim, p_sec, p_other, p_smus, active_trans],
                                                          window_load, show_src, board, pinno), daemon=True)
                    btn_ex_end["text"] = "Finish"
                    btn_ex_end["state"] = tk.DISABLED  # Disable the finish button
                    linlog()
                    btn_ex_abort["command"] = lambda: finish_third(True)
                    btn_ex_end["command"] = finish_third
                    th3.start()

            def finish_third(aborted=False):
                """
                Save the results of the exposure experiment (both sweeps of the exposure experiment), and close the
                window.
                :param: ex_v1, ex_v2, ex_i: As defined in finish_first().
                :param: aborted: True if called via the "Abort" button. In this case, the behavior should be the same
                as in run_characteristic().
                """
                if aborted:  # Let close() close the window, after the experiment has ended.
                    lbl_progress["text"] = "Closing (once the sweep is done)... "
                    window_load.title("Closing...")
                    if measurement_vars.ex_finished:  # If the measurement has already finished
                        window_load.grab_release()
                        window_load.destroy()
                        measurement_vars.stop_ex = False  # Just in case
                        measurement_vars.ex_finished = False
                    else:  # The current sweep must be allowed to finish
                        measurement_vars.abort_ex = True
                        measurement_vars.stop_ex = True
                else:  # If called from the "Finish" button, the window can close normally.
                    window_load.grab_release()
                    window_load.destroy()
                # # Reset these variables, just in case
                # measurement_vars.stop_ex = False
                # measurement_vars.ex_finished = False
                if len(measurement_vars.ex_vars) == 3:  # To avoid unpacking an empty list after aborting
                    ex_v1, ex_v2, ex_i = tuple(measurement_vars.ex_vars)  # Extract the measurement data
                    i_to_save = [[x for row in [meas[i] for meas in ex_i] for x in row] for i in range(len(ex_i[0]))]
                    global meas_prim, meas_sec, meas_i0, meas_ia, meas_order, exp_drains
                    meas_prim = np.tile(ex_v1[0], len(ex_v2))  # Convert the variable data into spreadsheet format
                    meas_sec = np.repeat(ex_v2, len(ex_v1[0]))
                    meas_i0 = exp_drains[-1]  # Only take the last drain!
                    meas_ia = i_to_save[-1]
                    run_vars = [p_prim[0], p_sec[0], p_other[0]]
                    meas_order = ''.join(
                        [extract_var_letter(x) for x in run_vars])  # Get the abbreviation
                    set_labels(meas_order)
                    global meas_type
                    meas_type = 'exposure'
                    names = [f"V({stv_name2.get()})", f"V({stv_name1.get()})", stv_ex_i0.get(), stv_ex_ia.get()]
                    info = [date.today().strftime("%d/%m/%y"), stv_op.get(), stv_gas.get(), stv_conc.get(), stv_carr.get(),
                            stv_atm.get(), '', '', stv_dec.get(), stv_thick.get(), stv_temp.get(), stv_hum.get()]
                    # As defined in add_experiment().
                    index = 0
                    with open("data/central.csv", newline='') as f:  # Find the last index and set the new one
                        csv_reader = reader(f)
                        ids = [int(row[0]) for row in list(csv_reader)[1:]]
                    if len(ids) != 0:
                        index = max(ids) + 1

                    ordered_names = [trans_names[row][col] for row in range(4) for col in range(4)
                                     if active_trans[row][col]]  # The names of the active transistors only
                    ordered_devs = [device_names[row] for row in range(4) for col in range(4)
                                    if active_trans[row][col]]  # The corresponding device of each transistor

                    for i in range(len(i_to_save)):  # For each drain
                        data_to_save = [list(x) for x in zip(meas_sec, meas_prim,
                                                             exp_drains[i][:len(meas_ia)], i_to_save[i])]
                        # Transpose the rows. If it was aborted, meas_ia is shorter than meas_i0, so take only part
                        # of it. TODO: Is this correct?!
                        data_to_save = [names, *data_to_save]  # Add a row for the variable names
                        params_to_file = [index, *info, meas_order, '']
                        params_to_file[7] = ordered_devs[i]  # TODO: Check if these work!!
                        params_to_file[8] = ordered_names[i]
                        add_experiment(*params_to_file, data_to_save)
                        index += 1

            # The main function starts here (runs when the user clicks "Start")
            measurement_vars.incr_vars = []     # Reset the variables that are used to communicate between
            measurement_vars.ex_vars = []       # measurements.py and this file
            measurement_vars.send_sweep = []
            measurement_vars.send_transient = []

            global stv_s_timegroup, drain_smus, stv_smu2, stv_smu3, stv_smu4, stv_name1, stv_name2, stv_name3, \
                active_trans, board, pinno
            # Determine which entryboxes are required and check that they're all filled in
            if inv_ex_type.get() == 0:  # Transient
                check_params = [s.get() for s in [stv_ex_i0, stv_ex_ia, *stvs_ex_tvars, *stvs_ex_tcomps,
                                                  stv_ex_interval, stv_ex_n, stv_ex_tot, stv_ex_hold, stv_s_timegroup]]
            else:  # Periodic sweep
                check_params = [s.get() for s in [stv_ex_i0, stv_ex_ia, stv_ex_sweepvar, stv_ex_s_comp, stv_ex_s_between]]
            for i in check_params:
                if i == '':
                    messagebox.showerror('', "Please fill out all the parameters for the selected type of experiment.")
                    # Now set the focus on the entrybox that needs to be filled in.
                    for f in window_exp.winfo_children():  # Find all entry widgets in the tab
                        for w in f.winfo_children():
                            if w.winfo_class() == "TEntry":
                                if w.get() == '':  # Focus on it if it's blank
                                    w.focus()
                                    return
                    return  # Juuust in case.
            for i in check_params[2:]:  # Everything except the names of the currents (and the sampling
                try:                                # parameter)
                    suffix(i)  # Check if they're numeric
                except ValueError:
                    messagebox.showerror('', "Please make sure all the values (besides the current names) are numeric.")
                    return
            if not any([any(x) for x in active_trans]):  # Check that at least one SMU is selected.
                messagebox.showerror('', "Please select at least one SMU.")
                return
            try:  # Make sure the SMUs are properly detected.
                smu_name_list = [*[x for x in drain_smus], stv_smu2.get(), stv_smu3.get(), stv_smu4.get()]
                if len(smu_name_list) > len(set(smu_name_list)):  # This means the SMUs aren't unique (at least one is
                    # selected twice!)
                    messagebox.showerror('', "Please make sure all the SMUs (in the 'Channels' tab) are different!")
                    return
            except Exception as e:
                messagebox.showerror('', "Something's wrong with the SMUs (\"" + e + "\").")
                tb = traceback.format_exc()
                logging.error(str(e) + ". Traceback: " + str(tb))
            # Gather and arrange the variables required for the measurement
            p_prim = [stv_name1.get(), *[suffix(x) for x in [stv_start1.get(), stv_stop1.get(), stv_step1.get(),
                                                             stv_n1.get(), stv_comp1.get()]]]
            p_sec = [stv_name2.get(), *[suffix(x) for x in [stv_start2.get(), stv_stop2.get(), stv_step2.get(),
                                                            stv_n2.get(), stv_comp2.get()]]]
            p_other = [split('\(|\)', stv_name3.get())[1], suffix(stv_const.get()), suffix(stv_const_comp.get()),
                       suffix(stv_hold.get()), suffix(stv_delay.get()), param_list]
            if inv_ex_type.get() == 0:  # These values are only relevant for transient measurements
                p_voltages = [suffix(s.get()) for s in stvs_ex_tvars]
                p_comps = [suffix(s.get()) for s in stvs_ex_tcomps]
                p_time_params = [params[0], *[suffix(s.get()) for s in [stv_ex_interval, stv_ex_n, stv_ex_tot,
                                                                        stv_ex_hold]]]  # TODO: Change the name after implementing the dropmenu
            p_smus = [drain_smus, stv_smu2.get(), stv_smu3.get(), stv_smu4.get()]
            # ordered_params = [stv_ex_sample.get(), *[x for x in param_list if not x == stv_ex_sample.get()]]
            # param_list, but the sampling parameter is first. To be used when determining the axis titles and file
            # headers. TODO: Is the order right?
            global inc_type
            inc_type = 'sweep'

            window_exp.destroy()

            window_load, fig, lbl_progress, chk_linlog, stv_ex_linlog, chk_currents, btn_ex_end, btn_ex_abort, prb, ax,\
            ax2, ax3, ax4, bar = open_measurement_window(p_prim, stv_linlog1)  # Open the measurement window, return the
                                                                            # objects that will be dynamically changed
            # Bind the commands to the checkboxes and buttons
            chk_linlog["command"] = linlog
            chk_currents["command"] = additional_currents
            btn_ex_end["text"] = "Proceed"
            btn_ex_abort["command"] = lambda: finish_first(True)
            btn_ex_end["command"] = finish_first
            # Bind the events for communication with measurements.py
            window_load.bind("<<prb-increment>>", increment)
            window_load.bind("<<add-sweep>>", add_sweep)
            window_load.bind("<<add-spot>>", add_spot)
            ax.set_ylabel("I ({})".format(param_list[0]))
            ax2.set_ylabel("I ({})".format(param_list[1]))
            ax3.set_ylabel("I ({})".format(param_list[2]))
            ax4.set_ylabel("I (Source)")
            ax.set_xlabel("V({}) (V)".format(p_prim[0]))
            show_src = stv_smu4.get() == "(None)"
            ax4.set_visible(show_src)
            bar.draw()

            # Set the drain colors based on the number of active drains
            global drain_colors, color_d1, color_d2
            num_drains = len([x for row in active_trans for x in row if x])  # The number of active drains
            drain_colors.clear()
            color_diff = [y - x for x, y in zip(color_d1, color_d2)]
            for i in range(num_drains):
                drain_colors[i] = tuple([color_d1[j] + color_diff[j] * i / (num_drains - 1) for j in range(3)])

            measurement_vars.ex_finished = False
            global b1500
            # Start the first measurement in a thread, so the window can update in real time
            th = threading.Thread(target=sweep, args=(b1500, [p_prim, p_sec, p_other, p_smus, active_trans],
                                                      window_load, show_src, board, pinno), daemon=True)
            th.start()

        # The following functions have to do with the setup window:
        def enable_ex_ents(ex_type):
            """
            Enable or disable the entryboxes and optionmenus when a radiobutton is selected.
            :param ex_type: 't' if the transient measurement radiobutton was selected, 's' if the periodic sweep
            radiobutton was selected.
            """
            if ex_type == 't':  # Define state_t for the transient-related objects, and state_s for the
                                # periodic-sweep-related objects. That way we don't need two nearly-identical
                                # large blocks of code.
                state_t = tk.NORMAL
                state_s = tk.DISABLED
            else:
                state_t = tk.DISABLED
                state_s = tk.NORMAL
            for i in range(3):  # Values and compliances of the transient variables
                ents_ex_tvars[i]["state"] = state_t
                ents_ex_tcomps[i]["state"] = state_t
            # drp_ex_t_sampling["state"] = state_t
            ent_ex_t_interval["state"] = state_t
            ent_ex_t_n["state"] = state_t
            ent_ex_t_tot["state"] = state_t
            ent_ex_t_hold["state"] = state_t
            ent_ex_s_var2["state"] = state_s
            ent_ex_s_v2comp["state"] = state_s
            ent_ex_s_n["state"] = state_s
            ent_ex_s_between["state"] = state_s

        # The setup window function starts here (when the user clicks "Run exposure").
        global stv_name1, stv_name2, stv_name3
        # Check that all the required entryboxes are filled in
        check_params = [stv_op.get(), stv_gas.get(), stv_conc.get(), stv_carr.get(), stv_atm.get(),
                        stv_dev.get(), stv_dec.get(), stv_thick.get(), stv_temp.get(), stv_hum.get(), stv_name1.get(),
                        stv_linlog1.get(), stv_start1.get(), stv_stop1.get(), stv_step1.get(), stv_n1.get(),
                        stv_comp1.get(), stv_name2.get(), stv_start2.get(), stv_stop2.get(), stv_step2.get(),
                        stv_n2.get(), stv_comp2.get(), stv_const.get(), stv_const_comp.get(), stv_hold.get(),
                        stv_delay.get()]
        for i in check_params:
            if i == '':
                messagebox.showerror('', "Please fill out all the parameters (including the info on the left)!")
                # Now set the focus on the entrybox that needs to be filled in.
                for f in tab_sweep.winfo_children():  # Find all entry widgets in the tab
                    for w in f.winfo_children():
                        if w.winfo_class() == "TEntry":
                            if w.get() == '':  # Focus on it if it's blank
                                w.focus()
                                return
                return  # Juuust in case.
        for i in [*check_params[12:17], *check_params[18:]]:
            # These are the parameters that must be numeric: start1, stop1, step1, n1, comp1, start2, stop2, step2,
            # n2, comp2, const, const comp, hold, delay.
            try:
                suffix(i)
            except ValueError:
                messagebox.showerror('', "The following parameters must be numeric: Start, Stop, Step, No. of steps, "
                                         "Compliance, Constant variable value.")
                return
        window_exp = tk.Toplevel(window)  # Open the setup window. TODO: Set geometry ('WxH+0+0')
        window_exp.title("Start Exposure Experiment")
        window_exp.rowconfigure(0, minsize=50)
        window_exp.rowconfigure(1, weight=1)
        window_exp.columnconfigure([0, 1], weight=1)
        frm_ex_names = ttk.Frame(window_exp, relief=tk.FLAT, borderwidth=2)
        frm_ex_names.grid(row=0, column=0, columnspan=2, sticky="nsew")
        frm_ex_transient = ttk.Frame(window_exp, relief=tk.SUNKEN, borderwidth=2)
        frm_ex_transient.grid(row=1, column=0, sticky="nsew")
        frm_ex_sweep = ttk.Frame(window_exp, relief=tk.SUNKEN, borderwidth=2)
        frm_ex_sweep.grid(row=1, column=1, sticky="nsew")
        inv_ex_type = tk.IntVar(value=0)  # 0 = transient, 1 = sweep

        params = [stv_name1.get(), stv_name2.get(), split('\(|\)', stv_name3.get())[1]]  # The variable names, ordered
        # by their "role" - Primary, secondary, constant.

        frm_ex_names.rowconfigure(0, weight=1)  # Contains the two current names and the "Run" button.
        frm_ex_names.columnconfigure([*range(5)], weight=1)
        stv_ex_i0, stv_ex_ia = tk.StringVar(), tk.StringVar()
        ttk.Label(frm_ex_names, text="Initial current name: ").grid(row=0, column=0, sticky="e", padx=10)
        ent_ex_i0 = ttk.Entry(frm_ex_names, textvariable=stv_ex_i0, width=5)
        ent_ex_i0.grid(row=0, column=1, sticky="ew")
        ttk.Label(frm_ex_names, text="Final current name: ").grid(row=0, column=2, sticky="e", padx=10)
        ent_ex_ia = ttk.Entry(frm_ex_names, textvariable=stv_ex_ia, width=5)
        ent_ex_ia.grid(row=0, column=3, sticky="ew")
        btn_ex_run = ttk.Button(frm_ex_names, text="Run", command=start_exposure)
        btn_ex_run.grid(row=0, column=4, sticky="ew", padx=10, pady=5)

        frm_ex_transient.rowconfigure([*range(10)], weight=1)  # Contains the parameters required for a transient...
        frm_ex_transient.columnconfigure([0, 1, 2, 3, 4], weight=1)  # ...second measurement.
        rdb_ex_transient = ttk.Radiobutton(frm_ex_transient, text="Transient measurement",
                                           variable=inv_ex_type, value=0, command=lambda: enable_ex_ents('t'))
        # TODO: Make this flexible (ie not arbitrary)
        rdb_ex_transient.grid(row=0, column=0, columnspan=3, sticky="nw", padx=5)
        # stvs_ex_tvars = [tk.StringVar(value='0'), tk.StringVar(value='15'), tk.StringVar(value='.1')]
        # stvs_ex_tcomps = [tk.StringVar(value='1u'), tk.StringVar(value='1u'), tk.StringVar(value='10u')]
        stvs_ex_tvars = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        stvs_ex_tcomps = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        ents_ex_tvars = []
        ents_ex_tcomps = []
        # stv_ex_sample = tk.StringVar()

        # ttk.Label(frm_ex_transient, text="Sampling parameter: ").grid(row=1, column=0, columnspan=2, sticky="nse")
        # drp_ex_t_sampling = ttk.OptionMenu(frm_ex_transient, stv_ex_sample, None, *param_list)
        # drp_ex_t_sampling.grid(row=1, column=2, columnspan=3, padx=5, sticky="nsew")
        for i in range(3):
            ttk.Label(frm_ex_transient, text=params[i] + ":").grid(row=i + 2, column=0)
            ents_ex_tvars.append(ttk.Entry(frm_ex_transient, textvariable=stvs_ex_tvars[i], width=5))
            ents_ex_tvars[-1].grid(row=i + 2, column=1, sticky="ew", padx=5)
            ttk.Label(frm_ex_transient, text="V, compliance: ").grid(row=i + 2, column=2, sticky="nsew")
            ents_ex_tcomps.append(ttk.Entry(frm_ex_transient, textvariable=stvs_ex_tcomps[i], width=5))
            ents_ex_tcomps[-1].grid(row=i + 2, column=3, sticky="ew", padx=5)
            ttk.Label(frm_ex_transient, text="V").grid(row=i + 2, column=4, sticky="w")
        # stv_ex_interval, stv_ex_n, stv_ex_tot, stv_ex_hold = tk.StringVar(value='400m'), tk.StringVar(value='11'),
        # tk.StringVar(value='4.0'), tk.StringVar(value='.1')
        stv_ex_interval, stv_ex_n, stv_ex_tot, stv_ex_hold = tk.StringVar(), tk.StringVar(), tk.StringVar(), \
                                                             tk.StringVar()
        ttk.Label(frm_ex_transient, text="Interval: ").grid(row=5, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(frm_ex_transient, text="No. of samples: ").grid(row=6, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(frm_ex_transient, text="Total sampling time: ").grid(row=7, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(frm_ex_transient, text="Hold: ").grid(row=8, column=0, columnspan=2, sticky="w", padx=5)
        ent_ex_t_interval = ttk.Entry(frm_ex_transient, textvariable=stv_ex_interval, width=5)
        ent_ex_t_interval.grid(row=5, column=2, columnspan=2, sticky="ew", padx=5)
        ent_ex_t_n = ttk.Entry(frm_ex_transient, textvariable=stv_ex_n, width=5)
        ent_ex_t_n.grid(row=6, column=2, columnspan=2, sticky="ew", padx=5)
        ent_ex_t_tot = ttk.Entry(frm_ex_transient, textvariable=stv_ex_tot, width=5)
        ent_ex_t_tot.grid(row=7, column=2, columnspan=2, sticky="ew", padx=5)
        ent_ex_t_hold = ttk.Entry(frm_ex_transient, textvariable=stv_ex_hold, width=5)
        ent_ex_t_hold.grid(row=8, column=2, columnspan=2, sticky="ew", padx=5)
        ttk.Label(frm_ex_transient, text="sec").grid(row=5, column=4, sticky="w")
        ttk.Label(frm_ex_transient, text="sec").grid(row=7, column=4, sticky="w")
        ttk.Label(frm_ex_transient, text="sec").grid(row=8, column=4, sticky="w")
        inv_ex_limit = tk.IntVar(value=1)
        chk_ex_limit_time = ttk.Checkbutton(frm_ex_transient, text="Limit run time to the set value",
                                            variable=inv_ex_limit, onvalue=1, offvalue=0)
        chk_ex_limit_time.grid(row=9, column=0, columnspan=5, sticky="nsw")

        # Bind the functions that update the interval/no./total time entryboxes
        ent_ex_t_interval.bind("<FocusOut>", lambda e: update_ex_time_params(stv_ex_interval, 'int'))
        ent_ex_t_n.bind("<FocusOut>", lambda e: update_ex_time_params(stv_ex_n, 'n'))
        ent_ex_t_tot.bind("<FocusOut>", lambda e: update_ex_time_params(stv_ex_tot, 'tot'))

        frm_ex_sweep.columnconfigure([*range(5)], weight=1)  # Contains the parameters required for a periodic...
        frm_ex_sweep.rowconfigure([*range(5)], weight=1)  # ...sweep as the second measurement.
        rdb_ex_sweep = ttk.Radiobutton(frm_ex_sweep, text="Periodic sweep measurement",
                                       variable=inv_ex_type, value=1, command=lambda: enable_ex_ents('s'))
        # TODO: Make this flexible (ie not arbitrary)
        rdb_ex_sweep.grid(row=0, column=0, columnspan=5, sticky="nw", padx=5)
        # stv_ex_sweepvar, stv_ex_s_comp, stv_ex_s_n, stv_ex_s_between = tk.StringVar(value='15'), tk.StringVar(value='1u'), tk.StringVar(value='4'), tk.StringVar(value='2')
        stv_ex_sweepvar, stv_ex_s_comp, stv_ex_s_n, stv_ex_s_between = tk.StringVar(), tk.StringVar(), tk.StringVar(), \
                                                                       tk.StringVar()
        ttk.Label(frm_ex_sweep, text=params[1] + ": ").grid(row=1, column=0, padx=5)
        ent_ex_s_var2 = ttk.Entry(frm_ex_sweep, textvariable=stv_ex_sweepvar, width=5, state=tk.DISABLED)  # The VALUE of the var
        ent_ex_s_var2.grid(row=1, column=1, sticky="nsew", padx=5)
        ttk.Label(frm_ex_sweep, text="V, compliance: ").grid(row=1, column=2, sticky="w")
        ent_ex_s_v2comp = ttk.Entry(frm_ex_sweep, textvariable=stv_ex_s_comp, width=5, state=tk.DISABLED)
        ent_ex_s_v2comp.grid(row=1, column=3, sticky="nsew", padx=5)
        ttk.Label(frm_ex_sweep, text="V").grid(row=1, column=4, sticky="w")
        ttk.Label(frm_ex_sweep, text="Number of sweeps: ").grid(row=2, column=0, columnspan=2, padx=5)
        ent_ex_s_n = ttk.Entry(frm_ex_sweep, textvariable=stv_ex_s_n, width=5, state=tk.DISABLED)
        ent_ex_s_n.grid(row=2, column=2, sticky="nsw", padx=5)
        ttk.Label(frm_ex_sweep, text="Delay between sweeps: ").grid(row=3, column=0, columnspan=2, padx=5)
        ent_ex_s_between = ttk.Entry(frm_ex_sweep, textvariable=stv_ex_s_between, width=5, state=tk.DISABLED)
        ent_ex_s_between.grid(row=3, column=2, columnspan=2, sticky="nsew", padx=5)
        ttk.Label(frm_ex_sweep, text=" sec").grid(row=3, column=4, sticky="w")
        ex_sweep_notification = "The parameters of the sweep (on " + params[0] + "), the \nconstant variable (" + \
                                params[1] + "), and the timing \n(hold, delay) will be taken from the main window. "
        ttk.Label(frm_ex_sweep, text=ex_sweep_notification).grid(row=4, column=0, columnspan=5, padx=5, pady=10)

        def update_ex_time_params(var, t):
            """
            When "Interval", "No. of samples", or "Total measuring time" are changed, the other two must update
            accordingly.
            :param t: Which of the three entryboxes was changed ('int'/'n'/'tot' respectively).
            :param var: The appropriate StringVar.
            """
            try:
                if var.get() != '':  # Don't do anything if the user just cleared the entrybox.
                    interval = stv_ex_interval.get()
                    n = stv_ex_n.get()
                    tot = stv_ex_tot.get()
                    num_of_blanks = 0  # The number of entryboxes that are currently blank.
                    for x in [interval, n, tot]:
                        if x == '':
                            num_of_blanks = num_of_blanks + 1
                    if num_of_blanks == 1:  # Fill the blank entrybox with the appropriate calculated value.
                        if interval == '':  # The interval can be any float.
                            n = str(int(round(float(n))))  # Round n. For some reason int(n) didn't work...
                            stv_ex_n.set(n)  # Set n to the round value, in case the user changed it to a float
                            stv_ex_interval.set(str(suffix(tot) / (int(n) - 1)))
                        if n == '':     # N must be an integer! So update the third entrybox (not the one that was just
                                        # updated, nor the N entrybox) accordingly if N was rounded.
                            stv_ex_n.set(str(round(suffix(tot) / suffix(interval) + 1)))
                            if t == 'int':  # If the interval was changed, update the total
                                stv_ex_tot.set(str(suffix(interval) * (int(stv_ex_n.get()) - 1)))
                            if t == 'tot':  # If the total was changed, update the interval
                                stv_ex_interval.set(str(suffix(tot) / (int(stv_ex_n.get()) - 1)))
                        if tot == '':  # The total can be any float.
                            n = str(int(round(float(n))))  # Round n
                            stv_ex_n.set(n)  # Set n to the round value, in case the user changed it to a float
                            stv_ex_tot.set(str(suffix(interval) * (int(n) - 1)))
                    elif num_of_blanks == 0:    # If all three entryboxes are filled in, update the total (arbitrarily),
                                                # unless that was the entrybox that was just updated (in which case the
                                                # interval or n will be updated).
                        if t == 'int':  # Update tot
                            stv_ex_tot.set(str(suffix(interval) * (int(n) - 1)))
                        if t == 'n':  # Round n and update it, then update tot
                            n = str(int(round(float(n))))
                            stv_ex_n.set(n)
                            stv_ex_tot.set(str(suffix(interval) * (int(n) - 1)))
                        if t == 'tot':  # Update int or n
                            if suffix(tot) % suffix(interval) == 0:  # If the total is divisible by the interval, the user
                                # probably deliberately set it that way. Therefore, update n.
                                stv_ex_n.set(str(int(suffix(tot) / suffix(interval) + 1)))
                            else:  # Otherwise, update the interval, since it can be any float.
                                stv_ex_interval.set(str(suffix(tot) / (int(n) - 1)))
            except (ValueError, ZeroDivisionError):
                return

    # Sweep tab setup starts here
    tab_sweep.rowconfigure(0, minsize=70, weight=1)
    tab_sweep.rowconfigure(1, minsize=300, weight=1)
    tab_sweep.rowconfigure([2, 3], minsize=65, weight=1)
    tab_sweep.columnconfigure(0, minsize=300)
    tab_sweep.columnconfigure([1, 2], weight=1)
    frm_info = ttk.Frame(tab_sweep, relief=tk.RAISED, borderwidth=2)
    frm_info.grid(row=0, column=0, rowspan=3, sticky="nsew")
    frm_trans = ttk.Frame(tab_sweep, relief=tk.RAISED, borderwidth=2)
    frm_trans.grid(row=0, column=1, columnspan=2, sticky="nsew")
    frm_primary = ttk.Frame(tab_sweep, relief=tk.RAISED, borderwidth=2)
    frm_primary.grid(row=1, column=1, sticky="nsew")  # 7 rows, 2 cols
    frm_secondary = ttk.Frame(tab_sweep, relief=tk.RAISED, borderwidth=2)
    frm_secondary.grid(row=1, column=2, sticky="nsew")
    frm_consts = ttk.Frame(tab_sweep, relief=tk.RAISED, borderwidth=2)
    frm_consts.grid(row=2, column=1, columnspan=2, sticky="nsew")
    frm_saveload = ttk.Frame(tab_sweep, relief=tk.RAISED, borderwidth=2)
    frm_saveload.grid(row=3, column=0, columnspan=3, sticky="nsew")

    # Info frame
    frm_info.rowconfigure([*range(10)], weight=1)
    frm_info.columnconfigure(1, weight=1)
    ttk.Label(frm_info, text="Operator: ").grid(row=0, column=0, sticky="e")
    ttk.Label(frm_info, text="Gas: ").grid(row=1, column=0, sticky="e")
    ttk.Label(frm_info, text="Concentration: ").grid(row=2, column=0, sticky="e")
    ttk.Label(frm_info, text="Carrier: ").grid(row=3, column=0, sticky="e")
    ttk.Label(frm_info, text="Atmosphere: ").grid(row=4, column=0, sticky="e")
    # ttk.Label(frm_info, text="Device (serial no.): ").grid(row=5, column=0, sticky="e")
    ttk.Label(frm_info, text="Decoration: ").grid(row=6, column=0, sticky="e")
    ttk.Label(frm_info, text="Dec. thickness: ").grid(row=7, column=0, sticky="e")
    ttk.Label(frm_info, text="Temperature: ").grid(row=8, column=0, sticky="e")
    ttk.Label(frm_info, text="Humidity: ").grid(row=9, column=0, sticky="e")
    ent_op = ttk.Entry(frm_info, textvariable=stv_op, width=12)
    ent_op.grid(row=0, column=1, columnspan=2, sticky="ew")
    ent_gas = ttk.Entry(frm_info, textvariable=stv_gas, width=12)
    ent_gas.grid(row=1, column=1, columnspan=2, sticky="ew")
    ent_conc = ttk.Entry(frm_info, textvariable=stv_conc, width=12)
    ent_conc.grid(row=2, column=1, sticky="ew")
    ent_carr = ttk.Entry(frm_info, textvariable=stv_carr, width=12)
    ent_carr.grid(row=3, column=1, columnspan=2, sticky="ew")
    ent_atm = ttk.Entry(frm_info, textvariable=stv_atm, width=12)
    ent_atm.grid(row=4, column=1, columnspan=2, sticky="ew")
    # ent_dev = ttk.Entry(frm_info, textvariable=stv_dev, width=12)
    # ent_dev.grid(row=5, column=1, columnspan=2, sticky="ew")
    ent_dec = ttk.Entry(frm_info, textvariable=stv_dec, width=12)
    ent_dec.grid(row=6, column=1, columnspan=2, sticky="ew")
    ent_thick = ttk.Entry(frm_info, textvariable=stv_thick, width=12)
    ent_thick.grid(row=7, column=1, sticky="ew")
    ent_temp = ttk.Entry(frm_info, textvariable=stv_temp, width=12)
    ent_temp.grid(row=8, column=1, sticky="ew")
    ent_hum = ttk.Entry(frm_info, textvariable=stv_hum, width=12)
    ent_hum.grid(row=9, column=1, sticky="ew")
    ttk.Label(frm_info, text="ppm").grid(row=2, column=2, sticky="w", padx=5)
    ttk.Label(frm_info, text="nm").grid(row=7, column=2, sticky="w", padx=5)
    ttk.Label(frm_info, text="°C").grid(row=8, column=2, sticky="w", padx=5)
    ttk.Label(frm_info, text="%").grid(row=9, column=2, sticky="w", padx=5)

    # Transistor selection frame
    frm_trans.columnconfigure(1, weight=1)
    frm_trans.columnconfigure([2, 3], minsize=150)
    frm_trans.rowconfigure(0, weight=1)
    btn_select_trans = ttk.Button(frm_trans, text="Select transistors", command=lambda: open_trans_selection())
    btn_select_trans.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
    btn_char = ttk.Button(frm_trans, text="Run characteristic", command=lambda: run_characteristic())
    btn_char.grid(row=0, column=2, sticky="nsew", padx=20, pady=20)
    btn_run = ttk.Button(frm_trans, text="Run exposure experiment", command=lambda: run_exposure())
    btn_run.grid(row=0, column=3, sticky="nsew", padx=20, pady=20)

    # if not spa_connected:
        # btn_char["state"] = tk.DISABLED
        # btn_run["state"] = tk.DISABLED

    # Parameter entry frame
    global stv_name1, stv_name2, stv_name3, param_list
    stv_name1 = tk.StringVar()  # The name of the primary variable
    stv_name2 = tk.StringVar()  # The name of the secondary variable
    stv_name3 = tk.StringVar(value="Constant variable: ")  # The text that appears in the "Constant variable (XXX)" label
    stv_name1.trace("w", lambda *args: update_const(stv_name2))  # Whenever one of the variables is changed, update the
    stv_name2.trace("w", lambda *args: update_const(stv_name1))  # other one.
    stv_linlog1 = tk.StringVar(value='Linear')
    stv_linlog1.set("Linear")
    stv_start1 = tk.StringVar()
    stv_start1.trace("w", lambda name, index, mode: enable_step_n(1))  # Whenever the start or stop points are changed,
    stv_start2 = tk.StringVar()                                        # determine whether to enable or disable the
    stv_start2.trace("w", lambda name, index, mode: enable_step_n(2))  # step and n entryboxes.
    stv_stop1 = tk.StringVar()
    stv_stop1.trace("w", lambda name, index, mode: enable_step_n(1))
    stv_stop2 = tk.StringVar()
    stv_stop2.trace("w", lambda name, index, mode: enable_step_n(2))
    stv_step1 = tk.StringVar()
    stv_n1 = tk.StringVar()
    stv_step2 = tk.StringVar()
    stv_n2 = tk.StringVar()
    stv_comp1 = tk.StringVar()
    stv_comp2 = tk.StringVar()

    # Primary
    frm_primary.rowconfigure([*range(7)], weight=1)
    frm_primary.columnconfigure([0, 1], weight=1)
    frm_primary.rowconfigure([0, 1], minsize=35)
    ttk.Label(frm_primary, text="Primary variable: ").grid(row=0, column=0, sticky="e")
    global drp_name1  # Must be global for set_var_name() and load_t_config()
    drp_name1 = ttk.OptionMenu(frm_primary, stv_name1, None, *param_list)
    drp_name1.grid(row=0, column=1, sticky="ew", columnspan=2)
    ttk.Label(frm_primary, text="Y-axis scale: ").grid(row=1, column=0, sticky="e")
    drp_linlog1 = ttk.OptionMenu(frm_primary, stv_linlog1, "Linear", "Linear", "Logarithmic")
    drp_linlog1.grid(row=1, column=1, columnspan=2, sticky="ew")
    ttk.Label(frm_primary, text="Start: ").grid(row=2, column=0, sticky="e")
    ent_start1 = ttk.Entry(frm_primary, textvariable=stv_start1, width=10)
    ent_start1.grid(row=2, column=1, sticky="ew")
    ttk.Label(frm_primary, text="V").grid(row=2, column=2, sticky="w", padx=5)
    ttk.Label(frm_primary, text="Stop: ").grid(row=3, column=0, sticky="e")
    ent_stop1 = ttk.Entry(frm_primary, textvariable=stv_stop1, width=10)
    ent_stop1.grid(row=3, column=1, sticky="ew")
    ttk.Label(frm_primary, text="V").grid(row=3, column=2, sticky="w", padx=5)
    ttk.Label(frm_primary, text="Step: ").grid(row=4, column=0, sticky="e")
    ent_step1 = ttk.Entry(frm_primary, state="disabled", textvariable=stv_step1, width=10)
    ent_step1.grid(row=4, column=1, sticky="ew")
    ent_step1.bind("<FocusOut>", lambda e: update_step_n(stv_step1, 'step', 1))
    ttk.Label(frm_primary, text="V").grid(row=4, column=2, sticky="w", padx=5)
    ttk.Label(frm_primary, text="No. of steps: ").grid(row=5, column=0, sticky="e")
    ent_n1 = ttk.Entry(frm_primary, state="disabled", textvariable=stv_n1, width=10)
    ent_n1.grid(row=5, column=1, columnspan=2, sticky="ew")
    ent_n1.bind("<FocusOut>", lambda e: update_step_n(stv_n1, 'n', 1))
    ttk.Label(frm_primary, text="Compliance: ").grid(row=6, column=0, sticky="e")
    ent_comp1 = ttk.Entry(frm_primary, textvariable=stv_comp1, width=10)
    ent_comp1.grid(row=6, column=1, sticky="ew")
    ttk.Label(frm_primary, text="A").grid(row=6, column=2, sticky="w", padx=5)

    # Secondary
    frm_secondary.rowconfigure([*range(7)], weight=1)
    frm_secondary.columnconfigure([0, 1], weight=1)
    frm_secondary.rowconfigure([0, 1], minsize=35)
    ttk.Label(frm_secondary, text="Secondary variable: ").grid(row=0, column=0, sticky="e")
    global drp_name2  # Must be global for set_var_name() and load_t_config()
    drp_name2 = ttk.OptionMenu(frm_secondary, stv_name2, None, *param_list)
    drp_name2.grid(row=0, column=1, columnspan=2, sticky="ew")
    ttk.Label(frm_secondary, text="Start: ").grid(row=2, column=0, sticky="e")
    ent_start2 = ttk.Entry(frm_secondary, textvariable=stv_start2, width=10)
    ent_start2.grid(row=2, column=1, sticky="ew")
    ttk.Label(frm_secondary, text="V").grid(row=2, column=2, sticky="w", padx=5)
    ttk.Label(frm_secondary, text="Stop: ").grid(row=3, column=0, sticky="e")
    ent_stop2 = ttk.Entry(frm_secondary, textvariable=stv_stop2, width=10)
    ent_stop2.grid(row=3, column=1, sticky="ew")
    ttk.Label(frm_secondary, text="V").grid(row=3, column=2, sticky="w", padx=5)
    ttk.Label(frm_secondary, text="Step: ").grid(row=4, column=0, sticky="e")
    ent_step2 = ttk.Entry(frm_secondary, state="disabled", textvariable=stv_step2, width=10)
    ent_step2.grid(row=4, column=1, sticky="ew")
    ttk.Label(frm_secondary, text="V").grid(row=4, column=2, sticky="w", padx=5)
    ent_step2.bind("<FocusOut>", lambda e: update_step_n(stv_step2, 'step', 2))
    ttk.Label(frm_secondary, text="No. of steps: ").grid(row=5, column=0, sticky="e")
    ent_n2 = ttk.Entry(frm_secondary, state="disabled", textvariable=stv_n2, width=10)
    ent_n2.grid(row=5, column=1, columnspan=2, sticky="ew")
    ent_n2.bind("<FocusOut>", lambda e: update_step_n(stv_n2, 'n', 2))
    ttk.Label(frm_secondary, text="Compliance: ").grid(row=6, column=0, sticky="e")
    ent_comp2 = ttk.Entry(frm_secondary, textvariable=stv_comp2, width=10)
    ent_comp2.grid(row=6, column=1, sticky="ew")
    ttk.Label(frm_secondary, text="A").grid(row=6, column=2, sticky="w", padx=5)

    # Constants entry frame
    frm_consts.columnconfigure([0, 1, 3, 4], weight=1)
    frm_consts.rowconfigure([0, 1], weight=1)
    stv_const = tk.StringVar()
    lbl_const = ttk.Label(frm_consts, textvariable=stv_name3)
    lbl_const.grid(row=0, column=0, padx=20)
    ent_const = ttk.Entry(frm_consts, textvariable=stv_const, width=10)
    ent_const.grid(row=0, column=1, sticky="ew")
    ttk.Label(frm_consts, text="V").grid(row=0, column=2, padx=5, sticky="w")
    ttk.Label(frm_consts, text="Compliance: ").grid(row=0, column=3, sticky="nsw", padx=20)
    stv_const_comp = tk.StringVar()
    ent_const_comp = ttk.Entry(frm_consts, textvariable=stv_const_comp, width=10)
    ent_const_comp.grid(row=0, column=4, sticky="ew")
    ttk.Label(frm_consts, text="A").grid(row=0, column=5, padx=5, sticky="w")
    ttk.Label(frm_consts, text="Hold: ").grid(row=1, column=0, padx=20)
    stv_hold = tk.StringVar()
    ent_hold = ttk.Entry(frm_consts, textvariable=stv_hold, width=10)
    ent_hold.grid(row=1, column=1, sticky="ew")
    ttk.Label(frm_consts, text="sec").grid(row=1, column=2, padx=5, sticky="w")
    ttk.Label(frm_consts, text="Delay: ").grid(row=1, column=3, sticky="nsw", padx=20)
    stv_delay = tk.StringVar()
    ent_delay = ttk.Entry(frm_consts, textvariable=stv_delay, width=10)
    ent_delay.grid(row=1, column=4, sticky="ew")
    ttk.Label(frm_consts, text="sec").grid(row=1, column=5, padx=5, sticky="w")

    # Save/Load frame
    with open("data/configs_s.csv", newline='') as f:
        csv_reader = reader(f)
        config_names = [row[0] for row in list(csv_reader)[1:]]  # Read the name of each config to config_names

    frm_saveload.columnconfigure([*range(8)], weight=1)
    frm_saveload.rowconfigure(0, weight=1)
    ttk.Label(frm_saveload, text="Save configuration as: ").grid(row=0, column=0, sticky="e")
    stv_savename = tk.StringVar()
    stv_loadname = tk.StringVar()
    ent_savename = ttk.Entry(frm_saveload, textvariable=stv_savename)
    ent_savename.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    btn_save = ttk.Button(frm_saveload, text="Save", command=save_config)
    btn_save.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
    ttk.Label(frm_saveload, text="Load configuration: ").grid(row=0, column=3, sticky="e")
    drp_load = ttk.OptionMenu(frm_saveload, stv_loadname, None, *config_names)
    drp_load.grid(row=0, column=4, sticky="nsew", padx=10, pady=10)
    btn_load = ttk.Button(frm_saveload, text="Load", command=lambda: load_config())
    btn_load.grid(row=0, column=5, sticky="nsew", padx=10, pady=10)
    btn_edit = ttk.Button(frm_saveload, text="Edit", command=lambda: save_config(True))
    btn_edit.grid(row=0, column=6, sticky="nsew", padx=10, pady=10)
    btn_delete = ttk.Button(frm_saveload, text="Delete", command=lambda: delete_config())
    btn_delete.grid(row=0, column=7, sticky="nsew", padx=10, pady=10)


def init_time_tab():
    # Set up transient measurements.
    def update_time_params(var, t):
        """
        When "Interval", "No. of samples", or "Total measuring time" are changed, the other two must update
        accordingly.
        :param t: Which of the three entryboxes was changed ('int'/'n'/'tot' respectively).
        :param var: The appropriate StringVar.
        """
        if var.get() != '':  # Don't do anything if the user just cleared the entrybox.
            try:
                interval = stv_int.get()
                n = stv_n.get()
                tot = stv_tot.get()
                num_of_blanks = 0  # The number of entryboxes that are currently blank.
                for x in [interval, n, tot]:
                    if x == '':
                        num_of_blanks = num_of_blanks + 1
                if num_of_blanks == 1:  # Fill the blank entrybox with the appropriate calculated value.
                    if interval == '':  # The interval can be any float.
                        n = str(int(round(float(n))))  # Round n. For some reason int(n) didn't work...
                        stv_n.set(n)  # Set n to the round value, in case the user changed it to a float
                        stv_int.set(str(suffix(tot) / (int(n) - 1)))
                    if n == '':     # N must be an integer! So update the third entrybox (not the one that was just
                                    # updated, nor the N entrybox) accordingly if N was rounded.
                        stv_n.set(
                            str(round(suffix(tot) / suffix(interval) + 1)))  # But now int or tot need to be set again,
                        if t == 'int':  # If the interval was changed, update the total
                            stv_tot.set(str(suffix(interval) * (int(stv_n.get()) - 1)))
                        if t == 'tot':  # If the total was changed, update the interval
                            stv_int.set(str(suffix(tot) / (int(stv_n.get()) - 1)))
                    if tot == '':  # The total can be any float.
                        n = str(int(round(float(n))))  # Round n
                        stv_n.set(n)  # Set n to the round value, in case the user changed it to a float
                        stv_tot.set(str(suffix(interval) * (int(n) - 1)))
                elif num_of_blanks == 0:    # If all three entryboxes are filled in, update the total (arbitrarily),
                                            # unless that was the entrybox that was just updated (in which case the
                                            # interval or n will be updated).
                    if t == 'int':  # Update tot
                        stv_tot.set(str(suffix(interval) * (int(n) - 1)))
                    if t == 'n':  # Round n and update it, then update tot
                        n = str(int(round(float(n))))
                        stv_n.set(n)
                        stv_tot.set(str(suffix(interval) * (int(n) - 1)))
                    if t == 'tot':  # Update int or n
                        if suffix(tot) % suffix(interval) == 0:  # If the total is divisible by the interval, the user
                                # probably deliberately set it that way. Therefore, update n.
                            stv_n.set(str(int(suffix(tot) / suffix(interval) + 1)))
                        else:  # Otherwise, update the interval, since it can be any float.
                            stv_int.set(str(suffix(tot) / (int(n) - 1)))
            except (ValueError, ZeroDivisionError):
                return

    def run_time(stvs):
        """
        Runs a transient measurement - that is, measures all four currents (while primarily displaying the drain
        current) over time.
        :param stvs: The StringVars holding the required parameters for the measurement.
        stvs = [[tvars], [tcomps], name, [int, n, tot, hold], linlog]
        """
        def increment(evt):  # Increments prb.
            """
            Increments the progressbar and updates the progress label.
            :param: val: The portion of the progressbar that should be full (between 0 and 1).
            """
            val = measurement_vars.incr_vars
            prb["value"] = val * 100
            lbl_progress["text"] = "Measuring..."
            if val == 1:
                btn_ex_end["state"] = tk.NORMAL
                lbl_progress["text"] = "Measurement complete. "

        def add_spot(evt):
            """
            Adds a spot measurement to the graph, for each of the four currents.
            :param: x: The time measurements.
            :param: y1s-y4: The four currents. y1s is a list of the drain currents, y2 and y3 are the gate currents, and
            y4 is the source current.
            """
            global drain_colors, color_g1, color_g2, color_src
            data = measurement_vars.send_transient
            x = data[0]
            secondary_col = -3 if show_src else -2  # To take the last 3 columns if the source SMU is active,
                                                         # or 2 otherwise.
            y1s = data[1:secondary_col]
            y2 = data[secondary_col]
            y3 = data[secondary_col+1]
            if show_src:
                y4 = data[-1]
            ax.clear()
            ax2.clear()
            ax3.clear()
            ax4.clear()
            for i, y in enumerate(y1s):
                ax.plot(x, y, color=drain_colors[i])
            ax2.plot(x, y2, color_g1)
            ax3.plot(x, y3, color_g2)
            if show_src:
                ax4.plot(x, y4, color_src)
            if chk_currents.instate(['selected']):  # Re-resize the plot and reposition the right axes
                ax3.spines.right.set_position(("axes", 1.2))
                ax4.spines.right.set_position(("axes", 1.4))
                ax3.get_yaxis().get_offset_text().set_position((1.2, 5.0))
                ax4.get_yaxis().get_offset_text().set_position((1.4, 5.0))
            ax.set_ylabel("I (" + stv_name.get() + ")")
            ax2.set_ylabel("I (" + right_params[0] + ")")
            ax3.set_ylabel("I (" + right_params[1] + ")")
            ax4.set_ylabel("I (Source)")
            if chk_linlog.instate(['selected']):  # Set the y-axis scale back to what it was
                ax.set_yscale('log')
                ax2.set_yscale('log')
                ax3.set_yscale('log')
                ax4.set_yscale('log')
            else:
                ax.set_yscale('linear')
                ax2.set_yscale('linear')
                ax3.set_yscale('linear')
                ax4.set_yscale('linear')
            bar.draw()

        def finish_sweep(aborted=False):
            """
            Closes the window, extracts the final measurement data, and saves the experiment.
            :param: data_to_save: A list of lists of length 5. After transposing, it becomes a list of 5 lists. The
            first contains the time measurements, and the other four contain the current measurements
            (as in add_spot - the order is D, G, G, S).
            :param: aborted: True if the function was called via the "Abort" button, False if it was called via the
            "Finish" button.
            """
            if aborted:  # Let close() close the window, after the experiment has ended.
                lbl_progress["text"] = "Closing (once the sweep is done)... "
                window_load.title("Closing...")
                if measurement_vars.ex_finished:  # If the measurement has already finished
                    window_load.grab_release()
                    window_load.destroy()
                    measurement_vars.stop_ex = False  # Just in case
                    measurement_vars.ex_finished = False
                else:  # The current measurement must be allowed to finish
                    measurement_vars.abort_ex = True
                    measurement_vars.stop_ex = True
            else:  # If called from the "Finish" button, the window can close normally.
                window_load.grab_release()
                window_load.destroy()
            # measurement_vars.stop_ex = False
            # measurement_vars.ex_finished = False
            global meas_type, meas_order, meas_prim, meas_i0, device_names, trans_names
            meas_type = 'transient'
            # Table headers:
            names = ['t', 'I (' + stv_name.get() + ')', 'I (' + right_params[0] + ')', 'I (' + right_params[1] + ')']
            if show_src:
                names.append('I (Source)')
            secondary_col = -3 if show_src else -2  # Take the last drain +3 columns if the source SMU is active, or
                                                    # 2 columns otherwise.
            if len(measurement_vars.ex_vars) != 0:  # To avoid unpacking an empty list after aborting
                data_to_save = measurement_vars.ex_vars  # Rows of length (num_drains+4)
                data_to_analyze = [list(x) for x in zip(*data_to_save)]  # (num_drains+4) columns
                data_to_analyze = [data_to_analyze[0], *data_to_analyze[secondary_col-1:]]  # 4/5 columns (uses the LAST drain)
                # data_to_save = [names, *data_to_save]
                meas_order = 'T' + extract_var_letter(stv_name.get())
                set_labels(meas_order)
                meas_prim = data_to_analyze[0]
                meas_i0 = data_to_analyze[1]  # TODO: Is this correct?

                info = [date.today().strftime("%d/%m/%y"), stv_op.get(), stv_gas.get(), stv_conc.get(), stv_carr.get(),
                        stv_atm.get(), '', '', stv_dec.get(), stv_thick.get(), stv_temp.get(), stv_hum.get()]
                index = 0
                with open("data/central.csv", newline='') as f:
                    csv_reader = reader(f)
                    ids = [int(row[0]) for row in list(csv_reader)[1:]]
                if len(ids) != 0:
                    index = max(ids) + 1
                # params_to_file = [index, *info, meas_order, '']
                # add_experiment(*params_to_file, data_to_save)

                ordered_names = [trans_names[row][col] for row in range(4) for col in range(4)
                                 if active_trans[row][col]]  # The names of the active transistors only
                ordered_devs = [device_names[row] for row in range(4) for col in range(4)
                                 if active_trans[row][col]]  # The corresponding device of each transistor
                for i in range(1, len(data_to_save[0])+secondary_col):  # Save each of the experiments separately
                    sliced = [[row[0], row[i], *row[secondary_col:]] for row in data_to_save]
                    sliced = [names, *sliced]
                    params_to_file = [index, *info, meas_order, '']
                    params_to_file[7] = ordered_devs[i]  # TODO: Check if these work!!
                    params_to_file[8] = ordered_names[i]
                    add_experiment(*params_to_file, sliced)
                    index += 1

        def linlog():
            """
            Updates the graph based on the state of the linear/logarithmic chechbox.
            """
            if chk_linlog.instate(['selected']):
                ax.set_yscale('log')
                ax2.set_yscale('log')
                ax3.set_yscale('log')
                ax4.set_yscale('log')
            else:
                ax.set_yscale('linear')
                ax2.set_yscale('linear')
                ax3.set_yscale('linear')
                ax4.set_yscale('linear')
            bar.draw()

        def additional_currents():
            """
            Shows/hides the three additional currents (jg, bg, s).
            """
            if chk_currents.instate(['selected']):
                ax2.set_visible(True)
                ax3.set_visible(True)
                ax3.spines.right.set_position(("axes", 1.2))
                ax3.get_yaxis().get_offset_text().set_position((1.2, 5.0))
                if show_src:
                    fig.subplots_adjust(right=0.65)
                    ax4.set_visible(True)
                    ax4.spines.right.set_position(("axes", 1.4))
                    ax4.get_yaxis().get_offset_text().set_position((1.4, 5.0))
                else:
                    fig.subplots_adjust(right=0.75)
            else:
                ax2.set_visible(False)
                ax3.set_visible(False)
                fig.subplots_adjust(right=0.9)
                ax4.set_visible(False)
            bar.draw()

        global stv_s_timegroup, drain_smus, stv_smu2, stv_smu3, stv_smu4, active_trans, board, pinno
        measurement_vars.incr_vars = []     # Reset the variables that are used to communicate between measurements.py
        measurement_vars.ex_vars = []       # and this file
        measurement_vars.send_transient = []
        # Check that all the required entryboxes are filled in
        check_info = [stv_op.get(), stv_gas.get(), stv_conc.get(), stv_carr.get(), stv_atm.get(),
                        stv_dev.get(), stv_dec.get(), stv_thick.get(), stv_temp.get(), stv_hum.get()]
        check_params = [s.get() for s in [*stvs[0], *stvs[1], stvs[2], *stvs[3], stv_s_timegroup]]
        for i in [*check_info, *check_params]:
            if i == '':
                messagebox.showerror('', "Please fill out all the parameters!")
                for f in tab_time.winfo_children():  # Find all entry widgets in the tab
                    for w in f.winfo_children():
                        if w.winfo_class() == "TEntry":
                            if w.get() == '':  # Focus on it if it's blank
                                w.focus()
                                return
                return  # Juuust in case.
        for i in [*check_params[:6], *check_params[7:]]:
            # These are the parameters that must be numeric: The three voltages, the three compliances, int, n,
            # tot, hold.
            try:
                suffix(i)
            except ValueError:
                messagebox.showerror('', "The following parameters must be numeric: Voltages, Compliances, "
                                         "Increment, No. of steps, Total measuring time, Hold time, and No. of "
                                         "measurements per update. ")
                return
        if not any([any(x) for x in active_trans]):  # Check that at least one SMU is selected.
            messagebox.showerror('', "Please select at least one SMU.")
            return
        try:  # Make sure the SMUs are properly detected.
            smu_name_list = [*[x for x in drain_smus], stv_smu2.get(), stv_smu3.get(), stv_smu4.get()]
            if len(smu_name_list) > len(set(smu_name_list)):  # This means the SMUs aren't unique (at least one is
                # selected twice!)
                messagebox.showerror('', "Please make sure all the SMUs (in the 'Channels' tab) are different!")
                return
        except Exception as e:
            messagebox.showerror('', "Something's wrong with the SMUs (\"" + e + "\").")
            tb = traceback.format_exc()
            logging.error(str(e) + ". Traceback: " + str(tb))

        p_voltages = [suffix(s.get()) for s in stvs[0]]  # The voltage of each SMU
        p_comps = [suffix(s.get()) for s in stvs[1]]  # The compliance of each SMU
        p_time_params = [stvs[2].get(), *[suffix(s.get()) for s in stvs[3]], stvs[4]]  # [name, int, n, tot, hold, linlog]
        p_smus = [drain_smus, stv_smu2.get(), stv_smu3.get(), stv_smu4.get()]  # The names of the SMUs (as strings)
        right_params = [x for x in param_list if not x == stv_name.get()]  # The two currents that aren't the main
        # variable - to display on the right side along I(s).
        show_src = stv_smu4.get() != "(None)"  # If the source SMU wasn't set, hide the axis (and don't add its sweeps)

        window_load, fig, lbl_progress, chk_linlog, stv_ex_linlog, chk_currents, btn_ex_end, btn_ex_abort, prb, ax, ax2,\
        ax3, ax4, bar = open_measurement_window(stv_name.get(), stv_linlog, True)  # Open the measurement window, return
        # the objects that will be dynamically changed
        ax.set_ylabel("I (" + stv_name.get() + ")")
        ax2.set_ylabel("I (" + right_params[0] + ")")
        ax3.set_ylabel("I (" + right_params[1] + ")")
        ax4.set_ylabel("I (Source)")
        ax.set_xlabel("t (sec)")
        ax4.set_visible(show_src)
        bar.draw()

        # Set the drain colors based on the number of active drains
        global drain_colors, color_d1, color_d2
        num_drains = len([x for row in active_trans for x in row if x])  # The number of active drains
        drain_colors.clear()
        color_diff = [y - x for x, y in zip(color_d1, color_d2)]
        for i in range(num_drains):
            drain_colors[i] = tuple([color_d1[j] + color_diff[j] * i / (num_drains - 1) for j in range(3)])

        # Bind the commands to the checkboxes and buttons
        chk_linlog["command"] = linlog
        chk_currents["command"] = additional_currents
        btn_ex_abort["command"] = lambda: finish_sweep(True)
        btn_ex_end["command"] = finish_sweep  # .bind() doesn't work, because it still works when the button is disabled
        # Bind the events for communication with measurements.py
        window_load.bind("<<prb-increment>>", increment)
        window_load.bind("<<add-spot>>", add_spot)

        measurement_vars.ex_finished = False
        global b1500
        if inv_limit_time.get() == 1:
            limit_time = True
        else:
            limit_time = False
        # Start the measurement in a thread, so the window can update in real time
        th = threading.Thread(target=transient, args=(b1500, [param_list, p_voltages, p_comps, p_time_params, p_smus,
                                                              active_trans], window_load, limit_time,
                                                      int(stv_s_timegroup.get()), show_src, board, pinno),
                              daemon=True)
        th.start()

    def save_t_config(edit=False):
        """
        Check if all the entryboxes are filled in, and if all the values that are supposed to be numeric indeed are.
        Then, save the configuration to configs_t.csv, or overwrite an existing row.
        :param edit: False to add a new row, True to overwrite an existing row.
        """
        try:
            params = [s.get() for s in [stv_t_savename, stv_op, stv_gas, stv_conc, stv_carr, stv_atm, stv_dev, stv_dec, stv_thick,
                                        stv_temp, stv_hum, *stvs_tvars, *stvs_tcomps, stv_name, stv_int, stv_n, stv_tot,
                                        stv_hold, stv_linlog]]
            for i in params:  # Check that all the entryboxes are filled in
                if i == '':
                    messagebox.showerror('', "Please fill out all the parameters (including the info on the left)!")
                    return
            for i in [*params[11:17], *params[18:22]]:  # Check that the relevant values are numeric
                try:
                    suffix(i)
                except ValueError:
                    messagebox.showerror('', "The following parameters must be numeric: Start, Stop, Step, No. of steps, "
                                             "Compliance, Constant variable value.")
                    return
            str_limit = "True" if inv_limit_time.get() == 1 else "False"
            save_params = [*params[:18], params[-1], *params[18:22], str_limit, *param_list]
            if not edit:  # Save
                with open("data/configs_t.csv", newline='') as f:  # Check if the name already exists
                    csv_reader = reader(f)
                    for row in list(csv_reader)[1:]:
                        if row[0] == stv_t_savename.get():
                            messagebox.showerror('', "Configuration name already exists!")
                            return
                with open("data/configs_t.csv", "a+", newline='') as f:  # Write a new line with the params
                    csv_writer = writer(f)
                    csv_writer.writerow(save_params)
                menu = drp_load["menu"]  # Add it to the menu
                options = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)]
                options.append(params[0])  # Clear the dropmenu and re-add the options including the new one
                menu.delete(0, "end")
                for s in options:
                    menu.add_command(label=s, command=tk._setit(stv_t_loadname, s))
                messagebox.showinfo('', 'Configuration saved. ')
            else:  # Edit
                with open("data/configs_t.csv", newline='') as f:  # Get the existing configs
                    csv_reader = reader(f)
                    loadouts = list(csv_reader)
                same_name = [row[0] == stv_t_savename.get() for row in loadouts]  # True on the row we need to edit, False otherwise
                if not any(same_name):  # Trying to edit a config that doesn't exist
                    messagebox.showerror('', "Configuration name does not exist!")
                    return
                with open("data/configs_t.csv", "w", newline='') as f:
                    csv_writer = writer(f)
                    for row in loadouts:
                        if row[0] == stv_t_savename.get():
                            csv_writer.writerow(save_params)
                        else:
                            csv_writer.writerow(row)
                messagebox.showinfo('', 'Configuration edited. ')
        except PermissionError as e:
            tb = str(traceback.format_exc())
            if 'used by another process' in tb:
                messagebox.showerror('', "The configuration list is open in another program. Please close it and "
                                         "try again.")
            else:  # Just in case
                messagebox.showerror('', "Permission error: Please make sure the configuration list is not open in "
                                         "another program.")
            return

    def load_t_config():
        """
        Loads the selected configuration into all the entryboxes.
        """
        global stv_name1, stv_name2, stv_name3, param_list
        with open("data/configs_t.csv", newline='') as f:
            csv_reader = reader(f)
            for row in list(csv_reader)[1:]:
                if row[0] == stv_t_loadname.get():  # For the row that corresponds to the selected config:
                    # Fill out the entryboxes (and update param_list)
                    stv_op.set(row[1])
                    stv_gas.set(row[2])
                    stv_conc.set(row[3])
                    stv_carr.set(row[4])
                    stv_atm.set(row[5])
                    stv_dev.set(row[6])
                    stv_dec.set(row[7])
                    stv_thick.set(row[8])
                    stv_temp.set(row[9])
                    stv_hum.set(row[10])
                    for i in range(3):
                        stvs_tvars[i].set(row[11 + i])
                        stvs_tcomps[i].set(row[14 + i])
                    stv_linlog.set(row[18])
                    stv_int.set(row[19])
                    stv_n.set(row[20])
                    stv_tot.set(row[21])
                    stv_hold.set(row[22])
                    inv_limit_time.set(1 if row[23] == "True" else 0)
                    stv_name.set(row[17])

                    # Now we must update param_list and the stv_name#s. Since the configuration is for the transient
                    # tab, the sweep configuration can be set somewhat arbitrarily. So, the primary and secondary
                    # variables will be set to the gate variables, and the constant will be set to the drain.
                    param_list[1] = row[-2]
                    stv_name1.set(row[-2])
                    param_list[2] = row[-1]
                    stv_name2.set(row[-1])
                    param_list[0] = row[-3]
                    stv_name3.set("Constant variable ({}): ".format(row[-3]))
                    stv_var1.set(row[-3])
                    stv_var2.set(row[-2])
                    stv_var3.set(row[-1])

                    # Update the dropmenus
                    m1 = drp_name1["menu"]
                    m1.delete(0, "end")
                    for x in param_list:
                        m1.add_command(label=x, command=lambda i=x: stv_name1.set(i))
                    m2 = drp_name2["menu"]
                    m2.delete(0, "end")
                    for x in param_list:
                        m2.add_command(label=x, command=lambda i=x: stv_name2.set(i))
                    m3 = drp_name["menu"]
                    m3.delete(0, "end")
                    for x in param_list:
                        m3.add_command(label=x, command=lambda i=x: stv_name.set(i))
                    # Update the corresponding label in the "Transient" tab
                    global lbls_tnames
                    for i in range(3):
                        lbls_tnames[i]["text"] = "V({}): ".format(param_list[i])
                    return

    def delete_t_config():
        """
        Deletes the selected configuration.
        """
        if tk.messagebox.askyesno('', "Are you sure you want to delete this configuration?"):
            try:
                del_id = stv_t_loadname.get()  # The name of the config to be deleted
                with open("data/configs_t.csv", newline='') as f:  # Get the existing configs
                    csv_reader = reader(f)
                    existing_data = list(csv_reader)
                with open("data/configs_t.csv", "w", newline='') as f:   # Write them back, except for the one that will
                    csv_writer = writer(f)                              # be deleted
                    for row in existing_data:
                        if row[0] != del_id:
                            csv_writer.writerow(row)
                menu = drp_load["menu"]  # Update the dropmenu
                options = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)]  # Get the options as a list
                options.remove(del_id)
                menu.delete(0, "end")  # Delete everything and rewrite them without the deleted option
                for s in options:
                    menu.add_command(label=s, command=tk._setit(stv_t_loadname, s))
                stv_t_loadname.set('')  # Reset the chosen config, since the one that was previously chosen no longer exists
                messagebox.showinfo('', 'Configuration deleted.')
            except PermissionError as e:
                tb = str(traceback.format_exc())
                if 'used by another process' in tb:
                    messagebox.showerror('', "The configuration list is open in another program. Please close it and "
                                             "try again.")
                else:  # Just in case
                    messagebox.showerror('', "Permission error: Please make sure the configuration list is not open in "
                                             "another program.")
                return

    tab_time.rowconfigure(0, weight=1)
    tab_time.columnconfigure(2, weight=1)
    frm_tinfo = ttk.Frame(tab_time, relief=tk.RAISED, borderwidth=2)
    frm_tinfo.grid(row=0, column=0, sticky="nsew")
    frm_tvars = ttk.Frame(tab_time, relief=tk.RAISED, borderwidth=2)
    frm_tvars.grid(row=0, column=1, sticky="nsew")
    frm_params = ttk.Frame(tab_time, relief=tk.RAISED, borderwidth=2)
    frm_params.grid(row=0, column=2, sticky="nsew")
    frm_tsaveload = ttk.Frame(tab_time, relief=tk.RAISED, borderwidth=2)
    frm_tsaveload.grid(row=1, column=0, columnspan=3, sticky="nsew")

    # Info frame
    frm_tinfo.rowconfigure([*range(10)], weight=1)
    frm_tinfo.columnconfigure(1, weight=1)
    ttk.Label(frm_tinfo, text="Operator: ").grid(row=0, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Gas: ").grid(row=1, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Concentration: ").grid(row=2, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Carrier: ").grid(row=3, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Atmosphere: ").grid(row=4, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Device (serial no.): ").grid(row=5, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Decoration: ").grid(row=6, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Dec. thickness: ").grid(row=7, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Temperature: ").grid(row=8, column=0, sticky="e")
    ttk.Label(frm_tinfo, text="Humidity: ").grid(row=9, column=0, sticky="e")
    ent_op = ttk.Entry(frm_tinfo, textvariable=stv_op, width=10)
    ent_op.grid(row=0, column=1, columnspan=2, sticky="ew")
    ent_gas = ttk.Entry(frm_tinfo, textvariable=stv_gas, width=10)
    ent_gas.grid(row=1, column=1, columnspan=2, sticky="ew")
    ent_conc = ttk.Entry(frm_tinfo, textvariable=stv_conc, width=5)
    ent_conc.grid(row=2, column=1, sticky="ew")
    ent_carr = ttk.Entry(frm_tinfo, textvariable=stv_carr, width=10)
    ent_carr.grid(row=3, column=1, columnspan=2, sticky="ew")
    ent_atm = ttk.Entry(frm_tinfo, textvariable=stv_atm, width=10)
    ent_atm.grid(row=4, column=1, columnspan=2, sticky="ew")
    ent_dev = ttk.Entry(frm_tinfo, textvariable=stv_dev, width=10)
    ent_dev.grid(row=5, column=1, columnspan=2, sticky="ew")
    ent_dec = ttk.Entry(frm_tinfo, textvariable=stv_dec, width=10)
    ent_dec.grid(row=6, column=1, columnspan=2, sticky="ew")
    ent_thick = ttk.Entry(frm_tinfo, textvariable=stv_thick, width=5)
    ent_thick.grid(row=7, column=1, sticky="ew")
    ent_temp = ttk.Entry(frm_tinfo, textvariable=stv_temp, width=5)
    ent_temp.grid(row=8, column=1, sticky="ew")
    ent_hum = ttk.Entry(frm_tinfo, textvariable=stv_hum, width=5)
    ent_hum.grid(row=9, column=1, sticky="ew")
    ttk.Label(frm_tinfo, text="ppm").grid(row=2, column=2, sticky="w", padx=5)
    ttk.Label(frm_tinfo, text="nm").grid(row=7, column=2, sticky="w", padx=5)
    ttk.Label(frm_tinfo, text="°C").grid(row=8, column=2, sticky="w", padx=5)
    ttk.Label(frm_tinfo, text="%").grid(row=9, column=2, sticky="w", padx=5)

    # Variables frame - contains the three voltages and their compliances.
    frm_tvars.rowconfigure([0, 1, 2], weight=1)
    frm_tvars.columnconfigure([1, 3], weight=1)
    global lbls_tnames
    lbls_tnames = []  # The names of the parameters (e.g. "V(d):" before its entry).
    # stvs_tvars = [tk.StringVar(value='0'), tk.StringVar(value='15'), tk.StringVar(value='0.1')]
    stvs_tvars = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
    ents_tvars = []
    # stvs_tcomps = [tk.StringVar(value='1u'), tk.StringVar(value='1u'), tk.StringVar(value='10u')]
    stvs_tcomps = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
    ents_tcomps = []
    for i in range(3):
        lbls_tnames.append(ttk.Label(frm_tvars, text="V({}): ".format(param_list[i])))
        lbls_tnames[-1].grid(row=i, column=0, padx=5)
        ents_tvars.append(ttk.Entry(frm_tvars, textvariable=stvs_tvars[i], width=5))
        ents_tvars[i].grid(row=i, column=1, sticky="nsew")
        ttk.Label(frm_tvars, text="V, Compliance: ").grid(row=i, column=2, padx=5)
        ents_tcomps.append(ttk.Entry(frm_tvars, textvariable=stvs_tcomps[i], width=5))
        ents_tcomps[i].grid(row=i, column=3, sticky="nsew")
        ttk.Label(frm_tvars, text="V").grid(row=i, column=4, padx=5)

    # Transient parameters frame
    frm_params.rowconfigure([*range(7)], weight=1)
    frm_params.columnconfigure([0, 1, 2], weight=1)
    # ttk.Label(frm_params, text="Sampling parameter: ").grid(row=0, column=0, sticky="e")
    ttk.Label(frm_params, text="Y-axis scale: ").grid(row=1, column=0, sticky="e")
    ttk.Label(frm_params, text="Interval: ").grid(row=2, column=0, sticky="e")
    ttk.Label(frm_params, text="No. of samples: ").grid(row=3, column=0, sticky="e")
    ttk.Label(frm_params, text="Total sampling time: ").grid(row=4, column=0, sticky="e")
    ttk.Label(frm_params, text="Hold time: ").grid(row=5, column=0, sticky="e")
    global stv_name
    # stv_name, stv_linlog, stv_int, stv_n, stv_tot, stv_hold = tk.StringVar(value=param_list[2]), \
    # tk.StringVar(value="Linear"), tk.StringVar(value='400m'), \
    # tk.StringVar(value='11'), tk.StringVar(value='4.0'), tk.StringVar(value='0.1')
    stv_name, stv_linlog, stv_int, stv_n, stv_tot, stv_hold = tk.StringVar(value=param_list[0]), \
                                                              tk.StringVar(value='Linear'), tk.StringVar(), \
                                                              tk.StringVar(), tk.StringVar(), tk.StringVar()
    global stv_var1
    stv_name.set(stv_var1.get())  # ?????
    # stv_int.trace("w", lambda name, index, mode, var=stv_int: update_time_params('int'))
    # stv_n.trace("w", lambda name, index, mode, var=stv_int: update_time_params('n'))
    # stv_tot.trace("w", lambda name, index, mode, var=stv_int: update_time_params('tot'))
    global drp_name
    drp_name = ttk.OptionMenu(frm_params, stv_name, stv_name.get(), *param_list)
    drp_name["state"] = tk.DISABLED
    # drp_name.grid(row=0, column=1, sticky="ew")
    drp_linlog = ttk.OptionMenu(frm_params, stv_linlog, stv_linlog.get(), "Linear", "Logarithmic")
    drp_linlog.grid(row=1, column=1, sticky="ew")
    ent_int = ttk.Entry(frm_params, textvariable=stv_int)
    ent_int.grid(row=2, column=1)
    ent_int.bind("<FocusOut>", lambda e: update_time_params(stv_int, 'int'))
    ent_n = ttk.Entry(frm_params, textvariable=stv_n)
    ent_n.grid(row=3, column=1)
    ent_n.bind("<FocusOut>", lambda e: update_time_params(stv_n, 'n'))
    ent_tot = ttk.Entry(frm_params, textvariable=stv_tot)
    ent_tot.grid(row=4, column=1)
    ent_tot.bind("<FocusOut>", lambda e: update_time_params(stv_tot, 'tot'))
    ent_hold = ttk.Entry(frm_params, textvariable=stv_hold)
    ent_hold.grid(row=5, column=1)
    ttk.Label(frm_params, text="WARNING: ", foreground="red").grid(row=6, column=0, sticky="ne")
    ttk.Label(frm_params, text="Actual interval and total time \nwill be much longer!")\
        .grid(row=6, column=1, columnspan=2, sticky="nw")
    inv_limit_time = tk.IntVar(value=1)
    chk_limit_time = ttk.Checkbutton(frm_params, text="Limit run time to the set value", variable=inv_limit_time,
                                     onvalue=1, offvalue=0)
    chk_limit_time.grid(row=7, column=0, columnspan=3, padx=10, sticky="nsw")
    btn_select_trans = ttk.Button(frm_params, text="Select transistors", command=lambda: open_trans_selection())
    btn_select_trans.grid(row=8, column=0, padx=20, pady=10, sticky="nsew")
    btn_run_time = ttk.Button(frm_params, text="Run transient experiment", command=lambda: run_time([stvs_tvars, stvs_tcomps, stv_name, [stv_int, stv_n, stv_tot, stv_hold], stv_linlog]))
    btn_run_time.grid(row=8, column=1, columnspan=2, padx=20, pady=10, sticky="nsew")
    ttk.Label(frm_params, text=" sec").grid(row=2, column=2, padx=5, sticky="w")
    ttk.Label(frm_params, text=" sec").grid(row=4, column=2, padx=5, sticky="w")
    ttk.Label(frm_params, text=" sec").grid(row=5, column=2, padx=5, sticky="w")

    # Save/Load frame
    with open("data/configs_t.csv", newline='') as f:
        csv_reader = reader(f)
        config_t_names = [row[0] for row in list(csv_reader)[1:]]  # Read the name of each config to config_names

    frm_tsaveload.columnconfigure([*range(8)], weight=1)
    frm_tsaveload.rowconfigure(0, weight=1)
    ttk.Label(frm_tsaveload, text="Save configuration as: ").grid(row=0, column=0, sticky="e")
    stv_t_savename = tk.StringVar()
    stv_t_loadname = tk.StringVar()
    ent_savename = ttk.Entry(frm_tsaveload, textvariable=stv_t_savename)
    ent_savename.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    btn_save = ttk.Button(frm_tsaveload, text="Save", command=lambda: save_t_config())
    btn_save.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
    ttk.Label(frm_tsaveload, text="Load configuration: ").grid(row=0, column=3, sticky="e")
    drp_load = ttk.OptionMenu(frm_tsaveload, stv_t_loadname, None, *config_t_names)
    drp_load.grid(row=0, column=4, sticky="nsew", padx=10, pady=10)
    btn_load = ttk.Button(frm_tsaveload, text="Load", command=lambda: load_t_config())
    btn_load.grid(row=0, column=5, sticky="nsew", padx=10, pady=10)
    btn_edit = ttk.Button(frm_tsaveload, text="Edit", command=lambda: save_t_config(True))
    btn_edit.grid(row=0, column=6, sticky="nsew", padx=10, pady=10)
    btn_delete = ttk.Button(frm_tsaveload, text="Delete", command=lambda: delete_t_config())
    btn_delete.grid(row=0, column=7, sticky="nsew", padx=10, pady=10)


def init_import_tab():
    # Lets the user import an experiment from Excel, by pasting the columns.
    tab_import.columnconfigure(0, weight=1)
    tab_import.rowconfigure(0, weight=1)

    import_tabs = ttk.Notebook(tab_import)
    import_tabs.grid(row=0, column=0, sticky="nsew")
    tab_imp_sweep = ttk.Frame(import_tabs)  # To import characteristic, exposure, and periodic sweep experiments.
    import_tabs.add(tab_imp_sweep, text="Sweep")
    tab_imp_time = ttk.Frame(import_tabs)  # To import transient experiments.
    import_tabs.add(tab_imp_time, text="Transient")

    tab_imp_sweep.columnconfigure([*range(4)], weight=1, minsize=w_width / 4)
    tab_imp_sweep.rowconfigure(0, weight=1)
    frm_imp_prim = ttk.Frame(tab_imp_sweep, relief=tk.RAISED, borderwidth=2)
    frm_imp_prim.grid(row=0, column=0, sticky="nsew")
    frm_imp_sec = ttk.Frame(tab_imp_sweep, relief=tk.RAISED, borderwidth=2)
    frm_imp_sec.grid(row=0, column=1, sticky="nsew")
    frm_imp_i0 = ttk.Frame(tab_imp_sweep, relief=tk.RAISED, borderwidth=2)
    frm_imp_i0.grid(row=0, column=2, sticky="nsew")
    frm_imp_ia = ttk.Frame(tab_imp_sweep, relief=tk.RAISED, borderwidth=2)
    frm_imp_ia.grid(row=0, column=3, sticky="nsew")
    frm_imp_prim.columnconfigure(0, weight=1)
    frm_imp_sec.columnconfigure(0, weight=1)
    frm_imp_i0.columnconfigure(0, weight=1)
    frm_imp_ia.columnconfigure(0, weight=1)
    stv_imp_prim = tk.StringVar(name='stv_imp_prim')  # The names will be used in paste_excel() to refer to them
    stv_imp_sec = tk.StringVar(name='stv_imp_sec')    # (as opposed to 'PY_VAR##')
    stv_imp_i0 = tk.StringVar(name='stv_imp_i0')
    stv_imp_ia = tk.StringVar(name='stv_imp_ia')
    ttk.Label(frm_imp_prim, text="Primary Variable: ").grid(row=0, column=0, sticky="w")
    ent_imp_prim = ttk.Entry(frm_imp_prim, textvariable=stv_imp_prim, width=4)
    ent_imp_prim.grid(row=0, column=1, padx=10)
    ttk.Label(frm_imp_sec, text="Secondary Variable: ").grid(row=0, column=0, sticky="w")
    ent_imp_sec = ttk.Entry(frm_imp_sec, textvariable=stv_imp_sec, width=4)
    ent_imp_sec.grid(row=0, column=1, padx=10)
    ttk.Label(frm_imp_i0, text="Dry-air results: ").grid(row=0, column=0, sticky="w")
    ent_imp_i0 = ttk.Entry(frm_imp_i0, textvariable=stv_imp_i0, width=4)
    ent_imp_i0.grid(row=0, column=1, padx=10)
    ttk.Label(frm_imp_ia, text="Post-exposure results: ").grid(row=0, column=0, sticky="w")
    ent_imp_ia = ttk.Entry(frm_imp_ia, textvariable=stv_imp_ia, width=4)
    ent_imp_ia.grid(row=0, column=1, padx=10)

    tab_imp_time.columnconfigure([*range(5)], weight=1, minsize=w_width / 5)
    tab_imp_time.rowconfigure(0, weight=1)
    frm_imp_time = ttk.Frame(tab_imp_time, relief=tk.RAISED, borderwidth=2)
    frm_imp_time.grid(row=0, column=0, sticky="nsew")
    frm_imp_i1 = ttk.Frame(tab_imp_time, relief=tk.RAISED, borderwidth=2)
    frm_imp_i1.grid(row=0, column=1, sticky="nsew")
    frm_imp_i2 = ttk.Frame(tab_imp_time, relief=tk.RAISED, borderwidth=2)
    frm_imp_i2.grid(row=0, column=2, sticky="nsew")
    frm_imp_i3 = ttk.Frame(tab_imp_time, relief=tk.RAISED, borderwidth=2)
    frm_imp_i3.grid(row=0, column=3, sticky="nsew")
    frm_imp_i4 = ttk.Frame(tab_imp_time, relief=tk.RAISED, borderwidth=2)
    frm_imp_i4.grid(row=0, column=4, sticky="nsew")
    frm_imp_time.columnconfigure(0, weight=1)
    frm_imp_i1.columnconfigure(0, weight=1)
    frm_imp_i2.columnconfigure(0, weight=1)
    frm_imp_i3.columnconfigure(0, weight=1)
    frm_imp_i4.columnconfigure(0, weight=1)
    stv_imp_i1, stv_imp_i2, stv_imp_i3, stv_imp_i4 = tk.StringVar(name='stv_imp_i1'), tk.StringVar(name='stv_imp_i2'), \
                                                     tk.StringVar(name='stv_imp_i3'), tk.StringVar(name='stv_imp_i4')
    ttk.Label(frm_imp_time, text="Time: ").grid(row=0, column=0, sticky="w")
    ttk.Label(frm_imp_i1, text="Main current: ").grid(row=0, column=0, sticky="w")
    ent_imp_i1 = ttk.Entry(frm_imp_i1, textvariable=stv_imp_i1, width=4)
    ent_imp_i1.grid(row=0, column=1, padx=10)
    ttk.Label(frm_imp_i2, text="Additional current: ").grid(row=0, column=0, sticky="w")
    ent_imp_i2 = ttk.Entry(frm_imp_i2, textvariable=stv_imp_i2, width=4)
    ent_imp_i2.grid(row=0, column=1, padx=10)
    ttk.Label(frm_imp_i3, text="Additional current: ").grid(row=0, column=0, sticky="w")
    ent_imp_i3 = ttk.Entry(frm_imp_i3, textvariable=stv_imp_i3, width=4)
    ent_imp_i3.grid(row=0, column=1, padx=10)
    ttk.Label(frm_imp_i4, text="Source current: ").grid(row=0, column=0, sticky="w")
    ent_imp_i4 = ttk.Entry(frm_imp_i4, textvariable=stv_imp_i4, width=4)
    ent_imp_i4.grid(row=0, column=1, padx=10)

    global var_ia, var_i4  # ??? Why is this required?
    var_prim, var_sec, var_i0, var_ia, var_time, var_i1, var_i2, var_i3, var_i4 = [], [], [], [], [], [], [], [], []
    global notes
    notes = ''
    lbls_prim, lbls_sec, lbls_i0, lbls_ia, lbls_time, lbls_i1, lbls_i2, lbls_i3, lbls_i4 = [], [], [], [], [], [], [], \
                                                                                           [], [],
    for i in range(10):
        lbls_prim.append(ttk.Label(frm_imp_prim, text="0"))
        lbls_prim[-1].grid(row=i + 2, column=0, columnspan=2)
        lbls_sec.append(ttk.Label(frm_imp_sec, text="0"))
        lbls_sec[-1].grid(row=i + 2, column=0, columnspan=2)
        lbls_i0.append(ttk.Label(frm_imp_i0, text="0"))
        lbls_i0[-1].grid(row=i + 2, column=0, columnspan=2)
        lbls_ia.append(ttk.Label(frm_imp_ia, text="0"))
        lbls_ia[-1].grid(row=i + 2, column=0, columnspan=2)
        lbls_time.append(ttk.Label(frm_imp_time, text="0"))
        lbls_time[-1].grid(row=i + 2, column=0, columnspan=2)
        lbls_i1.append(ttk.Label(frm_imp_i1, text="0"))
        lbls_i1[-1].grid(row=i + 2, column=0, columnspan=2)
        lbls_i2.append(ttk.Label(frm_imp_i2, text="0"))
        lbls_i2[-1].grid(row=i + 2, column=0, columnspan=2)
        lbls_i3.append(ttk.Label(frm_imp_i3, text="0"))
        lbls_i3[-1].grid(row=i + 2, column=0, columnspan=2)
        lbls_i4.append(ttk.Label(frm_imp_i4, text="0"))
        lbls_i4[-1].grid(row=i + 2, column=0, columnspan=2)
    ttk.Label(frm_imp_prim, text="...").grid(row=12, column=0, columnspan=2)
    ttk.Label(frm_imp_sec, text="...").grid(row=12, column=0, columnspan=2)
    ttk.Label(frm_imp_i0, text="...").grid(row=12, column=0, columnspan=2)
    ttk.Label(frm_imp_ia, text="...").grid(row=12, column=0, columnspan=2)
    ttk.Label(frm_imp_time, text="...").grid(row=12, column=0, columnspan=2)
    ttk.Label(frm_imp_i1, text="...").grid(row=12, column=0, columnspan=2)
    ttk.Label(frm_imp_i2, text="...").grid(row=12, column=0, columnspan=2)
    ttk.Label(frm_imp_i3, text="...").grid(row=12, column=0, columnspan=2)
    ttk.Label(frm_imp_i4, text="...").grid(row=12, column=0, columnspan=2)

    btn_paste_prim = ttk.Button(frm_imp_prim, text="Paste", command=lambda l=lbls_prim: paste_excel('prim', l))
    btn_paste_prim.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
    btn_paste_sec = ttk.Button(frm_imp_sec, text="Paste", command=lambda l=lbls_sec: paste_excel('sec', l))
    btn_paste_sec.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
    btn_paste_i0 = ttk.Button(frm_imp_i0, text="Paste", command=lambda l=lbls_i0: paste_excel('i0', l))
    btn_paste_i0.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
    btn_paste_ia = ttk.Button(frm_imp_ia, text="Paste", command=lambda l=lbls_ia: paste_excel('ia', l))
    btn_paste_ia.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
    btn_remove_ia = ttk.Button(frm_imp_ia, text="Remove", command=lambda: remove_ia())
    btn_remove_ia.grid(row=1, column=1, sticky="ew", padx=10, pady=10)

    btn_paste_time = ttk.Button(frm_imp_time, text="Paste", command=lambda l=lbls_time: paste_excel('time', l))
    btn_paste_time.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
    btn_paste_i1 = ttk.Button(frm_imp_i1, text="Paste", command=lambda l=lbls_i1: paste_excel('i1', l))
    btn_paste_i1.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
    btn_paste_i2 = ttk.Button(frm_imp_i2, text="Paste", command=lambda l=lbls_i2: paste_excel('i2', l))
    btn_paste_i2.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
    btn_paste_i3 = ttk.Button(frm_imp_i3, text="Paste", command=lambda l=lbls_i3: paste_excel('i3', l))
    btn_paste_i3.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
    btn_paste_i4 = ttk.Button(frm_imp_i4, text="Paste", command=lambda l=lbls_i4: paste_excel('i4', l))
    btn_paste_i4.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)


    # Info frame: 2x7 (actually 2x13)
    frm_imp_info = ttk.Frame(tab_import, relief=tk.RAISED, borderwidth=2)
    frm_imp_info.grid(row=1, column=0, sticky="nsew")
    ttk.Label(frm_imp_info, text="Date: ").grid(row=0, column=0)
    ttk.Label(frm_imp_info, text="Operator: ").grid(row=0, column=2)
    ttk.Label(frm_imp_info, text="Gas: ").grid(row=0, column=4)
    ttk.Label(frm_imp_info, text="Concentration: ").grid(row=0, column=6)
    ttk.Label(frm_imp_info, text="Carrier: ").grid(row=0, column=8)
    ttk.Label(frm_imp_info, text="Atmosphere: ").grid(row=0, column=10)
    ttk.Label(frm_imp_info, text="Serial No.: ").grid(row=0, column=12)
    ttk.Label(frm_imp_info, text="Transistor: ").grid(row=1, column=0)
    ttk.Label(frm_imp_info, text="Decoration: ").grid(row=1, column=2)
    ttk.Label(frm_imp_info, text="Dec. thickness: ").grid(row=1, column=4)
    ttk.Label(frm_imp_info, text="Temperature: ").grid(row=1, column=6)
    ttk.Label(frm_imp_info, text="Humidity: ").grid(row=1, column=8)

    stvs_imp_info = []
    ents_imp_info = []
    for i in range(12):
        r = i // 7
        c = (i % 7) * 2 + 1
        stvs_imp_info.append(tk.StringVar())
        ents_imp_info.append(ttk.Entry(frm_imp_info, textvar=stvs_imp_info[i], width=5))
        ents_imp_info[-1].grid(row=r, column=c)
    btn_imp_notes = ttk.Button(frm_imp_info, text="Add notes", command=lambda: add_notes())
    btn_imp_notes.grid(row=1, column=10, columnspan=2, sticky="nsew", padx=5, pady=5)
    btn_import = ttk.Button(frm_imp_info, text="Import", command=lambda: import_data())
    btn_import.grid(row=1, column=12, columnspan=2, sticky="nsew", padx=5, pady=5)

    def paste_excel(var, lbls):
        """
        Reads the data from the clipboard and pastes it in the column corresponding to the paste button that was
        pressed. If the data has headers, it removes them and saves them in the corresponding StringVar.
        :param var: The global(?) variable the data should be saved in.
        :param lbls: The label list in which the first 10 values will be displayed.
                    Can be 'prim', 'sec', 'i0', 'ia', 'time', and 'i1' through 'i4'.
        :return:
        """
        header_stvs = [stv_imp_prim, stv_imp_sec, stv_imp_i0, stv_imp_ia, stv_imp_i1, stv_imp_i2, stv_imp_i3,
                       stv_imp_i4]  # To include them in locals()
        values = window.clipboard_get().split('\n')[:-1]  # The last element will always be \n, so we can clip it.
        if len(values) < 3:  # TODO: Untrue
            tk.messagebox.showerror('', "Invalid data in clipboard!")
            return
        all_numeric = True
        header_set = False  # So that the header is set to the first row (if a header exists in the file).
        for i in range(2):  # Clip the first two rows if they're used as headers (TODO: change)
            if not numeric(values[0]):
                temp_header = values.pop(0)
                if var != 'time' and not header_set:
                    locals()['stv_imp_'+var].set(temp_header)
                    header_set = True
        for x in values:
            if not numeric(x):
                all_numeric = False
        if not all_numeric:
            messagebox.showerror("Paste Error", "All values must be numeric!")
            return
        for i in range(min(10, len(values))):
            lbls[i]["text"] = values[i]
        globals()['var_'+var] = values  # So for example, if var == 'prim', it updates var_prim.

    def remove_ia():
        global var_ia
        var_ia = []
        for i in range(10):
            lbls_ia[i]["text"] = '0'

    def add_notes():
        global notes
        notes = simpledialog.askstring("", "Enter notes")

    def import_data():
        """
        Saves the entered data as an experiment.
        """
        id_tab = import_tabs.index(import_tabs.select())  # Gets the currently selected tab
        if id_tab == 0:  # Sweep
            p = stv_imp_prim.get()
            s = stv_imp_sec.get()
            i0 = stv_imp_i0.get()
            ia = stv_imp_ia.get()
            # Determine the var order and store it in imp_vars
            options = ['J', 'B', 'D']
            newstr = [extract_var_letter(x) for x in [p, s]]
            if newstr[0] not in options or newstr[1] not in options:
                messagebox.showerror('', "Invalid variable names. Please include the letters j, b or d in the names, to "
                                         "denote the JG, BG and Drain respectively. ")
                return
            if newstr[0] == newstr[1]:
                messagebox.showerror('', "Please choose two different variables (JG, BG, D).")
                return
            for i in newstr:
                options.remove(i)
            newstr.append(options[0])
            imp_vars = ''.join(newstr)
        elif id_tab == 1:
            imp_vars = 'T' + extract_var_letter(stv_imp_i1.get())
        # Determine the new index
        params = [s.get() for s in stvs_imp_info]
        index = 0
        with open("data/central.csv", newline='') as f:
            csv_reader = reader(f)
            ids = [int(row[0]) for row in list(csv_reader)[1:]]
        if len(ids) != 0:
            index = max(ids) + 1
        # Determine the measurement type, catch format errors, and finally store the names and data in data_to_imp.
        global var_prim, var_sec, var_i0, var_ia, var_time, var_i1, var_i2, var_i3, var_i4
        try:
            if id_tab == 0:
                if var_ia != []:
                    if not len(var_prim) == len(var_sec) == len(var_i0) == len(var_ia):
                        messagebox.showerror('', "All columns must be the same length.")
                        return
                    data_to_imp = [list(x) for x in zip(var_sec, var_prim, var_i0, var_ia)]
                    data_to_imp = [[s, p, i0, ia], *data_to_imp]
                else:
                    if not len(var_prim) == len(var_sec) == len(var_i0):
                        messagebox.showerror('', "All columns must be the same length.")
                        return
                    data_to_imp = [list(x) for x in zip(var_sec, var_prim, var_i0)]
                    data_to_imp = [[s, p, i0], *data_to_imp]
                    imp_vars = 'C' + imp_vars
            elif id_tab == 1:
                if var_i4 != []:
                    if not len(var_time) == len(var_i1) == len(var_i2) == len(var_i3) == len(var_i4):
                        messagebox.showerror('', "All columns must be the same length.")
                        return
                    data_to_imp = [list(x) for x in zip(var_time, var_i1, var_i2, var_i3, var_i4)]
                    t_names = ['Time (sec)', *[x.get() for x in [stv_imp_i1, stv_imp_i2, stv_imp_i3, stv_imp_i4]]]
                    data_to_imp = [t_names, *data_to_imp]
                else:
                    if not len(var_time) == len(var_i1) == len(var_i2) == len(var_i3):
                        messagebox.showerror('', "All columns must be the same length.")
                        return
                    data_to_imp = [list(x) for x in zip(var_time, var_i1, var_i2, var_i3)]
                    t_names = ['Time (sec)', *[x.get() for x in [stv_imp_i1, stv_imp_i2, stv_imp_i3]]]
                    data_to_imp = [t_names, *data_to_imp]
        except NameError:
            tb = str(traceback.format_exc())
            messagebox.showerror('', "Invalid data. Please try pasting again. \nTraceback: " + tb)
            return
        global notes
        params_to_file = [index, *params, imp_vars, notes]

        add_experiment(*params_to_file, data_to_imp)
        messagebox.showinfo('', 'Experiment imported successfully. ')
        # update_table()


def init_analysis_tab():
    """
    Allows the user to analyze the experiments.
    """
    def enable_buttons(enable=True, meas=None):
        """
        Enables/disables the analysis buttons.
        :param enable: False if all the buttons should be disabled. True if any of them should be enabled.
        :param meas: The type of the selected experiment. Can be None/'char'/'exposure'/'transient'.
        """
        state_s, state_mult, state_t, state_file = tk.DISABLED, tk.DISABLED, tk.DISABLED, tk.DISABLED
        """
        The state_# variables define the state of each group of buttons: 
        - s: Buttons related to characteristic, exposure, or periodic sweep experiments. 
        - mult: Buttons related to exposure experiments (i.e. that require both 'before' and 'after' measurements). 
        - t: Buttons related to transient experiments. 
        - file: Open in Excel, Edit, Delete. 
        All four are initially set to DISABLED, and enabled based on the measurement type. 
        """
        if enable and meas == None:  # If called from the table radiobutton
            selected = tree.item(tree.focus()).get("values")
            if selected is not None and selected != '':  # "This triggers BEFORE the row is actually selected!!" - Not sure if fixed
                var_order = selected[-2]
                state_file = tk.NORMAL  # The option to edit/delete/etc is relevant to any type of experiment
                if len(var_order) == 3:  # Exposure experiment (before+after)
                    state_s = tk.NORMAL
                    state_mult = tk.NORMAL
                elif len(var_order) == 4:  # Characteristic or periodic sweep
                    state_s = tk.NORMAL
                elif len(var_order) == 2:  # Transient measurement
                    state_t = tk.NORMAL
        elif meas == 'char':  # If called from the 'last experiment' radiobutton
            state_s = tk.NORMAL
        elif meas == 'exposure':
            state_s = tk.NORMAL
            state_mult = tk.NORMAL
        elif meas == 'transient':
            state_t = tk.NORMAL
        # Now, set each button to the state of its respective group.
        btn_open["state"] = state_file
        btn_delete["state"] = state_file
        btn_edit["state"] = state_file
        btn_iv0["state"] = state_s
        btn_iva["state"] = state_mult
        btn_vth["state"] = state_s
        btn_response["state"] = state_mult
        btn_maxres["state"] = state_mult
        btn_sts["state"] = state_s
        btn_ioff["state"] = state_s
        btn_ion["state"] = state_s
        btn_i0_heatmap["state"] = state_s
        btn_ia_heatmap["state"] = state_mult
        btn_it["state"] = state_t
        btn_t_ioffon["state"] = state_t
        btn_t_risefall["state"] = state_t
        btn_t_fit["state"] = tk.DISABLED  # Temporarily

    def delete_experiment():
        """
        Deletes the selected experiment - both the ex_#.csv file and its row in central.csv.
        """
        if tk.messagebox.askyesno('', "This will also remove the experiment's data. Proceed?"):
            try:
                del_id = tree.item(tree.focus()).get("values")[0]  # Get the ID of the selected row
                del_path = "data/ex_" + str(del_id) + ".csv"  # Turn it into the desired file's path
                if os.path.isfile(del_path):  # If the path exists
                    os.remove(del_path)
                else:
                    tk.messagebox.showerror('', "File does not exist! (ID: " + del_id + ")")
                    return
                with open("data/central.csv", newline='') as f:  # Get the existing data for all experiments
                    csv_reader = reader(f)
                    existing_data = list(csv_reader)
                with open("data/central.csv", "w", newline='') as f:  # Rewrite everything except the row to be deleted
                    csv_writer = writer(f)
                    for row in existing_data:
                        if row[0] != str(del_id):
                            csv_writer.writerow(row)
                update_table(tree)  # Update the table
                enable_buttons(enable=False)  # Since nothing is selected now, disable all the buttons
                messagebox.showinfo('', 'Experiment deleted. ')
            except PermissionError as e:
                tb = str(traceback.format_exc())
                if 'used by another process' in tb:
                    messagebox.showerror('', "The experiment file is open in another program. Please close it and try "
                                             "again.")
                else:  # Just in case
                    messagebox.showerror('', "Permission error: Please make sure the experiment file is not open in "
                                             "another program.")
                return

    def edit_experiment():
        """
        Allows the user to edit any of the selected experiment's parameters (excluding the variable order/experiment
        type) in a separate dialog window.
        """
        edit_row = tree.item(tree.focus()).get("values")  # Get the values of the selected row
        edit_window_out = tk.Toplevel(window)  # Open a new window
        edit_window_out.title("Edit experiment #" + str(edit_row[0]))
        edit_window_out.rowconfigure(0, weight=1)
        edit_window_out.columnconfigure(0, weight=1)
        edit_window = ttk.Frame(edit_window_out)  # The frame covers the whole window, to match the style
        edit_window.grid(row=0, column=0, sticky="nsew")
        edit_window.rowconfigure([0, 1], weight=1)
        edit_window.columnconfigure([*range(14)], weight=1)
        # The labels for each parameter
        ttk.Label(edit_window, text="Date: ").grid(row=0, column=0, sticky="e")
        ttk.Label(edit_window, text="Operator: ").grid(row=0, column=2, sticky="e")
        ttk.Label(edit_window, text="Gas: ").grid(row=0, column=4, sticky="e")
        ttk.Label(edit_window, text="Gas concentration: ").grid(row=0, column=6, sticky="e")
        ttk.Label(edit_window, text="Carrier: ").grid(row=0, column=8, sticky="e")
        ttk.Label(edit_window, text="Atmosphere: ").grid(row=0, column=10, sticky="e")
        ttk.Label(edit_window, text="Device (serial no.): ").grid(row=0, column=12, sticky="e")
        ttk.Label(edit_window, text="Transistor: ").grid(row=1, column=0, sticky="e")
        ttk.Label(edit_window, text="Decoration: ").grid(row=1, column=2, sticky="e")
        ttk.Label(edit_window, text="Dec. thickness: ").grid(row=1, column=4, sticky="e")
        ttk.Label(edit_window, text="Temperature: ").grid(row=1, column=6, sticky="e")
        ttk.Label(edit_window, text="Humidity: ").grid(row=1, column=8, sticky="e")
        ttk.Label(edit_window, text="Notes: ").grid(row=1, column=10, sticky="e")
        edit_row.remove(edit_row[2])  # Ex. type
        edit_row.remove(edit_row[-2])  # Variables
        edit_stvs = []  # The StringVar()s associated with each of the entryboxes
        edit_ents = []  # The entryboxes in which the values will be displayed
        for i in range(13):
            r = i // 7  # Row 0 for 0-6, row 1 for 7-12
            c = (i % 7) * 2 + 1  # Odd numbers from 1 to 13, then from 1 to 11.
            edit_stvs.append(tk.StringVar(value=str(edit_row[i + 1])))
            edit_ents.append(ttk.Entry(edit_window, textvar=edit_stvs[i], width=5))
            if i < 12:  # To configure the "Notes" entry separately.
                edit_ents[-1].grid(row=r, column=c, sticky="ew")
            # Save when enter is pressed on any of the entryboxes
            edit_ents[-1].bind("<Return>", lambda e: finish_edit(edit_row[0]))
        edit_ents[-1]["width"] = 15  # Make the "Notes" entrybox wider than the rest (though the columnspan takes care
        # of it already... Unnecessary?!)
        edit_ents[-1].grid(row=1, column=11, columnspan=2, sticky="w")
        edit_ents[-1].bind("<Return>", lambda e: finish_edit(edit_row[0]))
        btn_finish_edit = ttk.Button(edit_window, text="Confirm", command=lambda: finish_edit(edit_row[0]))
        btn_finish_edit.grid(row=1, column=13, sticky="nsew", padx=10, pady=5)

        def finish_edit(edit_id):
            """
            Saves the edited experiment's info by updating its respective row in central.csv.
            :param edit_id: The ID of the experiment to be updated.
            """
            with open("data/central.csv", newline='') as f:  # Get the existing data for all experiments
                csv_reader = reader(f)
                existing_data = list(csv_reader)
            with open("data/central.csv", "w", newline='') as f:  # Rewrite each row, but use the new data for the row
                # to be updated.
                csv_writer = writer(f)
                for row in existing_data:
                    if row[0] == str(edit_id):
                        csv_writer.writerow([str(edit_id), *[x.get() for x in edit_stvs[:-1]], row[13],
                                             edit_stvs[-1].get()])  # row[13] is the var order
                    else:
                        csv_writer.writerow(row)
            edit_window_out.destroy()
            update_table(tree)  # Update the table
            enable_buttons(enable=False)  # Disable all the buttons

    def temp_update_table(t):
        """
        Whenever the "Analysis" tab is accessed, the table must be updated. So this function calls update_table(), but
        also disables the buttons since none of the experiments will be selected. Might redo this idea sometime.
        :param t: The table, to be passed on to update_table().
        """
        if control_tabs.tab(control_tabs.select(), "text") == "Analysis":
            # Only update the table if you're going to see it
            update_table(t)
            enable_buttons(enable=False)

    tab_analysis.rowconfigure([0, 1], weight=1)
    tab_analysis.columnconfigure(0, weight=1)
    frm_table = ttk.Frame(tab_analysis, relief=tk.RAISED, borderwidth=2)  # The frame containing the table, the...
    frm_table.grid(row=0, column=0, sticky="nsew")  # ...radiobuttons, and the open/edit/delete buttons.
    frm_table.rowconfigure([0, 2, 3], weight=1)
    frm_table.columnconfigure(0, weight=2)
    frm_table.columnconfigure([1, 2], weight=1)
    tree = ttk.Treeview(frm_table)  # The table that contains the experiment info
    tree.bind('<<TreeviewSelect>>', lambda e: enable_buttons())  # Whenever an experiment is selected, only enable the
    # buttons that are relevant to its type.
    tree.grid(row=0, column=0, columnspan=3, sticky="nsew")
    update_table(tree)  # Initialize the table
    control_tabs.bind("<<NotebookTabChanged>>", lambda e: temp_update_table(tree))  # Update it whenever the "Analysis"
    # tab is opened
    scrollbar_vertical = ttk.Scrollbar(frm_table, orient="vertical", command=tree.yview)
    scrollbar_vertical.grid(row=0, column=3, sticky="ns")
    scrollbar_horizontal = ttk.Scrollbar(frm_table, orient="horizontal", command=tree.xview)
    scrollbar_horizontal.grid(row=1, column=0, columnspan=3, sticky="ew")
    tree["yscrollcommand"] = scrollbar_vertical.set
    tree["xscrollcommand"] = scrollbar_horizontal.set

    global meas_type
    inv_input = tk.IntVar(value=0)  # Determines whether to use the data from the selected entry in the table or from
    # the last performed experiment.
    rdb_input1 = ttk.Radiobutton(frm_table, text="Use data from table", variable=inv_input, value=0,
                                 command=lambda: enable_buttons(enable=False))
    rdb_input1.grid(row=2, column=0, sticky="w")
    rdb_input2 = ttk.Radiobutton(frm_table, text="Use data from last experiment", variable=inv_input, value=1,
                                 command=lambda: enable_buttons(True, meas_type))
    rdb_input2.grid(row=3, column=0, sticky="w")
    btn_open = ttk.Button(frm_table, text="Open experiment data", state=tk.DISABLED, command=lambda: open_excel())
    btn_open.grid(row=2, column=1, columnspan=2, sticky="nsew", padx=10, pady=5)
    btn_delete = ttk.Button(frm_table, text="Delete experiment", state=tk.DISABLED, command=lambda: delete_experiment())
    btn_delete.grid(row=3, column=1, sticky="nsew", padx=10, pady=5)
    btn_edit = ttk.Button(frm_table, text="Edit experiment", state=tk.DISABLED, command=lambda: edit_experiment())
    btn_edit.grid(row=3, column=2, sticky="nsew", padx=10, pady=5)

    global data_prim, data_sec, data_i0, data_ia
    data_prim, data_sec, data_i0, data_ia = [], [], [], []  # Initialize the four data lists
    label_prim, label_sec, label_const = '', '', ''  # And the labels

    analysis_tabs = ttk.Notebook(tab_analysis)  # One tab for sweep analysis, one tab for transient analysis.
    analysis_tabs.grid(row=1, column=0, sticky="nsew")

    tab_a_sweep = ttk.Frame(analysis_tabs)
    analysis_tabs.add(tab_a_sweep, text="Sweep")
    tab_a_sweep.columnconfigure([*range(5)], weight=1)
    tab_a_sweep.rowconfigure([0, 1], weight=1)
    btn_iv0 = ttk.Button(tab_a_sweep, text="Plot I-V (before)", command=lambda: show_iv(False), state=tk.DISABLED)
    btn_iv0.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    btn_iva = ttk.Button(tab_a_sweep, text="Plot I-V (after)", command=lambda: show_iv(True), state=tk.DISABLED)
    btn_iva.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    btn_vth = ttk.Button(tab_a_sweep, text="Plot threshold voltage", command=lambda: show_vth(), state=tk.DISABLED)
    btn_vth.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
    btn_response = ttk.Button(tab_a_sweep, text="Plot response", command=lambda: show_response(False),
                              state=tk.DISABLED)
    btn_response.grid(row=0, column=3, sticky="nsew", padx=10, pady=10)
    btn_maxres = ttk.Button(tab_a_sweep, text="Plot max. response", command=lambda: show_response(True),
                            state=tk.DISABLED)
    btn_maxres.grid(row=0, column=4, sticky="nsew", padx=10, pady=10)
    btn_sts = ttk.Button(tab_a_sweep, text="Plot sub-threshold swing", command=lambda: show_sts(), state=tk.DISABLED)
    btn_sts.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    btn_ioff = ttk.Button(tab_a_sweep, text="Plot Ion&Ioff", command=lambda: show_ioffon(False), state=tk.DISABLED)
    btn_ioff.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
    btn_ion = ttk.Button(tab_a_sweep, text="Plot Ion/Ioff ratio", command=lambda: show_ioffon(True), state=tk.DISABLED)
    btn_ion.grid(row=1, column=2, sticky="nsew", padx=10, pady=10)
    btn_i0_heatmap = ttk.Button(tab_a_sweep, text="Plot current heatmap (before)",
                                command=lambda: show_i_heatmap(False), state=tk.DISABLED)
    btn_i0_heatmap.grid(row=1, column=3, sticky="nsew", padx=10, pady=10)
    btn_ia_heatmap = ttk.Button(tab_a_sweep, text="Plot current heatmap(after)", command=lambda: show_i_heatmap(True),
                                state=tk.DISABLED)
    btn_ia_heatmap.grid(row=1, column=4, sticky="nsew", padx=10, pady=10)

    tab_a_transient = ttk.Frame(analysis_tabs)
    analysis_tabs.add(tab_a_transient, text="Transient")
    tab_a_transient.rowconfigure(0, weight=1)
    tab_a_transient.columnconfigure([*range(4)], weight=1)
    btn_it = ttk.Button(tab_a_transient, text="Plot I-t", command=lambda: show_it(), state=tk.DISABLED)
    btn_it.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    btn_t_ioffon = ttk.Button(tab_a_transient, text="Show Ioff&Ion", command=lambda: show_t_ioffon(), state=tk.DISABLED)
    btn_t_ioffon.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    btn_t_risefall = ttk.Button(tab_a_transient, text="Show rise/fall time", command=lambda: show_t_risefall(),
                                state=tk.DISABLED)
    btn_t_risefall.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
    btn_t_fit = ttk.Button(tab_a_transient, text="Fit I-t curve", command=lambda: show_t_fit(), state=tk.DISABLED)
    btn_t_fit.grid(row=0, column=3, sticky="nsew", padx=10, pady=10)


    def load_data():
        """
        Reads the data of the selected experiment from its ex_#.csv file, or from the last performed experiment, and
        saves it in the data_#### variables.
        """
        global data_prim, data_sec, data_i0, data_ia
        if inv_input.get() == 0:  # Read from the ex_#.csv file associated with the selected row in the table
            global current_id
            new_id = tree.item(tree.focus()).get("values")[0]  # The ID of the selected row
            if new_id == current_id:  # If the same data has already been loaded, no need to do anything!
                return
            current_id = new_id  # Update current_id for the next time load_data() is called
            with open("data/ex_" + str(new_id) + ".csv", 'r', newline='') as f:  # Read the experiment's data
                reader = csv.reader(f)
                new_data = [list(x) for x in zip(*list(reader))]  # Transpose to obtain 3, 4 or 5 lists corresponding
                # to the columns.
            for col in new_data:
                while not numeric(col[0]):  # Remove the headers
                    col.pop(0)
            var_order = tree.item(tree.focus()).get("values")[-2]  # Get the variable abbreviation (e.g. "JBD")
            if len(var_order) == 3:  # Exposure -> Save in data_prim, data_sec, data_i0 and data_ia.
                data_prim, data_sec, data_i0, data_ia = spreadsheet_format_to_data(new_data[0], new_data[1],
                                                                                   new_data[2], new_data[3])
                data_i0 = off_noise(fix_e(data_i0), 1e-12)
                data_ia = off_noise(fix_e(data_ia), 1e-12)
            elif len(var_order) == 4:  # Characteristic or periodic sweep -> Don't save in data_ia!
                data_prim, data_sec, data_i0 = spreadsheet_format_to_data(new_data[0], new_data[1], new_data[2])
                data_ia = []  # Reset it completely
            elif len(var_order) == 2:  # Transient -> Save in data_prim and data_i0. Disregard the 3 additional currents
                data_prim = [float(x) for x in new_data[0]]
                data_i0 = off_noise(fix_e(new_data[1]), 1e-12)
                data_sec = []
                data_ia = []
            set_labels(var_order)  # Set the labels based on the abbreviation
        elif inv_input.get() == 1:  # Take the data from the meas_#### variables, convert them to the proper format, and
            # save them in the respective data_#### variables.
            global meas_prim, meas_sec, meas_i0, meas_ia, meas_order
            if data_sec != []:  # Not transient
                if data_ia != []:  # Exposure
                    data_prim, data_sec, data_i0, data_ia = spreadsheet_format_to_data(meas_sec, meas_prim, meas_i0,
                                                                                       meas_ia)
                else:  # Characteristic/periodic sweep
                    data_prim, data_sec, data_i0 = spreadsheet_format_to_data(meas_sec, meas_prim, meas_i0)
                    data_ia = []
            else:  # Transient
                data_prim = meas_prim
                data_i0 = meas_i0
            set_labels(meas_order)  # Set the labels based on the abbreviation
            current_id = -1  # Since the data might not match any of the experiments

    def show_iv(exposed):
        """
        Shows the I-V characteristic, where the x-axis is the primary variable's voltage, for each value of the
        secondary variable.
        :param exposed: If True, show the post-exposure characteristic; if False, show the pre-exposure characteristic.
        """
        try:
            load_data()
            global data_sec, data_prim, data_i0, data_ia, label_prim
            if exposed:  # Use either data_ia or data_i0, and set the y-axis label accordingly.
                plot_yvv(data_prim, data_sec, data_ia, label_prim, "$I_a (A)$", True)
            else:
                plot_yvv(data_prim, data_sec, data_i0, label_prim, "$I_0 (A)$", True)
        except ValueError as e:  # Most likely raised from within plot_yvv()
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, and all "
                                     "the values (besides the headers) are numeric.")
            # tb = traceback.format_exc()
            # logging.error(str(e) + ". Traceback: " + str(tb))
            global current_id
            current_id = -1
            return

    def show_vth():
        """
        Plots the threshold voltage against the secondary variable's voltage.
        If the selected experiment is an exposure experiment, it plots both pre- and post-exposure threshold voltages,
        as well as the difference between them (with a separate axis).
        """
        def vth_func(prim, sec, i):
            """
            Returns the threshold voltage extraction function based on the selected option.
            """
            global stv_s_vth, stv_s_const
            func = stv_s_vth.get()
            match func:
                case 'Constant':
                    try:
                        threshold = suffix(stv_s_const.get())
                    except ValueError as e:  # If the threshold wasn't properly set. Kinda hacky, but since ValueError
                        raise NameError  # is already taken, we raise a different error instead.
                    return vth_constant(prim, sec, i, threshold)
                case 'Linear extrapolation':
                    return vth_lin(prim, sec, i)
        try:
            load_data()
            global data_sec, data_prim, data_i0, data_ia, label_sec, current_id
            if data_ia != []:  # Exposure
                f_prim, f_sec, f_i0, f_ia = filter_regionless(data_prim, data_sec, data_i0, data_ia)  # See definition
                vt0 = vth_func(f_prim, f_sec, f_i0)  # Pre-exposure
                vta = vth_func(f_prim, f_sec, f_ia)  # Post-exposure
                # Plot all three curves:
                plot_yvv([f_sec] * 3, ['Dry air', 'Exposed', "$\Delta V_{TH} (V)$"],
                         [vt0, vta, [vt0[i] - vta[i] for i in range(len(vt0))]], label_sec, "$V_{TH} (V)$", False, True)
            else:  # Characteristic or periodic sweep
                f_prim, f_sec, f_i0 = filter_regionless(data_prim, data_sec, data_i0)
                vt0 = vth_func(f_prim, f_sec, f_i0)
                plot_yv(f_sec, vt0, label_sec, "$V_{TH} (V)$", True)
        except ValueError as e:  # Most likely raised from within plot_yvv() or plot_yv()
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, all the values "
                                     "(besides the headers) are numeric, and that the data spans multiple decades.")
            current_id = -1
            return
        except IndexError as e:  # If none of the measurements span the required range of decades, filter_regionless()
            # raises an IndexError (since the lists that would have been returned would be of length 0).
            messagebox.showerror('', "Invalid data: for this calculation, the data must span at least 2.5 decades. ")
            current_id = -1
            return
        except NameError:  # The constant threshold wasn't properly set
            messagebox.showerror('', "Please enter a valid threshold current (in the 'Settings' tab).")
            return

    def show_response(m):
        """
        Plots the response (in %) of the exposure experiment, either in a heatmap or in a graph showing the maximum
        response for each value of the secondary variable.
        :param m: If True, plots the max. response. If False, plots the whole response heatmap.
        """
        try:
            load_data()
            global data_sec, data_prim, data_i0, data_ia, label_prim, label_sec
            res = response(data_i0, data_ia)  # Calculate the response - returns a list of lists in the same format as
            # data_i0 and data_ia.
            if m:  # Max. response
                plot_yv(data_sec, [max(i)*100 for i in res], label_sec, "Max. response (%)")
            else:  # Response heatmap
                plot_heatmap([[x*100 for x in row] for row in res], data_sec, data_prim, label_sec, label_prim,
                             "Response (%)", interp=False)
        except ValueError as e:  # Most likely raised from within plot_yv() or plot_heatmap()
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, and all "
                                     "the values (besides the headers) are numeric. Actual error: \n" + str(e))
            global current_id
            current_id = -1
            return

    def show_sts():
        """
        Plots the sub-threshold swing for each value of the secondary variable.
        """
        try:
            load_data()
            global data_sec, data_prim, data_i0, data_ia, label_prim, label_sec, stv_s_sts
            try:
                try:
                    sts_val = suffix(stv_s_sts.get())
                    assert(0 < sts_val < 100)
                    threshold = 1 - sts_val / 100  # For example, "30" turns into 0.7.
                except (ValueError, AssertionError):  # If the threshold wasn't properly set. Kinda hacky, but since ValueError
                    raise NameError  # is already taken, we raise a different error instead.
                if data_ia != []:  # Exposure -> Plot both pre- and post-exposure STSs.
                    f_prim, f_sec, f_i0, f_ia = filter_regionless(data_prim, data_sec, data_i0, data_ia)
                    sts0 = [sts(f_prim[i], f_i0[i], threshold) for i in range(len(f_sec))]
                    stsa = [sts(f_prim[i], f_ia[i], threshold) for i in range(len(f_sec))]
                    plot_yvv([f_sec] * 2, ['Dry air', 'Exposed'], [[x * 1000 for x in sts0], [x * 1000 for x in stsa]],
                             label_sec, "S (mV/dec) (w.r.t. " + label_prim[:-4] + "$)", False)
                else:
                    f_prim, f_sec, f_i0 = filter_regionless(data_prim, data_sec, data_i0)
                    sts0 = [sts(f_prim[i], f_i0[i], threshold) for i in range(len(f_sec))]
                    plot_yv(f_sec, [x * 1000 for x in sts0], label_sec, "S (mV/dec) (w.r.t. " + label_prim[:-4] + "$)",
                            True)
            except ZeroDivisionError:
                messagebox.showerror('', 'There is not enough data in the sub-threshold region to calculate the swing.')
        except ValueError:  # Most likely raised from within plot_yvv() or plot_yv()
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, all the values "
                                     "(besides the headers) are numeric, and that the data spans multiple decades.")
            global current_id
            current_id = -1
            return
        except IndexError as e:  # If none of the measurements span the required range of decades, filter_regionless()
            # raises an IndexError (since the lists that would have been returned would be of length 0).
            messagebox.showerror('', "Invalid data: for this calculation, the data must span at least 2.5 decades. ")
            current_id = -1
            return
        except NameError:  # The constant threshold wasn't properly set
            messagebox.showerror('', "Please enter a valid subthreshold definition (in the 'Settings' tab).")
            return


    def show_ioffon(ratio):
        try:
            load_data()
            global data_sec, data_prim, data_i0, data_ia, label_sec, stv_s_ion
            on_th = suffix(stv_s_ion.get())
            if data_ia != []:
                f_prim, f_sec, f_i0, f_ia = filter_regionless(data_prim, data_sec, data_i0, data_ia)
                Ion0 = [ion(x, on_th) for x in f_i0]
                Iona = [ion(x, on_th) for x in f_ia]
                Ioff0 = [ioff(x) for x in f_i0]
                Ioffa = [ioff(x) for x in f_ia]
                if ratio:
                    plot_yvv([f_sec] * 2, ['Ion/Ioff (before)', 'Ion/Ioff (after)'],
                             [[Ion0[i] / Ioff0[i] for i in range(len(Ioff0))],
                              [Iona[i] / Ioffa[i] for i in range(len(Ioffa))]], label_sec, "$I (A)$", True)
                else:
                    plot_yvv([f_sec] * 4, ['Ioff (before)', 'Ioff (after)', 'Ion (before)', 'Ion (after)'],
                             [Ioff0, Ioffa, Ion0, Iona], label_sec, "$I (A)$", True)
            else:
                f_prim, f_sec, f_i0 = filter_regionless(data_prim, data_sec, data_i0)
                Ion0 = [ion(x, on_th) for x in f_i0]
                Ioff0 = [ioff(x) for x in f_i0]
                if ratio:
                    plot_yv(f_sec, [Ion0[i] / Ioff0[i] for i in range(len(Ioff0))], label_sec, "$Ion/Ioff (A)$")
                else:
                    plot_yvv([f_sec] * 2, ['Ioff', 'Ion'], [Ioff0, Ion0], label_sec, "$I (A)$", True)
        except ValueError:  # Most likely raised from within plot_yvv() or plot_yv()
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, all the values "
                                     "(besides the headers) are numeric, and that the data spans multiple decades.")
            global current_id
            current_id = -1
            return
        except IndexError as e:  # If none of the measurements span the required range of decades, filter_regionless()
            # raises an IndexError (since the lists that would have been returned would be of length 0).
            messagebox.showerror('', "Invalid data: for this calculation, the data must span at least 2.5 decades. ")
            current_id = -1
            return

    def show_i_heatmap(exposed):
        """
        The same as show_iv(), except as a heatmap.
        :param exposed: If True, show the post-exposure heatmap; if False, show the pre-exposure heatmap.
        """
        try:
            load_data()
            global data_sec, data_prim, data_i0, data_ia, label_prim, label_sec
            if exposed:
                plot_heatmap(data_ia, data_sec, data_prim, label_sec, label_prim, "$I_a (A)$", interp=False)
            else:
                plot_heatmap(data_i0, data_sec, data_prim, label_sec, label_prim, "$I_0 (A)$", interp=False)
        except ValueError:  # Most likely raised from within plot_heatmap()
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, and all "
                                     "the values (besides the headers) are numeric.")
            global current_id
            current_id = -1
            return

    def show_it():
        """
        Plots the current of a transient experiment over time.
        """
        try:
            load_data()
            global data_prim, data_i0
            plot_yv(data_prim, data_i0, "t (sec)", "I (A)", transient=True)
        except ValueError as e:  # Most likely raised from within plot_yv()
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, and all "
                                     "the values (besides the headers) are numeric.")
            # tb = traceback.format_exc()
            # logging.error(str(e) + ". Traceback: " + str(tb))
            global current_id
            current_id = -1
            return

    def show_t_ioffon():
        """
        Displays the off-current and on-current of a transient measurement in a messagebox.
        """
        try:
            load_data()
            global data_prim, data_i0
            if max(data_i0) / (10 ** 2.5) > min(data_i0):  # Ioff and Ion are only defined if the rise is significant!!
                arr = np.asarray(smooth(data_i0, 10))  # Converts the list into an array and smooths it.
                # The off- and on-currents are defined as the average of the points in the lower 10% and upper 10%
                # respectively. In a linear scale, it would look like this:
                # bound_low = min(arr) + (max(arr)-min(arr))*0.1
                # bound_high = max(arr) - (max(arr)-min(arr))*0.1
                bound_low = min(arr)*(max(arr)/min(arr))**0.1  # Like the above lines, but determined in log scale.
                bound_high = max(arr)*(min(arr)/max(arr))**0.1
                i_off = np.average(arr[arr < bound_low])
                i_on = np.average(arr[arr > bound_high])
                minlen = 10  # The minimum amount of points required to reliably calculate the currents. This is to
                # prevent outlier points distorting the 10% ranges and leading to incorrect results.
                if len(arr[arr < bound_low]) < minlen:
                    str_off = 'Not enough data points to determine Ioff'
                else:
                    str_off = 'Ioff = {}A'.format(i_off)
                if len(arr[arr > bound_high]) < minlen:
                    str_on = 'Not enough data points to determine Ion'
                else:
                    str_on = 'Ion = {}A'.format(i_on)
                messagebox.showinfo('', str_off + '\n' + str_on)
            else:
                messagebox.showerror('', "Invalid data. Make sure the data spans multiple decades.")
        except ValueError as e:
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, all the values "
                                     "(besides the headers) are numeric, and that the data spans multiple decades.")
            # tb = traceback.format_exc()
            # messagebox.showerror('', str(tb))
            # logging.error(str(e) + ". Traceback: " + str(tb))
            global current_id
            current_id = -1
            return

    def show_t_risefall():
        """
        Displays the rise and fall times of a transient measurement in a messagebox.
        """
        try:
            load_data()
            global data_prim, data_i0
            if max(data_i0) / (10 ** 2.5) > min(data_i0):  # The times are only defined if the rise is significant!!
                arr = np.asarray(smooth(data_i0, 10))  # Converts the list into an array and smooths it.
                # The same ranges as defined in show_t_ioffon().
                bound_low = min(arr)*(max(arr)/min(arr))**0.1
                bound_high = max(arr)*(min(arr)/max(arr))**0.1
                minlen = 20
                if len(arr[arr < bound_low]) < minlen or len(arr[arr > bound_high]) < minlen:  # If at least one of the
                    # ranges isn't properly defined
                    msg = 'Invalid data. Please make sure it includes both the off and on regions.'
                else:  # Find the closest points in arr to the bounds, and take the respective time for each. This is
                    # roughly equivalent to taking the 10% and 90% currents, as per the definition of rise/fall times.
                    # Find the closest current measurement to the 10%/90% point, get its index, and get the
                    # corresponding times. (The [0][0] has to do with the format of np.where()'s result - if I'm not
                    # mistaken, it's a tuple where the first element is an array, even if it only has one element. So
                    # the first [0] takes the array, and the second [0] takes the value itself.
                    t_low = data_prim[np.where(arr == min(arr, key=lambda x: abs(x - bound_low)))[0][0]]
                    t_high = data_prim[np.where(arr == min(arr, key=lambda x: abs(x - bound_high)))[0][0]]
                    delta = str(timedelta(seconds=round(abs(t_high-t_low))))
                    if t_high < t_low:  # Fall
                        msg = 'Fall time: ' + delta
                    else:  # Rise
                        msg = 'Rise time: ' + delta
                messagebox.showinfo('', msg)
            else:
                messagebox.showerror('', "Invalid data. Make sure the data spans multiple decades.")
        except ValueError as e:
            messagebox.showerror('', "Invalid data. Make sure all the columns are the same length, all the values "
                                     "(besides the headers) are numeric, and that the data spans multiple decades.")
            # tb = traceback.format_exc()
            # messagebox.showerror('', str(tb))
            # logging.error(str(e) + ". Traceback: " + str(tb))
            global current_id
            current_id = -1
            return

    def show_t_fit():
        messagebox.showinfo('', 'Not yet implemented. ')

    def open_excel():
        """
        Opens the selected experiment's data in Excel.
        """
        # print([tree.column(col, option="width") for col in tree["column"]])
        open_id = tree.item(tree.focus()).get("values")[0]
        filedir = os.path.dirname(os.path.realpath('__file__'));
        filename = os.path.join(filedir, './data/ex_' + str(open_id) + '.csv')
        xl = Dispatch('Excel.Application')
        wb = xl.Workbooks.Open(Filename=filename)
        xl.Visible = True


def init_settings_tab():
    def enable_settings_const():
        """
        Enables ent_s_const whenever drp_s_vth is set to "Constant", and disables it for any other value.
        """
        if stv_s_vth.get() == "Constant":
            ent_s_const["state"] = tk.NORMAL
        else:
            ent_s_const["state"] = tk.DISABLED

    def save_preferences():
        new_prefs = [s.get() for s in [stv_s_timegroup, stv_s_vth, stv_s_const, stv_s_sts, stv_s_ion]]
        with open('data/preferences.csv', 'w', newline='') as f:
            csv_writer = writer(f)
            csv_writer.writerows([[row] for row in new_prefs])  # TODO: Edge cases; Confirmation; Check empties.
        messagebox.showinfo('', 'Preferences saved.')

    def pick_color(sender, target, init_color=None):
        """
        Opens the color selection window and saves the selected color in the desired variable.
        :param sender: The label (colored rectangle) from which the function was called.
        :param target: A string, used to determine which variable to update.
        :param init_color: The initial color (rgb) of the label (from which the color picker then starts).
        """
        global color_d1, color_d2, color_g1, color_g2, color_src
        color = askcolor(color=to_hex(init_color), title=f"Choose color: {target} current")[0]  # TODO: color=?
        color = tuple([x/255 for x in color])
        # print(color)
        if color is not None:
            sender["background"] = to_hex(color)
            match target:
                case 'first drain':
                    color_d1 = color
                case 'last drain':
                    color_d2 = color
                case 'first gate':
                    color_g1 = color
                case 'second gate':
                    color_g2 = color
                case 'source':
                    color_src = color

    def test_colors():
        global drain_colors, color_d1, color_d2, color_g1, color_g2, color_src
        drain_colors.clear()
        color_diff = [y - x for x, y in zip(color_d1, color_d2)]
        for i in range(16):
            drain_colors[i] = tuple([color_d1[j] + color_diff[j] * i / 15 for j in range(3)])
        fake_p_prim = ['', 0, 10]
        fake_stv_linlog = tk.StringVar(value='linear')
        ax, ax2, ax3, ax4, bar = open_measurement_window(fake_p_prim, fake_stv_linlog, False, True)
        # ax2.set_visible(True)
        # ax3.set_visible(True)
        # ax4.set_visible(True)
        x = [i for i in range(10)]
        for i in range(16):
            ax.plot(x, [9 * i / 15 + (1 - i / 7.5) * y + 4.5 for y in x], color=drain_colors[i])
        ax.plot(x, [y / 10 + 3 for y in x], color=color_g1)
        ax.plot(x, [-y / 10 + 2.5 for y in x], color=color_g2)
        ax.plot(x, [y / 10 for y in x], color=color_src)

    def default_colors():
        global drain_colors, color_d1, color_d2, color_g1, color_g2, color_src
        drain_colors.clear()
        color_d1 = (0, 0, 1)
        color_d2 = (1, 0, 1)
        color_g1 = (44 / 255, 160 / 255, 44 / 255)
        color_g2 = (214 / 255, 39 / 255, 40 / 255)
        color_src = (23 / 255, 190 / 255, 207 / 255)
        clr_d1["background"] = to_hex(color_d1)
        clr_d2["background"] = to_hex(color_d2)
        clr_g1["background"] = to_hex(color_g1)
        clr_g2["background"] = to_hex(color_g2)
        clr_src["background"] = to_hex(color_src)

    # TODO: Row config
    tab_settings.columnconfigure([1, 4], weight=1)
    global stv_s_vth, stv_s_const, stv_s_sts, stv_s_ion, stv_s_timegroup, color_d1, color_d2, color_g1, color_g2, color_src

    stv_s_timegroup = tk.StringVar(value='1')
    ttk.Label(tab_settings, text="Update the transient display after every ").grid(row=0, column=0, sticky='ew')
    ent_timegroup = ttk.Entry(tab_settings, text='1', textvariable=stv_s_timegroup, width=7)
    ent_timegroup.grid(row=0, column=1, sticky='nsw', padx=5, pady=5)
    ttk.Label(tab_settings, text=" measurements (reduces unnecessary delay between measurements)")\
        .grid(row=0, column=2, columnspan=3, sticky="w")
    
    frm_s_colors = ttk.Frame(tab_settings)
    frm_s_colors.grid(row=1, column=0, rowspan=2, columnspan=5, sticky='nsw')
    frm_s_colors.rowconfigure([0, 1], weight=1)
    frm_s_colors.columnconfigure([*range(7)], weight=1)
    ttk.Label(frm_s_colors, text="Drain current colors:  from ").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    clr_d1 = ttk.Label(frm_s_colors, text='', width=5, background=to_hex(color_d1))
    clr_d1.grid(row=0, column=1, sticky='nsw', padx=5, pady=5)
    ttk.Label(frm_s_colors, text=" to ").grid(row=0, column=2, sticky='ew', padx=5, pady=5)
    clr_d2 = ttk.Label(frm_s_colors, text='', width=5, background=to_hex(color_d2))
    clr_d2.grid(row=0, column=3, sticky='nsw', padx=5, pady=5)
    clr_d1.bind('<Button-1>', lambda e: pick_color(clr_d1, 'first drain', color_d1))
    clr_d2.bind('<Button-1>', lambda e: pick_color(clr_d2, 'last drain', color_d2))
    
    ttk.Label(frm_s_colors, text="First gate current color: ").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    clr_g1 = ttk.Label(frm_s_colors, text='', width=5, background=to_hex(color_g1))
    clr_g1.grid(row=1, column=1, sticky='nsw', padx=5, pady=5)
    ttk.Label(frm_s_colors, text="Second gate current color: ").grid(row=1, column=2, columnspan=2, sticky='w',
                                                                     padx=5, pady=5)
    clr_g2 = ttk.Label(frm_s_colors, text='', width=5, background=to_hex(color_g2))
    clr_g2.grid(row=1, column=4, sticky='nsw', padx=5, pady=5)
    ttk.Label(frm_s_colors, text="Source current color: ").grid(row=1, column=5, sticky='w', padx=5, pady=5)
    clr_src = ttk.Label(frm_s_colors, text='', width=5, background=to_hex(color_src))
    clr_src.grid(row=1, column=6, sticky='nsw', padx=5, pady=5)
    clr_g1.bind('<Button-1>', lambda e: pick_color(clr_g1, 'first gate', color_g1))
    clr_g2.bind('<Button-1>', lambda e: pick_color(clr_g2, 'second gate', color_g2))
    clr_src.bind('<Button-1>', lambda e: pick_color(clr_src, 'source', color_src))

    btn_clrtest = ttk.Button(frm_s_colors, text="Test color scheme", command=lambda: test_colors())
    btn_clrtest.grid(row=0, column=5,padx=10, pady=5, ipadx=10, sticky='w')
    btn_clrdefault = ttk.Button(frm_s_colors, text="Restore to default", command=lambda: default_colors())
    btn_clrdefault.grid(row=0, column=6, padx=10, pady=5, ipadx=10, sticky='w')

    stv_s_vth = tk.StringVar(value='Constant')  # The threshold voltage extraction method. Global so it could be
    # 'remembered'.
    stv_s_const = tk.StringVar(value='1n')  # The constant threshold, for the relevant option.
    ttk.Label(tab_settings, text="Threshold voltage extraction method: ").grid(row=3, column=0, sticky="w", padx=5,
                                                                               pady=5)
    global vth_funcs
    drp_s_vth = ttk.OptionMenu(tab_settings, stv_s_vth, stv_s_vth.get(), *vth_funcs)
    drp_s_vth.grid(row=3, column=1, sticky="nsew", padx=5, pady=5)
    ttk.Label(tab_settings, text="Constant threshold: ").grid(row=3, column=2, sticky="ew", padx=5, pady=5)
    ent_s_const = ttk.Entry(tab_settings, text='1n', textvariable=stv_s_const, width=7)
    ent_s_const.grid(row=3, column=3, sticky="nsw", padx=5, pady=5)
    ttk.Label(tab_settings, text="A").grid(row=3, column=4, sticky="w")
    stv_s_vth.trace("w", lambda *args: enable_settings_const())

    ttk.Label(tab_settings, text="Subthreshold region definition: top ")\
        .grid(row=4, column=0, sticky="ew", padx=5, pady=5)
    stv_s_sts = tk.StringVar(value='30')
    ent_s_sts = ttk.Entry(tab_settings, textvariable=stv_s_sts, width=7)
    ent_s_sts.grid(row=4, column=1, sticky="nsw", padx=5, pady=5)
    ttk.Label(tab_settings, text="% of the second derivative")\
        .grid(row=4, column=2, columnspan=3, sticky="w", padx=5, pady=5)

    ttk.Label(tab_settings, text="On-current definition: greater than ")\
        .grid(row=5, column=0, sticky="ew", padx=5, pady=5)
    stv_s_ion = tk.StringVar(value='10n')
    ent_s_ion = ttk.Entry(tab_settings, textvariable=stv_s_ion, width=7)
    ent_s_ion.grid(row=5, column=1, sticky="nsw", padx=5, pady=5)
    ttk.Label(tab_settings, text="A (for sweep analysis only)")\
        .grid(row=5, column=2, columnspan=3, sticky="w", padx=5, pady=5)

    btn_save_prefs = ttk.Button(tab_settings, text="Save preferences", command=lambda: save_preferences())
    btn_save_prefs.grid(row=6, column=0, columnspan=5, sticky="nsw", padx=20, pady=5, ipadx=10)

    # Load preferences
    with open('data/preferences.csv', 'r', newline='') as f:
        csv_reader = reader(f)
        preferences = list(csv_reader)
    for s, p in zip([stv_s_timegroup, stv_s_vth, stv_s_const, stv_s_sts, stv_s_ion], preferences):
        s.set(p[0])


try:
    # Set up the main window
    window = ThemedTk()
    window.set_theme("scidblue")
    w_height, w_width = 500, 1000
    window.title("Multichip")
    window.geometry(str(w_width) + 'x' + str(w_height + 30) + '+0+0')  # Set the window's size and position it in the
    # top-left corner (temporarily...?)
    window.protocol("WM_DELETE_WINDOW", safe_quit)  # See safe_quit()'s definition
    control_tabs = ttk.Notebook(window, height=w_height, width=w_width)  # The main tab list
    tab_channels = ttk.Frame(control_tabs)
    tab_sweep = ttk.Frame(control_tabs)
    tab_time = ttk.Frame(control_tabs)
    tab_import = ttk.Frame(control_tabs)
    tab_analysis = ttk.Frame(control_tabs)
    tab_settings = ttk.Frame(control_tabs)
    control_tabs.add(tab_channels, text="Channels")
    control_tabs.add(tab_sweep, text="I-V Sweep")
    control_tabs.add(tab_time, text="Transient")
    control_tabs.add(tab_import, text="Import")
    control_tabs.add(tab_analysis, text="Analysis")
    control_tabs.add(tab_settings, text="Settings")
    control_tabs.pack(expand=1, fill="both")
    default_font = tkFont.nametofont("TkDefaultFont")  # Make the text size 12...
    default_font.configure(size=12)
    window.option_add("*Font", default_font)
    style = ttk.Style()
    style.configure("Treeview.Heading", font=(None, 10))  # ...except for the table headers, which will be size 10
    style.map("TEntry", fieldbackground=[("active", "white"), ("disabled", "grey")])  # TODO: Doesn't work!
    window.bind("<<no-spa>>", lambda e: hacky_no_spa_2())  # See the procedure in hacky_no_spa_1()
    # Initialize the (global) info StringVar()s
    stv_op, stv_gas, stv_conc, stv_carr, stv_atm, stv_dev, stv_dec, stv_thick, stv_temp, stv_hum = \
        tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), \
        tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
    global stv_smu2, stv_smu3, stv_smu4
    with open('data/transistor_data.csv', newline='') as f:
        csv_reader = reader(f)
        temp_trans_data = list(csv_reader)
        for i in range(4):
            active_trans.append([True if s == 'True' else False for s in temp_trans_data[i]])
        device_names = temp_trans_data[4]
        trans_names = temp_trans_data[5:9]
        # for (x, s) in ([smu for smu in temp_trans_data[10] if smu != ''], [stv_smu2, stv_smu3, stv_smu4]):
        #     s.set(x)
        # print(device_names)
        # print(trans_names)

    global spa_connected
    spa_connected = True  # Whether the program should try to access the SPA while running
    try_spa = True  # Whether the program should try to initialize the SPA

    # Are the Agilent IO services running? If not, an attempt to connect to the B1500 would stall the program
    # rather than raising an error.
    services = [get_service("AgilentIOLibrariesService"), get_service("AgtMdnsResponder"),
                get_service("AgilentPXIResourceManager")]  # For each service, gets either its name or None.
    if None not in services:  # If all the services exist
        status = [x["status"] for x in services]  # Gets the status of each service as a string
        running = [x == 'running' for x in status]  # True if the service is running
        if not all(running):  # If some of the services are disabled
            err_msg = "Some of the required services are not running. Please start them manually or restart the computer."  # TODO: Check if you can run them automatically
            th = threading.Thread(target=hacky_no_spa_1, args=(window,), daemon=True)
            th.start()
            window.title("(SPA Not Connected) Multichip v" + version)
            spa_connected = False
            try_spa = False
    else:  # Some of the required services don't exist!
        err_msg = "Please make sure that Agilent IO Suite is installed properly. "
        th = threading.Thread(target=hacky_no_spa_1, args=(window,), daemon=True)
        th.start()
        window.title("(SPA Not Connected) Multichip v" + version)
        spa_connected = False
        try_spa = False
    if try_spa:  # Only now, try to connect to the SPA.
        global b1500
        try:
            b1500 = init_spa()
        except pyvisa.Error:  # The SPA is not connected
            err_msg = "SPA not connected."
            th = threading.Thread(target=hacky_no_spa_1, args=(window,), daemon=True)
            th.start()
            window.title("(SPA Not Connected) Simulchip v" + version)
            spa_connected = False

    # Connect to the Arduino
    global board
    try:
        board = Arduino()
    except Exception as e:
        # tb = str(traceback.format_exc())
        if not suppress_errors:
            messagebox.showerror('', 'Please connect the Arduino controller and reopen the program.')  # \nTraceback: ' + tb)
        board = None
    # Set up the Arduino pin mapping
    # Pins: 2-12, A0-A4
    pinno = {}
    for i in range(11):  # Set pinno[0] to pinno[10] to 2-12
        pinno[i] = i + 2
    for i in range(5):  # Set pinno[11] to pinno[15] to 18-22
        pinno[i + 11] = i + 18

    # Set up the drain colors dictionary
    drain_colors = {}
    # for i in range(16):
    #     drain_colors[i] = (i/15, 0, 1)
    # The rest of the colors:
    color_d1 = (0, 0, 1)
    color_d2 = (1, 0, 1)
    color_g1 = (44/255, 160/255, 44/255)
    color_g2 = (214/255, 39/255, 40/255)
    color_src = (23/255, 190/255, 207/255)
except Exception as e:
    logging.error("FIRST BLOCK error: \"" + type(e).__name__ + ": " + str(e) + "\"")


try:
    # Initialize all the tabs
    init_channels_tab()
    init_sweep_tab()
    init_time_tab()
    init_import_tab()
    init_analysis_tab()
    init_settings_tab()
    window.mainloop()
except Exception as e:
    tb = traceback.format_exc()
    logging.error(str(e) + ". Traceback: " + str(tb))
    messagebox.showerror('', type(e).__name__ + ": " + str(e) + "\"")
finally:
    if spa_connected:  # If the SPA is connected, safely reset it.
        # Since window_mainloop() is in the try block, this will happen for any runtime error!!
        print("Resetting SMUs...")
        reset_spa()
        print("All SMUs were reset. ")

