import datetime
import zoneinfo
import logging

_LOGGER = logging.getLogger(__name__)

def parse_ws_payload(data):
    """Parse the WS payload and return a dict."""
        
    if "notification" not in data: return
    notification = data["notification"]

    if notification == "Device.stateChanged":
        params = data.get("params", {})
        device_id = params.get("deviceId").replace("{","").replace("}","")
        state_type = params.get("type")
        value = params.get("value")
        value = convert_statetype_value(state_type, value)
        return [{"device_id": device_id, "state_type": state_type, "value": value}]
    elif notification == "Device.updated":
        params = data.get("params", {})
        device_id = params.get("id").replace("{","").replace("}","")
        lastUpdate = params.get("lastUpdate")
        lastUpdate = convert_statetype_value("lastUpdate", lastUpdate)
        return [{"device_id": device_id, "state_type": "lastUpdate", "value": lastUpdate}]
    elif notification == "Circuit.stateChanged":
        params = data.get("params", {})
        device_id = params.get("circuitId").replace("{","").replace("}","")
        state_type = params.get("type")
        value = params.get("value")
        value = convert_statetype_value(state_type, value)
        return [{"device_id": device_id, "state_type": state_type, "value": value}]
    elif notification == "Circuit.edited":
        params = data.get("params", {})
        circuit = params.get("circuit", {})
        circuit_id = circuit.get("id").replace("{","").replace("}","")
        circuitParams = circuit.get("params", {})
        value_automaticMode = convert_statetype_value("automaticMode", str(circuitParams.get("automaticMode")))
        value_valveStaggering = convert_statetype_value("valveStaggering", str(circuitParams.get("valveStaggering")))
        return [{"device_id": circuit_id, "state_type": "automaticMode", "value": value_automaticMode},
                {"device_id": circuit_id, "state_type": "valveStaggering", "value": value_valveStaggering}]
    else: 
        return []

def convert_statetype_value(statetype, value):
    """Convert a value to the correct type based on statetype."""
    if statetype == "lastUpdate":
        try:
            dt = datetime.datetime.fromtimestamp(float(value), tz=datetime.timezone.utc)
            return dt
        except Exception:
            return None
    elif statetype in ("irrigationWasStarted", "valveStatus", "valve2Status", "automaticMode", "valveStaggering"):        
        if isinstance(value, str):
            return value.lower() in ["true", "1", "yes"]
        return bool(value)
    elif statetype in ("solarVoltage"):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    elif statetype in ("moisture", "brightness", "temperature", "duration"):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    else:
        return value