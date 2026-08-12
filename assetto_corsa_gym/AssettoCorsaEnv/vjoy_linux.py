import struct
from evdev import InputDevice, list_devices, ecodes

# Must match the AXLE numbers in windows-libs/Vjoy_linux.ini, which are dinput axis
# indices: AC/wine numbers the pad's ABS codes in order, so ABS_X=0, ABS_Y=1, ABS_Z=2,
# ABS_RX=3. The preset uses the 16-bit sticks (0/1/3), not the 8-bit triggers.
ABS_STEER = ecodes.ABS_X    # AXLE 0
ABS_GAS = ecodes.ABS_Y      # AXLE 1
ABS_BRAKE = ecodes.ABS_RX   # AXLE 3

def find_xbox360_controller():
    for path in list_devices():
        device = InputDevice(path)
        if "X-Box 360" in device.name:
            return device.path
    return None

class vJoy:
    def __init__(self, reference=1):
        self.reference = reference
        self.device = None
        self.acquired = False
        self.js_path = "/dev/input/js0"
        self.event_path = find_xbox360_controller()
        self.abs_range = {}

    def open(self):
        """Open the virtual joystick device"""
        try:
            # ranges differ per device (sticks are signed 16 bit, triggers are often 0..255)
            self.abs_range = {c: (a.min, a.max) for c, a in
                              InputDevice(self.event_path).capabilities().get(ecodes.EV_ABS, [])}
            self.device = open(self.event_path, 'wb')
            self.acquired = True
            return True
        except Exception as e:
            print("Failed to open vJoy device: {}".format(e))
            return False

    def close(self):
        """Close the virtual joystick device"""
        try:
            if self.device:
                self.device.close()
            self.acquired = False
            return True
        except Exception as e:
            print("Failed to open vJoy device: {}".format(e))
            return False

    def generateJoystickPosition(self, 
                               wThrottle=0, wRudder=0, wAileron=0,
                               wAxisX=0, wAxisY=0, wAxisZ=0,
                               wAxisXRot=0, wAxisYRot=0, wAxisZRot=0,
                               wSlider=0, wDial=0, wWheel=0,
                               wAxisVX=0, wAxisVY=0, wAxisVZ=0,
                               wAxisVBRX=0, wAxisVBRY=0, wAxisVBRZ=0,
                               lButtons=0, bHats=0, bHatsEx1=0, bHatsEx2=0, bHatsEx3=0):
        """Generate a joystick position structure compatible with the original vJoy"""
        joyPosFormat = "BlllllllllllllllllllIIII"
        pos = struct.pack(joyPosFormat, self.reference, wThrottle, wRudder,
                         wAileron, wAxisX, wAxisY, wAxisZ, wAxisXRot, wAxisYRot,
                         wAxisZRot, wSlider, wDial, wWheel, wAxisVX, wAxisVY, wAxisVZ,
                         wAxisVBRX, wAxisVBRY, wAxisVBRZ, lButtons, bHats, bHatsEx1, bHatsEx2, bHatsEx3)
        return pos

    def _send_event(self, event_type, code, value):
        """Send an input event to the device"""
        # Use signed integer format for steering events
        if event_type == 0x02:  # EV_REL
            EVENT_FORMAT = 'llHHi'
        else:
            EVENT_FORMAT = 'llHHi'
        event = struct.pack(EVENT_FORMAT, 0, 0, event_type, code, value)
        self.device.write(event)
        self.device.flush()

    def _send_abs(self, code, unit):
        """unit in [0, 1] -> the axis' own min..max range"""
        lo, hi = self.abs_range.get(code, (-32768, 32767))
        value = int(round(lo + min(max(unit, 0.), 1.) * (hi - lo)))
        self._send_event(0x03, code, max(lo, min(hi, value)))  # EV_ABS

    def update(self, joystickPosition):
        """Update the joystick state based on the provided position structure"""
        if not self.device or not self.acquired:
            return False

        try:
            # Unpack the joystick position structure
            values = struct.unpack("BlllllllllllllllllllIIII", joystickPosition)

            # wAxisX/Y/Z arrive as 0..32768 (see Controls.setJoy)
            self._send_abs(ABS_STEER, values[4] / 32768.)
            self._send_abs(ABS_GAS, values[5] / 32768.)
            self._send_abs(ABS_BRAKE, values[6] / 32768.)

            # Send a synchronization event
            self._send_event(0, 0, 0)

            return True
        except Exception as e:
            # breakpoint()
            print("Failed to open vJoy device: {}".format(e))
            return False