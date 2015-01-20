from __future__ import print_function, division

import numpy as np

_template = """\
+------+-------------------------------+-------------------------------+
|  k   |           Transitions         |            Transversions      |
+------+--------+-----------+----------+--------+-----------+----------+
|      | Prior  | iid Post. | CP Post. | Prior  | iid Post. | CP Post. | 
+======+========+===========+==========+========+===========+==========+
|   1  | {0000} | {0001}    | {0002}   | {0003} | {0004}    | {0005}   |
+------+--------+-----------+----------+--------+-----------+----------+
|   2  | {0006} | {0007}    | {0008}   | {0009} | {0010}    | {0011}   |
+------+--------+-----------+----------+--------+-----------+----------+
|   4  | {0012} | {0013}    | {0014}   | {0015} | {0016}    | {0017}   |
+------+--------+-----------+----------+--------+-----------+----------+\
"""

v = np.exp(np.random.randn(18)) * 100

print(v)

s = ['{:>6.1f}'.format(x) for x in v]

print(_template.format(*s))
