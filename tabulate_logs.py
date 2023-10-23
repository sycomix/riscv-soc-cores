#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4:sw=4:tw=78:wrap

#
# Install pandas and tabulate Python packages, e.g.:
#
#     apt-get install python-pandas python-tabulate
#

import re

class quartus_rpt():
    def __init__(self, filepref):
        self.quartus_vers = None
        self.quartus_short_vers = None
        self.device = None
        self.family = None
        self.used_le = None
        self.total_le = None
        self.used_pins = None
        self.total_pins = None
        self.used_mbits = None
        self.total_mbits = None

        self.clocks = {}

        flowfile = f"{filepref}.flow.rpt"
        stafile = f"{filepref}.sta.rpt"

        flowsumm = False
        fmaxflag = False

        txt = open(flowfile, 'r')
        for line in txt:

            if m := re.search(r"^; Flow Summary", line):
                flowsumm = True
                line = txt.next()
                continue

            if flowsumm:
                m = re.search(r"^\+-----", line)
                if m:
                    flowsumm = False
                    continue

                if m := re.search(r"^; Quartus [^;]* Version\s+; (.+) ;", line):
                    self.quartus_vers = m.groups()[0]
                    self.quartus_short_vers = re.sub(" Build.*$", "", self.quartus_vers)
                    continue

                if m := re.search(r"^; Device\s+; (\S+)", line):
                    self.device = m.groups()[0]
                    continue

                if m := re.search(r"^; Family\s+; (\S+)", line):
                    self.family = m.groups()[0]
                    continue

                if m := re.search(
                    r"^; Total logic elements\s+; ([0-9,]+) \/ ([0-9,]+) \( [0-9]* \% \)",
                    line,
                ):
                    self.used_le = re.sub(",", "", m.groups()[0])
                    self.total_le = re.sub(",", "", m.groups()[1])
                    continue

                if m := re.search(
                    r"^; Total pins\s+; ([0-9]+) \/ ([0-9]+) \( [0-9]* \% \)", line
                ):
                    self.used_pins = m.groups()[0]
                    self.total_pins = m.groups()[1]
                    continue

                if m := re.search(
                    r"^; Total memory bits\s+; ([0-9,]+) \/ ([0-9,]+) \( [0-9]* \% \)",
                    line,
                ):
                    self.used_mbits = re.sub(",", "", m.groups()[0])
                    self.total_mbits = re.sub(",", "", m.groups()[1])
                    continue


        txt = open(stafile, 'r')
        for line in txt:

            m = re.search(r"^; Slow 1200mV (85|100)C Model Fmax Summary", line)
            n = re.search(r"^; Slow Model Fmax Summary", line)
            if m or n:
                fmaxflag = True
                line = txt.next()
                line = txt.next()
                line = txt.next()
                continue

            if fmaxflag:
                m = re.search(r"^\+-----", line)
                if m:
                    fmaxflag = False
                    continue

                if m := re.search(
                    r"^; ([0-9\.]+) MHz\s+; ([0-9\.]+) MHz\s+; ([^ ]+)\s+;", line
                ):
                    fmax = m.groups()[0]
                    restrfmax = m.groups()[1]
                    clockname = m.groups()[2]

                    # HACK: fixme
                    clockname = re.sub("^.*clk\[", "clk[", clockname)

                    self.clocks[clockname] = (fmax, restrfmax, clockname)
                    continue

    def csv(self, names):
        ret = []
        for i in names:
            value = getattr(self, i)
            if value is None:
                value = ""
            ret.append(value)

        return ret

    def data_tuple(self):
        names = (
                    "quartus_short_vers",
                    "device",
                    "total_le",
                    "used_le",
                    "total_pins",
                    "used_pins",
                    "total_mbits",
                    "used_mbits",
                )

        s = list(self.csv(names))
        for i in sorted(self.clocks.keys()):
            (fmax, restrfmax, clockname) = self.clocks[i]
            s.append(fmax)

        return s


data = []
for (quartuss, boards) in (
        (("13.0",), ("core-ep2c5", "de1")),
        (("13.0", "13.1",), ("marsohod2",)),
        (("13.1", "17.1"), ("marsohod2bis", "marsohod2rpi",
                            "core-ep4ce6", "de0-nano")),
        (("17.1",), ("marsohod3", "marsohod3bis", "c10lp-evkit")),
                        ):

    for qv in quartuss:
        for b in boards:

            SYSTEM = f"{b}-picorv32-wb-soc"
            filepref = f"build.q{qv}/{SYSTEM}_0/bld-quartus/{SYSTEM}_0"
            q = quartus_rpt(filepref)

            data.append(q.data_tuple())

import pandas as pd
from tabulate import tabulate

dframe = pd.DataFrame(data)
dframe = dframe.sort_values(by=[0, 1])
headers = [ 'Quartus', 'Chip',
            'Total LE', 'Used LE',
            'Total pins', 'Used pins',
            'Total bits', 'Used bits',
            'Fwishbone', 'Fsdram' ]
print(tabulate(dframe, headers=headers, tablefmt="grid", showindex="never"))
