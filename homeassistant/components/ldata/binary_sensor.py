"""Defines a binary sensor for an LDATA entity."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .ldata_entity import LDATAEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the binary sensor for the breakers."""

    entry = hass.data[DOMAIN][config_entry.entry_id]

    for breaker_id in entry.data["breakers"]:
        breaker_data = entry.data["breakers"][breaker_id]
        if breaker_data["model"] is not None and breaker_data["model"] != "":
            sensor = LDATABinarySensor(entry, breaker_data)
            async_add_entities([sensor])


class LDATABinarySensor(LDATAEntity, BinarySensorEntity):
    """LDATA binary sensor class."""

    def __init__(self, coordinator, data) -> None:
        """Init LDATABinarySensor."""
        super().__init__(data=data, coordinator=coordinator)
        self._state = None

    @property
    def extra_state_attributes(self):
        """Returns the extra attributes for the breaker."""
        return self.breaker_data

    @property
    def is_on(self):
        """Returns true if the breaker is on."""
        if new_data := self.coordinator.data["breakers"][self.breaker_data["id"]]:
            if new_data["state"] == "ManualON":
                self._state = True
            else:
                self._state = False
        return self._state
