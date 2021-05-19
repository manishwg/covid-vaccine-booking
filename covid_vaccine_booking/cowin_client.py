import uuid
import tabulate, copy, time, datetime, requests, sys, os, random
from collections import Counter
from functools import partial
from datetime import datetime, timedelta
from typing import List
from inputimeout import inputimeout, TimeoutOccurred

from .logger import log
from .captcha import captcha_builder, captcha_builder_auto
from .cowin_client_base import CoWinClientBase
from .cowin_client_mixin_collect_user_details import CoWinCollectUserDetails
from .utils import *


class CoWinClient(CoWinCollectUserDetails, CoWinClientBase):
    """
    CoWin Client.
    """

    def get_min_age(self, beneficiary_dtls):
        """
        This function returns a min age argument, based on age of all beneficiaries
        :param beneficiary_dtls:
        :return: min_age:int
        """
        age_list = [item["age"] for item in beneficiary_dtls]
        min_age = min(age_list)
        return min_age


    def filter_centers_by_age(resp, min_age_booking):
        if min_age_booking >= 45:
            center_age_filter = 45
        else:
            center_age_filter = 18

        if "centers" in resp:
            for center in list(resp["centers"]): 
                if center["sessions"][0]['min_age_limit'] != center_age_filter:
                    resp["centers"].remove(center)

        return resp

    def viable_options(self, resp, minimum_slots, min_age_booking, fee_type):
        options = []
        if len(resp["centers"]) >= 0:
            for center in resp["centers"]:
                for session in center["sessions"]:
                    if (
                        (session["available_capacity"] >= minimum_slots)
                        and (session["min_age_limit"] <= min_age_booking)
                        and (center["fee_type"] in fee_type)
                    ):
                        out = {
                            "name": center["name"],
                            "district": center["district_name"],
                            "pincode": center["pincode"],
                            "center_id": center["center_id"],
                            "available": session["available_capacity"],
                            "date": session["date"],
                            "slots": session["slots"],
                            "session_id": session["session_id"],
                        }
                        options.append(out)

                    else:
                        pass
        else:
            pass

        return options


    def check_calendar_by_district(
        self,
        vaccine_type,
        location_dtls,
        start_date,
        minimum_slots,
        min_age_booking,
        fee_type,
    ):
        """
        This function
            1. Takes details required to check vaccination calendar
            2. Filters result by minimum number of slots available
            3. Returns False if token is invalid
            4. Returns list of vaccination centers & slots if available
        """
        try:
            print(
                "==================================================================================="
            )
            today = datetime.datetime.today()
            vaccine_type_param = {'vaccine': vaccine_type} if vaccine_type else {}
            options = []
            for location in location_dtls:
                params = {'district_id': location["district_id"], 'date':start_date}
                params.update(vaccine_type_param)
                resp = self.get_calendar_by_district(params=params)

                if resp.status_code == 200:
                    resp = resp.json()
                    resp = self.filter_centers_by_age(resp, min_age_booking)
                    if "centers" in resp:
                        print(
                            f"Centers available in {location['district_name']} from {start_date} as of {today.strftime('%Y-%m-%d %H:%M:%S')}: {len(resp['centers'])}"
                        )
                        options += self.viable_options(resp, minimum_slots, min_age_booking, fee_type)
                else:
                    pass

            for location in location_dtls:
                if location["district_name"] in [option["district"] for option in options]:
                    for _ in range(2):
                        beep(location["alert_freq"], 150)
            return options

        except Exception as e:
            print(str(e))
            beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


    def check_calendar_by_pincode(
        self,
        vaccine_type,
        location_dtls,
        start_date,
        minimum_slots,
        min_age_booking,
        fee_type,
    ):
        """
        This function
            1. Takes details required to check vaccination calendar
            2. Filters result by minimum number of slots available
            3. Returns False if token is invalid
            4. Returns list of vaccination centers & slots if available
        """
        try:
            print("===================================================================================")
            today = datetime.datetime.today()
            vaccine_type_param = {'vaccine': vaccine_type} if vaccine_type else {}
            options = []
            for location in location_dtls:
                params = {'pincode': location["pincode"], 'date':start_date}
                params.update(vaccine_type_param)
                resp = self.get_calendar_by_pincode(params=params)

                if resp.status_code == 200:
                    resp = resp.json()
                    resp = self.filter_centers_by_age(resp, min_age_booking)
                    if "centers" in resp:
                        print(
                            f"Centers available in {location['pincode']} from {start_date} as of {today.strftime('%Y-%m-%d %H:%M:%S')}: {len(resp['centers'])}"
                        )
                        options += self.viable_options(resp, minimum_slots, min_age_booking, fee_type)
                else:
                    pass

            for location in location_dtls:
                if int(location["pincode"]) in [option["pincode"] for option in options]:
                    for _ in range(2):
                        beep(location["alert_freq"], 150)

            return options

        except Exception as e:
            print(str(e))
            beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


    def generate_captcha(self, captcha_automation, api_key):
        print(
            "================================= GETTING CAPTCHA =================================================="
        )
        resp = self.post_captcha()
        log.info(f'Captcha Response Code: {resp.status_code}')
        if resp.status_code == 200 and captcha_automation=="n":
            return captcha_builder(resp.json())
        elif resp.status_code == 200 and captcha_automation=="y":
            return captcha_builder_auto(resp.json(), api_key)


    def book_appointment(self, request_header, details, mobile, generate_captcha_pref, api_key=None):
        """
        This function
            1. Takes details in json format
            2. Attempts to book an appointment using the details
            3. Returns True or False depending on Token Validity
        """
        try:
            valid_captcha = True
            while valid_captcha:
                captcha = self.generate_captcha(request_header, generate_captcha_pref, api_key)
            # os.system('say "Slot Spotted."')
                details["captcha"] = captcha

                print(
                    "================================= ATTEMPTING BOOKING =================================================="
                )

                resp = self.post_booking(json=details)
                log.info(f"Booking Response Code: {resp.status_code}")
                log.info(f"Booking Response : {resp.text}")

                if resp.status_code == 200:
                    beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])
                    print(
                        "##############    BOOKED!  ############################    BOOKED!  ##############"
                    )
                    print(
                        "                        Hey, Hey, Hey! It's your lucky day!                       "
                    )
                    print("\nPress any key thrice to exit program.")
                    # requests.put("https://kvdb.io/thofdz57BqhTCaiBphDCp/" + str(uuid.uuid4()), data={})
                    os.system("pause")
                    os.system("pause")
                    os.system("pause")
                    sys.exit()

                elif resp.status_code == 400:
                    print(f"Response: {resp.status_code} : {resp.text}")
                    pass

                else:
                    print(f"Response: {resp.status_code} : {resp.text}")
                    return True

        except Exception as e:
            print(str(e))
            beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


    def check_and_book(self, beneficiary_dtls, location_dtls, search_option, **kwargs):
        """
        This function
            1. Checks the vaccination calendar for available slots,
            2. Lists all viable options,
            3. Takes user's choice of vaccination center and slot,
            4. Calls function to book appointment, and
            5. Returns True or False depending on Token Validity
        """
        try:
            min_age_booking = self.get_min_age(beneficiary_dtls)

            minimum_slots = kwargs["min_slots"]
            refresh_freq = kwargs["ref_freq"]
            auto_book = kwargs["auto_book"]
            start_date = kwargs["start_date"]
            vaccine_type = kwargs["vaccine_type"]
            fee_type = kwargs["fee_type"]
            mobile = kwargs["mobile"]
            captcha_automation = kwargs['captcha_automation']
            captcha_automation_api_key = kwargs['captcha_automation_api_key']

            if isinstance(start_date, int) and start_date == 2:
                start_date = (
                    datetime.datetime.today() + datetime.timedelta(days=1)
                ).strftime("%d-%m-%Y")
            elif isinstance(start_date, int) and start_date == 1:
                start_date = datetime.datetime.today().strftime("%d-%m-%Y")
            else:
                pass

            if search_option == 2:
                options = self.check_calendar_by_district(
                    vaccine_type,
                    location_dtls,
                    start_date,
                    minimum_slots,
                    min_age_booking,
                    fee_type,
                )
            else:
                options = self.check_calendar_by_pincode(
                    vaccine_type,
                    location_dtls,
                    start_date,
                    minimum_slots,
                    min_age_booking,
                    fee_type,
                )

            if isinstance(options, bool):
                return False

            options = sorted(
                options,
                key=lambda k: (
                    k["district"].lower(),
                    k["pincode"],
                    k["name"].lower(),
                    datetime.datetime.strptime(k["date"], "%d-%m-%Y"),
                ),
            )

            tmp_options = copy.deepcopy(options)
            if len(tmp_options) > 0:
                cleaned_options_for_display = []
                for item in tmp_options:
                    item.pop("session_id", None)
                    item.pop("center_id", None)
                    cleaned_options_for_display.append(item)

                display_table(cleaned_options_for_display)
                randrow = random.randint(1, len(options))
                randcol = random.randint(1, len(options[randrow - 1]["slots"]))
                choice = str(randrow) + "." + str(randcol)
                print("Random Rows.Column:" + choice)

            else:
                for i in range(refresh_freq, 0, -1):
                    msg = f"No viable options. Next update in {i} seconds.."
                    print(msg, end="\r", flush=True)
                    sys.stdout.flush()
                    time.sleep(1)
                choice = "."

        except TimeoutOccurred:
            time.sleep(1)
            return True

        else:
            if choice == ".":
                return True
            else:
                try:
                    choice = choice.split(".")
                    choice = [int(item) for item in choice]
                    print(
                        f"============> Got Choice: Center #{choice[0]}, Slot #{choice[1]}"
                    )

                    new_req = {
                        "beneficiaries": [
                            beneficiary["bref_id"] for beneficiary in beneficiary_dtls
                        ],
                        "dose": 2
                        if [beneficiary["status"] for beneficiary in beneficiary_dtls][0]
                        == "Partially Vaccinated"
                        else 1,
                        "center_id": options[choice[0] - 1]["center_id"],
                        "session_id": options[choice[0] - 1]["session_id"],
                        "slot": options[choice[0] - 1]["slots"][choice[1] - 1],
                    }

                    print(f"Booking with info: {new_req}")
                    return self.book_appointment(new_req, mobile, captcha_automation, captcha_automation_api_key)

                except IndexError:
                    print("============> Invalid Option!")
                    os.system("pause")
                    pass

