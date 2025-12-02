# [![MIYO Cube](miyo-logo.png)](https://miyo.garden/)


# MIYO Cube Home Assistant Custom Component

This custom component integrates your MIYO Cube smart irrigation system with Home Assistant.



## Features

- Automatic discovery and setup via config flow
- Real-time updates using WebSocket
- Supports MIYO Sensors & Valves

## Installation

1. Copy the `custom_components/miyocube` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings > Devices & Services** in Home Assistant.
2. Click **Add Integration** and search for **MIYO Cube**.
3. Press the hardware button on your MIYO Cube.
4. If your MIYO Cube is on the same network, its IP address should be detected automatically. If not, enter the IP address manually and follow the instructions.

## Entities

- **Sensors:** Moisture, temperature, brightness, solar voltage, last update, circuit name
- **Switches:** Automatic irrigation, valve staggering
- **Buttons:** Start/stop irrigation
- **Numbers:** Manual irrigation duration
- **Binary Sensors:** Irrigation active, valve status

## Support

- [Documentation](https://github.com/miyosmart/miyocube-homeassistant-custom-component)
- [Issue Tracker](https://github.com/miyosmart/miyocube-homeassistant-custom-component/issues)

---

MIT License © Nauticast