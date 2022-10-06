import numpy as np
from csv import writer, reader
from visualization import off_noise


def numeric(s):
    try:
        float(fix_e(s, 'e'))
        return True
    except ValueError:
        return False


def fix_e(x, letter='E'):
    if type(x) == list or type(x) == np.ndarray:
        return [fix_e(i) for i in list(x)]
    # if type(x) != str:
    #     return
    xu = str(x).upper()
    lu = letter.upper()
    if lu in xu:
        num = float(xu[:xu.find(lu)])
        power = int(xu[xu.find(lu)+1:])
        return num * 10**power
    else:
        return float(x)


def suffix(x):  #TODO: Rename
    if len(x) == 0:
        raise ValueError
    if len(x) == 1 and numeric(x):
        return float(x)
    try:
        return fix_e(x, 'e')
    except ValueError:
        pass
    s = x[-1]
    num = float(x[:-1])
    match s:
        case 'm':
            return num * 1e-3
        case 'u':
            return num * 1e-6
        case 'n':
            return num * 1e-9
        case 'p':
            return num * 1e-12
    if numeric(x):
        return float(x)
    raise ValueError


# def fix_e_list(lst):
#     if type(lst[0]) == list:
#         return [list(map(fix_e,row)) for row in lst]
#     else:
#         return list(map(fix_e,lst))


#Non-Pandas version:
def add_experiment(index, date, operator, gas, concentration, carrier, atmosphere, serial, transistor, decoration, thickness, temperature, humidity, order, notes, data):
    with open("data/central.csv", newline='') as f:
        csv_reader = reader(f)
        existing_data = list(csv_reader)
    if str(index) not in [x[0] for x in existing_data]:
        with open("data/central.csv", "a+", newline='') as f:
            csv_writer = writer(f)
            csv_writer.writerow([index, date, operator, gas, concentration, carrier, atmosphere, serial, transistor, decoration, thickness, temperature, humidity, order, notes])
        with open("data/ex_"+str(index)+".csv", "w", newline='') as f:
            csv_writer = writer(f)
            csv_writer.writerows(data)
    else:
        print("Experiment index already exists!")


def data_to_spreadsheet_format(var1, var2, I0, Ia, label1, label2):
    col1 = np.repeat(var2, len(var1))
    col1 = ['V', label2, *col1]
    col2 = np.tile(var1, len(var2))
    col2 = ['V', label1, *col2]
    col3 = ['A', 'Idryair', *I0.flatten()]
    col4 = ['A', 'Ia', *Ia.flatten()]
    mat = np.asarray([col1, col2, col3, col4])
    return mat.transpose()


def spreadsheet_format_to_data(col1, col2, col3, col4=None): # No labels!
    same = 0
    while col1[same] == col1[0]:
        same = same + 1
        if same > len(col1) - 1:
            break
    rounds = len(col1) / same
    var1 = fix_e(np.array_split(col2, rounds))
    var2 = fix_e(col1[::same])
    i0 = off_noise(fix_e(np.array_split(col3, rounds)), 10**(-12))
    if col4 is not None:
        ia = off_noise(fix_e(np.array_split(col4, rounds)), 10**(-12))
        return var1, var2, i0, ia
    else:
        return var1, var2, i0




#Pandas version!
# def add_experiment_pandas(index, date, operator,  gas, carrier, serial, transistor, decoration, atmosphere, concentration, temperature, humidity, thickness, data):
#     df = pd.read_csv("data/central.csv", index_col=[0])
#     if not index in df.index:
#         ex = [date, operator,  gas, carrier, serial, transistor, decoration, atmosphere, concentration, temperature, humidity, thickness]
#         df.loc[index] = ex
#         df.to_csv("data/central.csv")
#
#     else:
#         print("Experiment index already exists!")


# mat = [[1,2,3],[4,5,6],[7,8,9]]
# add_experiment(0,date.today(),"Ofer","H2","dry air","i53","1","bare","?",0.5,300,0.5,10**-9,"JBD","Nothing useful.",mat)
# dmat = data_to_spreadsheet_format(np.linspace(-2.5,0.25,10), [-5,0,5], np.random.random_integers(0,100,30), np.random.random_integers(0,100,30), 'a', 'b')
# with open('data/test3.csv', "w", newline='') as f:
#     csv_writer = writer(f)
#     csv_writer.writerows(dmat)

# df = pd.read_csv("data/central.csv", index_col=[0])







#
# import matplotlib_inline
# # %matplotlib inline
# import shutil
# from pathlib import Path
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
#
# import qcodes as qc
# from qcodes.dataset import (
#     initialise_or_create_database_at,
#     load_or_create_experiment,
#     Measurement,
#     load_by_run_spec,
#     load_from_netcdf,
# )
# from qcodes.tests.instrument_mocks import (
#     DummyInstrument,
#     DummyInstrumentWithMeasurement,
# )
# from qcodes.dataset.plotting import plot_dataset
#
# # qc.logger.start_all_logging()
#
# # preparatory mocking of physical setup
# dac = DummyInstrument("dac", gates=["ch1", "ch2"])
# dmm = DummyInstrumentWithMeasurement("dmm", setter_instr=dac)
# station = qc.Station(dmm, dac)
#
# initialise_or_create_database_at("./export_example.db")
# exp = load_or_create_experiment(
#     experiment_name="exporting_data", sample_name="no sample"
# )
#
# meas = Measurement(exp)
# meas.register_parameter(dac.ch1)  # register the first independent parameter
# meas.register_parameter(dac.ch2)  # register the second independent parameter
# meas.register_parameter(
#     dmm.v2, setpoints=(dac.ch1, dac.ch2)
# )  # register the dependent one
#
# # run a 2D sweep
#
# with meas.run() as datasaver:
#     for v1 in np.linspace(0, 1, 200, endpoint=False):
#         for v2 in np.linspace(1, 2, 201):
#             dac.ch1(v1)
#             dac.ch2(v2)
#             val = dmm.v2.get()
#             datasaver.add_result((dac.ch1, v1), (dac.ch2, v2), (dmm.v2, val))
#
# dataset2 = datasaver.dataset
#
# dataset2.export("csv", path=".")
# dataset2.export_info
#
