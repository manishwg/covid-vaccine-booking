from collections import Counter
from functools import partial
from datetime import datetime, timedelta
from typing import List

from .logger import log
from .cowin_client_base import CoWinClientBase
from .utils import (
    beep,
    Beeper,
    display_table
)


class CoWinCollectUserDetails(CoWinClientBase):
    """
    CoWin Client.
    """

    def select_beneficiaries(self):
        """
        This function
            1. Fetches all beneficiaries registered under the mobile number,
            2. Prompts user to select the applicable beneficiaries, and
            3. Returns the list of beneficiaries as list(dict)
        """
        response = self.get_beneficiaries()

        if response.status_code == 200:
            beneficiaries = response.json()["beneficiaries"]
            refined_beneficiaries = []
            for beneficiary in beneficiaries:
                refined_beneficiaries.append({
                    "bref_id": beneficiary["beneficiary_reference_id"],
                    "name": beneficiary["name"],
                    "vaccine": beneficiary["vaccine"],
                    "age": datetime.today().year - int(beneficiary["birth_year"]),
                    "status": beneficiary["vaccination_status"],
                })

            display_table(refined_beneficiaries)
            print(
                """
                ################# IMPORTANT NOTES #################
                # 1. While selecting beneficiaries, make sure that selected beneficiaries are all taking the same dose: either first OR second.
                #    Please do no try to club together booking for first dose for one beneficiary and second dose for another beneficiary.
                #
                # 2. While selecting beneficiaries, also make sure that beneficiaries selected for second dose are all taking the same vaccine: COVISHIELD OR COVAXIN.
                #    Please do no try to club together booking for beneficiary taking COVISHIELD with beneficiary taking COVAXIN.
                #
                # 3. If you're selecting multiple beneficiaries, make sure all are of the same age group (45+ or 18+) as defined by the govt.
                #    Please do not try to club together booking for younger and older beneficiaries.
                ###################################################
                """
            )
            reqd_beneficiaries = input("Enter comma separated index numbers of beneficiaries to book for : ")
            reqd_beneficiaries = reqd_beneficiaries.replace(' ', '')
            beneficiary_idx = [int(idx) - 1 for idx in reqd_beneficiaries.split(",")]
            reqd_beneficiaries = [ item for idx, item in enumerate(beneficiaries) if idx in beneficiary_idx]

            print(f"Selected beneficiaries: ")
            display_table(reqd_beneficiaries)
            return reqd_beneficiaries

        else:
            log.error(f"fetch beneficiaries response (code: {response.status_code} ): {response.text}")
            os.system("pause")
            return []

    def select_vaccine_preference(self):
        print(
            "It seems you're trying to find a slot for your first dose. Do you have a vaccine preference?"
        )
        preference = input(
            "Enter 0 for No Preference, 1 for COVISHIELD, or 2 for COVAXIN. Default 0 : "
        )
        preference = int(preference) if preference and int(preference) in [0, 1, 2] else 0

        if preference == 1:
            return "COVISHIELD"
        elif preference == 2:
            return "COVAXIN"
        else:
            return None

    def select_districts(self):
        """
        This function
            1. Lists all states, prompts to select one,
            2. Lists all districts in that state, prompts to select required ones, and
            3. Returns the list of districts as list(dict)
        """
        resp_states = self.get_states()

        if resp_states.status_code == 200:
            states = resp_states.json()["states"]

            display_table([{"state": state["state_name"]} for state in states])
            state = int(input("\nEnter State index: "))
            state_id = states[state - 1]["state_id"]

            resp_districts = self.get_districts(state_id=state_id)

            if resp_districts.status_code == 200:
                districts = resp_districts.json()["districts"]

                refined_districts = []
                for district in districts:
                    tmp = {"district": district["district_name"]}
                    refined_districts.append(tmp)

                display_table(refined_districts)
                reqd_districts = input(
                    "\nEnter comma separated index numbers of districts to monitor : "
                )
                districts_idx = [int(idx) - 1 for idx in reqd_districts.split(",")]
                reqd_districts = [
                    {
                        "district_id": item["district_id"],
                        "district_name": item["district_name"],
                        "alert_freq": 440 + ((2 * idx) * 110),
                    }
                    for idx, item in enumerate(districts)
                    if idx in districts_idx
                ]

                print(f"Selected districts: ")
                display_table(reqd_districts)
                return reqd_districts

            else:
                log.error(f"fetch districts response (code: {resp_districts.status_code}): {resp_districts.text}")
                os.system("pause")
                sys.exit(1)

        else:
            log.error(f"fetch states response (code: {resp_states.status_code}): {resp_states.text}")
            os.system("pause")
            sys.exit(1)

    def get_pincodes(self):
        locations = []
        pincodes = input("Enter comma separated index numbers of pincodes to monitor: ")
        for idx, pincode in enumerate(pincodes.split(",")):
            pincode = {"pincode": pincode, "alert_freq": 440 + ((2 * idx) * 110)}
            locations.append(pincode)
        return locations

    def get_fee_type_preference(self):
        print("\nDo you have a fee type preference?")
        preference = input(
            "Enter 0 for No Preference, 1 for Free Only, or 2 for Paid Only. Default 0 : "
        )
        preference = int(preference) if preference and int(preference) in [0, 1, 2] else 0

        if preference == 1:
            return ["Free"]
        elif preference == 2:
            return ["Paid"]
        else:
            return ["Free", "Paid"]


    def collect_user_details(self):
        # Get Beneficiaries
        print("Fetching registered beneficiaries.. ")
        beneficiary_dtls = self.select_beneficiaries()

        if len(beneficiary_dtls) == 0:
            print("There should be at least one beneficiary. Exiting.")
            os.system("pause")
            sys.exit(1)

        # Make sure all beneficiaries have the same type of vaccine
        vaccine_types = [beneficiary["vaccine"] for beneficiary in beneficiary_dtls]
        vaccines = Counter(vaccine_types)

        if len(vaccines.keys()) != 1:
            log.error(f"All beneficiaries in one attempt should have the same vaccine type. Found {len(vaccines.keys())}")
            os.system("pause")
            sys.exit(1)

        vaccine_type = vaccine_types[
            0
        ]  # if all([beneficiary['status'] == 'Partially Vaccinated' for beneficiary in beneficiary_dtls]) else None
        if not vaccine_type:
            print(
                "\n================================= Vaccine Info =================================\n"
            )
            vaccine_type = self.select_vaccine_preference()

        print(
            "\n================================= Location Info =================================\n"
        )
        # get search method to use
        search_option = input(
            """Search by Pincode? Or by State/District? \nEnter 1 for Pincode or 2 for State/District. (Default 2) : """
        )
        search_option = int(search_option) if search_option and int(search_option) in [1, 2] else 2

        if search_option == 2:
            # Collect vaccination center preferance
            location_dtls = self.select_districts()

        else:
            # Collect vaccination center preferance
            location_dtls = self.get_pincodes()

        print(
            "\n================================= Additional Info =================================\n"
        )

        # Set filter condition
        minimum_slots = input(
            f"Filter out centers with availability less than ? Minimum {len(beneficiary_dtls)} : "
        )
        minimum_slots = int(minimum_slots) if minimum_slots and int(minimum_slots) >= len(beneficiary_dtls) else len(beneficiary_dtls)

        # Get refresh frequency
        refresh_freq = input(
            "How often do you want to refresh the calendar (in seconds)? Default 10. Minimum 1. : "
        )
        refresh_freq = int(refresh_freq) if refresh_freq and int(refresh_freq) >= 1 else 10

        # Get search start date
        start_date = input(
            "\nSearch for next seven day starting from when?\nUse 1 for today, 2 for tomorrow, or provide a date in the format yyyy-mm-dd. Default 2: "
        )
        if not start_date:
            start_date = 2
        elif start_date in ["1", "2"]:
            start_date = int(start_date)
        else:
            try:
                datetime.datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                start_date = 2

        # Get preference of Free/Paid option
        fee_type = self.get_fee_type_preference()

        print(
            "\n=========== CAUTION! =========== CAUTION! CAUTION! =============== CAUTION! =======\n"
            "===== BE CAREFUL WITH THIS OPTION! AUTO-BOOKING WILL BOOK THE FIRST AVAILABLE CENTRE, DATE, AND A RANDOM SLOT! ====="
        )
        auto_book = "yes-please"


        print("\n================================= Captcha Automation =================================\n")
        print("======== Caution: This will require a paid API key from https://anti-captcha.com =============")

        captcha_automation = input("Do you want to automate captcha autofill? (y/n) Default n: ")
        captcha_automation = "n" if not captcha_automation else captcha_automation
        if captcha_automation=="y":
            captcha_automation_api_key = input("Enter your Anti-Captcha API key: ")
        else:
            captcha_automation_api_key = None

        collected_details = {
            "beneficiary_dtls": beneficiary_dtls,
            "location_dtls": location_dtls,
            "search_option": search_option,
            "minimum_slots": minimum_slots,
            "refresh_freq": refresh_freq,
            "auto_book": auto_book,
            "start_date": start_date,
            "vaccine_type": vaccine_type,
            "fee_type": fee_type,
            'captcha_automation': captcha_automation,
            'captcha_automation_api_key': captcha_automation_api_key
        }

        return collected_details
