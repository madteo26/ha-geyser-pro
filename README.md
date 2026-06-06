# Geyser PRO - Home Assistant Add-on

[![Version](https://img.shields.io/badge/version-0.6.8-green.svg)](https://github.com/mad_teo26/ha-geyser-pro)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Home Assistant add-on for the **Stocker Geyser PRO** mosquito repellent system.

## Features

- 📡 **MQTT Autodiscovery** — all entities appear automatically in Home Assistant
- 🔄 **Real-time sync** — status updates every 7 seconds
- 🗓️ **Full strategy management** — create, toggle, and delete strategies and cycles
- 🌿 **Multi-zone support** — Zone 1 and Zone 2 output valves
- ⚡ **Quick Start** — trigger instant nebulization from HA
- 🌧️ **Weather automation ready** — webhook endpoints for IFTTT wind/rain triggers
- 📊 **Custom dashboard** — beautiful dark-mode HTML panel included

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.geyser_pro_stato` | Sensor | Device status |
| `sensor.geyser_pro_batteria` | Sensor | Battery percentage |
| `sensor.geyser_pro_serbatoio_1` | Sensor | Tank 1 level % |
| `sensor.geyser_pro_serbatoio_2` | Sensor | Tank 2 level % |
| `sensor.geyser_pro_prossimo_trattamento` | Sensor | Next treatment time |
| `binary_sensor.geyser_pro_alert` | Binary Sensor | Active alarm |
| `binary_sensor.geyser_pro_quick_start_disponibile` | Binary Sensor | Quick Start available |
| `button.geyser_pro_quick_start` | Button | Trigger Quick Start |
| `switch.geyser_pro_strategia_*` | Switch | Per-strategy toggle |
| `switch.geyser_pro_*_ciclo_*` | Switch | Per-cycle toggle |

## Installation

### Prerequisites
- Home Assistant with Supervisor
- Mosquitto MQTT broker add-on installed and configured
- Stocker Geyser PRO device with active cloud account

### Add-on Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Click the **⋮** menu → **Repositories**
3. Add: `https://github.com/mad_teo26/ha-geyser-pro`
4. Find **Geyser PRO** and click **Install**

### Configuration

```yaml
email: "matteo@example.com"
password: "yourpassword"
mqtt_host: "core-mosquitto"
mqtt_port: 1883
mqtt_username: "your_mqtt_user"
mqtt_password: "your_mqtt_password"
poll_interval: 7
log_level: "info"
```

| Option | Description | Default |
|--------|-------------|---------|
| `email` | Stocker cloud account email | — |
| `password` | Stocker cloud account password | — |
| `mqtt_host` | MQTT broker hostname | `core-mosquitto` |
| `mqtt_port` | MQTT broker port | `1883` |
| `mqtt_username` | MQTT username | — |
| `mqtt_password` | MQTT password | — |
| `poll_interval` | Status polling interval (seconds, 3-300) | `7` |
| `log_level` | Log verbosity | `info` |

## Dashboard

The add-on includes a custom HTML dashboard. To install it:

1. Copy `geyser_dashboard.html` to `/config/www/geyser_dashboard.html`
2. Generate a Long-Lived Access Token in HA (**Profile → Security → Create Token**)
3. Edit the file and replace `const TOKEN = ''` with your token
4. Add to `configuration.yaml`:

```yaml
panel_custom:
  - name: geyser-pro
    sidebar_title: Geyser PRO
    sidebar_icon: mdi:spray
    url_path: geyser-pro
    module_url: /local/geyser_dashboard.html
```

## Weather Automation (IFTTT)

The add-on is designed to work with IFTTT webhooks. Create automations in HA that listen to:

- `geyser_vento_forte` — disables strategies when wind is strong
- `geyser_pioggia` — disables strategies when it rains
- `geyser_meteo_ok` — re-enables strategies when weather is OK

Webhook URL format:
```
https://YOUR-NABU-CASA-URL.ui.nabu.casa/api/webhook/geyser_vento_forte
```

## Support

- [Issues](https://github.com/mad_teo26/ha-geyser-pro/issues)
- [Home Assistant Community](https://community.home-assistant.io)

## License

MIT License — see [LICENSE](LICENSE) for details.
