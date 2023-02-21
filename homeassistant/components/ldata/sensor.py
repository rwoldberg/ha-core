"""Support for power sensors in LDATA devices."""
from __future__ import annotations

import time
from typing import cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt

from .const import DATA_UPDATED, DOMAIN
from .ldata_entity import LDATAEntity
from .ldata_uppdate_coordinator import LDATAUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the power and kilowatt sendors for the breakers."""

    entry = hass.data[DOMAIN][config_entry.entry_id]

    for breaker_id in entry.data["breakers"]:
        breaker_data = entry.data["breakers"][breaker_id]
        usage_sensor = LDATATotalUsageSensor(entry, breaker_data)
        async_add_entities([usage_sensor])
        power_sensor = LDATAPowerSensor(entry, breaker_data)
        async_add_entities([power_sensor])


class LDATATotalUsageSensor(LDATAEntity, RestoreEntity, SensorEntity):
    """Sensor that reads attributes of a LDATA device."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, coordinator: LDATAUpdateCoordinator, data) -> None:
        """Init AttributeSensor."""
        super().__init__(data=data, coordinator=coordinator)
        self._state = 0.0
        self.last_update_time = 0.0
        self.previous_value = 0.0
        self.last_update_date = dt.now()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        last_update_date = dt.as_local(state.last_updated)
        current_date = dt.now()
        # Only load running total if the last update day is same as today
        if (
            (last_update_date.day == current_date.day)
            and (last_update_date.month == current_date.month)
            and (last_update_date.year == current_date.year)
        ):
            if state.state is not None and state.state != "unknown":
                self._state = self._state + float(state.state)

        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )
        # Subscribe to updates.
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        if new_data := self.coordinator.data["breakers"][self.breaker_data["id"]]:
            current_value = new_data["power"]

            # Save the current date and time
            current_time = time.time()
            current_date = dt.now()
            # Only update if we have a previous update
            if self.last_update_time > 0:
                # Clear the running total if the last update date and now are not the same day
                if (
                    (self.last_update_date.day != current_date.day)
                    or (self.last_update_date.month != current_date.month)
                    or (self.last_update_date.year != current_date.year)
                ):
                    self._state = 0
                # Power usage is hale the previous plus current power consumption in kilowatts
                power = ((self.previous_value + current_value) / 2) / 1000
                # How long has it been since the last update in hours
                time_span = (current_time - self.last_update_time) / 3600
                # Update our running total
                self._state = self._state + (power * time_span)
            # Save the current values
            self.last_update_time = current_time
            self.previous_value = current_value
            self.last_update_date = current_date
            self.async_write_ha_state()

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    @property
    def name_suffix(self) -> str | None:
        """Suffix to append to the LDATA device's name."""
        return "Total Daily Energy"

    @property
    def unique_id_suffix(self) -> str | None:
        """Suffix to append to the LDATA device's unique ID."""
        return "todaymw"

    def convert_state(self, value: StateType) -> StateType:
        """Convert native state to a value appropriate for the sensor."""
        return round(cast(float, value), 2)

    @property
    def native_value(self) -> StateType:
        """Return the used kilowatts of the device."""
        return round(self._state, 2)


class LDATAPowerSensor(LDATAEntity, SensorEntity):
    """Sensor that reads attributes of a LDATA device."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator: LDATAUpdateCoordinator, data) -> None:
        """Init AttributeSensor."""
        super().__init__(data=data, coordinator=coordinator)
        self._state = float(self.breaker_data["power"])
        # Subscribe to updates.
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        if new_data := self.coordinator.data["breakers"][self.breaker_data["id"]]:
            self._state = new_data["power"]
        self.async_write_ha_state()

    @property
    def name_suffix(self) -> str | None:
        """Suffix to append to the LDATA device's name."""
        return "Watts"

    @property
    def unique_id_suffix(self) -> str | None:
        """Suffix to append to the LDATA device's unique ID."""
        return "_watts"

    def convert_state(self, value: StateType) -> StateType:
        """Convert native state to a value appropriate for the sensor."""
        return round(cast(float, value), 2)

    @property
    def native_value(self) -> StateType:
        """Return the power value."""
        return round(self._state, 2)
