"""Defines a binary sensor for an LDATA entity."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .ldata_entity import LDATAEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the binary sensor for the breakers."""

    entry = hass.data[DOMAIN][config_entry.entry_id]

    for breaker_id in entry.data["breakers"]:
        breaker_data = entry.data["breakers"][breaker_id]
        sensor = LDATABinarySensor(entry, breaker_data)
        async_add_entities([sensor])


class LDATABinarySensor(LDATAEntity, BinarySensorEntity):
    """LDATA binary sensor class."""

    def __init__(self, coordinator, data) -> None:
        """Init LDATABinarySensor."""
        super().__init__(data=data, coordinator=coordinator)
        self._state = None
        if current_data := self.coordinator.data["breakers"][self.breaker_data["id"]]:
            if current_data["state"] == "ManualON":
                self._state = True
        # Subscribe to updates.
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        if new_data := self.coordinator.data["breakers"][self.breaker_data["id"]]:
            if new_data["state"] == "ManualON":
                self._state = True
            else:
                self._state = False
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Returns the extra attributes for the breaker."""
        return self.breaker_data

    @property
    def is_on(self) -> bool | None:
        """Returns true if the breaker is on."""
        return self._state
