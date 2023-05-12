"""Switch support for an LDATA devices."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER_NAME, READ_ONLY, READ_ONLY_DEFAULT
from .ldata_entity import LDATAEntity

_LOGGER = logging.getLogger(LOGGER_NAME)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the switch for the breakers."""

    entry = hass.data[DOMAIN][config_entry.entry_id]

    read_only = config_entry.options.get(
        READ_ONLY,
        config_entry.data.get(
            READ_ONLY, config_entry.data.get(READ_ONLY, READ_ONLY_DEFAULT)
        ),
    )
    if read_only is False:
        for breaker_id in entry.data["breakers"]:
            breaker_data = entry.data["breakers"][breaker_id]
            switch = LDATASwitch(entry, breaker_data)
            async_add_entities([switch])


class LDATASwitch(LDATAEntity, SwitchEntity):
    """Define the switch for the breaker."""

    def __init__(self, coordinator, data) -> None:
        """Init LDATASwitch."""
        super().__init__(data=data, coordinator=coordinator)
        self.breaker_data = data
        self._state = None
        if current_data := self.coordinator.data["breakers"][self.breaker_data["id"]]:
            if current_data["state"] == "ManualON":
                self._state = True
        # Subscribe to updates.
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        try:
            if breakers := self.coordinator.data["breakers"]:
                if new_data := breakers[self.breaker_data["id"]]:
                    if new_data["state"] == "ManualON":
                        self._state = True
                    else:
                        self._state = False
        except Exception:  # pylint: disable=broad-except
            self._state = None
        self.async_write_ha_state()

    @property
    def icon(self) -> str:
        """Return the icon type."""
        if self.is_on is True:
            return "mdi:electric-switch-open"
        return "mdi:electric-switch-closed"

    @property
    def is_on(self) -> bool | None:
        """Returns true if the switch is on."""
        return self._state

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Trip the breaker."""
        await self.coordinator.hass.async_add_executor_job(
            self.coordinator.service.turn_off, self.breaker_data["id"]
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Reset the breaker."""
        _LOGGER.debug("turn_on is not supported!")

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Returns the extra attributes for the breaker."""
        attributes = super().extra_state_attributes
        attributes["panel_id"] = self.breaker_data["panel_id"]

        return attributes
