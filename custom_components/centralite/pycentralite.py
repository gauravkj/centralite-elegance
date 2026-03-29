from __future__ import annotations

import logging
import sys
import threading

import serial

WAIT_DELAY = 2

_LOGGER = logging.getLogger(__name__)

FAN_LOADS = {50, 51, 52, 54, 55, 56, 59, 60}


class CentraliteThread(threading.Thread):
    """Background reader thread for the Centralite RS232 connection."""

    def __init__(self, serial_port, notify_event):
        super().__init__(name="CentraliteThread", daemon=True)
        self._serial = serial_port
        self._lastline = None
        self._recv_event = threading.Event()
        self._notify_event = notify_event

    def run(self):
        """Continuously read incoming serial lines."""
        while True:
            line = self._readline()
            _LOGGER.debug("Incoming serial line: %s", line)

            if len(line) == 5 and (line[0] == "P" or line[0] == "R"):
                self._notify_event(line)
                continue

            if len(line) == 7 and line[0] == "^" and line[1] == "K":
                self._notify_event(line)
                continue

            self._lastline = line
            self._recv_event.set()

    def _readline(self):
        """Read one CR terminated line from the serial port."""
        output = ""

        while True:
            byte = self._serial.read(size=1)

            if not byte:
                continue

            if byte[0] == 0x0D:
                break

            output += byte.decode("utf-8", errors="ignore")

            if len(output) >= 100:
                _LOGGER.warning("Readline hit 100 chars, forcing break: %s", output)
                break

        return output

    def get_response(self):
        """Wait briefly for the next command response line."""
        self._recv_event.wait(timeout=WAIT_DELAY)
        self._recv_event.clear()
        return self._lastline


class Centralite:
    """Centralite Elegance serial controller wrapper."""

    FANS_LIST = sorted(FAN_LOADS)
    LOADS_LIST = [i for i in range(1, 193) if i not in FAN_LOADS]

    ACTIVE_SCENES_DICT = {
        "4": "Front Landscape"
    }

    SWITCHES_LIST = [1, 2, 3, 4]

    LOAD_NAMES = {
        1: "Kitchen Table",
        2: "Laundry Lights",
        3: "Kitchen Island",
        4: "Dining Chandelier",
        5: "Dining China",
        6: "Sunroom Porch Lights",
        7: "Kitchen Sink",
        8: "Hallway Lights",
        9: "Powder Room Ceiling Light",
        10: "Office Ceiling Lights",
        11: "Lower Patio Lights",
        12: "Garage Lights",
        13: "Kitchen Isle",
        14: "Sun Room Ceiling Lights",
        15: "Garage Exterior Lights",
        16: "Garage Spot Lights",
        17: "Kitchen Under Cabinet",
        18: "Kitchen Above Cabinet",
        19: "Equipment Room Light",
        20: "Gym Lights",
        21: "Patio Post Lights",
        26: "Office Desk Lamp",
        29: "Powder Room Exhaust Fan",
        30: "Soffit Receptacles Lights",
        31: "Hallway Main",
        32: "Rear Spots Lights",
        33: "Family Room Fireplace Lights",
        34: "Tisya Room Ceiling Lights",
        35: "Family Room Ceiling Lights",
        36: "Master Bedroom Entry",
        37: "Front Porch Recess Lights",
        38: "Dining Room Spot Lights",
        39: "Front Porch Lights",
        40: "Front Porch Outlet Lights",
        41: "Dining Sconce Lights",
        42: "Walkin Closet Lights",
        43: "Powder Room Vanity Lights",
        44: "Living Room Main",
        45: "Living Room Bay Window",
        46: "Master Bath Vanity",
        47: "Utility Room Lights",
        48: "Dining Ceiling Lights",
        73: "Office Etagere Lights",
        74: "Living Room Etagere",
        75: "Foyer Chandelier",
        76: "Laundry Room Porch",
        77: "Exterior Spot(R) Lights",
        78: "Bath Exhaust Fan",
        79: "Bath Sink Light",
        80: "Aadya Room Ceiling Lights",
        81: "Family Room Etagere Lights",
        82: "Bath Ceiling Light",
        83: "Master Bath Toilet",
        84: "Master Bath Shower",
        85: "Master Bath Sink Right",
        86: "Master Bath Tub",
        87: "Master Bath Main",
        88: "Master Bath Sink Left",
        89: "Bath Tub Light",
        90: "Master Bedroom Main",
        91: "Master Bedroom Attic Closet",
        92: "Guest Room Ceiling Lights",
        93: "Master Bath Fan",
        94: "Master Bedroom Sitting",
        95: "Master Bedroom Walkin Closet",
        96: "Bath Vanity Lights",
        121: "Lounge Kitchen",
        122: "Lounge Bar",
        123: "Movie Theater Seat",
        124: "Powder Vanity",
        125: "Powder Fan",
        126: "Powder Main",
        127: "Movie Theater Middle",
        128: "Movie Theater Under Front",
        129: "Lounge Main",
        130: "Landscape 1 Lights",
        131: "Movie Theater Front",
        132: "Powder Entry",
        133: "Game Room Storage Light",
        134: "Foyer Accent Outlet Lights",
        135: "Game Room Ceiling Lights",
        136: "Movie Theater Pillars",
        137: "Lounge Art",
        138: "Lounge Sink",
        139: "Movie Theater Step",
        140: "Lounge Bar Display",
        141: "Movie Theater Under Main",
        142: "Lounge Under Cabinet",
        143: "Landscape 2 Lights",
        144: "Lounge Stairs",
    }

    FAN_NAMES = {
        50: "Master Bedroom Fan",
        51: "Family Room Fan",
        52: "Master Bedroom Fan Sitting",
        54: "Guest Room Fan",
        55: "Aadya Room Fan",
        56: "Tisya Room Fan",
        59: "Sun Room Fan 1",
        60: "Sun Room Fan 2",
    }

    def __init__(self, url):
        _LOGGER.info("Start serial setup using %s", url)
        self._serial = serial.serial_for_url(
            url,
            baudrate=19200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        _LOGGER.info(
            "CENTRALITE SERIAL OPENED url=%s baud=%s parity=%s stopbits=%s",
            url,
            19200,
            serial.PARITY_NONE,
            serial.STOPBITS_ONE,
        )

        self._events = {}
        self._thread = CentraliteThread(self._serial, self._notify_event)
        self._thread.start()
        self._command_lock = threading.Lock()

    def _send(self, command):
        """Send a command that does not require waiting for a reply."""
        with self._command_lock:
            self._serial.write(command.encode("utf-8"))

    def _sendrecv(self, command):
        """Send a command and wait for a single reply line."""
        with self._command_lock:
            self._serial.write(command.encode("utf-8"))
            return self._thread.get_response()

    def _add_event(self, event_name, handler):
        """Register an event handler for a Centralite event name."""
        event_list = self._events.get(event_name)
        if event_list is None:
            event_list = []
            self._events[event_name] = event_list
        event_list.append(handler)

    def _notify_event(self, event_name):
        """Dispatch a spontaneous Centralite event to registered handlers."""
        handler_params = ""
        line = str(event_name)

        if line[0] == "^" and line[1] == "K":
            load = event_name[2:5]
            level = event_name[5:7]
            event_name = "^K" + load
            handler_params = level

        event_list = self._events.get(event_name)

        if event_list is not None:
            for handler in event_list:
                try:
                    handler(handler_params)
                except Exception:
                    error_msg = sys.exc_info()[0]
                    _LOGGER.debug("Handler failed with error: %s", error_msg)

    def _hex2bin_loads(self, response):
        """Convert a load status hex response into a binary string."""
        hex2bin_map = {
            "0": "0000", "1": "0001", "2": "0010", "3": "0011",
            "4": "0100", "5": "0101", "6": "0110", "7": "0111",
            "8": "1000", "9": "1001", "A": "1010", "B": "1011",
            "C": "1100", "D": "1101", "E": "1110", "F": "1111",
        }

        i = 0
        byte_groups = []
        while i < len(response):
            byte_groups.append(response[i:i + 6])
            i += 6

        reversed_bytes = []
        for byteset in byte_groups:
            i = 0
            newbytes = ""
            while i < 6:
                newbytes = newbytes + byteset[i + 1] + byteset[i]
                i += 2
            reversed_bytes.append(newbytes[::-1])

        binary_bytes = []
        for byteset in reversed_bytes:
            binary_rep = "".join(hex2bin_map[x] for x in byteset)
            binary_bytes.append(binary_rep[::-1])

        return "".join(binary_bytes)

    def _hex2bin_switches(self, response):
        """Convert a switch status hex response into a binary string."""
        hex2bin_map = {
            "0": "0000", "1": "0001", "2": "0010", "3": "0011",
            "4": "0100", "5": "0101", "6": "0110", "7": "0111",
            "8": "1000", "9": "1001", "A": "1010", "B": "1011",
            "C": "1100", "D": "1101", "E": "1110", "F": "1111",
        }

        i = 0
        byte_groups = []
        while i < len(response):
            byte_groups.append(response[i:i + 4])
            i += 4

        reversed_bytes = []
        for byteset in byte_groups:
            i = 0
            newbytes = ""
            while i < 4:
                newbytes = newbytes + byteset[i + 1] + byteset[i]
                i += 2
            reversed_bytes.append(newbytes[::-1])

        binary_bytes = []
        for byteset in reversed_bytes:
            binary_rep = "".join(hex2bin_map[x] for x in byteset)
            binary_bytes.append(binary_rep[::-1])

        return "".join(binary_bytes)

    def on_load_change(self, index, handler):
        self._add_event("^K{0:03}".format(index), handler)

    def on_switch_pressed(self, index, handler):
        self._add_event("P{0:04d}".format(index), handler)

    def on_switch_released(self, index, handler):
        self._add_event("R{0:04d}".format(index), handler)

    def activate_load(self, index):
        self._send("^A{0:03d}".format(index))

    def deactivate_load(self, index):
        self._send("^B{0:03d}".format(index))

    def activate_scene(self, index, scene_name):
        index = int(index)
        if "-ON" in scene_name.upper():
            self._send("^C{0:03d}".format(index))
        elif "-OFF" in scene_name.upper():
            self._send("^D{0:03d}".format(index))

    def activate_load_at(self, index, level, rate):
        self._send("^E{0:03d}{1:02d}{2:02d}".format(index, level, rate))

    def get_load_level(self, index):
        response = self._sendrecv("^F{0:03d}".format(index))
        return int(response)

    def get_all_load_states(self):
        response = self._sendrecv("^G")
        return self._hex2bin_loads(response)

    def get_all_switch_states(self):
        response = self._sendrecv("^H")
        return self._hex2bin_switches(response)

    def press_switch(self, index):
        self._send("^I{0:03d}".format(index))
        self._send("^J{0:03d}".format(index))

    def release_switch(self, index):
        self._send("^I{0:03d}".format(index))
        self._send("^J{0:03d}".format(index))

    def get_switch_name(self, index):
        return "SW{0:03d}".format(index)

    def get_load_name(self, index):
        return self.LOAD_NAMES.get(index, f"L{index:03d}")

    def get_fan_name(self, index):
        return self.FAN_NAMES.get(index, f"L{index:03d} Fan")

    def loads(self):
        return Centralite.LOADS_LIST

    def button_switches(self):
        return Centralite.SWITCHES_LIST

    def scenes(self):
        return Centralite.ACTIVE_SCENES_DICT

    def fans(self):
        return Centralite.FANS_LIST
