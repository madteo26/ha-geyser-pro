# Geyser PRO - Home Assistant Add-on

![Version](https://img.shields.io/badge/version-0.7.14-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Home Assistant add-on for the **Stocker Geyser PRO** mosquito repellent system.

## Features

* MQTT Autodiscovery: all entities appear automatically in Home Assistant
* Real-time sync: status updates every 7 seconds by default
* Full strategy management: create, toggle, and delete strategies and cycles
* Multi-zone support: Zone 1 and Zone 2 with configurable friendly names
* Device friendly name: configurable `device_name`, ready for future multi-device dashboard handling
* Quick Start: trigger instant nebulization from HA
* Custom dashboard: dark-mode HTML panel with zone filtering and cycle status
* Auto token injection: `dashboard_token` written automatically to `/config/www/geyser_token.js`

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.geyser_pro_stato` | Sensor | Device status |
| `sensor.geyser_pro_device_name` | Sensor | Friendly name shown in dashboard |
| `sensor.geyser_pro_batteria` | Sensor | Battery percentage |
| `sensor.geyser_pro_serbatoio_1/2` | Sensor | Tank level % |
| `sensor.geyser_pro_liquido_1/2` | Sensor | Tank product name |
| `sensor.geyser_pro_prossimo_trattamento` | Sensor | Next treatment time |
| `sensor.geyser_pro_zona_1_nome` | Sensor | Zone 1 friendly name |
| `sensor.geyser_pro_zona_2_nome` | Sensor | Zone 2 friendly name |
| `binary_sensor.geyser_pro_alert` | Binary Sensor | Active alarm |
| `binary_sensor.geyser_pro_quickstart_disponibile` | Binary Sensor | Quick Start available |
| `binary_sensor.geyser_pro_quickstart_attivo` | Binary Sensor | Quick Start active |
| `button.geyser_pro_quickstart_cmd` | Button | Trigger Quick Start |
| `switch.geyser_pro_strategia_*` | Switch | Per-strategy toggle |
| `switch.geyser_pro_ciclo_*` | Switch | Per-cycle toggle |

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
device_name: ""             # Nome logico del device (es. Casa, Giardino). Vuoto = Geyser PRO      # Nome device mostrato nella dashboard
zone_1_name: "Zona 1"          # Nome visualizzato in dashboard per la zona 1
zone_2_name: "Zona 2"          # Nome visualizzato in dashboard per la zona 2
dashboard_token: ""            # Long-Lived Access Token HA
```


### Device friendly name

`device_name` is written into `/config/www/geyser_token.js` and mirrored as an attribute on `sensor.geyser_pro_stato`, so the dashboard does not depend on Home Assistant creating a separate name sensor.

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

The token is injected automatically via `dashboard_token` in the add-on config.

## License

MIT License.
