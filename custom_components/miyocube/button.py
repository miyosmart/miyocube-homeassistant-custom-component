from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.core import callback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from .const import DOMAIN
import logging
import datetime
from .utils import convert_statetype_value, camel_to_snake

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor entity from config entry."""    

    circuits_data = hass.data[DOMAIN][entry.entry_id]
    entities = []
    cube_id = entry.data.get('cube_uuid')

    for circuit in circuits_data:
        
        circuit_id      = circuit["id"]
        circuit_name    = f"{circuit["name"]}"

        entities.append(MiyoButton(hass, cube_id, circuit_id, circuit_id, "circuit", circuit_name, "startIrrigation"))
        entities.append(MiyoButton(hass, cube_id, circuit_id, circuit_id, "circuit", circuit_name, "stopIrrigation"))

    async_add_entities(entities)

    

class MiyoButton(ButtonEntity):
    """Button receiving updates via WS."""

    def __init__(self, hass, cube_id: str, circuit_id: str, device_id: str, device_type: str, device_name: str, state: str):
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
        self._circuit_id        = circuit_id

        self._attr_unique_id    = f"{device_id}_{state}"
        self._attr_has_entity_name = True
        self._attr_translation_key = camel_to_snake(state)

    #
    #  ---------- HA Entity Properties ----------
    #

    @property
    def native_value(self):
        return self._state

    @property
    def device_class(self):
        return "button"

    @property
    def icon(self):
        if self._statetype == "startIrrigation":
            return "mdi:water"
        elif self._statetype == "stopIrrigation":
            return "mdi:water-off"
        else:
            return "mdi:sensor"

    @property
    def device_info(self):
        """Associate this entity with a HA device."""
        device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "translation_key": camel_to_snake(self._device_type)    ,
            "translation_placeholders": {"id": self._device_name},
            "manufacturer": "MIYO",
            "model": "Smart Irrigation"
        }

        if self._device_type != "circuit":
            device_info["via_device"] = (DOMAIN, self._circuit_id)
        
        return device_info

    #
    #  ---------- WS Handling ----------
    #

    async def async_press(self, **kwargs):
        """Handle the button press."""


        if self._statetype == "startIrrigation":
            duration = None

            entity_registry = async_get_entity_registry(self.hass)
            entry = entity_registry.async_get_entity_id("number", DOMAIN, self._circuit_id + "_duration")
            
            duration_state = None
            if entry:
                duration_state = self.hass.states.get(entry)
            
            if duration_state is not None and duration_state.state != "unknown":
                duration = int(float(duration_state.state))

            if duration is not None:
                ws_client = self.hass.data[DOMAIN]["ws_client"]
                await ws_client.send({
                    "method": "Circuit.irrigation",            
                    "params": {
                        "circuitId": self._circuit_id,
                        "mode": "start",
                        "duration": duration
                    }
                })
        elif self._statetype == "stopIrrigation":
        
            ws_client = self.hass.data[DOMAIN]["ws_client"]            
            await ws_client.send({
                "method": "Circuit.irrigation",            
                "params": {
                    "circuitId": self._circuit_id,
                    "mode": "stop"
                }
            })
        
