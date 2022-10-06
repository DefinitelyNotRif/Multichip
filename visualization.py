import datetime

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
import numpy as np
# import scipy.interpolate
import matplotlib.colors as colors
from tkinter import messagebox
from statistics import mean

from matplotlib.ticker import MaxNLocator


def off_noise(data, threshold):
    if type(data[0]) == list:
        return [off_noise(x, threshold) for x in data]
    return [max(threshold, x) for x in data]

# IDK if I should set the primary and secondary variables explicitly... For now, var1 is VJG and var2 is VBG. VD is constant.
# The only things that should be changed if different variables are used, are the rows that call each function.

# noise = 10**-12
# var2 = np.linspace(-25,25,11)
# var1_nosplit = [-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25,-2.5,-2.457,-2.414,-2.371,-2.328,-2.28525,-2.24225,-2.19925,-2.15625,-2.11325,-2.07025,-2.02725,-1.98425,-1.9415,-1.8985,-1.8555,-1.8125,-1.7695,-1.7265,-1.6835,-1.6405,-1.59775,-1.55475,-1.51175,-1.46875,-1.42575,-1.38275,-1.33975,-1.29675,-1.254,-1.211,-1.168,-1.125,-1.082,-1.039,-0.996,-0.953,-0.91025,-0.86725,-0.82425,-0.78125,-0.73825,-0.69525,-0.65225,-0.60925,-0.5665,-0.5235,-0.4805,-0.4375,-0.3945,-0.3515,-0.3085,-0.2655,-0.22275,-0.17975,-0.13675,-0.09375,-0.05075,-0.00775,0.03525,0.078,0.121,0.164,0.207,0.25]
# var1 = np.array_split(var1_nosplit, 11) #Generates a 2d list with length 65 and height 11
# I0_nosplit = off_noise([3.97E-12, 2.45E-12, 2.09E-12, 3.99E-12, 4.05E-12, 4.05E-12, 1.90E-12, 3.88E-12, 1.80E-12, 1.95E-12, 3.80E-12, 1.58E-12, 1.60E-12, 3.20E-12, 1.66E-12, 1.47E-12, 3.46E-12, 1.79E-12, 2.27E-12, 1.22E-12, 3.20E-12, 3.16E-12, 1.37E-12, 1.22E-12, 1.09E-12, 1.22E-12, 3.10E-12, 2.77E-12, 1.20E-12, 2.97E-12, 1.25E-12, 2.78E-12, 1.22E-12, 2.81E-12, 1.78E-12, 2.36E-12, 2.01E-12, 1.87E-12, 1.95E-12, 2.22E-12, 1.57E-12, 1.51E-12, 1.09E-12, 1.54E-12, 1.01E-12, 1.25E-12, 2.02E-12, 2.11E-12, 5.60E-13, 3.90E-13, 4.00E-13, 1.80E-13, 4.00E-14, 6.40E-13, 1.60E-13, 7.50E-13, 7.00E-14, 9.00E-14, 6.00E-13, -3.50E-13, 2.20E-13, 4.17E-12, 2.45E-11, 1.25E-10, 5.62E-10, 9.50E-13, 1.84E-12, 1.07E-12, 7.00E-13, 9.70E-13, 1.45E-12, 1.33E-12, 5.30E-13, 1.05E-12, 1.21E-12, 1.31E-12, 3.40E-13, 7.70E-13, 5.10E-13, 1.26E-12, 1.02E-12, 1.16E-12, 1.03E-12, 1.03E-12, 1.33E-12, 8.81E-13, 7.92E-13, 4.40E-13, 5.95E-13, 6.10E-13, 5.00E-13, 1.50E-13, 1.40E-13, 2.20E-13, 6.50E-13, 2.90E-13, 6.50E-13, 2.00E-13, 4.30E-13, 7.00E-13, 4.10E-13, 2.00E-13, 5.90E-13, 5.30E-13, 2.80E-13, -2.20E-13, 2.10E-13, 4.30E-13, 3.50E-13, 3.70E-13, 1.00E-14, 3.40E-13, 7.00E-14, -7.00E-14, 2.30E-13, 2.00E-13, -2.60E-13, 5.60E-13, -2.10E-13, -4.20E-13, 1.70E-13, 4.70E-13, -3.20E-13, -3.30E-13, -2.50E-13, 7.90E-13, 5.09E-12, 2.80E-11, 1.42E-10, 6.21E-10, 1.01E-12, 8.10E-13, 7.60E-13, 7.70E-13, 8.80E-13, 8.70E-13, 7.00E-13, 8.50E-13, 7.50E-13, 2.70E-13, 9.30E-13, 5.70E-13, 7.10E-13, 4.20E-13, 7.09E-13, 8.47E-13, 5.54E-13, 6.55E-13, 7.70E-14, 7.22E-13, 5.25E-13, 3.25E-13, 2.65E-13, 4.21E-13, 7.39E-13, 4.69E-13, 2.16E-13, 3.30E-14, 5.00E-14, 3.80E-13, -2.50E-13, 3.90E-13, 2.60E-13, 2.90E-13, 5.30E-13, -3.90E-13, 4.50E-13, 4.50E-13, -1.40E-13, -5.40E-13, -4.20E-13, 2.40E-13, -6.20E-13, 3.20E-13, -4.60E-13, 9.00E-14, -6.30E-13, 0, 2.10E-13, -5.10E-13, 6.00E-14, -5.20E-13, -3.60E-13, -3.00E-14, -4.30E-13, -5.30E-13, -1.30E-13, -1.60E-13, -4.60E-13, 1.00E-14, 5.60E-13, 6.12E-12, 3.51E-11, 1.76E-10, 7.52E-10, 7.10E-13, 8.10E-13, 6.80E-13, 1.04E-12, 5.90E-13, 5.40E-13, 3.90E-13, 6.60E-13, 5.00E-13, 2.90E-13, 5.90E-13, 3.70E-13, 2.90E-13, 3.40E-13, 3.20E-13, 3.70E-13, 4.17E-13, 2.52E-13, 2.94E-13, 3.70E-13, 2.30E-13, 4.50E-13, -1.00E-14, 3.00E-13, 1.50E-13, 4.10E-13, 3.40E-13, 1.90E-13, -3.50E-13, 4.00E-13, -3.90E-13, -3.50E-13, -3.40E-13, -4.00E-13, 2.10E-13, -6.50E-13, -1.80E-13, -5.30E-13, 1.80E-13, -5.00E-13, 3.50E-13, -4.90E-13, 4.60E-13, 2.20E-13, 2.00E-13, 2.30E-13, -7.50E-13, 2.60E-13, -5.60E-13, -1.00E-12, -6.60E-13, 1.30E-13, -1.01E-12, -9.50E-13, -8.50E-13, -8.00E-13, 6.00E-14, -9.90E-13, -1.10E-13, -5.50E-13, 1.51E-12, 1.44E-11, 6.98E-11, 3.31E-10, 1.30E-09, 5.70E-13, -2.00E-14, 1.60E-13, 9.80E-13, 9.50E-13, -1.00E-14, 7.70E-13, 4.00E-14, 9.00E-13, 2.20E-13, -1.70E-13, 7.70E-13, -1.20E-13, 5.90E-13, 6.80E-13, 8.00E-14, 7.90E-13, 1.10E-13, 4.80E-13, -2.20E-13, -2.70E-13, 6.30E-13, -4.30E-13, 6.00E-13, -2.00E-13, 3.80E-13, 1.50E-13, -4.80E-13, 4.80E-13, -4.50E-13, 2.70E-13, 2.30E-13, -4.30E-13, -5.40E-13, -3.40E-13, -5.80E-13, -4.50E-13, -2.50E-13, -5.40E-13, -4.00E-14, -2.50E-13, -4.20E-13, 1.10E-13, -2.80E-13, -5.70E-13, -4.60E-13, 1.90E-13, -6.70E-13, -2.40E-13, -7.80E-13, -4.30E-13, -5.10E-13, -2.70E-13, -2.10E-13, -6.70E-13, -2.40E-13, -5.20E-13, -6.90E-13, 5.90E-13, 4.51E-12, 2.72E-11, 1.34E-10, 5.86E-10, 2.09E-09, 5.71E-09, 5.40E-13, 7.70E-13, 4.10E-13, 2.90E-13, 4.60E-13, 4.40E-13, 2.70E-13, 1.30E-13, 1.00E-13, 2.10E-13, -2.00E-14, -1.20E-13, 2.00E-14, 1.10E-13, 2.50E-13, -1.70E-13, 1.70E-13, 3.00E-14, 2.20E-13, -1.50E-13, -1.20E-13, -7.00E-14, -1.20E-13, 7.00E-14, -2.40E-13, -2.30E-13, -1.90E-13, -4.30E-13, -3.50E-13, -9.00E-14, -2.40E-13, -1.40E-13, -1.30E-13, -4.60E-13, -1.70E-13, -2.40E-13, -7.00E-13, -4.10E-13, -5.80E-13, -5.70E-13, -6.60E-13, -1.40E-13, -6.10E-13, -3.50E-13, -7.60E-13, -2.50E-13, 0, -5.50E-13, -7.40E-13, -2.70E-13, -6.60E-13, -1.05E-12, -2.50E-13, -7.30E-13, -1.00E-13, -5.60E-13, 1.66E-12, 9.45E-12, 4.44E-11, 1.94E-10, 7.35E-10, 2.29E-09, 5.76E-09, 1.17E-08, 2.08E-08, 1.16E-12, 8.60E-13, 1.60E-13, 7.10E-13, 6.20E-13, -3.00E-13, 5.00E-14, 5.40E-13, 7.00E-14, 4.10E-13, -9.00E-14, -2.00E-13, 4.70E-13, -5.40E-13, 2.10E-13, -4.40E-13, -1.70E-13, -1.70E-13, 2.20E-13, -1.60E-13, 2.20E-13, -6.90E-13, -4.60E-13, 1.10E-13, -4.13E-13, 2.20E-13, 2.99E-13, 1.58E-13, 3.77E-13, 1.15E-13, 1.91E-13, -4.41E-13, 4.63E-13, 4.40E-14, 2.43E-13, -1.53E-13, -1.91E-13, -1.11E-12, -4.06E-13, -6.29E-13, -7.73E-13, -9.45E-13, -1.90E-14, -7.98E-13, -1.07E-12, -6.90E-13, -9.10E-13, -6.20E-13, -2.30E-13, -1.34E-12, -2.80E-13, -4.40E-13, -8.70E-13, 3.30E-13, 3.46E-12, 1.90E-11, 8.68E-11, 3.58E-10, 1.17E-09, 3.46E-09, 8.43E-09, 1.62E-08, 2.70E-08, 3.99E-08, 5.41E-08, 5.70E-13, 1.50E-13, 3.00E-14, 1.80E-13, 0, 1.90E-13, -5.00E-14, -2.00E-14, 0, 1.40E-13, 5.00E-14, 5.00E-14, 2.10E-13, -1.30E-13, -2.80E-13, 1.10E-13, -3.40E-13, -5.00E-14, -2.30E-13, -3.80E-13, -1.10E-13, -2.28E-13, -3.00E-15, -5.20E-14, 1.86E-13, -2.95E-13, -1.30E-13, -1.30E-13, -6.60E-13, -1.80E-13, -7.70E-13, -1.60E-13, -4.80E-13, -1.00E-14, -1.07E-12, -6.60E-13, 2.00E-13, -9.40E-13, -1.08E-12, -3.70E-13, -6.00E-14, -1.17E-12, -3.40E-13, -1.07E-12, -3.90E-13, -6.00E-13, -1.28E-12, -4.00E-13, -2.00E-14, -1.15E-12, 3.20E-13, 2.05E-12, 1.07E-11, 4.73E-11, 1.85E-10, 6.46E-10, 1.98E-09, 5.49E-09, 1.24E-08, 2.38E-08, 3.86E-08, 5.55E-08, 7.35E-08, 9.09E-08, 1.08E-07, 1.40E-13, -2.50E-13, 3.70E-13, 5.80E-13, -3.50E-13, 5.60E-13, -4.00E-13, 4.30E-13, -2.80E-13, -3.20E-13, 3.60E-13, 4.30E-13, -3.00E-13, -6.30E-13, 2.40E-13, -9.00E-14, -6.00E-13, 6.00E-14, 7.00E-14, -6.00E-13, -6.40E-13, -6.30E-13, -1.30E-13, -3.20E-13, -9.60E-13, -8.40E-13, -6.80E-13, -3.10E-13, -3.50E-13, -3.90E-13, -7.20E-13, -1.80E-13, -8.80E-13, -7.70E-13, -3.70E-13, -5.20E-13, -5.30E-13, -6.40E-13, -1.13E-12, -5.50E-13, -9.50E-13, -7.40E-13, -6.00E-13, -3.90E-13, -9.80E-13, -4.20E-13, 5.40E-13, 3.28E-12, 1.29E-11, 4.19E-11, 1.56E-10, 4.83E-10, 1.38E-09, 3.55E-09, 7.83E-09, 1.57E-08, 2.86E-08, 4.56E-08, 6.39E-08, 8.31E-08, 1.03E-07, 1.22E-07, 1.40E-07, 1.59E-07, 1.77E-07, 9.70E-13, -4.70E-13, -4.20E-13, 5.10E-13, -5.00E-13, 1.70E-13, -2.00E-14, -5.10E-13, -6.90E-13, 6.00E-14, -8.20E-13, 3.80E-13, 5.80E-13, -6.40E-13, -2.00E-13, 6.20E-13, -9.70E-13, 6.20E-13, -7.10E-13, 3.20E-13, -8.10E-13, 3.90E-13, -1.12E-12, -5.90E-13, 2.80E-13, 3.60E-13, -1.04E-12, -1.33E-12, 4.20E-13, -1.01E-12, 1.60E-13, 1.00E-13, -7.20E-13, -9.00E-13, -3.00E-14, -1.40E-12, -1.30E-13, -2.00E-13, 3.00E-14, 2.40E-13, -9.10E-13, 1.13E-12, 3.56E-12, 1.39E-11, 4.06E-11, 1.07E-10, 2.96E-10, 7.44E-10, 1.71E-09, 4.17E-09, 8.45E-09, 1.57E-08, 2.68E-08, 4.23E-08, 5.99E-08, 8.11E-08, 1.01E-07, 1.23E-07, 1.42E-07, 1.62E-07, 1.80E-07, 1.99E-07, 2.18E-07, 2.37E-07, 2.55E-07, 4.80E-13, 4.70E-13, 5.70E-13, 2.00E-13, -5.00E-14, 4.20E-13, 2.41E-13, 3.11E-13, -4.50E-14, -2.00E-14, 9.00E-14, 2.20E-13, -2.80E-13, 2.10E-13, -5.70E-13, 2.60E-13, 6.00E-14, -4.50E-13, -2.80E-13, -3.00E-14, -5.50E-13, -6.80E-13, -6.20E-13, 0, 7.00E-14, -9.40E-13, -1.20E-13, -4.10E-13, 1.00E-13, -9.20E-13, -3.20E-13, -8.00E-14, 1.70E-13, -4.10E-13, 1.49E-12, 2.09E-12, 7.18E-12, 1.96E-11, 4.02E-11, 9.99E-11, 2.22E-10, 5.07E-10, 1.01E-09, 1.91E-09, 3.88E-09, 7.11E-09, 1.24E-08, 2.14E-08, 3.33E-08, 4.91E-08, 6.82E-08, 8.88E-08, 1.10E-07, 1.31E-07, 1.51E-07, 1.71E-07, 1.91E-07, 2.10E-07, 2.29E-07, 2.47E-07, 2.65E-07, 2.84E-07, 3.02E-07, 3.20E-07, 3.39E-07], noise)
# I0 = np.array_split(I0_nosplit,11)
# Ia_nosplit = off_noise([5.73E-12, 5.52E-12, 6.36E-12, 5.98E-12, 5.48E-12, 4.89E-12, 5.63E-12, 5.46E-12, 4.81E-12, 4.93E-12, 4.82E-12, 5.21E-12, 4.92E-12, 4.98E-12, 4.84E-12, 4.71E-12, 4.57E-12, 4.28E-12, 4.85E-12, 5.18E-12, 4.92E-12, 4.63E-12, 4.68E-12, 5.06E-12, 4.89E-12, 4.50E-12, 4.86E-12, 4.66E-12, 4.04E-12, 4.48E-12, 4.55E-12, 4.17E-12, 4.52E-12, 4.27E-12, 4.16E-12, 4.60E-12, 4.27E-12, 4.52E-12, 4.15E-12, 4.12E-12, 3.95E-12, 4.13E-12, 4.58E-12, 3.89E-12, 4.03E-12, 3.86E-12, 3.70E-12, 3.87E-12, 3.13E-12, 3.00E-12, 2.98E-12, 3.17E-12, 3.77E-12, 6.01E-12, 9.43E-12, 1.58E-11, 2.86E-11, 5.16E-11, 9.25E-11, 1.72E-10, 3.34E-10, 6.51E-10, 1.30E-09, 2.61E-09, 5.08E-09, 4.98E-12, 5.13E-12, 5.19E-12, 4.32E-12, 4.70E-12, 4.72E-12, 4.87E-12, 4.73E-12, 4.87E-12, 4.33E-12, 4.56E-12, 4.60E-12, 4.30E-12, 4.23E-12, 4.06E-12, 4.55E-12, 4.17E-12, 4.63E-12, 4.44E-12, 4.81E-12, 4.97E-12, 4.57E-12, 4.14E-12, 4.42E-12, 4.49E-12, 3.97E-12, 4.19E-12, 3.93E-12, 4.16E-12, 4.02E-12, 3.98E-12, 3.91E-12, 4.18E-12, 4.11E-12, 3.87E-12, 3.88E-12, 4.34E-12, 4.09E-12, 3.26E-12, 3.99E-12, 3.88E-12, 3.43E-12, 3.12E-12, 3.70E-12, 3.48E-12, 3.38E-12, 2.72E-12, 2.18E-12, 2.62E-12, 2.07E-12, 2.77E-12, 3.05E-12, 4.38E-12, 6.78E-12, 1.20E-11, 2.03E-11, 3.50E-11, 6.11E-11, 1.11E-10, 2.04E-10, 3.88E-10, 7.36E-10, 1.46E-09, 2.83E-09, 5.43E-09, 6.84E-12, 6.79E-12, 6.15E-12, 6.08E-12, 5.77E-12, 5.53E-12, 5.47E-12, 5.43E-12, 5.37E-12, 4.99E-12, 5.04E-12, 5.07E-12, 5.28E-12, 4.88E-12, 4.94E-12, 5.03E-12, 4.96E-12, 5.17E-12, 5.12E-12, 4.92E-12, 5.14E-12, 5.56E-12, 4.57E-12, 4.88E-12, 5.26E-12, 5.27E-12, 4.63E-12, 4.52E-12, 4.40E-12, 4.79E-12, 4.89E-12, 3.92E-12, 5.04E-12, 3.77E-12, 4.18E-12, 5.00E-12, 4.94E-12, 4.85E-12, 4.37E-12, 4.89E-12, 3.60E-12, 4.92E-12, 4.71E-12, 3.14E-12, 4.50E-12, 3.19E-12, 4.13E-12, 4.18E-12, 4.29E-12, 4.99E-12, 6.75E-12, 8.72E-12, 1.29E-11, 1.76E-11, 3.00E-11, 4.68E-11, 7.29E-11, 1.24E-10, 2.03E-10, 3.46E-10, 6.11E-10, 1.09E-09, 1.97E-09, 3.60E-09, 6.49E-09, 9.60E-12, 9.34E-12, 9.87E-12, 9.10E-12, 7.83E-12, 7.56E-12, 9.27E-12, 6.46E-12, 8.92E-12, 7.15E-12, 7.03E-12, 7.40E-12, 8.31E-12, 6.53E-12, 6.93E-12, 8.48E-12, 7.36E-12, 6.45E-12, 8.49E-12, 6.57E-12, 6.84E-12, 7.56E-12, 8.52E-12, 7.98E-12, 5.90E-12, 7.16E-12, 7.67E-12, 6.85E-12, 6.08E-12, 7.22E-12, 7.88E-12, 5.69E-12, 6.68E-12, 6.34E-12, 7.02E-12, 5.30E-12, 5.31E-12, 5.18E-12, 4.41E-12, 6.03E-12, 4.30E-12, 5.86E-12, 3.87E-12, 6.04E-12, 4.69E-12, 6.09E-12, 6.80E-12, 1.00E-11, 1.28E-11, 1.79E-11, 2.94E-11, 4.24E-11, 6.45E-11, 9.86E-11, 1.49E-10, 2.24E-10, 3.34E-10, 5.07E-10, 7.60E-10, 1.13E-09, 1.73E-09, 2.66E-09, 4.14E-09, 6.51E-09, 1.02E-08, 1.67E-11, 1.63E-11, 1.43E-11, 1.72E-11, 1.63E-11, 1.45E-11, 1.38E-11, 1.34E-11, 1.32E-11, 1.43E-11, 1.43E-11, 1.23E-11, 1.37E-11, 1.22E-11, 1.30E-11, 1.20E-11, 1.13E-11, 1.40E-11, 1.41E-11, 1.14E-11, 1.21E-11, 1.09E-11, 1.13E-11, 1.11E-11, 1.25E-11, 1.15E-11, 1.31E-11, 1.14E-11, 1.15E-11, 1.16E-11, 1.11E-11, 1.05E-11, 1.15E-11, 1.14E-11, 9.97E-12, 9.61E-12, 1.09E-11, 9.69E-12, 1.19E-11, 1.22E-11, 1.49E-11, 1.81E-11, 2.41E-11, 3.59E-11, 4.33E-11, 5.94E-11, 8.41E-11, 1.22E-10, 1.78E-10, 2.50E-10, 3.51E-10, 4.90E-10, 6.66E-10, 9.38E-10, 1.29E-09, 1.76E-09, 2.36E-09, 3.20E-09, 4.19E-09, 5.55E-09, 7.33E-09, 9.72E-09, 1.29E-08, 1.71E-08, 2.28E-08, 5.37E-11, 5.64E-11, 5.17E-11, 5.07E-11, 4.44E-11, 4.41E-11, 4.45E-11, 4.43E-11, 4.21E-11, 4.15E-11, 4.21E-11, 3.98E-11, 3.65E-11, 3.95E-11, 4.09E-11, 3.88E-11, 3.68E-11, 3.70E-11, 3.58E-11, 3.70E-11, 3.66E-11, 3.39E-11, 3.23E-11, 3.44E-11, 3.37E-11, 3.36E-11, 3.19E-11, 3.02E-11, 2.79E-11, 3.08E-11, 2.89E-11, 2.92E-11, 3.07E-11, 3.20E-11, 3.27E-11, 3.68E-11, 5.14E-11, 6.37E-11, 8.17E-11, 1.03E-10, 1.40E-10, 2.07E-10, 2.83E-10, 4.04E-10, 5.72E-10, 7.67E-10, 1.11E-09, 1.46E-09, 1.95E-09, 2.61E-09, 3.51E-09, 4.57E-09, 5.59E-09, 7.12E-09, 9.07E-09, 1.13E-08, 1.33E-08, 1.59E-08, 1.82E-08, 2.14E-08, 2.52E-08, 2.90E-08, 3.37E-08, 3.94E-08, 4.67E-08, 1.49E-10, 1.52E-10, 1.51E-10, 1.46E-10, 1.44E-10, 1.37E-10, 1.44E-10, 1.36E-10, 1.28E-10, 1.30E-10, 1.22E-10, 1.30E-10, 1.22E-10, 1.17E-10, 1.19E-10, 1.23E-10, 1.12E-10, 1.18E-10, 1.03E-10, 1.06E-10, 1.03E-10, 1.02E-10, 1.01E-10, 1.03E-10, 1.06E-10, 1.13E-10, 1.16E-10, 1.33E-10, 1.71E-10, 2.31E-10, 2.96E-10, 3.60E-10, 5.46E-10, 7.63E-10, 1.01E-09, 1.41E-09, 1.72E-09, 2.39E-09, 2.94E-09, 3.64E-09, 4.42E-09, 5.48E-09, 7.10E-09, 8.09E-09, 9.77E-09, 1.19E-08, 1.41E-08, 1.64E-08, 1.82E-08, 2.11E-08, 2.35E-08, 2.65E-08, 3.01E-08, 3.31E-08, 3.79E-08, 4.16E-08, 4.60E-08, 4.96E-08, 5.38E-08, 5.81E-08, 6.26E-08, 6.71E-08, 7.25E-08, 7.90E-08, 8.67E-08, 3.12E-10, 3.40E-10, 3.30E-10, 3.47E-10, 3.45E-10, 3.33E-10, 3.44E-10, 3.40E-10, 3.52E-10, 3.41E-10, 3.45E-10, 3.44E-10, 3.30E-10, 3.30E-10, 3.23E-10, 3.32E-10, 3.25E-10, 3.36E-10, 4.14E-10, 5.34E-10, 6.90E-10, 1.12E-09, 1.38E-09, 2.01E-09, 3.48E-09, 4.57E-09, 6.21E-09, 7.34E-09, 9.82E-09, 1.06E-08, 1.49E-08, 1.73E-08, 2.04E-08, 2.43E-08, 2.84E-08, 3.14E-08, 3.46E-08, 3.81E-08, 4.29E-08, 4.68E-08, 5.04E-08, 5.40E-08, 5.66E-08, 6.11E-08, 6.37E-08, 6.59E-08, 6.95E-08, 7.32E-08, 7.62E-08, 7.91E-08, 8.24E-08, 8.55E-08, 8.88E-08, 9.21E-08, 9.50E-08, 9.84E-08, 1.02E-07, 1.05E-07, 1.09E-07, 1.13E-07, 1.17E-07, 1.22E-07, 1.28E-07, 1.35E-07, 1.44E-07, 1.04E-09, 1.02E-09, 1.00E-09, 8.71E-10, 8.69E-10, 8.46E-10, 7.93E-10, 8.53E-10, 8.18E-10, 8.20E-10, 9.10E-10, 1.11E-09, 1.65E-09, 2.47E-09, 3.82E-09, 5.03E-09, 7.52E-09, 1.18E-08, 1.69E-08, 2.30E-08, 2.73E-08, 3.36E-08, 3.89E-08, 4.39E-08, 5.11E-08, 5.47E-08, 5.98E-08, 6.46E-08, 6.90E-08, 7.29E-08, 7.76E-08, 8.18E-08, 8.64E-08, 8.92E-08, 9.32E-08, 9.75E-08, 1.01E-07, 1.04E-07, 1.08E-07, 1.11E-07, 1.14E-07, 1.18E-07, 1.21E-07, 1.24E-07, 1.28E-07, 1.31E-07, 1.34E-07, 1.38E-07, 1.41E-07, 1.44E-07, 1.48E-07, 1.51E-07, 1.55E-07, 1.58E-07, 1.62E-07, 1.66E-07, 1.70E-07, 1.74E-07, 1.78E-07, 1.82E-07, 1.86E-07, 1.92E-07, 1.98E-07, 2.05E-07, 2.14E-07, 2.91E-09, 2.90E-09, 3.18E-09, 3.63E-09, 4.98E-09, 6.42E-09, 9.59E-09, 1.53E-08, 1.99E-08, 2.80E-08, 3.42E-08, 4.24E-08, 4.96E-08, 5.78E-08, 6.61E-08, 7.33E-08, 8.15E-08, 8.68E-08, 9.16E-08, 9.58E-08, 1.03E-07, 1.07E-07, 1.12E-07, 1.17E-07, 1.21E-07, 1.25E-07, 1.29E-07, 1.33E-07, 1.37E-07, 1.41E-07, 1.45E-07, 1.48E-07, 1.52E-07, 1.56E-07, 1.60E-07, 1.64E-07, 1.67E-07, 1.71E-07, 1.75E-07, 1.79E-07, 1.82E-07, 1.86E-07, 1.90E-07, 1.94E-07, 1.97E-07, 2.01E-07, 2.05E-07, 2.09E-07, 2.13E-07, 2.17E-07, 2.21E-07, 2.25E-07, 2.29E-07, 2.32E-07, 2.36E-07, 2.40E-07, 2.45E-07, 2.49E-07, 2.54E-07, 2.58E-07, 2.63E-07, 2.69E-07, 2.76E-07, 2.83E-07, 2.93E-07, 6.97E-08, 7.34E-08, 8.20E-08, 8.79E-08, 9.32E-08, 1.01E-07, 1.07E-07, 1.14E-07, 1.20E-07, 1.24E-07, 1.29E-07, 1.36E-07, 1.39E-07, 1.45E-07, 1.50E-07, 1.53E-07, 1.58E-07, 1.63E-07, 1.67E-07, 1.71E-07, 1.75E-07, 1.79E-07, 1.84E-07, 1.88E-07, 1.91E-07, 1.96E-07, 2.00E-07, 2.04E-07, 2.08E-07, 2.12E-07, 2.16E-07, 2.19E-07, 2.24E-07, 2.27E-07, 2.31E-07, 2.35E-07, 2.39E-07, 2.43E-07, 2.47E-07, 2.51E-07, 2.55E-07, 2.59E-07, 2.63E-07, 2.67E-07, 2.71E-07, 2.75E-07, 2.80E-07, 2.84E-07, 2.88E-07, 2.92E-07, 2.97E-07, 3.01E-07, 3.06E-07, 3.10E-07, 3.15E-07, 3.20E-07, 3.25E-07, 3.29E-07, 3.35E-07, 3.40E-07, 3.46E-07, 3.52E-07, 3.59E-07, 3.67E-07, 3.77E-07], noise)
# Ia = np.array_split(Ia_nosplit,11)


def remove_latex(s):
    if '$' in s:  # In case it's in LaTeX, make it readable in plaintext.
        return str(s).replace('$', '').replace('\\', '').replace('_', '').replace('{', '').replace('}', '')
    else:
        return str(s)


def plot_yvv(primary, secondary, y, labelx, labely, log, last_right=False):
    # if len(secondary) == 1:
    #     plot_yv(primary, y[0], labelx, labely)
    #     return
    if all([len(row) == 1 for row in y]):  # There is only 1 data point per secondary value.
        msg = ''
        for s, val in zip(secondary, y):
            val_msg = str(float('%.4g' % val[0]))
            msg += (remove_latex(s) + ': ' + val_msg + '\n')
        messagebox.showinfo('', msg[:-1])  # The [:-1] clips the '\n' at the end
        return
    font = {'family': 'Times New Roman',
            'size': 10,
            }
    # matplotlib.rcParams['toolbar'] = 'None'
    if last_right:
        fig, ax1 = plt.subplots(figsize=(3.5, 3.5))
        ax2 = ax1.twinx()
        ax1.format_coord = lambda x, y: ''
        ax2.format_coord = lambda x, y: ''
        for i in range(0, len(secondary)-1):
            ax1.plot(primary[i], y[i])
        if all([type(l) != str for l in secondary[:-1]]):   # If the secondary axis consists of numbers, round them to
                                                            # avoid float errors.
            ax1.legend([str(round(x, 3)) for x in secondary[:-1]], prop=font, loc='center left')
        else:
            ax1.legend([str(x) for x in secondary[:-1]], prop=font, loc='center left')
        ax2.plot(primary[-1], y[-1], color='g')
        plt.rcParams.update({'mathtext.default': 'regular'})
        if log:
            plt.yscale('log')
        ax1.set_xlabel(labelx, fontdict=font)
        ax2.set_xlabel(labelx, fontdict=font)
        ax1.set_ylabel(labely, fontdict=font)
        ax2.set_ylabel(secondary[-1], fontdict=font)
        ax1.tick_params(labelsize=10)
        ax2.tick_params(labelsize=10)

        # plt.savefig('IV from test data.png', bbox_inches="tight")
        plt.tight_layout(h_pad=None, w_pad=None, rect=None)
        plt.show()
    else:
        figure(figsize=(3.5, 3.5))
        plt.gca().format_coord = lambda x, y: ''
        for i in range(0, len(secondary)):
            plt.plot(primary[i], y[i])
        plt.rcParams.update({'mathtext.default':  'regular' })
        if log:
            plt.yscale('log')
        plt.xlabel(labelx, fontdict=font)
        plt.ylabel(labely, fontdict=font)
        plt.xticks(fontsize=10, fontname='Times New Roman')
        plt.yticks(fontsize=10, fontname='Times New Roman')
        plt.locator_params(axis='x', nbins=6)
        if all([type(l) != str for l in secondary[:-1]]):   # If the secondary axis consists of numbers, round them to
                                                            # avoid float errors.
            plt.legend([str(round(x, 3)) for x in secondary], prop=font)
        else:
            plt.legend([str(x) for x in secondary], prop=font)
        # plt.savefig('IV from test data.png', bbox_inches="tight")
        plt.tight_layout(h_pad=None, w_pad=None, rect=None)
        plt.show()


def plot_yv(x, y, labelx, labely, forcelin=False, transient=False):
    if len(x) == 1:
        messagebox.showinfo('', remove_latex(labely) + ": " + str(float('%.4g' % y[0])))
        return
    # matplotlib.rcParams['toolbar'] = 'None'
    figure(figsize=(3.5, 3.5))
    plt.gca().format_coord = lambda x, y: ''
    font = {'family': 'Times New Roman',
            'size': 10,
            }
    plt.plot(x, y)
    plt.rcParams.update({'mathtext.default': 'regular'})
    plt.xlabel(labelx, fontdict=font)
    plt.ylabel(labely, fontdict=font)
    plt.xticks(fontsize=10, fontname='Times New Roman')
    plt.yticks(fontsize=10, fontname='Times New Roman')
    if transient:
        locator = MaxNLocator(nbins=6)
        plt.gca().xaxis.set_major_locator(locator)
        plt.gca().xaxis.set_major_formatter(lambda x, pos: str(datetime.timedelta(seconds=x)))
    if max(y)/100 > min(y) and not forcelin:
        plt.yscale('log')
    # plt.savefig('IV from test data.png', bbox_inches="tight")
    plt.tight_layout(h_pad=None, w_pad=None, rect=None)
    plt.show()


closest = lambda lst, val : min(lst, key=lambda x:abs(x-val))

def vth_constant(V1, V2, I, const):
    VTH = []
    for i in range(len(V2)):
        # Iarr = np.asarray(I[i])
        # if not any(Iarr > const):
        #     VTH.append(max(V1[i]))  # TODO: Do something else...
        # else:
        #     VTH.append(V1[i][list(I[i]).index(min(Iarr[Iarr > const]))])
        VTH.append(V1[i][list(I[i]).index(closest(I[i], const))])
    return VTH


def vth_rel(V1, V2, I, threshold): #USE WITH FILTERED!
    VTH=[]
    for i in range(len(V2)):
        imax = max(I[i])
        imin = min(I[i])
        VTH.append(V1[i][list(I[i]).index(closest(I[i], (imax-imin)*threshold+imin))])
    return VTH


# gavg = lambda arr: np.exp(np.mean(np.log(arr)))


# from scipy import ndimage
def smooth(arr, win):
    # arr = np.asarray(lst)
    filtered = []
    for i in range(len(arr)):
        filtered.append(mean(arr[max(i-win, 0):min(i+win, len(arr))]))
    return filtered


def vth_sd(V1, V2, I):
    VTH = []
    win = 3
    for i in range(len(V2)):
        zd = np.asarray(I[i])
        # zd = smooth(zd, win)
        fd = np.gradient(zd)
        fd = smooth(fd, win)
        sd = np.gradient(fd)
        # sd = smooth(sd, win)
        plt.plot(fd)
        VTH.append(V1[i][list(sd).index(max(sd))])
    # plt.yscale('log')
    plt.show()
    return VTH


def vth_lin(V1, V2, I):
    VTH = []
    for i in range(len(V2)):
        zd = np.asarray(I[i])
        # zd = smooth(zd, win)
        fd = np.gradient(zd)
        # fd = smooth(fd, win)
        sd = list(np.gradient(fd))[:60]
        maxidx = sd.index(max(sd))
        indices = [index for index, value in enumerate(sd) if index >= maxidx and value <= 0]
        if indices == []:
            VTH.append(V1[i][-1])
        else:
            lin = zd[indices[0]:]
            linx = V1[i][indices[0]:]
            slope = (lin[-1]-lin[0])/(linx[-1]-linx[0])
            mid = round(len(lin)/2)
            b = lin[mid] - slope * linx[mid]
            th = -b/slope
            VTH.append(th)
            # linfunc = [slope * x + b for x in V1[i]]
            # figure()
            # plt.plot(V1[i], I[i])
            # plt.plot(V1[i], linfunc)
            # plt.show()
    return VTH


def response(I0, Ia):
    s = []
    for i in range(len(I0)):
        srow=[]
        for j in range(len(I0[i])):
            Ihigh = max(I0[i][j],Ia[i][j])
            Ilow = min(I0[i][j],Ia[i][j])
            srow.append(abs((Ihigh-Ilow)/Ilow))
        s.append(srow)
    return s


def plot_heatmap(mat, varx, vary, labelx, labely, labelc, interp):
    if len(varx) == 1:
        plot_yv(vary[0], mat[0], labely, labelc)
        return
    fig = figure(figsize=(3.5, 3.5))
    # matplotlib.rcParams['toolbar'] = 'None'
    plt.gca().format_coord = lambda x, y: ''
    font = {'family': 'Times New Roman',
            'size': 10,
            }
    plt.rcParams.update({'mathtext.default': 'regular'})
    plt.xlabel(labelx, fontdict=font)
    plt.ylabel(labely, fontdict=font)
    plt.xticks(fontsize=10, fontname='Times New Roman')
    plt.yticks(fontsize=10, fontname='Times New Roman')
    # plt.set_label(labely, labelpad=8, rotation=270)
    # plt.savefig('IV from test data.png', bbox_inches="tight")
    plt.tight_layout(h_pad=None, w_pad=None, rect=None)

    if interp:
        # y = [vary[row][col] for col in range(len(vary[0])) for row in range(len(vary))]
        # x = np.tile(varx, len(y))
        # # y = np.repeat(vary, len(varx))
        # z = np.asarray(mat).transpose().flatten()
        # xi = np.linspace(min(x), max(x), 100)
        # yi = np.linspace(min(y), max(y), 100)
        # xi, yi = np.meshgrid(xi, yi)
        # interp = scipy.interpolate.LinearNDInterpolator(list(zip(x, y)), z)
        # zi = interp(xi, yi)
        # plt.pcolormesh(xi, yi, zi, shading='auto', cmap='plasma')
        pass
    else:
        x = varx
        # y = vary
        y = vary[0]
        z = np.asarray(mat).transpose()
        z[z < 1e-12] = 1e-12  # To prevent 0 values with a log scale
        plt.pcolormesh(x, y, z, shading='auto', cmap='plasma', norm=colors.LogNorm(vmin=z.min(), vmax=z.max()))
    cbar = plt.colorbar(fraction=0.22)
    # print(cbar.fraction)
    cbar.set_label(labelc, labelpad=8, rotation=270, fontdict=font)
    cbar.format_coord = lambda x, y: ''
    plt.show()


def sts(V, I):
    zd = np.log(np.asarray(I))
    fd = np.gradient(zd)
    # plt.plot(fd)
    halfmax = fd.min() + 0.7 * (fd.max() - fd.min())  # TODO: Arbitrarily defined by 0.7. Is there a value I "should" use?
    STz = zd[fd > halfmax]
    STv = np.asarray(V)[fd > halfmax]
    if len(STz) < 2 or len(STv) < 2:
        raise ZeroDivisionError
    else:
        slope = (STz[-1] - STz[0]) / (STv[-1] - STv[0])
        # slope = max(fd)
        return np.log(10)/slope


def ioff(I):
    Iarr = np.asarray((I))
    li = np.log(Iarr)
    halfmax = li.min() + 0.2 * (li.max() - li.min()) #TODO: Arbitrarily defined as 0.2!
    off = Iarr[li < halfmax]
    return np.average(off)


def ion(I, threshold): #TODO: The "on" region is defined by an arbitrary threshold. Maybe make it relative? Maybe define it by the derivative?!
    Iarr = np.asarray((I))
    on = Iarr[Iarr >= threshold]
    if on.size != 0:
        return np.average(on)
    else:
        return 0


def filter_regionless(V1, V2, i0, ia=None):
    v1_filtered = []
    v2_filtered = []
    i0_filtered = []
    ia_filtered = []
    threshold = 2.5
    if V2 is not None:
        for i in range(len(V2)):
            if ia is not None:
                if max(i0[i])/(10**threshold) > min(i0[i]) and max(ia[i])/(10**threshold) > min(ia[i]):
                    v1_filtered.append(V1[i])
                    v2_filtered.append(V2[i])
                    i0_filtered.append(i0[i])
                    ia_filtered.append(ia[i])
            else:
                if max(i0[i]) / (10 ** threshold) > min(i0[i]): #TODO: There's probably a more elegant way to write this. I'm tired.
                    v1_filtered.append(V1[i])
                    v2_filtered.append(V2[i])
                    i0_filtered.append(i0[i])
        if len(i0_filtered) == 0:  # Trying to return empty lists, since none of the sweeps span 2.5 decades
            raise IndexError
        if ia is not None:
            return v1_filtered, v2_filtered, i0_filtered, ia_filtered
        return v1_filtered, v2_filtered, i0_filtered
    else:  # Called from a transient measurement, only V1 and i0 exist. TODO: Will this ever be called?!
        for i in range(len(i0)):
            if max(i0[i]) / (10 ** threshold) > min(i0[i]):
                v1_filtered.append(V1[i])
                i0_filtered.append(i0[i])
        if len(i0_filtered) == 0:
            raise IndexError
        return v1_filtered, i0_filtered


# def main():
    # plot_yvv(var1,var2,I0, "$V_{JG} (V)$", "$I_0 (A)$", True)
    # plot_yvv(var1,var2,Ia, "$V_{JG} (V)$", "$I_a (A)$", True)
    # TH1 = vth_constant(var1, var2, I0, 10**-9)
    # plot_yv(var2, TH1, "$V_{BG} (V)$", "$V_{TH} (V)$")
    # TH2 = vth_sd(var1, var2, I0)
    # plot_yv(var2, TH2, "$V_{BG} (V)$", "$V_{TH} (V)$")
    # plot_vth(var2, [TH1[i]-TH2[i] for i in range(len(TH1))], "$V_{BG} (V)", "$\Delta V_{TH} (V)$")   #Difference between the two methods
    # THa1 = vth_constant(var1, var2, Ia, 10**-9)
    # THa2 = vth_sd(var1, var2, Ia)
    # plot_vth(var2, [TH1[i]-THa1[i] for i in range(len(TH1))], "$V_{BG} (V)$", "$\Delta V_{TH} (V)$")  #Difference after exposure
    # plot_yvv(var1, var2, response(I0, Ia), "$V_{JG} (V)$", "Response", True)
    # plt.imshow(response(I0,Ia), cmap='plasma', interpolation='nearest', aspect='auto')
    # plot_heatmap(Ia,var2,var1[0],"$V_{BG} (V)$","$V_{JG} (V)$", True)

    # res = np.asarray(response(I0,Ia))
    # plot_heatmap(res,var2,var1[0],"$V_{BG} (V)$","$V_{JG} (V)$", False)
    # plot_yv(var2, res.max(1), "$V_{BG}} (V)$", "Max response")

    # STS0, STSa = [], []
    # for i in range(len(var2)):
    #     STS0.append(sts(var1[i],I0[i]))
    #     STSa.append(sts(var1[i],Ia[i]))
    # plt.plot(var2,STS0)
    # plt.plot(var2,STSa)
    # plt.show()

    # Ioff = [ioff(x) for x in I0]
    # plot_yv(var2,Ioff,"$V_{BG} (V)$","$I_{off} (A)$")
    # Ion = [ion(x,10**-8) for x in Ia]
    # plot_yv(var2,Ion,"$V_{BG} (V)$","$I_{on} (A)$")


# TH1 = vth_constant(var1, var2, Ia, 10**-9)
# TH4 = vth_rel(var1, var2, Ia, 0.05)
# plot_yvv([var2]*2, ['const', 'rel'], [TH1, TH4], "$V_{BG} (V)$", "$V_{TH} (V)$", False)
# f1, f2, fi0, fia = filter_regionless(var1, var2, I0, Ia)
# vth = vth_rel(f1, f2, fia, 0.05)
# vthc = vth_constant(f1, f2, fia, 10**-9)
# for i in range(len(f2)):
#     plt.plot(f1[i], fia[i])
#     plt.yscale('log')
    # th = (max(fia[i])-min(fia[i]))*0.05+min(fia[i])
    # plt.plot(vth[i], th, 'o')
    # plt.plot(vthc[i], 10**-9, 'x')
# plt.show()

# TH2 = vth_sd(var1, var2, Ia)
# plot_yv(var2, TH2, "$V_{BG} (V)$", "$V_{TH} (V)$", True)
# plot_yvv([var2]*2, ['const', 'sd'], [TH1, TH2], "$V_{BG} (V)$", "$V_{TH} (V)$", False)
# THa2 = vth_sd(var1, var2, Ia)
# plot_yv(var2, THa2, "$V_{BG} (V)$", "$V_{TH} (V)$", True)
# TH3 = vth_lin(var1, var2, Ia)
# plot_yv(var2, TH3, "$V_{BG} (V)$", "$V_{TH} (V)$", True)
# plot_yvv([var2]*3, ['const', 'sd', 'lin'], [TH1, THa2, TH3], "$V_{BG} (V)$", "$V_{TH} (V)$", False)

# STS0, STSa = [], []
# for i in range(len(var2)-1):
#     STS0.append(1000*sts(var1[i],I0[i]))
#     STSa.append(1000*sts(var1[i],Ia[i]))
# plt.plot(var2[:-1], STS0)
# plt.plot(var2[:-1], STSa)
# plt.show()

# i = 5
# v = np.asarray(var1[i])
# zd = np.log(np.asarray(I0[i]))
# fd = np.gradient(zd)
# sd = np.gradient(fd)
#
# halfmax = fd.min() + 0.7 * (fd.max() - fd.min())
# STz = zd[fd > halfmax]
# STf = fd[fd > halfmax]
# STv = v[fd > halfmax]
# slope = (STz[-1]-STz[0])/(STv[-1]-STv[0])
# lin = slope * (v - STv[0]) + STz[0]

# fig, (ax1, ax2, ax3) = plt.subplots(1, 3)
# ax1.plot(v,zd)
# ax2.plot(v,fd)
# ax3.plot(v,sd)
# plt.show()

# fig, ax1 = plt.subplots()
# ax1.plot(v,zd)
# ax2=ax1.twinx()
# ax2.plot(v,fd)
# plt.show()

# plt.plot(v,zd)
# plt.plot(v,lin)
# plt.ylim([zd.min()-1,zd.max()+1])
# plt.show()



# fig = plt.figure()
# ax=plt.axes(projection='3d')

# zdata = 15 * np.random.random(100)
# xdata = np.sin(zdata) + 0.1 * np.random.randn(100)
# ydata = np.cos(zdata) + 0.1 * np.random.randn(100)
# ax.scatter3D(xdata, ydata, zdata, c=zdata, cmap='Greens');

# plt.show(block=None)