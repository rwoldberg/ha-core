"""The LDATAService object."""
import logging

import requests

from .const import _LEG1_POSITIONS, LOGGER_NAME, THREE_PHASE, THREE_PHASE_DEFAULT

defaultHeaders = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "host": "my.leviton.com",
}

_LOGGER = logging.getLogger(LOGGER_NAME)


class LDATAService:
    """The LDATAService object."""

    def __init__(self, username, password, entry) -> None:
        """Init LDATAService."""
        self.username = username
        self.password = password
        self.entry = entry
        self.auth_token = ""
        self.userid = ""
        self.account_id = ""
        self.residence_id = ""

    def clear_tokens(self) -> None:
        """Clear the tokens to force a re-login."""
        self.auth_token = ""
        self.userid = ""
        self.account_id = ""
        self.residence_id = ""

    def auth(self) -> bool:
        """Authenticate to the server."""
        headers = {**defaultHeaders}
        data = {"email": self.username, "password": self.password}
        # Try logging in 3 times due to controller timeout
        login = 0
        while login < 3:
            result = requests.post(
                "https://my.leviton.com/api/Person/login?include=user",
                headers=headers,
                json=data,
                timeout=15,
            )
            _LOGGER.debug(
                "Authorization result %d: %s", result.status_code, result.text
            )

            if result.status_code == 200:
                self.auth_token = result.json()["id"]
                self.userid = result.json()["userId"]
                return True
            login += 1

        return False

    def get_residential_account(self) -> bool:
        """Get the Residential Account for the user."""
        headers = {**defaultHeaders}
        headers["authorization"] = self.auth_token
        url = f"https://my.leviton.com/api/Person/{self.userid}/residentialPermissions"

        try:
            result = requests.get(
                url,
                headers=headers,
                timeout=15,
            )
            _LOGGER.debug(
                "Get Residential Account result %d: %s", result.status_code, result.text
            )
            result_json = result.json()
            if result.status_code == 200 and len(result_json) > 0:
                self.account_id = result_json[0]["residentialAccountId"]
                return True
            _LOGGER.exception("Unable to get Residential Account!")
            self.clear_tokens()
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Unable to get Residential Account! %s", ex)
            self.clear_tokens()

        return False

    def get_residence(self) -> bool:
        """Get the Residential Account for the user."""
        headers = {**defaultHeaders}
        headers["authorization"] = self.auth_token
        url = "https://my.leviton.com/api/ResidentialAccounts/{}/residences".format(
            self.account_id
        )
        try:
            result = requests.get(
                url,
                headers=headers,
                timeout=15,
            )
            _LOGGER.debug(
                "Get Residence Account result %d: %s", result.status_code, result.text
            )
            result_json = result.json()
            if result.status_code == 200 and len(result_json) > 0:
                self.residence_id = result_json[0]["id"]
                return True
            _LOGGER.exception("Unable to get Residence!")
            self.clear_tokens()
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Unable to get Residence! %s", ex)
            self.clear_tokens()
        return False

    def get_Whems_breakers(self, panel_id: str) -> object:
        """Get the whemns modules for the residence."""
        headers = {**defaultHeaders}
        headers["authorization"] = self.auth_token
        headers["filter"] = "{}"
        url = f"https://my.leviton.com/api/IotWhems/{panel_id}/residentialBreakers"
        try:
            result = requests.get(
                url,
                headers=headers,
                timeout=15,
            )
            _LOGGER.debug(
                "Get WHEMS breakers result %d: %s", result.status_code, result.text
            )
            if result.status_code == 200:
                return result.json()
            _LOGGER.exception("Unable to WHEMS breakers!")
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Unable to get WHEMS breakers! %s", ex)
            self.clear_tokens()

        return None

    def get_iotWhemsPanels(self) -> object:
        """Get the whemns modules for the residence."""
        headers = {**defaultHeaders}
        headers["authorization"] = self.auth_token
        headers["filter"] = "{}"
        url = f"https://my.leviton.com/api/Residences/{self.residence_id}/iotWhems"
        try:
            result = requests.get(
                url,
                headers=headers,
                timeout=15,
            )
            _LOGGER.debug(
                "Get WHEMS Panels result %d: %s", result.status_code, result.text
            )

            if result.status_code == 200:
                returnPanels = result.json()
                for panel in returnPanels:
                    panel["ModuleType"] = "WHEMS"
                    # Make the data look like an LDATA module
                    panel["rmsVoltage"] = panel["rmsVoltageA"]
                    panel["rmsVoltage2"] = panel["rmsVoltageB"]
                    panel["updateVersion"] = panel["version"]
                    panel["residentialBreakers"] = self.get_Whems_breakers(panel["id"])
                return returnPanels
            _LOGGER.exception("Unable to get WHEMS Panels!")
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Unable to get WHEMS Panels! %s", ex)
            self.clear_tokens()
        return None

    def get_ldata_panels(self) -> object:
        """Get the breaker panels for the residence."""
        headers = {**defaultHeaders}
        headers["authorization"] = self.auth_token
        headers["filter"] = '{"include":["residentialBreakers"]}'
        url = (
            "https://my.leviton.com/api/Residences/{}/residentialBreakerPanels".format(
                self.residence_id
            )
        )
        try:
            result = requests.get(
                url,
                headers=headers,
                timeout=15,
            )
            _LOGGER.debug("Get Panels result %d: %s", result.status_code, result.text)

            if result.status_code == 200:
                returnPanels = result.json()
                for panel in returnPanels:
                    panel["ModuleType"] = "LDATA"
                return returnPanels
            _LOGGER.exception("Unable to get Panels!")
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Unable to get Panels! %s", ex)
            self.clear_tokens()

        return None

    def put_residential_breaker_panels(self, panel_id: str, panel_type: str) -> None:
        """Call PUT  on the ResidentialBreakerPanels API this must be done to force an update of the power values."""
        # https://my.leviton.com/api/IotWhems/1000_002F_A3B4
        if panel_type == "LDATA":
            url = f"https://my.leviton.com/api/ResidentialBreakerPanels/{panel_id}"
        else:
            url = f"https://my.leviton.com/api/IotWhems/{panel_id}"
        headers = {**defaultHeaders}
        headers["authorization"] = self.auth_token
        data = {"bandwidth": 1}
        requests.put(
            url,
            headers=headers,
            json=data,
            timeout=15,
        )

    def turn_off(self, breaker_id):
        """Turn off a breaker."""
        # Call PUT on the ResidentialBreakerPanels/{breaker_id}.  The data is remoteTrip set to true, this will trip the breaker.
        url = f"https://my.leviton.com/api/ResidentialBreakers/{breaker_id}"
        headers = {**defaultHeaders}
        headers["authorization"] = self.auth_token
        headers[
            "referer"
        ] = f"https://my.leviton.com/home/residential-breakers/{breaker_id}/settings"
        data = {"remoteTrip": True}
        result = requests.put(
            url,
            headers=headers,
            json=data,
            timeout=15,
        )
        return result

    def none_to_zero(self, value) -> float:
        """Convert a value to a float and replace None with 0.0."""
        result = 0.0
        if value is None:
            return result
        try:
            result = float(value)
        except Exception:  # pylint: disable=broad-except
            result = 0.0
        return result

    def status(self):
        """Get the breakers from the API."""
        # Make sure we are logged in.
        three_phase = self.entry.options.get(
            THREE_PHASE, self.entry.data.get(THREE_PHASE, THREE_PHASE_DEFAULT)
        )
        if self.auth_token is None or self.auth_token == "":
            _LOGGER.debug("Not authenticated yet!")
            self.auth()
        if self.auth_token is None or self.auth_token == "":
            return
        # Make sure we have a residential Account
        if self.account_id is None or self.account_id == "":
            _LOGGER.debug("Get Account ID!")
            self.get_residential_account()
        if self.account_id is None or self.account_id == "":
            return
        # Lookup the residential id from the account.
        if self.residence_id is None or self.residence_id == "":
            _LOGGER.debug("Get Residence ID!")
            self.get_residence()
        if self.residence_id is None or self.residence_id == "":
            return
        # Get the breaker panels.
        panels_json = self.get_ldata_panels()
        whems_panels_json = self.get_iotWhemsPanels()
        if panels_json is None:
            panels_json = whems_panels_json
        elif whems_panels_json is not None:
            for panel in whems_panels_json:
                panels_json.append(panel)
        status_data = {}
        breakers = {}
        panels = []
        if panels_json is not None:
            for panel in panels_json:
                self.put_residential_breaker_panels(panel["id"], panel["ModuleType"])
                panel_data = {}
                panel_data["firmware"] = panel["updateVersion"]
                panel_data["model"] = panel["model"]
                panel_data["id"] = panel["id"]
                panel_data["name"] = panel["name"]
                panel_data["serialNumber"] = panel["id"]
                if three_phase is False:
                    panel_data["voltage"] = (
                        float(panel["rmsVoltage"]) + float(panel["rmsVoltage2"])
                    ) / 2.0
                else:
                    panel_data["voltage"] = (
                        float(panel["rmsVoltage"]) * 0.866025403784439
                    ) + (float(panel["rmsVoltage2"]) * 0.866025403784439)
                panel_data["voltage1"] = float(panel["rmsVoltage"])
                panel_data["voltage2"] = float(panel["rmsVoltage2"])
                panels.append(panel_data)
                for breaker in panel["residentialBreakers"]:
                    if (
                        breaker["model"] is not None
                        and breaker["model"] != "NONE-2"
                        and breaker["model"] != "NONE-1"
                    ):
                        breaker_data = {}
                        breaker_data["panel_id"] = panel["id"]
                        breaker_data["rating"] = breaker["currentRating"]
                        breaker_data["position"] = breaker["position"]
                        breaker_data["name"] = breaker["name"]
                        breaker_data["state"] = breaker["currentState"]
                        breaker_data["id"] = breaker["id"]
                        breaker_data["model"] = breaker["model"]
                        breaker_data["poles"] = breaker["poles"]
                        breaker_data["serialNumber"] = breaker["serialNumber"]
                        breaker_data["hardware"] = breaker["hwVersion"]
                        breaker_data["firmware"] = breaker["firmwareVersionMeter"]
                        breaker_data["power"] = self.none_to_zero(
                            breaker["power"]
                        ) + self.none_to_zero(breaker["power2"])
                        if (three_phase is False) or (breaker["poles"] == 1):
                            breaker_data["voltage"] = self.none_to_zero(
                                breaker["rmsVoltage"]
                            ) + self.none_to_zero(breaker["rmsVoltage2"])
                        else:
                            breaker_data["voltage"] = (
                                self.none_to_zero(breaker["rmsVoltage"])
                                * 0.866025403784439
                            ) + (
                                self.none_to_zero(breaker["rmsVoltage2"])
                                * 0.866025403784439
                            )

                        breaker_data["current"] = self.none_to_zero(
                            breaker["rmsCurrent"]
                        ) + self.none_to_zero(breaker["rmsCurrent2"])
                        if breaker["poles"] == 2:
                            breaker_data["frequency"] = (
                                self.none_to_zero(breaker["lineFrequency"])
                                + self.none_to_zero(breaker["lineFrequency2"])
                            ) / 2.0
                        else:
                            breaker_data["frequency"] = self.none_to_zero(
                                breaker["lineFrequency"]
                            )
                        if breaker["position"] in _LEG1_POSITIONS:
                            breaker_data["leg"] = 1
                            breaker_data["power1"] = self.none_to_zero(breaker["power"])
                            breaker_data["power2"] = self.none_to_zero(
                                breaker["power2"]
                            )
                            breaker_data["voltage1"] = self.none_to_zero(
                                breaker["rmsVoltage"]
                            )
                            breaker_data["voltage2"] = self.none_to_zero(
                                breaker["rmsVoltage2"]
                            )
                            breaker_data["current1"] = self.none_to_zero(
                                breaker["rmsCurrent"]
                            )
                            breaker_data["current2"] = self.none_to_zero(
                                breaker["rmsCurrent2"]
                            )
                            breaker_data["frequency1"] = self.none_to_zero(
                                breaker["lineFrequency"]
                            )
                            breaker_data["frequency2"] = self.none_to_zero(
                                breaker["lineFrequency2"]
                            )
                        else:
                            breaker_data["leg"] = 2
                            breaker_data["power1"] = self.none_to_zero(
                                breaker["power2"]
                            )
                            breaker_data["power2"] = self.none_to_zero(breaker["power"])
                            breaker_data["voltage1"] = self.none_to_zero(
                                breaker["rmsVoltage2"]
                            )
                            breaker_data["voltage2"] = self.none_to_zero(
                                breaker["rmsVoltage"]
                            )
                            breaker_data["current1"] = self.none_to_zero(
                                breaker["rmsCurrent2"]
                            )
                            breaker_data["current2"] = self.none_to_zero(
                                breaker["rmsCurrent"]
                            )
                            breaker_data["frequency1"] = self.none_to_zero(
                                breaker["lineFrequency2"]
                            )
                            breaker_data["frequency2"] = self.none_to_zero(
                                breaker["lineFrequency"]
                            )
                        # Add the breaker to the list.
                        breakers[breaker["id"]] = breaker_data

        status_data["breakers"] = breakers
        status_data["panels"] = panels

        return status_data
