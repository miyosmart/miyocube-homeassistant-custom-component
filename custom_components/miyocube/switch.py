from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
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

        entities.append(MiyoSwitch(hass, cube_id, circuit_id, circuit_id, "circuit", circuit_name, "automaticMode", circuit["params"].get("automaticMode", None)))
        entities.append(MiyoSwitch(hass, cube_id, circuit_id, circuit_id, "circuit", circuit_name, "valveStaggering", circuit["params"].get("valveStaggering", None)))

    async_add_entities(entities)

    

class MiyoSwitch(SwitchEntity):
    """Switch receiving updates via WS."""

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

        if init_value is not None: 
            self._state = convert_statetype_value(self._statetype, init_value)

    #
    #  ---------- HA Entity Properties ----------
    #

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
        if self._statetype == "automaticMode":
            return "mdi:robot"
        elif self._statetype == "valveStaggering":
            return "mdi:stairs"
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

    #
    #  ---------- WS Handling ----------
    #
    @callback
    async def _handle_update(self, event):
        updates = event.data
        for data in updates:
            if "device_id" in data and "state_type" in data and "value" in data:
                device_id = data["device_id"]
                state_type = data["state_type"]
                value = data["value"]

                if device_id == self._device_id and state_type == self._statetype:
                    self._state = value
                    self.async_write_ha_state()
        

    async def async_added_to_hass(self):
        """Subscribe to WS event when entity is added."""
        self._unsub = self.hass.bus.async_listen(f"{DOMAIN}_update", self._handle_update)

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        ws_client = self.hass.data[DOMAIN]["ws_client"]
        await ws_client.send({
            "method": "Circuit.edit",            
            "params": {
                "circuitId": self._circuit_id,
                "state_type": self._statetype,
                self._statetype: True
            }
        })

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        ws_client = self.hass.data[DOMAIN]["ws_client"]
        await ws_client.send({
            "method": "Circuit.edit",            
            "params": {
                "circuitId": self._circuit_id,
                "state_type": self._statetype,
                self._statetype: False
            }
        })

    async def async_will_remove_from_hass(self):
        """Unsubscribe from WS event when entity is removed."""
        if hasattr(self, "_unsub") and self._unsub is not None:
            self._unsub()
            self._unsub = None