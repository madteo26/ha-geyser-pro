# Geyser PRO - Home Assistant Add-on

[![Version](https://img.shields.io/badge/version-0.7.7-green.svg)](https://github.com/madteo26/ha-geyser-pro)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Home Assistant add-on for the **Stocker Geyser PRO** mosquito repellent system.

## Features

* 📡 **MQTT Autodiscovery** — all entities appear automatically in Home Assistant
* 🔄 **Real-time sync** — status updates every 7 seconds
* 🗓️ **Full strategy management** — create, toggle, and delete strategies and cycles
* 🌿 **Multi-zone support** — Zone 1 and Zone 2 with configurable friendly names
* ⚡ **Quick Start** — trigger instant nebulization from HA
* 📊 **Custom dashboard** — dark-mode HTML panel with zone filtering and cycle status
* 🔑 **Auto token injection** — HA token set once in addon config, written automatically to dashboard
* 🏷️ **Zone friendly names** — configurable names (e.g. "Barbecue", "Siepe") shown in dashboard tabs

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.geyser_pro_stato` | Sensor | Device status |
| `sensor.geyser_pro_batteria` | Sensor | Battery percentage |
| `sensor.geyser_pro_serbatoio_1/2` | Sensor | Tank level % |
| `sensor.geyser_pro_liquido_1/2` | Sensor | Tank product name |
| `sensor.geyser_pro_prossimo_trattamento` | Sensor | Next treatment time |
| `sensor.geyser_pro_zona_1_nome` | Sensor | Zone 1 friendly name |
| `sensor.geyser_pro_zona_2_nome` | Sensor | Zone 2 friendly name |
| `binary_sensor.geyser_pro_alert` | Binary Sensor | Active alarm |
| `binary_sensor.geyser_pro_quickstart_disponibile` | Binary Sensor | Quick Start available |
| `button.geyser_pro_quickstart_cmd` | Button | Trigger Quick Start |
| `switch.geyser_pro_strategia_*` | Switch | Per-strategy toggle |
| `switch.geyser_pro_*_ciclo_*` | Switch | Per-cycle toggle |

## Installation

1. In Home Assistant go to **Settings → Add-ons → Add-on Store**
2. Click **⋮ → Repositories** and add: `https://github.com/madteo26/ha-geyser-pro`
3. Find **Geyser PRO** and click **Install**

## Configuration

```yaml
email: "your@email.com"
password: "yourpassword"
mqtt_host: "core-mosquitto"
mqtt_port: 1883
mqtt_username: "mqtt_user"
mqtt_password: "mqtt_password"
poll_interval: 7
log_level: "info"
zone_1_name: "Zona 1"      # Nome visualizzato in dashboard per la zona 1
zone_2_name: "Zona 2"      # Nome visualizzato in dashboard per la zona 2
dashboard_token: ""         # Long-Lived Access Token HA — scritto automaticamente in /config/www/geyser_token.js
```

## Dashboard

Copy `geyser_dashboard.html` to `/config/www/geyser_dashboard.html`.

Add to `configuration.yaml`:

```yaml
panel_custom:
  - name: geyser-pro
    sidebar_title: Geyser PRO
    sidebar_icon: mdi:spray
    url_path: geyser-pro
    module_url: /local/geyser_dashboard.html
```

The token is injected automatically via `dashboard_token` in addon config — no manual HTML editing needed.

## License

MIT License
