"""
Module defines ADP client.
"""
import os
import json
import copy
import time
import base64
import secrets
from hashlib import sha256
import requests
import threading
from requests.auth import AuthBase
from requests.sessions import Session
from requests.status_codes import codes
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib3.exceptions import MaxRetryError
from collections import OrderedDict
from os import curdir, sep
from datetime import datetime, timedelta
from urllib.parse import urlencode
import sys
from .logger import log
from .config import (
    STORAGE_URL_BASE,
)

class Custom_Retry(Retry):
    BACKOFF_MAX = 1


class TimeoutHTTPAdapter(HTTPAdapter):
    DEFAULT_TIMEOUT = 7 # seconds

    def __init__(self, *args, **kwargs):
        self.timeout = self.DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)




class CoWinSession(Session):

    base_url = 'https://cdn-api.co-vin.in/api/v2/'

    api = {
        # 'booking':             f"{base_url}appointment/schedule",
        # 'beneficiaries':       f"{base_url}appointment/beneficiaries",
        # 'calendar_district':   f"{base_url}appointment/sessions/calendarByDistrict?district_id={0}&date={1}",
        # 'calendar_pincode':    f"{base_url}appointment/sessions/calendarByPin?pincode={0}&date={1}",
        'captcha':             f"{base_url}auth/getRecaptcha",
        'validate_otp':        f"{base_url}auth/validateMobileOtp",
        'generate_otp_public': f"{base_url}auth/public/generateOTP",
        'generate_otp':        f"{base_url}auth/generateMobileOTP",

    }
    TXN_VALID_TILL = (60 * 3) - 5
    TOKEN_VALID_TILL = 60 * 15
    TOKEN_PREFETCH_TIME = 60 * 2
    FORCE_TOKEN_PREFETCH: bool = False

    mobile = None

    _access_token_info = dict({
        'token': None,
        'expires': None,
    })
    _txn_info = dict({
        'txn_id': None,
        'expires': None,
    })
    _otp_secrete = "U2FsdGVkX1+z/4Nr9nta+2DrVJSv7KS6VoQUSQ1ZXYDx/CJUkWxFYG6P3iM/VW+6jLQ9RDQVzp/RcZ8kbT41xw=="

    auth_thread = None
    _thread_stop_f: bool = False

    timeout = (2, 7)
    retry_obj = Custom_Retry(
        total=10,
        status_forcelist=[
            # 400,402,404,405,406,407,408,409,410,411,412,413,
            429,431,444,451,499,
            500,501,502,503,504,505,506,507,508,510,511,599,
            # 429, 500, 502, 503, 504
        ],
        method_whitelist=["HEAD", "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"],
        backoff_factor=1
    )

    def __init__(self, mobile, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setattr(self, 'auth', self.bearer_token_auth)
        # self._otp_secrete = base64.b64encode(b'Salted__' + os.urandom(56)).decode('utf-8')
        # self._otp_secrete = base64.b64encode(b'Salted__' + secrets.token_bytes(56)).decode('utf-8')
        self.mobile = mobile

        self.headers.update({
            # 'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:74.0) Gecko/20100101 Firefox/74.0',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        }),
        adapter = TimeoutHTTPAdapter(timeout=self.timeout, max_retries=self.retry_obj)
        self.mount('https://', adapter)
        self.mount('http://', adapter)
        self.auth_thread = threading.Thread(
            target=self.fetch_access_token_thread,
            args=(),
            name='AuthThread',
            daemon=True
        )
        self.auth_thread.start()

        self.hooks['response'].append(self.response_hook)

    def bearer_token_auth(self, request):
        if not self.is_access_token_valid:
            self.get_access_token()
        # if self.is_access_token_prefetch_allowed:
        #     self.prefetch_access_token()
        request.headers['Authorization'] = f"Bearer { self._access_token_info['token'] }"
        return request

    def no_auth(self, request):
        return request

    @property
    def is_txn_id_valid(self):
        return  self._txn_info['txn_id'] and datetime.now() < self._txn_info['expires']

    @property
    def is_access_token_valid(self):
        return  self._access_token_info['token'] and datetime.now() < self._access_token_info['expires']

    @property
    def is_access_token_prefetch_allowed(self):
        return not self._access_token_info['token'] or datetime.now() > (self._access_token_info['expires'] - timedelta(seconds=self.TOKEN_PREFETCH_TIME))

    @property
    def storage_url(self):
        return STORAGE_URL_BASE+str(self.mobile)

    def generate_otp(self):
        ret = False
        data = {
            "mobile": self.mobile,
            "secret": self._otp_secrete,
        }
        log.info(f"Requesting OTP with mobile number {self.mobile}")
        response = self.post(
            url=self.api['generate_otp'],
            json=data,
            auth=self.no_auth,
        )
        # log.debug(f"generate_otp response: {response.json()}")
        if response.status_code == 200:
            txn_id = response.json()["txnId"]
            self._txn_info['txn_id']  = txn_id
            self._txn_info['expires'] = datetime.now() + timedelta(seconds=self.TXN_VALID_TILL)
            ret = True

        else:
            log.error("Unable to Create OTP")
            log.error(response.text)
            time.sleep(5)  # Saftey net againt rate limit

        return ret

    def clear_storage_bucket(self):
        log.info("clearing OTP bucket: " + self.storage_url)
        response = self.put(self.storage_url, data={}, auth=self.no_auth,)

    def fetch_otp(self):
        OTP = None
        response = self.get(self.storage_url, auth=self.no_auth,)
        if response:
            # log.debug(f"fetch_otp response: {response.text}")
            if response.status_code == 200:
                log.info(f"OTP SMS (len: {len(response.text)}) is: {response.text}")
                OTP = response.text
                OTP = OTP.replace("Your OTP to register/access CoWIN is ", "")
                OTP = OTP.replace(". It will be valid for 3 minutes. - CoWIN", "")
        if OTP:
            log.info(f"Parsed OTP: {OTP}")
        return OTP

    def validate_otp_and_get_access_token(self, OTP):
        data = {
            "otp": sha256(str(OTP.strip()).encode("utf-8")).hexdigest(),
            "txnId": self._txn_info['txn_id']
        }
        log.info(f"Validating OTP..")

        response = self.post(
            url=self.api['validate_otp'],
            json=data,
            auth=self.no_auth,
        )
        log.debug(f"validate_otp response: {response.json()}")
        if response.status_code == 200:
            data = response.json()
            token = data['token']
            self._access_token_info['token']   = token
            self._access_token_info['expires'] = datetime.now() + timedelta(seconds=self.TOKEN_VALID_TILL)
        else:
            log.error("Unable to Validate OTP")
            log.error(response.text)
            exit(1)
            # return None

        log.info(f"Token Generated: {token}")
        return token

    def _get_access_token(self):
        self.clear_storage_bucket()
        if self.generate_otp():
            time.sleep(10)
            while self.is_txn_id_valid:
                otp = self.fetch_otp()
                if not otp:
                    time.sleep(5)
                    continue
                elif self.validate_otp_and_get_access_token(otp):
                    return True
            else:
                # Hope it won't 500 a little later
                log.error(f"Unable to get access token.")
        time.sleep(5)
        return self._get_access_token()

    def get_access_token(self):
        self.FORCE_TOKEN_PREFETCH = True
        while not self.is_access_token_valid:
            time.sleep(3)


    def fetch_access_token_thread(self):
        while not self._thread_stop_f:
            if self.FORCE_TOKEN_PREFETCH or self.is_access_token_prefetch_allowed:
                try:
                    self._get_access_token()
                except Exception as exc:
                    log.error(exc)
                    time.sleep(5)
                else:
                    self.FORCE_TOKEN_PREFETCH = False
            else:
                log.debug('Sleeping...')
                time.sleep(5)

    def response_hook(self, res, *args, **kwargs):
        if not res.request.url.startswith((self.storage_url, *self.api.values()),):
            if res.status_code == 401:
                if res.request.headers.get('REATTEMPT'):
                    res.raise_for_status()
                self.get_access_token()
                req = res.request
                req.headers['REATTEMPT'] = 1
                req = self.auth(req)
                return self.send(req)
        return res

    def __del__(self):
        self._thread_stop_f = True

if __name__ == "__main__":
    pass