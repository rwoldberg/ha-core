"""Switch support for an LDATA devices."""
import logging

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .ldata_entity import LDATAEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the switch for the breakers."""

    entry = hass.data[DOMAIN][config_entry.entry_id]

    for breaker_id in entry.data["breakers"]:
        breaker_data = entry.data["breakers"][breaker_id]
        switch = LDATASwitch(entry, breaker_data)
        async_add_entities([switch])


class LDATASwitch(LDATAEntity, SwitchEntity):
    """Define the switch for the breaker."""

    def __init__(self, coordinator, data) -> None:
        """Init LDATASwitch."""
        super().__init__(data=data, coordinator=coordinator)
        self._state = None

    @property
    def icon(self) -> str:
        """Return the icon type."""
        return "mdi:electric-switch-closed"

    @property
    def is_on(self):
        """Returns true if the switch is on."""
        if new_data := self.coordinator.data["breakers"][self.breaker_data["id"]]:
            if new_data["state"] == "ManualON":
                self._state = True
            else:
                self._state = False
        return self._state
