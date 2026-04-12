from __future__ import annotations

import json
import logging
import sys
import threading
from pathlib import Path
from queue import Empty, Queue

import serial

WAIT_DELAY = 5

_LOGGER = logging.getLogger(__name__)

FAN_LOADS = {50, 51, 52, 54, 55, 56, 59, 60}
NAMES_FILE = Path("/config/centralite_names.json")


class CentraliteThread(threading.Thread):
    """Background reader thread for the Centralite RS232 connection."""

    def __init__(self, serial_port, notify_event):
        super().__init__(name="CentraliteThread", daemon=True)
        self._serial = serial_port
        self._notify_event = notify_event
        self._responses: Queue[str] = Queue()
        self._stop_event = threading.Event()

    def run(self):
        """Continuously read incoming serial lines."""
        while not self._stop_event.is_set():
            try:
                line = self._readline()
                if not line:
                    continue

                _LOGGER.debug("Incoming serial line: %s", line)

                if len(line) == 5 and line[0] in ("P", "R"):
                    self._notify_event(line)
                    continue

                if len(line) == 7 and line.startswith("^K"):
                    self._notify_event(line)
                    continue

                self._responses.put(line)

            except Exception as err:
                _LOGGER.error("Centralite reader error: %s", err)
                self._stop_event.wait(1.0)

    def _readline(self):
        """Read one CR terminated line from the serial port."""
        output = ""

        while not self._stop_event.is_set():
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

    def stop(self):
        """Stop the reader thread."""
        self._stop_event.set()

    def clear_responses(self):
        """Discard any queued command responses."""
        while True:
            try:
                self._responses.get_nowait()
            except Empty:
                break

    def get_response(self, timeout=WAIT_DELAY):
        """Wait briefly for the next command response line."""
        try:
            return self._responses.get(timeout=timeout)
        except Empty:
            return None


class Centralite:
    """Centralite Elegance serial controller wrapper."""

    FANS_LIST = sorted(FAN_LOADS)
    LOADS_LIST = [i for i in range(1, 193) if i not in FAN_LOADS]

    ACTIVE_SCENES_DICT = {
        "4": "Front Landscape"
    }

    SWITCHES_LIST = [1, 2, 3, 4]

    def __init__(self, url):
        _LOGGER.info("Start serial setup using %s", url)
        self._serial = serial.serial_for_url(
            url,
            baudrate=19200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0,
            write_timeout=2.0,
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

        self._load_names: dict[int, str] = {}
        self._fan_names: dict[int, str] = {}

    def close(self):
        """Clean shutdown."""
        self._thread.stop()
        self._thread.join(timeout=2.0)
        try:
            self._serial.close()
        except Exception:
            pass

    def load_local_names(self):
        """Load optional local names from /config/centralite_names.json."""
        if not NAMES_FILE.exists():
            _LOGGER.info("No Centralite names file found at %s, using defaults", NAMES_FILE)
            self._load_names = {}
            self._fan_names = {}
            return

        try:
            with NAMES_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)

            raw_loads = data.get("loads", {})
            raw_fans = data.get("fans", {})

            self._load_names = {
                int(k): str(v).strip()
                for k, v in raw_loads.items()
                if str(v).strip()
            }
            self._fan_names = {
                int(k): str(v).strip()
                for k, v in raw_fans.items()
                if str(v).strip()
            }

            _LOGGER.info(
                "Loaded Centralite local names: %s loads, %s fans",
                len(self._load_names),
                len(self._fan_names),
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed to load Centralite names file %s: %s. Falling back to generic names.",
                NAMES_FILE,
                err,
            )
            self._load_names = {}
            self._fan_names = {}

    def _send(self, command):
        """Send a command that does not require waiting for a reply."""
        with self._command_lock:
            _LOGGER.debug("Centralite send sending command: %s", command)
            self._serial.write(command.encode("utf-8"))

    def _sendrecv(self, command):
        """Send a command and wait for a single reply line."""
        with self._command_lock:
            self._thread.clear_responses()
            _LOGGER.debug("Centralite sendrecv sending command: %s", command)
            self._serial.write(command.encode("utf-8"))
            response = self._thread.get_response()
            _LOGGER.debug("Centralite sendrecv response for %s: %s", command, response)
            return response

    def _add_event(self, event_name, handler):
        """Register an event handler for a Centralite event name."""
        event_list = self._events.get(event_name)
        if event_list is None:
            event_list = []
            self._events[event_name] = event_list
        event_list.append(handler)

        def _remove():
            handlers = self._events.get(event_name, [])
            if handler in handlers:
                handlers.remove(handler)
            if not handlers:
                self._events.pop(event_name, None)

        return _remove

    def _notify_event(self, event_name):
        """Dispatch a spontaneous Centralite event to registered handlers."""
        handler_params = ""
        line = str(event_name)

        if line and line[0] == "^" and len(line) >= 7 and line[1] == "K":
            load = event_name[2:5]
            level = event_name[5:7]
            event_name = "^K" + load
            handler_params = level

        event_list = self._events.get(event_name)

        if event_list is not None:
            for handler in list(event_list):
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
        return self._add_event("^K{0:03}".format(index), handler)

    def on_switch_pressed(self, index, handler):
        return self._add_event("P{0:04d}".format(index), handler)

    def on_switch_released(self, index, handler):
        return self._add_event("R{0:04d}".format(index), handler)

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
        if response is None:
            raise TimeoutError(f"No Centralite response for load {index}")
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
        return self._load_names.get(index, f"L{index:03d}")

    def get_fan_name(self, index):
        return self._fan_names.get(index, f"L{index:03d} Fan")

    def loads(self):
        return self.LOADS_LIST

    def button_switches(self):
        return self.SWITCHES_LIST

    def scenes(self):
        return self.ACTIVE_SCENES_DICT

    def fans(self):
        return self.FANS_LIST
