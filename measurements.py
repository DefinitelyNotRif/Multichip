#Characteristic: Set SMUs based on var order, then set up the sweep with the parameters.
from pymeasure.instruments.agilent import AgilentB1500
import numpy as np
import time
from datetime import datetime
import measurement_vars
import logging
import traceback


def init_spa():  # TODO: Move to main file??? Does it matter?
    b1500 = AgilentB1500("GPIB0::18::INSTR", read_termination='\r\n', write_termination='\r\n', timeout=60000)
    b1500.initialize_all_smus()
    b1500.data_format(21, mode=1)
    return b1500
    # raise Exception


def sweep(b1500, params, w):  # params is a nested list (NO LINLOG).
    try:
        b1500.meas_mode('STAIRCASE_SWEEP', *b1500.smu_references)
        for smu in b1500.smu_references:
            smu.enable()  # enable SMU
            smu.adc_type = 'HRADC'  # set ADC to high-resoultion ADC
            smu.meas_range_current = '1 nA'  # TODO: ??????
            smu.meas_op_mode = 'COMPLIANCE_SIDE'  # other choices: Current, Voltage, FORCE_SIDE, COMPLIANCE_AND_FORCE_SIDE
        b1500.adc_setup('HRADC', 'PLC', 3)
        b1500.sweep_timing(params[2][3], params[2][4], step_delay=params[2][4])  # hold, delay, step delay.
        b1500.sweep_auto_abort(False, post='STOP')
        n = params[0][4]

        smus = list(b1500.smu_references)
        names = list(b1500.smu_names.values())
        # From inner scope to outer: Var name, place in param order, SMU name, place in SMU order, SMU reference.
        smu_prim = smus[names.index(params[3][params[2][-1].index(params[0][0])])]
        smu_sec = smus[names.index(params[3][params[2][-1].index(params[1][0])])]
        smu_const = smus[names.index(params[3][params[2][-1].index(params[2][0])])]
        # print(params[0][0] + ", " + params[1][0] + ", " + params[2][0])
        # print("prim: " + str(names.index(params[3][params[2][-1].index(params[0][0])])) + ", \n"
        #         "sec: " + str(names.index(params[3][params[2][-1].index(params[1][0])])) + ", \n"
        #         "const: " + str(names.index(params[3][params[2][-1].index(params[2][0])])))
        n_columns = 3 if params[3][3] == "(None)" else 4  # Don't define the ground SMU, and "return" 3 columns
        if n_columns == 4:  # If the ground SMU was defined
            smu_ground = smus[names.index(params[3][3])]
            smu_ground.compliance = 10e-6  # Arbitrary
            smu_ground.force('Voltage', 'Auto Ranging', 0)
        smu_prim.compliance = params[0][5]
        smu_sec.compliance = params[1][5]
        smu_const.compliance = params[2][2]
        smu_const.force('Voltage', 'Auto Ranging', params[2][1])
        smu_prim.staircase_sweep_source('Voltage', 'LINEAR_SINGLE', 'Auto Ranging', params[0][1], params[0][2], n, params[0][5])  # jg

        b1500.check_errors()
        b1500.clear_buffer()
        b1500.clear_timer()

        v1 = list(np.linspace(params[0][1], params[0][2], int(params[0][4])))
        v2 = list(np.linspace(params[1][1], params[1][2], int(params[1][4])))
        i = []
        d_index = names.index(params[3][0])
        for v in v2:
            # smu_sec.ramp_source('Voltage', 'Auto Ranging', v, stepsize=0.1, pause=20e-3)  #bg
            position = v2.index(v)
            smu_sec.force('Voltage', 'Auto Ranging', v)
            # print("forced secondary to " + str(v))
            print("Starting measurement ("+params[1][0]+"=" + str(v) + "V)...")
            if len(v2) == 1:         # TODO: Fix. Not urgent.
                measurement_vars.incr_vars = [0, v, False]
            else:
                measurement_vars.incr_vars = [(2*position+1)/(2*len(v2)), v, False]
            w.event_generate("<<prb-increment>>", when="tail")
            if measurement_vars.stop_ex:
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return
            b1500.send_trigger()
            b1500.check_idle()
            print("Measurement complete. ")
            if len(v2) == 1:
                measurement_vars.incr_vars = [1, v, True]
            else:
                measurement_vars.incr_vars = [(2*position+2)/(2*len(v2)), v, True]
            w.event_generate("<<prb-increment>>", when="tail")
            data = b1500.read_data(n)
            # print(data)
            new_i = []
            for col in range(n_columns):
                new_i.append(data.iloc[:, col].values.tolist())  # new_i is now a list of 4 lists
            i.append(new_i[d_index])
            measurement_vars.send_sweep = [v1, v2, new_i]
            if measurement_vars.stop_ex:
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return
            w.event_generate("<<add-sweep>>", when="tail")
            measurement_vars.ex_vars = [[v1] * (v2.index(v) + 1), v2[:v2.index(v) + 1], i]  # For abortion purposes
        # return [v1]*len(v2), v2, i
        # plot_yvv([v1]*len(v2), v2, i, "test x", "test y", True)
        # widgets[0].destroy()
        # i = [list(x) for x in zip(*i)]
        measurement_vars.ex_vars = [[v1]*len(v2), v2, i]
        # w.event_generate("<<finish-sweep>>", when="tail")
        measurement_vars.ex_finished = True
    except Exception as e:
        tb = traceback.format_exc()
        logging.error("Measurement error: " + str(e) + ". Traceback: " + str(tb))


def transient(b1500, params, w, limit_time):  # Params = [param_list, [voltages], [comps], [varname, int, n, tot, hold, linlog], [SMU names]]
    try:
        for smu in b1500.smu_references:
            smu.enable()  # enable SMU
            smu.adc_type = 'HRADC'  # set ADC to high-resoultion ADC
            smu.meas_range_current = '1 nA'  # TODO: ??????
            smu.meas_op_mode = 'COMPLIANCE_SIDE'  # other choices: Current, Voltage, FORCE_SIDE, COMPLIANCE_AND_FORCE_SIDE
        b1500.adc_setup('HRADC', 'PLC', 3)
        # b1500.adc_setup('HRADC', 'AUTO', 6)

        orderly_smus = list(b1500.smu_references)  # [smu1, smu2, smu3, smu4]
        names = list(b1500.smu_names.values())  # ['SMU1', ...]
        smu1 = orderly_smus[names.index(params[4][0])]
        smu2 = orderly_smus[names.index(params[4][1])]
        smu3 = orderly_smus[names.index(params[4][2])]
        n_columns = 3 if params[4][3] == "(None)" else 4  # Don't define the ground SMU, and "return" 3 columns
        if n_columns == 4:
            smu_ground = orderly_smus[names.index(params[4][3])]
            smu_ground.compliance = 1e-6  # Arbitrary.
            smu_ground.force('Voltage', 'Auto Ranging', 0)
        smus = [smu1, smu2, smu3]
        for i in range(3):
            smus[i].compliance = params[2][i]
            smus[i].force('Voltage', 'Auto Ranging', params[1][i])

        smu_meas = smus[params[0].index(params[3][0])]
        ch_meas = names.index(params[4][params[0].index(params[3][0])]) + 1
        channels = [names.index(s) + 1 for s in params[4]]
        channels.remove(ch_meas)
        print("ch_meas = " + str(ch_meas) + ", channels = " + str(channels))
        time.sleep(params[3][4])
        b1500.check_errors()
        b1500.clear_buffer()
        b1500.clear_timer()
        data = []
        for i in range(int(params[3][2])):
            tempdata = []
            b1500.write("TTI " + str(ch_meas))
            b1500.check_idle()
            if measurement_vars.stop_ex:
                print("stop_ex detected as True (before)")
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return
            tempdata.append(b1500.read_data(1).iloc[0].values.flatten().tolist())
            for x in channels:
                b1500.write("TTI " + str(x))  # TODO: Check if the improvement helps
            b1500.check_idle()
            for q in range(n_columns - 1):
                tempdata.append(b1500.read_data(1).iloc[0].values.flatten().tolist())
            data.append([tempdata[0][0], *[tempdata[j][1] for j in range(n_columns)]])
            measurement_vars.send_transient = [list(x) for x in zip(*list(data))]
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
            time.sleep(params[3][1])
        # for row in data:
        #     t = row[0]
        #     row[0] = t.seconds + t.microseconds/1e6
        measurement_vars.ex_vars = data  # List of lists of length 5 (or 4) - no need to transpose later!
        measurement_vars.ex_finished = True
    except Exception as e:
        tb = traceback.format_exc()
        logging.error("Measurement error: " + str(e) + ". Traceback: " + str(tb))


def transient_sweep(b1500, params, w): #params = [p_prim, p_sec, p_other, p_smus]. p_sec = [name, value, n, comp, between]
    try:
        b1500.meas_mode('STAIRCASE_SWEEP', *b1500.smu_references)
        for smu in b1500.smu_references:
            smu.enable()  # enable SMU
            smu.adc_type = 'HRADC'  # set ADC to high-resoultion ADC
            smu.meas_range_current = '1 nA'  # TODO: ??????
            smu.meas_op_mode = 'COMPLIANCE_SIDE'  # other choices: Current, Voltage, FORCE_SIDE, COMPLIANCE_AND_FORCE_SIDE
        b1500.adc_setup('HRADC', 'PLC', 3)
        b1500.sweep_timing(params[2][3], params[2][4], step_delay=params[2][4])  # hold,delay. TODO: step delay?
        b1500.sweep_auto_abort(False, post='STOP')
        n = params[0][4]

        smus = list(b1500.smu_references)
        names = list(b1500.smu_names.values())
        # From inner scope to outer: Var name, place in param order, SMU name, place in SMU order, SMU reference.
        smu_prim = smus[names.index(params[3][params[2][-1].index(params[0][0])])]
        smu_sec = smus[names.index(params[3][params[2][-1].index(params[1][0])])]
        smu_const = smus[names.index(params[3][params[2][-1].index(params[2][0])])]
        smu_ground = smus[names.index(params[3][3])]
        smu_prim.compliance = params[0][5]
        smu_sec.compliance = params[1][2]
        smu_const.compliance = params[2][2]
        smu_ground.compliance = 1e-6  # Arbitrary
        smu_ground.force('Voltage', 'Auto Ranging', 0)
        smu_sec.force('Voltage', 'Auto Ranging', params[1][1])
        smu_const.force('Voltage', 'Auto Ranging', params[2][1])
        smu_prim.staircase_sweep_source('Voltage', 'LINEAR_SINGLE', 'Auto Ranging', params[0][1], params[0][2], n, params[0][5]) #jg

        b1500.check_errors()
        b1500.clear_buffer()
        b1500.clear_timer()

        v1 = list(np.linspace(params[0][1], params[0][2], int(params[0][4])))
        i = []
        start_time = datetime.now()
        t = []
        d_index = names.index(params[3][0])
        for k in range(int(params[1][3])):
            v = params[1][1]
            print("Starting measurement (" + params[1][0] + "=" + str(v) + "V)...")
            measurement_vars.incr_vars = [(2*k+1)/(2*params[1][3]), v, False]
            w.event_generate("<<prb-increment>>", when="tail")
            temp_t = datetime.now() - start_time
            t.append(temp_t.seconds + temp_t.microseconds/1e6)  # TODO: Where do I put this?
            b1500.send_trigger()
            b1500.check_idle()
            print("Measurement complete. ")
            measurement_vars.incr_vars = [(2*k+2)/(2*params[1][3]), v, True]
            w.event_generate("<<prb-increment>>", when="tail")
            if measurement_vars.stop_ex:
                measurement_vars.stop_ex = False
                w.event_generate("<<close-window>>", when="tail")
                return
            data = b1500.read_data(n)
            new_i = []
            for col in range(4):
                new_i.append(data.iloc[:, col].values.tolist())  # new_i is now a list of 4 lists
            i.append(new_i[d_index])
            measurement_vars.send_sweep = [v1, t, new_i]
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
            measurement_vars.ex_vars = [[v1] * (k + 1), t, i]  # For abortion purposes
        measurement_vars.ex_vars = [[v1]*int(params[1][3]), t, i]
        measurement_vars.ex_finished = True
    except Exception as e:
        tb = traceback.format_exc()
        logging.error("Measurement error: " + str(e) + ". Traceback: " + str(tb))
