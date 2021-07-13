
from typing import Iterable
import tabulate, copy, time, datetime, requests, sys, os, random
import threading
WARNING_BEEP_DURATION = (1000, 1000)

try:
    import winsound
except ImportError:
    import os
    if sys.platform == "darwin":
        def beep(freq, duration):
            # brew install SoX --> install SOund eXchange universal sound sample translator on mac
            os.system(
                f"play -n synth {duration/1000} sin {freq} >/dev/null 2>&1")
    else:
        def beep(freq, duration):
            # apt-get install beep  --> install beep package on linux distros before running
            os.system('beep -f %s -l %s' % (freq, duration))
else:
    def beep(freq, duration):
        winsound.Beep(freq, duration)

if sys.platform.startswith('win32'):
    def _pause():
        os.system("pause")
else:
    def _pause():
        os.system('bash -c \'read -s -n 1\'')

def pause(msg='Press any key to continue...', key_count=1):
        # print(msg, end='')
        print(msg)
        for _ in range(key_count):
            _pause()


class Beeper(object):
    thread = None
    _stop = False
    _freq, _duration = 1000, 300
    def __init__(self, **kwargs):
        if 'freq' in kwargs:
            self._freq = kwargs['freq']
        if 'duration' in kwargs:
            self._duration = kwargs['duration']
        return super().__init__()

    def start(self):
        self._stop = False
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run, name='BeepThread',)
            self.thread.start()

    def stop(self):
        self._stop = True

    def _run(self):
        while not self._stop:
            for _ in range(3):
                beep(self._freq, self._duration)
            time.sleep(1)

    def __del__(self):
        self._stop = True


def display_table(dict_list):
    """
    This function
        1. Takes a list of dictionary
        2. Add an Index column, and
        3. Displays the data in tabular format
    """
    header = ["idx"] + list(dict_list[0].keys())
    rows = [[idx + 1] + list(x.values()) for idx, x in enumerate(dict_list)]
    print(tabulate.tabulate(rows, header, tablefmt="grid"))


def select_list_item_by_csi(ls: Iterable, csi) -> list:
        if isinstance(csi, str):
            csi = csi.replace(' ', '')
            select_ids = [int(idx) - 1 for idx in csi.split(",")]
        elif isinstance(csi, Iterable[int]):
            select_ids = input
        else:
            return []
        return [ item for idx, item in enumerate(ls) if idx in select_ids]


def display_info_dict(details):
    for key, value in details.items():
        if isinstance(value, list):
            if all(isinstance(item, dict) for item in value):
                print(f"\t{key}:")
                display_table(value)
            else:
                print(f"\t{key}\t: {value}")
        else:
            print(f"\t{key}\t: {value}")


def confirm_and_proceed(collected_details):
    print(
        "\n================================= Confirm Info =================================\n"
    )
    display_info_dict(collected_details)

    confirm = input("\nProceed with above info (y/n Default y) : ")
    confirm = confirm if confirm else "y"
    if confirm != "y":
        print("Details not confirmed. Exiting process.")
        pause()
        sys.exit()


def save_user_info(filename, details):
    print(
        "\n================================= Save Info =================================\n"
    )
    save_info = input(
        "Would you like to save this as a JSON file for easy use next time?: (y/n Default y): "
    )
    save_info = save_info if save_info else "y"
    if save_info == "y":
        with open(filename, "w") as f:
            json.dump(details, f)

        print(f"Info saved to {filename} in {os.getcwd()}")


def get_saved_user_info(filename):
    with open(filename, "r") as f:
        data = json.load(f)

    return data
