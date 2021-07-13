# !/usr/bin/env python3
import time, sys, argparse
from types import SimpleNamespace
from rich.console import Console
from .logger import log
from .booking_client import BookingClient
from .utils import pause

# from utils import (generate_token_OTP, generate_token_OTP_manual, check_and_book, beep, BENEFICIARIES_URL, WARNING_BEEP_DURATION,
#     display_info_dict, save_user_info, collect_user_details, get_saved_user_info, confirm_and_proceed)

console = Console()

parser = argparse.ArgumentParser()

try:
    # mobile = input("Enter the registered mobile number: ")
    # filename = 'vaccine-booking-details-' + mobile + ".json"
    # otp_pref = input("\nDo you want to enter OTP manually, instead of auto-read? \nRemember selecting n would require some setup described in README (y/n Default n): ")
    # otp_pref = otp_pref if otp_pref else "n"
    mobile = 9657830140
    bc = BookingClient(mobile)

    while True:
        # call function to check and book slots
        try:
            bc.check_and_book()

        except Exception as e:
            print(str(e))
            print('Retryin in 5 seconds')
            time.sleep(5)


except KeyboardInterrupt as exc:
    print('', end="\r", flush=True)
    sys.stdout.flush()
    console.print("User Interrupted", style="bold red", justify="left")
    exit(0)

except Exception as e:
    print(str(e))
    print('Exiting Script')
    pause()
