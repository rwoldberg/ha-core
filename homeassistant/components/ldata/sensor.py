"""Support for power sensors in LDATA devices."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import logging
import time

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt

from .const import DATA_UPDATED, DOMAIN, LOGGER_NAME
from .ldata_entity import LDATAEntity
from .ldata_uppdate_coordinator import LDATAUpdateCoordinator

_LOGGER = logging.getLogger(LOGGER_NAME)


@dataclass
class SensorDescription(SensorEntityDescription):
    """SensorEntityDescription for LDATA entities."""

    unique_id_suffix: str | None = None


SENSOR_TYPES = (
    SensorDescription(  # index=0
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        name="Watts",
        key="power",
        unique_id_suffix="_watts",
    ),
    SensorDescription(  # index=1
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        name="Volts",
        key="voltage",
        unique_id_suffix="_volts",
    ),
    SensorDescription(  # index=2
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        name="Amps",
        key="current",
        unique_id_suffix="_amps",
    ),
    SensorDescription(  # index=3
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        name="Frequency",
        key="frequency",
        unique_id_suffix="_hz",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the power and kilowatt sensors for the breakers."""

    entry = hass.data[DOMAIN][config_entry.entry_id]

    for breaker_id in entry.data["breakers"]:
        breaker_data = entry.data["breakers"][breaker_id]
        usage_sensor = LDATADailyUsageSensor(entry, breaker_data)
        async_add_entities([usage_sensor])
        power_sensor = LDATAOutputSensor(entry, breaker_data, SENSOR_TYPES[0])
        async_add_entities([power_sensor])
        power_sensor = LDATAOutputSensor(entry, breaker_data, SENSOR_TYPES[1])
        async_add_entities([power_sensor])
        power_sensor = LDATAOutputSensor(entry, breaker_data, SENSOR_TYPES[2])
        async_add_entities([power_sensor])
        power_sensor = LDATAOutputSensor(entry, breaker_data, SENSOR_TYPES[3])
        async_add_entities([power_sensor])
    for panel in entry.data["panels"]:
        entity_data = {}
        entity_data["id"] = panel["serialNumber"]
        entity_data["name"] = panel["name"]
        entity_data["serialNumber"] = panel["serialNumber"]
        entity_data["model"] = panel["model"]
        entity_data["hardware"] = "LDATA"
        entity_data["firmware"] = panel["firmware"]
        entity_data["poles"] = 2
        total_sensor = LDATATotalUsageSensor(
            entry, entity_data, SENSOR_TYPES[0], average=False, which_leg="both"
        )
        async_add_entities([total_sensor])
        total_sensor = LDATATotalUsageSensor(
            entry, entity_data, SENSOR_TYPES[2], average=False, which_leg="both"
        )
        async_add_entities([total_sensor])
        total_sensor = LDATATotalUsageSensor(
            entry, entity_data, SENSOR_TYPES[3], average=True, which_leg="both"
        )
        async_add_entities([total_sensor])
        entity_data = copy.deepcopy(entity_data)
        entity_data["poles"] = 1
        entity_data["position"] = 1
        total_sensor = LDATATotalUsageSensor(
            entry, entity_data, SENSOR_TYPES[0], average=False, which_leg="1"
        )
        async_add_entities([total_sensor])
        total_sensor = LDATATotalUsageSensor(
            entry, entity_data, SENSOR_TYPES[2], average=False, which_leg="1"
        )
        async_add_entities([total_sensor])
        entity_data = copy.deepcopy(entity_data)
        entity_data["position"] = 3
        total_sensor = LDATATotalUsageSensor(
            entry, entity_data, SENSOR_TYPES[0], average=False, which_leg="2"
        )
        async_add_entities([total_sensor])
        total_sensor = LDATATotalUsageSensor(
            entry, entity_data, SENSOR_TYPES[2], average=False, which_leg="2"
        )
        async_add_entities([total_sensor])


class LDATADailyUsageSensor(LDATAEntity, RestoreEntity, SensorEntity):
    """Sensor that tracks daily usage for an LDATA device."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, coordinator: LDATAUpdateCoordinator, data) -> None:
        """Init sensor."""
        super().__init__(data=data, coordinator=coordinator)
        self.breaker_data = data
        self._state = None
        self.last_update_time = 0.0
        self.previous_value = 0.0
        self.last_update_date = dt.now()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        last_state = await self.async_get_last_state()
        await super().async_added_to_hass()
        if not last_state:
            return
        last_update_date = dt.as_local(last_state.last_updated)
        current_date = dt.now()
        new_state = 0.0
        # Only load running total if the last update day is same as today
        if (
            (last_update_date.day == current_date.day)
            and (last_update_date.month == current_date.month)
            and (last_update_date.year == current_date.year)
        ):
            if self._state is not None:
                new_state = float(self._state) + float(last_state.state)
            else:
                try:
                    new_state = float(last_state.state)
                except Exception:  # pylint: disable=broad-except
                    new_state = 0.0
        self._state = new_state  # type: ignore[assignment]
        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )
        # Subscribe to updates.
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))

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

    @property
    def native_value(self) -> StateType:
        """Return the used kilowatts of the device."""
        if self._state is not None:
            return round(self._state, 2)
        return None

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        try:
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
        except Exception:  # pylint: disable=broad-except
            self._state = None
        self.async_write_ha_state()


class LDATATotalUsageSensor(LDATAEntity, SensorEntity):
    """Sensor that reads all outputs from all LDATA devices based on the passed in description."""

    entity_description: SensorDescription

    def __init__(
        self,
        coordinator: LDATAUpdateCoordinator,
        data,
        description: SensorDescription,
        average: bool,
        which_leg: str,
    ) -> None:
        """Init sensor."""
        self.entity_description = description
        self.leg_to_total = which_leg
        super().__init__(data=data, coordinator=coordinator)
        self.is_average = average
        self._state = self.total_values()
        # Subscribe to updates.
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))

    def total_values(self) -> float:
        """Total value for all breakers."""
        total = 0.0
        count = 0
        for breaker_id in self.coordinator.data["breakers"]:
            breaker_data = self.coordinator.data["breakers"][breaker_id]
            if breaker_data["panel_id"] == self.entity_data["serialNumber"]:
                if self.leg_to_total == "both":
                    total += float(breaker_data[self.entity_description.key])
                else:
                    total += float(
                        breaker_data[self.entity_description.key + self.leg_to_total]
                    )
                count += 1
        if self.is_average is True:
            return total / count
        return total

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        self._state = self.total_values()
        self.async_write_ha_state()

    @property
    def name_suffix(self) -> str | None:
        """Suffix to append to the LDATA device's name."""
        if (self.entity_description.name is not None) and (self.leg_to_total != "both"):
            return str(self.entity_description.name) + " Leg " + self.leg_to_total
        return self.entity_description.name

    @property
    def unique_id_suffix(self) -> str | None:
        """Suffix to append to the LDATA device's unique ID."""
        if (self.entity_description.name is not None) and (self.leg_to_total != "both"):
            return (
                "_leg_"
                + self.leg_to_total
                + str(self.entity_description.unique_id_suffix)
            )
        return self.entity_description.unique_id_suffix

    @property
    def native_value(self) -> StateType:
        """Return the power value."""
        return round(self._state, 2)


class LDATAOutputSensor(LDATAEntity, SensorEntity):
    """Sensor that reads an output based on the passed in description from an LDATA device."""

    entity_description: SensorDescription

    def __init__(
        self, coordinator: LDATAUpdateCoordinator, data, description: SensorDescription
    ) -> None:
        """Init sensor."""
        self.entity_description = description
        super().__init__(data=data, coordinator=coordinator)
        self.breaker_data = data
        self._state = float(self.breaker_data[self.entity_description.key])
        # Subscribe to updates.
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        try:
            if breakers := self.coordinator.data["breakers"]:
                if new_data := breakers[self.breaker_data["id"]]:
                    self._state = new_data[self.entity_description.key]
        except Exception:  # pylint: disable=broad-except
            self._state = None
        self.async_write_ha_state()

    @property
    def name_suffix(self) -> str | None:
        """Suffix to append to the LDATA device's name."""
        return self.entity_description.name

    @property
    def unique_id_suffix(self) -> str | None:
        """Suffix to append to the LDATA device's unique ID."""
        return self.entity_description.unique_id_suffix

    @property
    def native_value(self) -> StateType:
        """Return the power value."""
        return round(self._state, 2)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Returns the extra attributes for the breaker."""
        attributes = super().extra_state_attributes
        attributes["panel_id"] = self.breaker_data["panel_id"]

        return attributes
