import sys
import os
import json
from collections import Counter
from functools import partial
from datetime import date, datetime, timedelta
from typing import (List, Union,)

from .logger import log
from .cowin_client import CoWinClient
from .utils import (
    beep,
    Beeper,
    display_table,
    select_list_item_by_csi,
)
from .config import (
    DATA_FILENAME_FORMAT,
    DATA_FILENAME_DIR,
)

class BookingData(object):

    beneficiary_ls: List[dict]
    vaccine_type: str
    search_option: int
    location_ls: List[dict]
    location_blocks: List[str]
    minimum_slots: int
    refresh_freq: int
    start_date: Union[int,date]
    fee_type: List[str]
    auto_book: str
    captcha_automation: bool
    captcha_automation_api_key: Union[type(None), str]

    DATA_ATTRS = (
        'beneficiary_ls', 'location_ls', 'location_blocks', 'search_option',
        'minimum_slots', 'refresh_freq', 'auto_book','start_date', 'vaccine_type',
        'fee_type', 'captcha_automation', 'captcha_automation_api_key',
    )


    VACCINE_TYPES = ("", "COVISHIELD", "COVAXIN")
    FEE_TYPES = (["Free", "Paid"], ["Free"], ["Paid"])

    collection_data = {}

    def __init__(self, mobile, cowin_client, **kwargs):
        if 'data' in kwargs:
            self.data = kwargs['data']
        self.mobile = mobile
        self.client = cowin_client
        filename = DATA_FILENAME_DIR + DATA_FILENAME_FORMAT.format(mobile=mobile)
        filename =  os.path.expandvars(os.path.expanduser(filename))
        print(filename)
        os.system("pause")

        if os.path.exists(filename):
            print("\n=================================== Note ===================================\n")
            print(f"Info from perhaps a previous run already exists in {filename} in this directory.")
            print(f"IMPORTANT: If this is your first time running this version of the application, DO NOT USE THE FILE!")
            try_file = input("Would you like to see the details and confirm to proceed? (y/n Default y): ")
            try_file = not try_file.strip().lower().startswith('n')

            if try_file:
                self.load_from_json_file(filename=filename)
                print("\n================================= Info =================================\n")
                self.display()

                file_acceptable = input("\nProceed with above info? (y/n Default y): ")
                file_acceptable = not file_acceptable.strip().lower().startswith('n')

                if not file_acceptable:
                    self.collect_user_details()
                    self.save_to_json_file_with_prompt(filename)
            else:
                self.collect_user_details()
                self.save_to_json_file_with_prompt(filename)

        else:
            self.collect_user_details()
            self.save_to_json_file_with_prompt(filename)




    @property
    def data(self):
        return {k: v for k,v in self.__dict__.items() if k in self.DATA_ATTRS}

    @data.setter
    def data(self, value):
        if isinstance(value, dict):
            self.__dict__.update({k: v for k,v in value.items() if k in self.DATA_ATTRS})
        else:
            raise ValueError(f"Expected 'dict' got {type(value)}")

    def is_data_collected(self):
        return all(map(lambda x : hasattr(self, x) and getattr(self,x)), self.DATA_ATTRS)

    def load_from_json_file(self, filename):
        with open(filename, "r") as f:
            self.data = json.load(f)
        return self.data

    def save_to_json_file(self, filename):
        with open(filename, "w") as f:
            json.dump(self.data, f)

    def display(self):
        for key, value in self.data.items():
            if isinstance(value, list):
                if all(isinstance(item, dict) for item in value):
                    print(f"\t{key}:")
                    display_table(value)
                else:
                    print(f"\t{key}\t: {value}")
            else:
                print(f"\t{key}\t: {value}")

    def save_to_json_file_with_prompt(self, filename):
        print("\n================================= Save Booking info =================================\n")
        save_info = input(
            "Would you like to save this as a JSON file for easy use next time?: (y/n Default y): "
        )
        save_info = save_info if save_info else "y"
        if save_info == "y":
            self.save_to_json_file(filename=filename)
            print(f"Info saved to {filename} in {os.getcwd()}")

    def confirm_and_proceed(self):
        print(
            "\n================================= Confirm Info =================================\n"
        )
        self.display()

        confirm = input("\nProceed with above info (y/n Default y) : ")
        confirm = confirm if confirm else "y"
        if confirm != "y":
            print("Details not confirmed. Exiting process.")
            os.system("pause")
            sys.exit()

    def select_beneficiaries(self):
        """
        This function
            1. Fetches all beneficiaries registered under the mobile number,
            2. Prompts user to select the applicable beneficiaries, and
            3. Returns the list of beneficiaries as list(dict)
        """
        response = self.client.get_beneficiaries()

        if response.status_code == 200:
            beneficiaries = response.json()["beneficiaries"]
            if len(beneficiaries) == 0:
                log.error("please add beneficiary to the account and try again. Exiting.")
                os.system("pause")
                sys.exit(1)

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
            select_loop = True
            while select_loop:
                select_str = input("\nEnter comma separated index numbers of beneficiaries to book for : ")
                Selected_beneficiaries = select_list_item_by_csi(refined_beneficiaries, select_str)

                if len(Selected_beneficiaries) > 0:
                    vaccine_types = [beneficiary["vaccine"] for beneficiary in Selected_beneficiaries]
                    vaccines = Counter(vaccine_types)
                    if len(vaccines.keys()) == 1:
                        self.collection_data['vaccine_type'] = vaccine_types[0]
                        select_loop = False
                    else:
                        print(f"All beneficiaries in one attempt should have the same vaccine type. Found {len(vaccines.keys())}")
                        # os.system("pause")
                        # sys.exit(1)
                else:
                    print("There should be at least one beneficiary.")
                    # os.system("pause")

            print(f"Selected beneficiaries: ")
            display_table(Selected_beneficiaries)
            self.collection_data['beneficiary_ls'] = Selected_beneficiaries
            return Selected_beneficiaries

        else:
            log.error(f"fetch beneficiaries response (code: {response.status_code} ): {response.text}")
            os.system("pause")
            return []

    def select_vaccine_preference(self):
        print(
            "\n================================= Vaccine Info =================================\n"
            "It seems you're trying to find a slot for your first dose. Do you have a vaccine preference?"
        )

        preference = input(" 0 for No Preference.\n 1 for COVISHIELD.\n 2 for COVAXIN.\n Default 0 : ")
        preference = int(preference) if preference and int(preference) in [0, 1, 2] else 0

        self.collection_data['vaccine_type'] = self.VACCINE_TYPES[preference]
        return self.VACCINE_TYPES[preference]

    def select_districts(self):
        """
        This function
            1. Lists all states, prompts to select one,
            2. Lists all districts in that state, prompts to select required ones, and
            3. Returns the list of districts as list(dict)
        """
        resp_states = self.client.get_states()

        if resp_states.status_code == 200:
            states = resp_states.json()["states"]

            display_table([{"state": state["state_name"]} for state in states])
            state = int(input("\nEnter State index: "))
            state_id = states[state - 1]["state_id"]

            resp_districts = self.client.get_districts(state_id=state_id)

            if resp_districts.status_code == 200:
                districts = resp_districts.json()["districts"]

                display_table([{"district": district["district_name"]} for district in districts])
                select_str = input("\nEnter comma separated index numbers of districts to monitor : ")
                Selected_districts = select_list_item_by_csi(districts, select_str)

                Selected_districts = [
                    {
                        "district_id": item["district_id"],
                        "district_name": item["district_name"],
                        "alert_freq": 440 + ((2 * idx) * 110),
                    }
                    for idx, item in enumerate(Selected_districts)
                ]

                print(f"Selected districts: ")
                display_table(Selected_districts)
                self.collection_data['location_ls'] = Selected_districts
                return Selected_districts

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
        self.collection_data['location_ls'] = locations
        return locations

    def get_fee_type_preference(self):
        preference = input(
            "\nDo you have a fee type preference?\n"
            " 0 for No Preference,\n"
            " 1 for Free Only,\n"
            " 2 for Paid Only.\n"
            "Default 0 : "
        )
        preference = int(preference) if preference and int(preference) in [0, 1, 2] else 0

        self.collection_data['fee_type'] = self.FEE_TYPES[preference]
        return self.FEE_TYPES[preference]



    def collect_user_details(self):
        self.collection_data = {}
        # Get Beneficiaries
        print("Fetching registered beneficiaries.. ")
        self.select_beneficiaries()

        if not self.collection_data['vaccine_type']:
            vaccine_type = self.select_vaccine_preference()

        print(
            "\n================================= Location Info =================================\n"
        )
        # get search method to use
        search_option = input(
            """Search by Pincode? Or by State/District? \nEnter 1 for Pincode or 2 for State/District. (Default 2) : """
        )
        search_option = int(search_option) if search_option and int(search_option) in [1, 2] else 2
        self.collection_data['search_option'] = search_option
        if search_option == 2:
            # Collect vaccination center preferance
            self.select_districts()

        else:
            # Collect vaccination center preferance
            self.get_pincodes()

        print(
            "\n================================= Additional Info =================================\n"
        )

        # Set filter condition
        ben_len = len(self.collection_data['beneficiary_ls'])
        minimum_slots = input(f"Filter out centers with availability less than ? Minimum {ben_len} : ")
        self.collection_data['minimum_slots'] = int(minimum_slots) if minimum_slots and int(minimum_slots) >= ben_len else ben_len

        # Get refresh frequency
        refresh_freq = input("How often do you want to refresh the calendar (in seconds)? Default 10. Minimum 1. : ")
        self.collection_data['refresh_freq'] = int(refresh_freq) if refresh_freq and int(refresh_freq) >= 1 else 10

        # Get search start date
        start_date = input(
            "\nSearch for next seven day starting from when?\n 1 for today,\n 2 for tomorrow, \nor provide a date in the format dd-mm-yyyy. Default 2: "
        )
        if not start_date:
            start_date = 2
        elif start_date in ["1", "2"]:
            start_date = int(start_date)
        else:
            try:
                datetime.datetime.strptime(start_date, "%d-%m-%Y")
            except ValueError:
                start_date = 2
        self.collection_data['start_date'] = start_date

        # Get preference of Free/Paid option
        fee_type = self.get_fee_type_preference()

        print(
            "\n=========== CAUTION! =========== CAUTION! CAUTION! =============== CAUTION! =======\n"
            "===== BE CAREFUL WITH THIS OPTION! AUTO-BOOKING WILL BOOK THE FIRST AVAILABLE CENTRE, DATE, AND A RANDOM SLOT! ====="
        )
        self.collection_data['auto_book'] = "yes-please"

        print("\n================================= Captcha Automation =================================\n")
        print("======== Caution: This will require a paid API key from https://anti-captcha.com =============")

        captcha_automation = input("Do you want to automate captcha autofill? (y/n) Default n: ")
        self.collection_data['captcha_automation'] = captcha_automation.strip().lower().startswith('y')
        if self.collection_data['captcha_automation']:
            self.collection_data['captcha_automation_api_key'] = input("Enter your Anti-Captcha API key: ")
        else:
            self.collection_data['captcha_automation_api_key'] = None

        self.data = self.collection_data
        return self.collection_data
