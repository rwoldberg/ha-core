"""Switch support for an LDATA devices."""
import logging

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN, SWITCHES
from .ldata_entity import LDATAEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the switch for the breakers."""

    entry = hass.data[DOMAIN][config_entry.entry_id]

    for value in entry.data["breakers"]:
        switch = LDATASwitch(entry, value)
        async_add_entities([switch], True)


class LDATASwitch(LDATAEntity, SwitchEntity):
    """Define the switch for the breaker."""

    def __init__(self, coordinator, data) -> None:
        """Init LDATASwitch."""
        super().__init__(data=data, coordinator=coordinator)
        self._state = None

    @property
    def icon(self):
        """Return the icon type."""
        breaker_type = self.breaker_data["type"]
        if type in SWITCHES:
            return SWITCHES[breaker_type]["icon"]
        _LOGGER.debug("Missing icon for type %s", breaker_type)
        return None

    @property
    def is_on(self):
        """Returns true if the switch is on."""
        for value in self.coordinator.data["breakers"]:
            if value["id"] == self.breaker_data["id"]:
                if value["state"] == "ManualON":
                    self._state = True
                self._state = False
                break
        return self._state
