"""Checks that steer/acc/brake land on the axes Vjoy_linux.ini binds (AXLE 0/1/3).

Needs the virtual X-Box 360 pad present; skips otherwise. Run: python test_vjoy_axes.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "assetto_corsa_gym"))

from evdev import InputDevice, ecodes
from AssettoCorsaEnv.vjoy_linux import find_xbox360_controller, ABS_STEER, ABS_GAS, ABS_BRAKE
from AssettoCorsaPlugin.plugins.sensors_par.car_control import Controls

AXES = {"ABS_X": ABS_STEER, "ABS_GAS": ABS_GAS, "ABS_BRAKE": ABS_BRAKE}


def read(path):
    d = InputDevice(path)
    try:
        return {n: d.absinfo(c).value for n, c in AXES.items()}
    finally:
        d.close()


def main():
    path = find_xbox360_controller()
    if not path:
        print("no X-Box 360 pad found, skipping")
        return

    c = Controls()
    steer_lo, steer_hi = c.vj.abs_range[ABS_STEER]
    gas_lo, gas_hi = c.vj.abs_range[ABS_GAS]
    brake_lo, brake_hi = c.vj.abs_range[ABS_BRAKE]

    for (steer, acc, brake), want in [
        ((0, -1, -1), {"ABS_X": (steer_lo + steer_hi) // 2, "ABS_GAS": gas_lo, "ABS_BRAKE": brake_lo}),
        ((0, -1, 1), {"ABS_BRAKE": brake_hi}),
        ((0, 1, -1), {"ABS_GAS": gas_hi}),
        ((-1, -1, -1), {"ABS_X": steer_lo}),
        ((1, -1, -1), {"ABS_X": steer_hi}),
    ]:
        c.set_controls(steer=steer, acc=acc, brake=brake)
        time.sleep(0.05)
        got = read(path)
        d = InputDevice(path)
        fuzz = {n: d.absinfo(c).fuzz for n, c in AXES.items()}  # kernel defuzzes small steps
        d.close()
        for axis, expected in want.items():
            assert abs(got[axis] - expected) <= fuzz[axis] + 1, \
                f"steer={steer} acc={acc} brake={brake}: {axis}={got[axis]}, expected {expected}"
        print(f"ok  steer={steer:+} acc={acc:+} brake={brake:+} -> {got}")

    c.set_controls(steer=0, acc=-1, brake=-1)
    print("all axes ok")


if __name__ == "__main__":
    main()
