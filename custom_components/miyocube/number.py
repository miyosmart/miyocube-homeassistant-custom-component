from __future__ import annotations
from homeassistant.components.number import NumberEntity
from homeassistant.core import callback
from homeassistant.const import UnitOfTime
from .const import DOMAIN
from .utils import convert_statetype_value, camel_to_snake
import logging
import datetime

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor entity from config entry."""    

    circuits_data = hass.data[DOMAIN][entry.entry_id]
    entities = []
    cube_id = entry.data.get('cube_uuid')

    for circuit in circuits_data:
        
        circuit_id      = circuit["id"]
        circuit_name    = f"{circuit["name"]}"

        entities.append(MiyoSlider(hass, cube_id, circuit_id, circuit_id, "circuit", circuit_name, "duration", 1))

    async_add_entities(entities)

    

class MiyoSlider(NumberEntity):
    """Slider receiving updates via WS."""

    def __init__(self, hass, cube_id: str, circuit_id: str, device_id: str, device_type: str, device_name: str, state: str, init_value = None):
        """
        Parameters:
            hass: HomeAssistant core object
            cube_id: ID of the Miyo cube
            circuit_id: ID of the circuit
            device_id: ID of the sensor device
            device_type: Type of the device (e.g., "moistureOutdoor", "circuit", "valve")
            deviceName: Name of the device
            state: Type of state this sensor represents (e.g., "moisture", "temperature")            
        """
        self.hass = hass
        self._device_id         = device_id
        self._statetype         = state
        self._device_name       = device_name
        self._device_type       = device_type
        self._state             = None
        self._circuit_id        = circuit_id

        self._attr_unique_id    = f"{device_id}_{state}"
        self._attr_has_entity_name = True
        self._attr_translation_key = camel_to_snake(state)
        
        self._attr_native_min_value = 1
        self._attr_native_max_value = 60
        self._attr_native_step = 1

        if init_value is not None: 
            self._state = convert_statetype_value(self._statetype, init_value)

    #
    #  ---------- HA Entity Properties ----------
    #
    @property
    def native_unit_of_measurement(self):        
        if self._statetype == "duration":
            return UnitOfTime.MINUTES
        return None

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state is True

    @property
    def native_value(self):
        return self._state

    @property
    def device_class(self):
        return "switch"

    @property
    def icon(self):
        if self._statetype == "duration":
            return "mdi:timelapse"
        else:
            return "mdi:sensor"

    @property
    def device_info(self):
        """Associate this entity with a HA device."""
        device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "translation_key": camel_to_snake(self._device_type),
            "translation_placeholders": {"id": self._device_name},
            "manufacturer": "MIYO",
            "model": "Smart Irrigation"
        }

        if self._device_type != "circuit":
            device_info["via_device"] = (DOMAIN, self._circuit_id)
        
        return device_info

    async def async_set_native_value(self, value: float) -> None:
        """Handle slider value change from the UI."""
        self._state = value
        self.async_write_ha_state()