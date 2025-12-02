import logging
import aiohttp
import json
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from .const import DOMAIN
from .ws_client import WSClient
from .utils import parse_ws_payload

_LOGGER = logging.getLogger(__name__)

# Setup function, called from HA when the integration is loaded
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    host = entry.data.get("host")
    api_key = entry.data.get("api_key")
    _LOGGER.info(f"MIYO Cube wrapper started for device at {host}")

    async def handle_ws_message(msg):
        """Receive ws messages and dispatch updates to entities."""
        _LOGGER.info(f"Received WS message: {msg}")
        payload = parse_ws_payload(msg)
        hass.bus.async_fire(f"{DOMAIN}_update", payload)

    ws_client = WSClient(url=f"ws://{host}:3810", on_message=handle_ws_message, api_key=api_key)
    hass.data[DOMAIN]["ws_client"] = ws_client

    await ws_client.start()

    cube = await async_query_cube(host, api_key)
    if not cube or "uuid" not in cube:
        _LOGGER.error("Failed to connect to MIYO Cube during setup")
        return False

    new_data = dict(entry.data)
    new_data["cube_uuid"] = cube["uuid"]
    hass.config_entries.async_update_entry(entry, data=new_data)

    circuits = await async_query_circuits(host, api_key)

    hass.data[DOMAIN][entry.entry_id] = circuits

    await hass.config_entries.async_forward_entry_setups(entry, ["switch", "sensor", "button", "number", "binary_sensor"])

    return True

# Teardown function, called from HA when the integration is unloaded
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    ws_client = hass.data[DOMAIN].get("ws_client")
    if ws_client:
        await ws_client.stop()
    return True

# Query function to get circuit information from MIYO Cube HTTP API
async def async_query_cube(host: str, api_key: str):
    """Query basic info from the MIYO Cube."""
    url = f"http://{host}/api/System/status?apiKey={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    _LOGGER.error(f"Failed to fetch circuits: HTTP {resp.status}")
                    return None
                data = await resp.json()
                if "params" in data:
                    return data["params"]
                else:
                    _LOGGER.error("No 'params' in cube status response")
                    return None
    except Exception as e:
        _LOGGER.error(f"Error fetching circuits from {host}: {e}")
        return None

# Query function to get circuit information from MIYO Cube HTTP API
async def async_query_circuits(host: str, api_key: str):
    """Query all circuits from the MIYO Cube and extract name, id, sensor (ip, id), and valves (ip, id)."""
    url = f"http://{host}/api/circuit/all?apiKey={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    _LOGGER.error(f"Failed to fetch circuits: HTTP {resp.status}")
                    return None
                data = await resp.json()
    except Exception as e:
        _LOGGER.error(f"Error fetching circuits from {host}: {e}")
        return None

    circuits = []
    try:
        circuits_data = data["params"]["circuits"]
        for circuit_id, circuit in circuits_data.items():
            
            circuitStateTypes = {}
            for stateType in circuit.get("stateTypes", {}).values():
                circuitStateTypes[stateType.get("type")] = stateType.get("value")

            sensorStateTypes = {}
            for stateType in circuit.get("sensorData", {}).get("stateTypes", {}).values():
                sensorStateTypes[stateType.get("type")] = stateType.get("value")

            circuit_info = {
                "id": circuit_id.replace("{", "").replace("}", ""),
                "name": circuit.get("name"),
                "stateTypes": circuitStateTypes,
                "params": circuit.get("params", {}),
                "sensor": {
                    "id": circuit.get("sensorData", {}).get("id"),
                    "ip": circuit.get("sensorData", {}).get("ipv6"),
                    "lastUpdate": circuit.get("sensorData", {}).get("lastUpdate"),
                    "stateTypes": sensorStateTypes
                },                
                "valves": []
            }
            valves = circuit.get("valves", {})
            for valve in valves.values():
                valve_data = valve.get("valveData", {})

                stateTypes = {}
                for stateType in valve_data.get("stateTypes", {}).values():
                    stateTypes[stateType.get("type")] = stateType.get("value")

                circuit_info["valves"].append({
                    "id": valve_data.get("id"),
                    "ip": valve_data.get("ipv6"),
                    "lastUpdate": valve_data.get("lastUpdate"),
                    "hardwareRevision": valve_data.get("hardwareRevision"),
                    "channel": valve.get("channel"),
                    "stateTypes": stateTypes           
                })

            circuits.append(circuit_info)

    except Exception as e:
        _LOGGER.error(f"Error parsing circuits data: {e}")
        return None

    return circuits