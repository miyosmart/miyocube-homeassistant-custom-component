import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_API_KEY = "api_key"

# Function to discover MIYO Cube on the network via upnp/ssdp
async def async_discover_miyo_cube():
    """Try to discover the MIYO Cube using SSDP/UPnP."""
    try:
        from async_upnp_client.search import async_search
    except ImportError:
        _LOGGER.warning("async_upnp_client is not installed, skipping discovery.")
        return None

    found_host = None

    async def device_callback(device):
        nonlocal found_host
        server = device["Server"]
        host = device["_host"]
        if "miyocube" in server:
            _LOGGER.info(f"Discovered MIYO Cube at {host}")
            found_host = host
            return

    try:
        await async_search(device_callback)
    except Exception as e:
        _LOGGER.error(f"Error during MIYO Cube discovery: {e}")
        return None

    return found_host

# Function to get API key from MIYO Cube
async def async_get_api_key(host):
    """Query the MIYO Cube for an API key (simulate button press)."""
    import aiohttp
    url = f"http://{host}/api/link"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("apiKey")
    except Exception as e:
        _LOGGER.error(f"Error fetching API key from {host}: {e}")
    return None

# Options flow handler for updating configuration options
class MiyocubeOptionsFlowHandler(config_entries.OptionsFlow):
    @property
    def config_entry(self):
        return self.hass.config_entries.async_get_entry(self.handler)

    def __init__(self, config_entry):
        super().__init__()

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({                
                vol.Required(
                    CONF_HOST,
                    default=self.config_entry.options.get(CONF_HOST, self.config_entry.data.get(CONF_HOST, ""))
                ): str,
                vol.Required(
                    CONF_API_KEY,
                    default=self.config_entry.options.get(CONF_API_KEY, self.config_entry.data.get(CONF_API_KEY, ""))
                ): str,
            }),
            errors=errors,
        )

# Main configuration flow for MIYO Cube
class MiyocubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    # Step to handle user input for host configuration
    async def async_step_user(self, user_input=None):        
        errors = {}

        discovered_host = await async_discover_miyo_cube()
        default_host = discovered_host if discovered_host else ""

        schema = vol.Schema({
            vol.Required(CONF_HOST, default=default_host): str
        })

        if user_input is not None:
            host = user_input[CONF_HOST]
            api_key = user_input.get(CONF_API_KEY)
            if not errors:
                self.host = host
                return await self.async_step_get_api_key()

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )

    # Step to get API key after user confirms host
    async def async_step_get_api_key(self, user_input=None):
        """Step to get API key by button press and API call."""
        host = getattr(self, "host", None)  # Retrieve host set in previous step
        errors = {}
        api_key = None

        if host:
            api_key = await async_get_api_key(host)
            if api_key:
                return self.async_create_entry(
                    title="MIYO Cube",
                    data={CONF_HOST: host, CONF_API_KEY: api_key}
                )
            else:
                errors["base"] = "api_key_failed"
        else:
            errors["base"] = "no_host"

        schema = vol.Schema({})

        return self.async_show_form(
            step_id="get_api_key",
            data_schema=schema,
            errors=errors
        )

    # Static method to get options flow handler
    @staticmethod
    def async_get_options_flow(config_entry):
        return MiyocubeOptionsFlowHandler(config_entry)