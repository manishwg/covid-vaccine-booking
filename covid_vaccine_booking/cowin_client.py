from collections import Counter
from functools import partial
from datetime import datetime, timedelta
from typing import List


from .cowin_session import CoWinSession
from .utils import *



class CoWinClient(object):
    """
    CoWin Client.
    """
    mobile = None

    base_url = 'https://cdn-api.co-vin.in/api/v2/'

    api = {
        'booking':              f"{base_url}appointment/schedule",
        'beneficiaries':        f"{base_url}appointment/beneficiaries",
        'states':               f"{base_url}admin/location/states",
        'districts':            f"{base_url}admin/location/districts/{{state_id}}",
        # 'calendar_district':    f"{base_url}appointment/sessions/calendarByDistrict?district_id={0}&date={1}",
        'calendar_by_district': f"{base_url}appointment/sessions/calendarByDistrict",
        # 'calendar_pincode':     f"{base_url}appointment/sessions/calendarByPin?pincode={0}&date={1}",
        'calendar_by_pincode':  f"{base_url}appointment/sessions/calendarByPin",
        'captcha':              f"{base_url}auth/getRecaptcha",

    }
    api_methods = ['get', 'post',]

    def __init__(self, mobile, *args, **kwargs):
        """
        constructor.
        """
        super().__init__(*args, **kwargs)
        self.mobile = mobile
        self.session = CoWinSession(mobile=mobile)

        for api, url in self.api.items():
            for method in self.api_methods:
                if not hasattr(self, f'{method}_{api}'):
                    setattr(self, f'{method}_{api}', self._get_partial_api_method(method, url=url))

    def _get_partial_api_method(self, method, url,**kwargs):

        method = getattr(self.session, method)
        if method:
            return partial(method, url=url, **kwargs)

    def get_districts(self, state_id):
        url = self.api['districts']
        return self.session.get(url=url.format(state_id=state_id))


# if __name__ == "__main__":
#     co = CoWinSession(9822511138)
#     co.get_beneficiaries()