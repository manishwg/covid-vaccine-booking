import uuid
import tabulate, copy, time, datetime, requests, sys, os, random
from collections import Counter
from functools import cached_property, partial
from datetime import datetime, timedelta
from typing import List
from inputimeout import inputimeout, TimeoutOccurred

from .logger import log
from .captcha import captcha_builder, captcha_builder_auto
from .cowin_client import CoWinClient
from .booking_data import BookingData
from .utils import *


class BookingClient(object):
    """
    CoWin Client.
    """

    def __init__(self, mobile) -> None:

        self.mobile = mobile
        self.client = CoWinClient(mobile=mobile)
        self.info = BookingData(mobile=mobile, cowin_client=self.client)

    def get_start_date(self):
        sd = self.info.start_date
        if isinstance(sd, int) and sd in (1, 2):
            return (datetime.datetime.today() + datetime.timedelta(days=sd-1)).strftime("%d-%m-%Y")
        elif isinstance(sd, str):
            return sd
        else:
            return datetime.datetime.today().strftime("%d-%m-%Y")

    @cached_property
    def min_age_booking(self):
        """
        This function returns a min age argument, based on age of all beneficiaries
        :param beneficiary_dtls:
        :return: min_age:int
        """
        age_list = [item["age"] for item in self.info.beneficiary_ls]
        min_age = min(age_list)
        return min_age

    def filter_centers_by_age(self, resp):
        center_age_filter = 45 if self.min_age_booking >= 45 else 18
        if "centers" in resp:
            for center in list(resp["centers"]): 
                if center["sessions"][0]['min_age_limit'] != center_age_filter:
                    resp["centers"].remove(center)

        return resp

    def viable_options(self, resp,):
        options = []
        if len(resp["centers"]) >= 0:
            for center in resp["centers"]:
                for session in center["sessions"]:
                    if (
                        (session["available_capacity"] >= self.info.minimum_slots)
                        and (session["min_age_limit"] <= self.min_age_booking)
                        and (center["fee_type"] in self.info.fee_type)
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


    def check_calendar_by_district(self):
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
            vaccine_type_param = {'vaccine': self.info.vaccine_type} if self.info.vaccine_type else {}
            start_date = self.get_start_date()
            options = []
            for location in self.info.location_ls:
                params = {'district_id': location["district_id"], 'date':start_date}
                params.update(vaccine_type_param)
                resp = self.client.get_calendar_by_district(params=params)
                if resp.status_code == 200:
                    resp = resp.json()
                    resp = self.filter_centers_by_age(resp)
                    if "centers" in resp:
                        print(
                            f"Centers available in {location['district_name']} from {start_date} as of {today.strftime('%Y-%m-%d %H:%M:%S')}: {len(resp['centers'])}"
                        )
                        options += self.viable_options(resp)
                else:
                    pass

            for location in self.info.location_ls:
                if location["district_name"] in [option["district"] for option in options]:
                    for _ in range(2):
                        beep(location["alert_freq"], 150)
            return options

        except Exception as e:
            print(str(e))
            beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


    def check_calendar_by_pincode(self):
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
            vaccine_type_param = {'vaccine': self.info.vaccine_type} if self.info.vaccine_type else {}
            start_date = self.get_start_date()
            options = []
            for location in self.info.location_ls:
                params = {'pincode': location["pincode"], 'date':start_date}
                params.update(vaccine_type_param)
                resp = self.client.get_calendar_by_pincode(params=params)

                if resp.status_code == 200:
                    resp = resp.json()
                    resp = self.filter_centers_by_age(resp)
                    if "centers" in resp:
                        print(
                            f"Centers available in {location['pincode']} from {start_date} as of {today.strftime('%Y-%m-%d %H:%M:%S')}: {len(resp['centers'])}"
                        )
                        options += self.viable_options(resp)
                else:
                    pass

            for location in self.info.location_ls:
                if int(location["pincode"]) in [option["pincode"] for option in options]:
                    for _ in range(2):
                        beep(location["alert_freq"], 150)

            return options

        except Exception as e:
            print(str(e))
            beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


    def generate_captcha(self):
        print(
            "================================= GETTING CAPTCHA =================================================="
        )
        resp = self.client.post_captcha()
        log.info(f'Captcha Response Code: {resp.status_code}')
        if resp.status_code == 200:
            if self.info.captcha_automation:
                return captcha_builder_auto(resp.json(), self.info.captcha_automation_api_key)
            else:
                return captcha_builder(resp.json())


    def book_appointment(self, details):
        """
        This function
            1. Takes details in json format
            2. Attempts to book an appointment using the details
            3. Returns True or False depending on Token Validity
        """
        try:
            valid_captcha = True
            while valid_captcha:
                captcha = self.generate_captcha()
            # os.system('say "Slot Spotted."')
                details["captcha"] = captcha

                print(
                    "================================= ATTEMPTING BOOKING =================================================="
                )

                resp = self.client.post_booking(json=details)
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
                    # requests.put("https://kvdb.io/thofdz57BqhTCaiBphDCp/" + str(uuid.uuid4()), data={})
                    pause("\nPress any key thrice to exit program.", 3)
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


    def check_and_book(self, **kwargs):
        """
        This function
            1. Checks the vaccination calendar for available slots,
            2. Lists all viable options,
            3. Takes user's choice of vaccination center and slot,
            4. Calls function to book appointment, and
            5. Returns True or False depending on Token Validity
        """
        try:

            if self.info.search_option == 2:
                options = self.check_calendar_by_district()
            else:
                options = self.check_calendar_by_pincode()

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

            if len(options) > 0:
                # display_table(cleaned_options_for_display)
                display_table([{k:v for k, v in opt.items() if k not in ('session_id', 'center_id')} for opt in options])
                randrow = random.randint(1, len(options))
                randcol = random.randint(1, len(options[randrow - 1]["slots"]))
                choice = str(randrow) + "." + str(randcol)
                print("Random Rows.Column:" + choice)

            else:
                for i in range(self.info.refresh_freq, 0, -1):
                    print(f"No viable options. Next update in {i} seconds..", end="\r", flush=True)
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
                            beneficiary["bref_id"] for beneficiary in self.info.beneficiary_ls
                        ],
                        "dose": 2
                        if [beneficiary["status"] for beneficiary in self.info.beneficiary_ls][0]
                        == "Partially Vaccinated"
                        else 1,
                        "center_id": options[choice[0] - 1]["center_id"],
                        "session_id": options[choice[0] - 1]["session_id"],
                        "slot": options[choice[0] - 1]["slots"][choice[1] - 1],
                    }

                    print(f"Booking with info: {new_req}")
                    return self.book_appointment(new_req)

                except IndexError:
                    print("============> Invalid Option!")
                    pause()
                    pass

