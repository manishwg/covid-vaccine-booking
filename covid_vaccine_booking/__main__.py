# !/usr/bin/env python3
import sys
from .logger import log
from .booking_client import BookingClient
global use_subprocess
use_subprocess = True

    # cs.get_access_token()



import copy
import time
from types import SimpleNamespace
import requests, sys, argparse, os, datetime
# from utils import (generate_token_OTP, generate_token_OTP_manual, check_and_book, beep, BENEFICIARIES_URL, WARNING_BEEP_DURATION,
#     display_info_dict, save_user_info, collect_user_details, get_saved_user_info, confirm_and_proceed)


parser = argparse.ArgumentParser()

try:
    # mobile = input("Enter the registered mobile number: ")
    # filename = 'vaccine-booking-details-' + mobile + ".json"
    # otp_pref = input("\nDo you want to enter OTP manually, instead of auto-read? \nRemember selecting n would require some setup described in README (y/n Default n): ")
    # otp_pref = otp_pref if otp_pref else "n"
    mobile = 9657830140
    bc = BookingClient(mobile)


    #     # call function to check and book slots
    #     try:
    #         token_valid = check_and_book(request_header, info.beneficiary_dtls, info.location_dtls, info.search_option,
    #                                         min_slots=info.minimum_slots,
    #                                         ref_freq=info.refresh_freq,
    #                                         auto_book=info.auto_book,
    #                                         start_date=info.start_date,
    #                                         vaccine_type=info.vaccine_type,
    #                                         fee_type=info.fee_type,
    #                                         mobile=mobile,
    #                                         captcha_automation=info.captcha_automation,
    #                                         captcha_automation_api_key=info.captcha_automation_api_key,)

    #     except Exception as e:
    #         print(str(e))
    #         print('Retryin in 5 seconds')
    #         time.sleep(5)


except KeyboardInterrupt as exc:
    print('', end="\r", flush=True)
    sys.stdout.flush()
    log.error("User Interrupted")
    exit(0)

except Exception as e:
    print(str(e))
    print('Exiting Script')
    os.system("pause")
