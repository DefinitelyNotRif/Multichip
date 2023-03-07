import datetime
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
import numpy as np
import matplotlib.colors as colors
from tkinter import messagebox
from statistics import mean
from matplotlib.ticker import MaxNLocator
from scipy import optimize


"""
This file includes all the function that have to do with calculating certain parameters (e.g. threshold voltage) and 
visualizing them. 
"""


def off_noise(data, threshold):
    """
    Sets any values below the set threshold, to it. The purpose of this function is to remove low-current noises.
    :param data: The data to be filtered.
    :param threshold: The minimum current, below which the values will be set to it.
    :return: The filtered data.
    """
    if type(data[0]) == list:  # Perform the function recursively.
        return [off_noise(x, threshold) for x in data]
    return [max(threshold, x) for x in data]  # If the value is lower than the threshold, set it to the threshold.


def remove_latex(s):
    """
    Convert a string formatted in LaTeX - mainly used in the axis labels in the graphs - to a regular string, which
    can then be displayed in a messagebox.
    :param s: The string to be converted.
    :return: The "pure" string.
    """
    if '$' in s:  # In case it's in LaTeX, make it readable in plaintext. Remove all LaTeX-related characters.
        return str(s).replace('$', '').replace('\\', '').replace('_', '').replace('{', '').replace('}', '')
    else:  # If it's already humanly readable
        return str(s)


def plot_yvv(primary, secondary, y, labelx, labely, log, last_right=False):
    """
    Plots the values of (each row of) y against the primary variable, for each value of the secondary variable.
    Note that the secondary variable may also consist of labels (e.g. ["Dry Air", "Exposed"]).
    :param primary: The primary variable - a list of lists, each corresponding to a different secondary variable value.
    :param secondary: The secondary variable - a 1D list.
    :param y: The data to be plotted - a list of lists, each corresponding to a different secondary variable value.
    :param labelx: The label for the x-axis.
    :param labely: The label for the y-axis
    :param log: Whether the y-axis should be in a logarithmic scale.
    :param last_right: If True, the last row of the primary variable and y will be plotted on a separate axis, which
    will be positioned to the right of the graph.
    """
    if all([len(row) == 1 for row in y]):  # There is only 1 data point per secondary value
        msg = ''
        for s, val in zip(secondary, y):  # Show a messagebox with the value, for each secondary variable value.
            val_msg = str(float('%.4g' % val[0]))  # Round the value
            msg += (remove_latex(s) + ': ' + val_msg + '\n')  # e.g. "Dry Air: 0.1"
        messagebox.showinfo('', msg[:-1])  # The [:-1] clips the '\n' at the end
        return
    font = {'family': 'Times New Roman', 'size': 10, }
    # matplotlib.rcParams['toolbar'] = 'None'  # Uncomment to disable the toolbar below the graph
    if last_right:  # Create two x-axes, which prevents us from using plt.___() functions
        fig, ax1 = plt.subplots(figsize=(3.5, 3.5))  # Standard figure size
        ax2 = ax1.twinx()  # Right axis
        ax1.format_coord = lambda x, y: ''  # Hide the coordinates at the bottom, to prevent the figure from constantly
        ax2.format_coord = lambda x, y: ''  # stretching and flickering!
        for i in range(0, len(secondary)-1):  # Plot all but the last series
            ax1.plot(primary[i], y[i])
        if all([type(l) != str for l in secondary[:-1]]):   # If the secondary axis consists of numbers, round them to
                                                            # avoid float errors.
            ax1.legend([str(round(x, 3)) for x in secondary[:-1]], prop=font, loc='center left')
        else:  # If the secondary variable consists of text (labels)
            ax1.legend([str(x) for x in secondary[:-1]], prop=font, loc='center left')
        ax2.plot(primary[-1], y[-1], color='g')  # Plot the right series
        plt.rcParams.update({'mathtext.default': 'regular'})
        if log:
            plt.yscale('log')
        ax1.set_xlabel(labelx, fontdict=font)  # Set the labels to have the standard font
        ax2.set_xlabel(labelx, fontdict=font)
        ax1.set_ylabel(labely, fontdict=font)
        ax2.set_ylabel(secondary[-1], fontdict=font)
        ax1.tick_params(labelsize=10)
        ax2.tick_params(labelsize=10)
        plt.tight_layout(h_pad=None, w_pad=None, rect=None)
        plt.show()
    else:
        figure(figsize=(3.5, 3.5))  # Standard figure size
        plt.gca().format_coord = lambda a, b: ''  # Hide the coordinates at the bottom
        for i in range(0, len(secondary)):  # Plot all the series
            plt.plot(primary[i], y[i])
        plt.rcParams.update({'mathtext.default':  'regular'})
        if log:
            plt.yscale('log')
        plt.xlabel(labelx, fontdict=font)  # Set the labels to have the standard font
        plt.ylabel(labely, fontdict=font)
        plt.xticks(fontsize=10, fontname='Times New Roman')
        plt.yticks(fontsize=10, fontname='Times New Roman')
        locator = MaxNLocator(nbins=6)  # These two rows are supposed to prevent the x-axis from being so dense it
        plt.gca().xaxis.set_major_locator(locator)  # becomes unreadable.
        if all([type(l) != str for l in secondary[:-1]]):   # If the secondary axis consists of numbers, round them to
                                                            # avoid float errors.
            plt.legend([str(round(x, 3)) for x in secondary], prop=font)
        else:  # If the secondary variable consists of text (labels)
            plt.legend([str(x) for x in secondary], prop=font)
        plt.tight_layout(h_pad=None, w_pad=None, rect=None)
        plt.show()


def plot_yv(x, y, labelx, labely, forcelin=False, transient=False):
    """
    Plots y as a function of x, but with the standard formatting and the specified labels.
    So it's basically a glorified plt.plot().
    :param x: The x-axis values.
    :param y: The data to be plotted.
    :param labelx: The label for the x-axis.
    :param labely: The label for the y-axis.
    :param forcelin: If True, forces the y-axis scale to be linear. Otherwise, it determines the scale based on the
    range that the data spans.
    :param transient: Whether the data is from a transient measurement. If True, it modified the x-axis ticks so they're
    not so dense they're unreadable.
    """
    if len(x) == 1:  # If there is only one data point (e.g. the user chose "Show Threshold Voltage" for a single sweep)
        messagebox.showinfo('', remove_latex(labely) + ": " + str(float('%.4g' % y[0])))  # Just display a messagebox
        return
    # matplotlib.rcParams['toolbar'] = 'None'  # Uncomment to disable the toolbar below the graph
    figure(figsize=(3.5, 3.5))  # Standard figure size
    plt.gca().format_coord = lambda a, b: ''  # Hide the coordinates at the bottom
    font = {'family': 'Times New Roman',
            'size': 10,
            }
    plt.plot(x, y)
    plt.rcParams.update({'mathtext.default': 'regular'})
    plt.xlabel(labelx, fontdict=font)  # Set the labels to have the standard font
    plt.ylabel(labely, fontdict=font)
    plt.xticks(fontsize=10, fontname='Times New Roman')
    plt.yticks(fontsize=10, fontname='Times New Roman')
    if transient:
        locator = MaxNLocator(nbins=6)
        plt.gca().xaxis.set_major_locator(locator)
        plt.gca().xaxis.set_major_formatter(lambda x, pos: str(datetime.timedelta(seconds=x)))
    if max(y)/100 > min(y) and not forcelin:  # The axis scale is logarithmic if the data spans at least two decades
        plt.yscale('log')
    plt.tight_layout(h_pad=None, w_pad=None, rect=None)
    plt.show()


def closest(lst, val): return min(lst, key=lambda x: abs(x-val))  # Returns the value in lst that is closest to val. 


def vth_constant(v1, v2, i, const):
    """
    Returns the threshold voltage of each sweep.
    The threshold voltage is defined as the voltage where the current reaches a specified threshold (const).
    :param v1: The primary variable (voltage). A list of len(v2) lists. 
    :param v2: The secondary variable (voltage). A 1D list. 
    :param i: The current for each point. A list of len(v2) lists.
    :param const: The threshold current that defines the threshold voltage.
    :return: A list (of length len(v2)) containing the threshold voltage for each value of v2.
    """
    return [v1[j][list(i[j]).index(closest(i[j], const))] for j in range(len(v2))]
    # Explanation: For each secondary voltage value (the index of which is j), take the respective row of the current,
    # and find the index for which the current is closest to the threshold current. Then, return the primary voltage
    # value that corresponds to that current (that is, that index in the j-th row of v1).


def vth_rel(v1, v2, i, threshold): #USE WITH FILTERED!
    """
    Returns the threshold voltage of each sweep.
    The threshold voltage is defined relatively to the minimum and maximum current values. For example, if the threshold
    parameter is 0.2, then the threshold current is defined as 20% of the way between the minimum and maximum currents,
    and the threshold voltage is defined accordingly.
    Since this method is defined by the most extreme current values, it must be used in conjunction with
    filter_regionless()!
    :param v1: The primary variable (voltage). A list of len(v2) lists.
    :param v2: The secondary variable (voltage). A 1D list.
    :param i: The current for each point. A list of len(v2) lists.
    :param threshold: The percentage that defines the threshold current, as explained above. A float between 0 and 1.
    :return: A list (of length len(v2)) containing the threshold voltage for each value of v2.
    """
    vth = []
    for j in range(len(v2)):  # For each secondary voltage value
        imax = max(i[j])  # Find the minimum and maximum currents
        imin = min(i[j])
        vth.append(v1[j][list(i[j]).index(closest(i[j], (imax - imin) * threshold + imin))])
        # The logic here is similar to that in vth_constand(), with the only difference being the second argument in
        # the closest() function (i.e., the "target" threshold current).
    return vth


# from scipy import ndimage
def smooth(arr, win):
    # arr = np.asarray(lst)
    filtered = []
    for i in range(len(arr)):
        if i < win:
            filtered.append(np.mean(arr[0:2*i+1]))
        elif i + win + 1 > len(arr):
            filtered.append(np.mean(arr[-2*(len(arr)-i)+1:]))
        else:
            filtered.append(np.mean(arr[i-win:i+win+1]))
        # filtered.append(mean(arr[max(i - win, 0):min(i + win, len(arr))]))
    return filtered


def vth_sd(v1, v2, I):
    VTH = []
    win = 3
    for i in range(len(v2)):
        zd = np.asarray(I[i])
        # spl = scipy.interpolate.splrep(v1[i], i[i], k=3)
        # ddy = scipy.interpolate.splev(v1[i], spl, der=2)
        zd = smooth(zd, win)
        fd = np.gradient(zd)
        # fd = smooth(fd, win)
        sd = np.gradient(fd)
        # sd = smooth(sd, win)
        # ddy_spl = scipy.interpolate.splrep(v1[i], sd, k=3)
        plt.plot(zd)
        # plt.plot(np.gradient(np.gradient(smooth(spl[1], win)))[:-8])
        # print(len(v1))
        # m = v1[i][-1]
        # for j in range(len(v1[i])-1):
        #     if i[i][j] > 1.1*i[i][j+1]:
        #         m = v1[i][j]
        #         break
        # VTH.append(m)

        # peaks = scipy.signal.find_peaks(sd[:-win], prominence=max(sd)/10)[0]
        # print(str(v2[i]) + ": " + str(peaks) + " -> " + str(v1[i][peaks[0]]))
        # VTH.append(v1[i][peaks[0]])

        # VTH.append(v1[i][list(sd).index(max(sd))])
    plt.yscale('log')
    plt.show()
    return VTH


import numpy.polynomial.polynomial as npoly






import piecewise_regression
def vth_lin(v1, v2, I):


    VTH = []
    for i in range(len(v2)):
        # pw_fit = piecewise_regression.Fit(v1[i], i[i], n_breakpoints=1)
        # VTH.append(pw_fit.get_results()['estimates']['breakpoint1']['estimate'])
        # pw_fit.plot_data(color="grey", s=20)
        # pw_fit.plot_fit(color="red", linewidth=4)
        # plt.show()

        def piecewise_linear(x, x0, y0, k1, k2):
            return np.piecewise(x, [x < x0], [lambda x: k1 * x + y0 - k1 * x0, lambda x: k2 * x + y0 - k2 * x0])

        x, y = v1[i], I[i]
        y = [a/max(y) for a in y]  # Normalize
        p, e = optimize.curve_fit(piecewise_linear, x, y, [np.mean([min(x), max(x)]), 0, 0, 0.5/(max(x)-min(x))])
        VTH.append(p[0] - p[1] / p[3])  # x0 - (y0/k2) gives the intersection of the right line with zero
        # th = p[0] - p[1] / p[3]
        # plt.plot(x, y, "o")
        # plt.plot(x, piecewise_linear(x, *p))
        # plt.plot(th, 0, "o")
        # plt.show()
    return VTH


def vth_lin_alt(v1, v2, I):
    for i in range(len(v2)):
        off = ioff(I[i])
        li = np.log10(np.asarray(I[i]))
        plt.plot(li)
        plt.plot(np.ones(len(I[i]))*np.log10(off))
        plt.show()
        # if i[i][-1] < off:  # No on-region - shouldn't be accessed, because of filter_regionless()!!!
        #     print("No on-region!")
        # else:
        #     for j in range(len(li)-1, -1, -1):  # Go backwards from the end. Find the LEFTMOST POINT in the RIGHTMOST
        #         if i[i][j] < off:               # BLOCK that's greater than the off-threshold.
        #             lower = i[i][j+1]
        #             break
        #     else:  # No off-region - should never be accessed...
        #         print("No off-region?!")



def response(I0, Ia):
    """
    Given two characteristics - before and after the exposure - this function calculates and returns the response for
    each point.
    :param I0: The pre-exposure currents.
    :param Ia: The post-exposure currents.
    :return: The response for each point.
    (All three are nested lists)
    """
    s = []
    for i in range(len(I0)):
        srow=[]  # A temporary list to store the values for each row
        for j in range(len(I0[i])):  # Append the response
            srow.append(abs((I0[i][j]-Ia[i][j])/min(I0[i][j], Ia[i][j])))
        s.append(srow)
    return s


def plot_heatmap(mat, varx, vary, labelx, labely, labelc, interp):
    """
    Plots a heatmap of the data in mat.
    :param mat: The data to be plotted.
    :param varx: The x-axis values (the secondary variable).
    :param vary: The y-axis values (the primary variable).
    :param labelx: The x-axis label.
    :param labely: The y-axis label.
    :param labelc: The label for the color bar.
    :param interp: If True, attempts to interpolate the heatmap and increase the resolution. Currently unused!
    """
    if len(varx) == 1:  # If there is only one column, just plot a regular graph.
        plot_yv(vary[0], mat[0], labely, labelc)
        return
    fig = figure(figsize=(3.5, 3.5))  # Standard figure size
    # matplotlib.rcParams['toolbar'] = 'None'
    plt.gca().format_coord = lambda x, y: ''  # Hide the coordinates at the bottom
    font = {'family': 'Times New Roman',
            'size': 10,
            }
    plt.rcParams.update({'mathtext.default': 'regular'})
    plt.xlabel(labelx, fontdict=font)  # Set the labels to have the standard font
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
    else:  # For now, only this part is reached
        x = varx
        # y = vary
        y = vary[0]  # Only take one row of the primary variable. They're supposed to be virtually identical anyways
        z = np.asarray(mat).transpose()  # Transpose so that the primary variable is on the y-axis and the secondary
        # variable is on the x-axis.
        z[z < 1e-12] = 1e-12  # Set a minimum current, to prevent 0 values with a log scale
        plt.pcolormesh(x, y, z, shading='auto', cmap='plasma', norm=colors.LogNorm(vmin=z.min(), vmax=z.max()))
    cbar = plt.colorbar(fraction=0.22)  # Set up the color bar. fraction = essentially its width...?
    # print(cbar.fraction)
    cbar.set_label(labelc, labelpad=8, rotation=270, fontdict=font)  # Set the colorbar label
    cbar.format_coord = lambda x, y: ''  # Hide the coordinates at the bottom
    plt.show()


def sts(V, I, threshold=0.7):
    """
    Calculates the sub-threshold swing for an i-V sweep.
    :param V: The x-axis values (voltages).
    :param I: The y-axis values (currents).
    :return: The sub-threshold swing for the sweep (float).
    """
    zd = np.log(np.asarray(I))  # Convert the data to an array, and take its log
    fd = np.gradient(zd)  # First derivative
    # plt.plot(fd)
    halfmax = fd.min() + threshold * (fd.max() - fd.min())  # Finds the value that's 70% of the way between the minimum and
    # maximum derivative values. The sub-threshold region will then be defined as the region where the derivative is
    # higher than this value. Since a typical i-V graph would be split into three segments - constant, exponential,
    # linear - its log would be split into constant, linear, and logarithmic segments. Of these, the linear segment
    # (exponential in the original graph) would have the highest derivative! Thus, this definition of the sub-threshold
    # region attempts to contain that entire segment.
    # TODO: Arbitrarily defined by 0.7. Is there a value i "should" use?
    STz = zd[fd > halfmax]  # Current (log) values for the sub-threshold region.
    STv = np.asarray(V)[fd > halfmax]  # Derivative values for the sub-threshold region
    if len(STz) < 2 or len(STv) < 2:  # If the sub-threshold region is too small, the sts cannot be calculated.
        raise ZeroDivisionError  # Because of the denominator in the expression below
    else:
        slope = (STz[-1] - STz[0]) / (STv[-1] - STv[0])  # The slope of a linear approximation between the edges of
        # the sub-threshold region.
        return np.log(10)/slope  # Return the STS


def ioff(I, threshold=0.2):
    """
    Returns the off-current for a given series of currents.
    Currently, it's defined as the average current of the lower 20% of the current range. TODO: Better definition!!!
    :param I: The current data.
    :param threshold: The threshold below which the device is considered off - defaults to 20% (the lower 20% of the
    range in a log scale).
    """
    Iarr = np.asarray(I)  # Convert the current to an array
    li = np.log(Iarr)  # Log scale
    halfmax = li.min() + threshold * (li.max() - li.min())  # Find the 20% threshold
    off = Iarr[li < halfmax]  # Get the current in the off-region
    return np.average(off)  # Return its average


def ion(I, threshold):  # TODO: The "on" region is defined by an arbitrary threshold. Maybe make it relative? Maybe define it by the derivative?!
    """
    Returns the on-current for a given series of currents.
    Currently, the on-current is defined as the average current in the region that's above a specified threshold.
    TODO: Better definition!!!
    :param I:  The current data.
    :param threshold: The threshold that defines the on-current.
    """
    Iarr = np.asarray(I)  # Convert the current to an array
    on = Iarr[Iarr >= threshold]  # Get the current in the on-region
    if on.size != 0:
        return np.average(on)  # Return its average
    else:  # If the on-region doesn't exist
        return 0


def filter_regionless(v1, v2, i0, ia=None):
    """
    Given a complete data set (primary and secondary variables, pre- and optionally post-exposure currents), filters
    out the sweeps where the current spans less than 2.5 decades (arbitrary, may be changed).
    This is required for calculations that require a transition from the off-region to the on-region, such as the
    threshold voltage.
    :param v1: The primary variable (voltages). A list of lists of length len(v2).
    :param v2: The secondary variable (voltages).
    :param i0: The pre-exposure currents. A list of lists of length len(v2).
    :param ia: The post-exposure currents. A list of lists of length len(v2).
    :return: The filtered lists. If ia wasn't given, it's not returned either.
    """
    v1_filtered = []  # These lists will contain the sweeps that DO span more than 2.5 decades.
    v2_filtered = []  # (That is, these are the lists that will be returned in the end.)
    i0_filtered = []
    ia_filtered = []
    threshold = 2.5
    if v2 is not None:  # Called from some kind of sweep measurement
        for i in range(len(v2)):
            if ia is not None:  # Exposure
                if max(i0[i])/(10**threshold) > min(i0[i]) and max(ia[i])/(10**threshold) > min(ia[i]):
                    # If both currents span more than 2.5 decades, append the sweep to the new lists.
                    v1_filtered.append(v1[i])
                    v2_filtered.append(v2[i])
                    i0_filtered.append(i0[i])
                    ia_filtered.append(ia[i])
            else:  # Characteristic or periodic sweep
                if max(i0[i]) / (10 ** threshold) > min(i0[i]):  # If the current spans more than 2.5 decades
                    v1_filtered.append(v1[i])
                    v2_filtered.append(v2[i])
                    i0_filtered.append(i0[i])
        if len(i0_filtered) == 0:  # Trying to return empty lists, since none of the sweeps span 2.5 decades
            raise IndexError
        if ia is not None:  # Exposure -> return all four lists
            return v1_filtered, v2_filtered, i0_filtered, ia_filtered
        return v1_filtered, v2_filtered, i0_filtered  # Not exposure -> don't return ia!
    else:  # Called from a transient measurement, only v1 and i0 exist. TODO: Will this ever be called?!
        for i in range(len(i0)):
            if max(i0[i]) / (10 ** threshold) > min(i0[i]):  # If the current spans more than 2.5 decades
                v1_filtered.append(v1[i])
                i0_filtered.append(i0[i])
        if len(i0_filtered) == 0:  # Trying to return an empty list, since the current doesn't span 2.5 decades
            raise IndexError
        return v1_filtered, i0_filtered  # Return the x- and y-axis values


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