import math


# rounded limit
def rl(x, threshold=1):
    return (math.ceil(x / threshold)) * threshold


# based on numpy_financial.pv
def pv(rate, nper, pmt, fv=0, when=0):
    temp = (1 + rate) ** nper

    if rate == 0:
        fact = nper
    else:
        fact = (1 + rate * when) * (temp - 1) / rate

    return -(fv + pmt * fact) / temp
