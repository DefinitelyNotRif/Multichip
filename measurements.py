from pymeasure.instruments.agilent import AgilentB1500
import numpy as np
import time
from datetime import datetime
import measurement_vars
import logging
import traceback
from Arduino import Arduino


def init_spa():
    b1500 = AgilentB1500("GPIB0::17::INSTR", read_termination='\r\n', write_termination='\r\n', timeout=60000)
    b1500.initialize_all_smus()
    b1500.data_format(21, mode=1)
    return b1500


def sweep(b1500, params, w, source_active, board, pinno):  # params is a nested list (NO LINLOG).
    # Params = [prim, sec, other, smus, active_trans].
    # Prim/sec = [name, start, stop, step, n, comp]
    # Other = [name3, const, constcomp, hold, delay, param_list]
    logging.basicConfig(filename="logs.log", level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')  # Set the format to use in logs.txt
    try:
        # Display the "Initializing" message
        measurement_vars.incr_vars = [0, 0, 4]
        w.event_generate("<<prb-increment>>", when="tail")

        # Set up the SPA
        b1500.meas_mode('STAIRCASE_SWEEP', *b1500.smu_references)
        for smu in b1500.smu_references:
            smu.enable()  # enable SMU
            smu.adc_type = 'HRADC'  # set ADC to high-resoultion ADC
            smu.meas_range_current = '1 nA'  # Not entirely sure what this means.
            smu.meas_op_mode = 'COMPLIANCE_SIDE'  # other choices: Current, Voltage, FORCE_SIDE, COMPLIANCE_AND_FORCE_SIDE
        b1500.adc_setup('HRADC', 'PLC', 3)
        b1500.sweep_timing(params[2][3], params[2][4], step_delay=0)  # hold, delay, step delay.
        b1500.sweep_auto_abort(False, post='STOP')

        orderly_smus = list(b1500.smu_references)
        names = list(b1500.smu_names.values())
        if params[0][0] == params[2][-1][0]:  # Prim is the drains
            smu_prim = [orderly_smus[names.index(s)] for s in params[3][0]]
            for s in smu_prim:
                s.compliance = params[0][5]
                s.staircase_sweep_source('Voltage', 'LINEAR_SINGLE', 'Auto Ranging', params[0][1], params[0][2],
                                         params[0][4], params[0][5])
        else:  # Prim is only one SMU
            smu_prim = orderly_smus[names.index(params[3][params[2][-1].index(params[0][0])])]
            # From inner scope to outer: Var name, place in param order, SMU name, place in SMU order, SMU reference.
            smu_prim.compliance = params[0][5]
            smu_prim.staircase_sweep_source('Voltage', 'LINEAR_SINGLE', 'Auto Ranging', params[0][1], params[0][2],
                                            params[0][4], params[0][5])
        if params[1][0] == params[2][-1][0]:  # Sec is the drains
            smu_sec = [orderly_smus[names.index(s)] for s in params[3][0]]
            for s in smu_sec:
                s.compliance = params[1][5]
        else:  # Sec is only one SMU
            smu_sec = orderly_smus[names.index(params[3][params[2][-1].index(params[1][0])])]
            smu_sec.compliance = params[1][5]
        if params[2][0] == params[2][-1][0]:  # Const is the drains
            smu_const = [orderly_smus[names.index(s)] for s in params[3][0]]
            for s in smu_const:
                s.compliance = params[2][2]
                s.force('Voltage', 'Auto Ranging', params[2][1])
        else:  # Const is only one SMU
            smu_const = orderly_smus[names.index(params[3][params[2][-1].index(params[2][0])])]
            smu_const.compliance = params[2][2]
            smu_const.force('Voltage', 'Auto Ranging', params[2][1])

        if source_active:  # If the ground SMU was defined
            smu_ground = orderly_smus[names.index(params[3][3])]
            smu_ground.compliance = 10e-6  # Arbitrary
            smu_ground.force('Voltage', 'Auto Ranging', 0)

        # For debugging purposes:
        # print(f"param_list: {params[0][0]}, {params[1][0]}, {params[2][0]}")

        for i in range(16):  # Set up the Arduino
            board.pinMode(pinno[i], "OUTPUT")
            board.digitalWrite(pinno[i], "LOW")
        num_active = len([x for row in params[4] for x in row if x])  # The number of active drains
        row_active = [any(row) for row in params[4]]  # True if the corresponding row has at least one active transistor
        num_active_rows = len([x for x in row_active if x])  # The number of rows that have an active transistor
        # print(f"{num_active} active drains; {num_active_rows} active rows.")

        b1500.check_errors()
        b1500.clear_buffer()
        b1500.clear_timer()

        v1 = list(np.linspace(params[0][1], params[0][2], int(params[0][4])))
        v2 = list(np.linspace(params[1][1], params[1][2], int(params[1][4])))
        data = []  # The data that will be sent for saving. The nested list format: top level, measurements (each with
        # a different sec voltage), columns (each for a different SMU).
        times_waited = 0  # debug var
        for v in v2:
            position = v2.index(v)
            if type(smu_sec) == list:  # If sec is the drains, force ALL of them
                for s in smu_sec:
                    s.force('Voltage', 'Auto Ranging', v)
            else:  # Sec is a single SMU
                smu_sec.force('Voltage', 'Auto Ranging', v)

            print("Starting measurement ("+params[1][0]+"=" + str(v) + "v)...")

            if measurement_vars.stop_ex:
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return

            tempdata = []  # The current round of measurements
            measured_rows = 0  # For the progressbar - the number of devices (rows) that have been measured this round
            for row in range(4):
                if row_active[row]:  # Only measure the row if at least one transistor in it is selected
                    # Update the progressbar
                    if len(v2) == 1:  # TODO: Fix. Not urgent.
                        measurement_vars.incr_vars = [measured_rows/num_active_rows, v, row]
                    else:
                        measurement_vars.incr_vars = [(position*num_active_rows+measured_rows) /
                                                      (len(v2)*num_active_rows), v, row]
                    w.event_generate("<<prb-increment>>", when="tail")
                    for col in range(4):
                        if params[4][row][col]:  # If this transistor should be measured (active)
                            board.digitalWrite(pinno[4*row+col], "HIGH")  # Open its relay
                    times_waited += 1

                    b1500.send_trigger()
                    b1500.check_idle()
                    # Turn off these 4
                    for col in range(4):
                        board.digitalWrite(pinno[4 * row + col], "LOW")
                    measured_rows += 1

                    raw_data = b1500.read_data(params[0][4])  # A pandas dataframe, where each column corresponds to
                    # a different SMU (in the order of orderly_smus!).
                    tempdrains = [raw_data.iloc[:, col].values.tolist() for col in range(raw_data.shape[1]-1)
                                  if names[col] in params[3][0]]  # The columns corresponding to the drains only
                    for col in range(len(tempdrains)):  # Iterate over the drain columns; but now they're indexed in
                        # the same order as active_trans
                        if params[4][row][col]:  # Only add the column if its drain is supposed to be active!
                            # Otherwise, it's just a measurement of a closed relay.
                            tempdata.append(tempdrains[col])
                    # tempdata should now have the ACTIVE DRAIN measurements only.

                    if measurement_vars.stop_ex:
                        measurement_vars.stop_ex = False
                        w.event_generate("<<close-window>>", when="tail")
                        return

            # Run one more measurement where all of the relays are closed
            # b1500.send_trigger()
            # b1500.check_idle()
            # other_currents = b1500.read_data(params[0][4])
            # TODO: Does taking from raw_data instead of other_currents work?
            tempdata.append(raw_data.iloc[:, names.index(params[3][1])].values.tolist())  # The two non-drain currents
            tempdata.append(raw_data.iloc[:, names.index(params[3][2])].values.tolist())
            if source_active:
                tempdata.append(raw_data[names.index(params[3][3])])  # Source
            print("Measurement complete. ")
            # tempdata now contains all the drain measurements, then sec, then const, then (optionally) source.

            if len(v2) == 1:
                measurement_vars.incr_vars = [1, v, 5]
            else:
                measurement_vars.incr_vars = [(position+1)/len(v2), v, 5]
            w.event_generate("<<prb-increment>>", when="tail")

            measurement_vars.send_sweep = [v1, v2, tempdata]  # Send all the currents to display them
            data.append(tempdata[:num_active])  # Only the drains should be saved
            if measurement_vars.stop_ex:
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return
            w.event_generate("<<add-sweep>>", when="tail")
            measurement_vars.ex_vars = [[v1] * (v2.index(v) + 1), v2[:v2.index(v) + 1], data]  # For abortion purposes.
        measurement_vars.ex_vars = [[v1]*len(v2), v2, data]
        measurement_vars.ex_finished = True
    except Exception as e:
        tb = traceback.format_exc()
        logging.error("Measurement error: " + str(e) + ". Traceback: " + str(tb))


def transient(b1500, params, w, limit_time, groupsize, source_active, board, pinno):
    # Params = [param_list, [voltages], [comps], [varname, int, n, tot, hold, linlog], [SMU names], active_trans]
    logging.basicConfig(filename="logs.log", level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')  # Set the format to use in logs.txt
    try:
        for smu in b1500.smu_references:
            smu.enable()  # enable SMU
            smu.adc_type = 'HRADC'  # set ADC to high-resoultion ADC
            smu.meas_range_current = '1 nA'  # Not entirely sure what this means.
            smu.meas_op_mode = 'COMPLIANCE_SIDE'  # other choices: Current, Voltage, FORCE_SIDE, COMPLIANCE_AND_FORCE_SIDE
        b1500.adc_setup('HRADC', 'PLC', 3)

        orderly_smus = list(b1500.smu_references)  # [smu1, smu2, smu3, smu4]
        names = list(b1500.smu_names.values())  # ['SMU1', ...]
        if source_active:  # Set the ground to 0 and define its compliance
            smu_ground = orderly_smus[names.index(params[4][3])]
            smu_ground.compliance = 1e-6  # Arbitrary.
            smu_ground.force('Voltage', 'Auto Ranging', 0)
        smu2 = orderly_smus[names.index(params[4][1])]  # Secondary variables
        smu3 = orderly_smus[names.index(params[4][2])]
        for s in params[4][0]:  # This should be a list of all the drain SMUs
            orderly_smus[names.index(s)].compliance = params[2][0]
            orderly_smus[names.index(s)].force('Voltage', 'Auto Ranging', params[1][0])
        smu2.compliance = params[2][1]
        smu2.force('Voltage', 'Auto Ranging', params[1][1])
        smu3.compliance = params[2][2]
        smu3.force('Voltage', 'Auto Ranging', params[1][2])

        for i in range(16):
            board.pinMode(pinno[i], "OUTPUT")
            board.digitalWrite(pinno[i], "LOW")
        num_active = len([x for row in params[5] for x in row if x])  # The number of active drains
        row_active = [any(row) for row in params[5]]  # True if the corresponding row has at least one active transistor
        num_active_rows = len([x for x in row_active if x])
        fractional_int = params[3][1]/num_active_rows  # The interval for each device.
        # print(f"{num_active} active drains; {num_active_rows} active rows; Wait {fractional_int} "
        #       f"between each measurement.")

        time.sleep(params[3][4])
        b1500.check_errors()
        b1500.clear_buffer()
        b1500.clear_timer()
        data = []  # The data that will be sent for displaying and saving
        if measurement_vars.stop_ex:
            print("stop_ex detected as True (before)")
            measurement_vars.stop_ex = False
            w.event_generate("<<close-window>>", when="tail")
            return
        # debug var
        times_waited = 0
        for i in range(int(params[3][2])):
            tempdata = []  # The row to be appended to data after each "round"
            for row in range(4):
                if row_active[row]:  # Only measure the row if at least one transistor in it is selected
                    for col in range(4):
                        if params[5][row][col]:  # If this transistor should be measured (active)
                            board.digitalWrite(pinno[4*row+col], "HIGH")
                    time.sleep(fractional_int)  # Wait (also to make sure the relays have had the time to connect)
                    times_waited += 1
                    for col in range(4):  # Get drains
                        if params[5][row][col]:
                            b1500.write("TTI " + params[4][0][col][-1])
                    b1500.check_idle()
                    # Turn off these 4
                    for col in range(4):
                        board.digitalWrite(pinno[4*row+col], "LOW")
            #  The stored data may now have up to 16 rows, each with a time measurement and a current measurement
            for j in range(num_active):  # Add the drain measurements to the new line of data
                tempdata.append(b1500.read_data(1).iloc[0].values.flatten().tolist())
            # Secondary variables, with all of the drains closed
            b1500.write("TTI " + params[4][1][-1])  # Get secondary 1 (e.g. JG)
            b1500.write("TTI " + params[4][2][-1])  # Get secondary 2 (e.g. BG)
            if source_active:
                b1500.write("TTI " + params[4][3][-1])  # Get source
            b1500.check_idle()
            for q in range(2):  # Add these measurements to the new line of data
                tempdata.append(b1500.read_data(1).iloc[0].values.flatten().tolist())
            if source_active:  # Source
                tempdata.append(b1500.read_data(1).iloc[0].values.flatten().tolist())
            t_avg = np.average([t[0] for t in tempdata])  # t[0] is the time of each spot measurement; Take the average.
            data.append([t_avg, *[t[1] for t in tempdata]])
            if i % groupsize == 0:
                measurement_vars.send_transient = [list(x) for x in zip(*data)]
                w.event_generate("<<add-spot>>", when="tail")
            if limit_time:
                measurement_vars.incr_vars = min(1, tempdata[0][0]/params[3][3])  # Time elapsed as part of the total time
            else:
                measurement_vars.incr_vars = (i+1)/params[3][2]  # No. of samples taken as part of the desired number
            w.event_generate("<<prb-increment>>", when="tail")
            if measurement_vars.stop_ex:
                print("stop_ex detected as True (after)")
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return
            if limit_time and tempdata[0][0] > params[3][3]:
                break
            measurement_vars.ex_vars = data  # For abortion purposes

        # Update the graph one more time, in case groupsize > 0
        measurement_vars.send_transient = [list(x) for x in zip(*data)]
        w.event_generate("<<add-spot>>", when="tail")

        measurement_vars.ex_vars = data  # List of lists of length 5 (or 4) - no need to transpose later!
        measurement_vars.ex_finished = True

        # Bandaid solution to the mistiming:
        measurement_vars.incr_vars = 1
        w.event_generate("<<prb-increment>>", when="tail")
        # print(times_waited)

    except Exception as e:
        tb = traceback.format_exc()
        logging.error("Measurement error: " + str(e) + ". Traceback: " + str(tb))


def transient_sweep(b1500, params, w, source_active, board, pinno):
    logging.basicConfig(filename="logs.log", level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')  # Set the format to use in logs.txt
    # params = [p_prim, p_sec, p_other, p_smus, active_trans].
    # p_prim = [name, start, stop, step, n, comp]
    # p_sec = [name, value, comp, n, between]
    # p_other = [name, value, comp, hold, delay, param_list]
    try:
        # Display the "Initializing" message
        measurement_vars.incr_vars = [0, 0, 4]
        w.event_generate("<<prb-increment>>", when="tail")

        # Set up the SPA
        b1500.meas_mode('STAIRCASE_SWEEP', *b1500.smu_references)
        for smu in b1500.smu_references:
            smu.enable()  # enable SMU
            smu.adc_type = 'HRADC'  # set ADC to high-resoultion ADC
            smu.meas_range_current = '1 nA'  # Not entirely sure what this means.
            smu.meas_op_mode = 'COMPLIANCE_SIDE'  # other choices: Current, Voltage, FORCE_SIDE, COMPLIANCE_AND_FORCE_SIDE
        b1500.adc_setup('HRADC', 'PLC', 3)
        b1500.sweep_timing(params[2][3], params[2][4], step_delay=0)  # hold, delay, step delay.
        b1500.sweep_auto_abort(False, post='STOP')

        orderly_smus = list(b1500.smu_references)
        names = list(b1500.smu_names.values())
        if params[0][0] == params[2][-1][0]:  # Prim is the drains
            smu_prim = [orderly_smus[names.index(s)] for s in params[3][0]]
            for s in smu_prim:
                s.compliance = params[0][5]
                s.staircase_sweep_source('Voltage', 'LINEAR_SINGLE', 'Auto Ranging', params[0][1], params[0][2],
                                         params[0][4], params[0][5])
        else:  # Prim is only one SMU
            # From inner scope to outer: Var name, place in param order, SMU name, place in SMU order, SMU reference.
            smu_prim = orderly_smus[names.index(params[3][params[2][-1].index(params[0][0])])]
            smu_prim.compliance = params[0][5]
            smu_prim.staircase_sweep_source('Voltage', 'LINEAR_SINGLE', 'Auto Ranging', params[0][1], params[0][2],
                                            params[0][4], params[0][5])
        if params[1][0] == params[2][-1][0]:  # Sec is the drains
            smu_sec = [orderly_smus[names.index(s)] for s in params[3][0]]
            for s in smu_sec:
                s.compliance = params[1][2]
                s.force('Voltage', 'Auto Ranging', params[1][1])
        else:  # Sec is only one SMU
            smu_sec = orderly_smus[names.index(params[3][params[2][-1].index(params[1][0])])]
            smu_sec.compliance = params[1][2]
            smu_sec.force('Voltage', 'Auto Ranging', params[1][1])
        if params[2][0] == params[2][-1][0]:  # Const is the drains
            smu_const = [orderly_smus[names.index(s)] for s in params[3][0]]
            for s in smu_const:
                s.compliance = params[2][2]
                s.force('Voltage', 'Auto Ranging', params[2][1])
        else:  # Const is only one SMU
            smu_const = orderly_smus[names.index(params[3][params[2][-1].index(params[2][0])])]
            smu_const.compliance = params[2][2]
            smu_const.force('Voltage', 'Auto Ranging', params[2][1])

        if source_active:  # If the ground SMU was defined
            smu_ground = orderly_smus[names.index(params[3][3])]
            smu_ground.compliance = 10e-6  # Arbitrary
            smu_ground.force('Voltage', 'Auto Ranging', 0)

        # For debugging purposes:
        # print(f"param_list: {params[0][0]}, {params[1][0]}, {params[2][0]}")

        for i in range(16):  # Set up the Arduino
            board.pinMode(pinno[i], "OUTPUT")
            board.digitalWrite(pinno[i], "LOW")
        num_active = len([x for row in params[4] for x in row if x])  # The number of active drains
        row_active = [any(row) for row in params[4]]  # True if the corresponding row has at least one active transistor
        num_active_rows = len([x for x in row_active if x])  # The number of rows that have an active transistor
        # print(f"{num_active} active drains; {num_active_rows} active rows.")

        b1500.check_errors()
        b1500.clear_buffer()
        b1500.clear_timer()

        v1 = list(np.linspace(params[0][1], params[0][2], int(params[0][4])))
        data = []  # A list of lists - each corresponding to a different time point (or rather, series of consecutive
        # time points, since the measurements aren't instant)
        start_time = datetime.now()
        t = []  # A list of lists - each sub-list corresponds to a different series of consecutive time points, and
        # each time point within it corresponds to a different sweep (in the order of the measurements). The length
        # of each sub-list is the number of active devices (num_active_rows).
        for k in range(int(params[1][3])):
            print("Starting measurement (" + str(k+1) + ")...")

            if measurement_vars.stop_ex:
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return

            # temp_t = datetime.now() - start_time
            temp_t = []  # The timestamps for the current round of measurements
            # t.append(temp_t.seconds + temp_t.microseconds/1e6)  # TODO: Where do i put this? TODO: Minutes?
            tempdata = []  # The current round of measurements
            measured_rows = 0  # For the progressbar - the number of devices (rows) that have been measured this round
            for row in range(4):
                if row_active[row]:  # Only measure the row if at least one transistor in it is selected
                    # Update the progressbar
                    measurement_vars.incr_vars = [(k*num_active_rows+measured_rows) /
                                                  (params[1][3]*num_active_rows), k+1, row]
                    w.event_generate("<<prb-increment>>", when="tail")
                    for col in range(4):
                        if params[4][row][col]:  # If this transistor should be measured (active)
                            board.digitalWrite(pinno[4*row+col], "HIGH")  # Open its relay

                    temp_t.append(datetime.now() - start_time)  # Add the time and start the measurements
                    b1500.send_trigger()
                    b1500.check_idle()
                    # Turn off these 4
                    for col in range(4):
                        board.digitalWrite(pinno[4 * row + col], "LOW")
                    measured_rows += 1

                    raw_data = b1500.read_data(params[0][4])  # A pandas dataframe, where each column corresponds to
                    # a different SMU (in the order of orderly_smus!).
                    tempdrains = [raw_data.iloc[:, col].values.tolist() for col in range(raw_data.shape[1]-1)
                                  if names[col] in params[3][0]]  # The columns corresponding to the drains only
                    for col in range(len(tempdrains)):  # Iterate over the drain columns; but now they're indexed in
                        # the same order as active_trans
                        if params[4][row][col]:  # Only add the column if its drain is supposed to be active!
                            # Otherwise, it's just a measurement of a closed relay.
                            tempdata.append(tempdrains[col])

                    if measurement_vars.stop_ex:
                        measurement_vars.stop_ex = False
                        w.event_generate("<<close-window>>", when="tail")
                        return
            # tempdata should now have the ACTIVE DRAIN measurements only.

            # Run one more measurement where all of the relays are closed
            # b1500.send_trigger()
            # b1500.check_idle()
            # other_currents = b1500.read_data(params[0][4])
            # TODO: Does taking from raw_data instead of other_currents work?
            tempdata.append(raw_data.iloc[:, names.index(params[3][1])].values.tolist())  # The two non-drain currents
            tempdata.append(raw_data.iloc[:, names.index(params[3][2])].values.tolist())
            if source_active:
                tempdata.append(raw_data[names.index(params[3][3])])  # Source
            t.append(temp_t)
            print("Measurement complete. ")

            measurement_vars.incr_vars = [(k+1)/params[1][3], k+1, 5]
            w.event_generate("<<prb-increment>>", when="tail")

            measurement_vars.send_sweep = [v1, t, tempdata]
            data.append(tempdata[:num_active])  # Only the drains
            measurement_vars.ex_vars = [[v1] * (k + 1), t, data]  # For abortion purposes

            if measurement_vars.stop_ex:
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return
            w.event_generate("<<add-sweep>>", when="tail")
            if k != params[1][3] - 1:  # Otherwise the user could click "Finish" before the ex_vars are sent
                time.sleep(params[1][4])
            if measurement_vars.stop_ex:  # Juuust in case, because both the sweep and the sleep take non-negligible time.
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return
        measurement_vars.ex_vars = [[v1]*int(params[1][3]), t, data]
        measurement_vars.ex_finished = True
    except Exception as e:
        tb = traceback.format_exc()
        logging.error("Measurement error: " + str(e) + ". Traceback: " + str(tb))
