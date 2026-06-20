# Geyser PRO - Home Assistant Add-on

![Version](https://img.shields.io/badge/version-0.8.7-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Home Assistant add-on for the **Stocker Geyser PRO** mosquito repellent system.

## Features

* MQTT Autodiscovery: all entities appear automatically in Home Assistant
* Multi-device support: manage multiple Geyser PRO units, each with its own Stocker account
* Per-device MQTT namespace: no collisions between strategies, cycles, status and commands
* Real-time sync: status updates every 7 seconds by default
* Full strategy management: create, toggle and delete strategies and cycles
* Multi-zone support: Zone 1 and Zone 2 with configurable friendly names per device
* Quick Start: trigger instant nebulization on the selected device
* Custom dashboard: dark-mode HTML panel with device selector, zone filtering and cycle status
* Disabled strategy visual cue: cycles belonging to disabled strategies are grayed out in the dashboard
* Auto token injection: `dashboard_token` written automatically to `/config/www/geyser_token.js`
* Webapp settings import: edit zone nozzles/tube length and tank liquid/dilution/type from the dashboard

## Entity naming

With device id `casa`:

| Entity | Description |
|--------|-------------|
| `sensor.geyser_pro_casa_stato` | Device status |
| `sensor.geyser_pro_casa_device_name` | Friendly name shown in dashboard |
| `sensor.geyser_pro_casa_batteria` | Battery percentage |
| `sensor.geyser_pro_casa_serbatoio_1/2` | Tank level % |
| `sensor.geyser_pro_casa_liquido_1/2` | Tank product name |
| `sensor.geyser_pro_casa_prossimo_trattamento` | Next treatment time |
| `sensor.geyser_pro_casa_zona_1_nome` | Zone 1 friendly name |
| `sensor.geyser_pro_casa_zona_2_nome` | Zone 2 friendly name |
| `sensor.geyser_pro_casa_zona_1_ugelli` | Zone 1 nozzle count from Stocker settings |
| `sensor.geyser_pro_casa_zona_1_tubo_m` | Zone 1 installed tube length |
| `sensor.geyser_pro_casa_zona_2_ugelli` | Zone 2 nozzle count from Stocker settings |
| `sensor.geyser_pro_casa_zona_2_tubo_m` | Zone 2 installed tube length |
| `binary_sensor.geyser_pro_casa_buzzer_off` | Acoustic signal disabled |
| `sensor.geyser_pro_casa_tanica_1_nome/diluizione/tipo` | Tank 1 settings |
| `sensor.geyser_pro_casa_tanica_2_nome/diluizione/tipo` | Tank 2 settings |
| `binary_sensor.geyser_pro_casa_alert` | Active alarm |
| `binary_sensor.geyser_pro_casa_quickstart_disponibile` | Quick Start available |
| `binary_sensor.geyser_pro_casa_quickstart_attivo` | Quick Start active |
| `switch.geyser_pro_casa_strategia_*` | Per-strategy toggle |
| `switch.geyser_pro_casa_ciclo_*` | Per-cycle toggle |

MQTT topics use the same device namespace:

```text
geyser_pro/casa/stato/state
geyser_pro/casa/quickstart/cmd
geyser_pro/casa/cmd/reload
geyser_pro/casa/cmd/create_strategy
geyser_pro/casa/cmd/create_cycle
geyser_pro/casa/cmd/set_geyser_settings
geyser_pro/casa/cmd/set_tank
```

## Configuration

Recommended multi-device configuration:

```yaml
devices:
  - id: "casa"
    device_name: "Casa"
    email: "account-casa@email.com"
    password: "password-casa"
    zone_1_name: "Barbecue"
    zone_2_name: "Siepe"

  - id: "giardino"
    device_name: "Giardino"
    email: "account-giardino@email.com"
    password: "password-giardino"
    zone_1_name: "Piscina"
    zone_2_name: "Gazebo"

mqtt_host: "core-mosquitto"
mqtt_port: 1883
mqtt_username: "mqtt_user"
mqtt_password: "mqtt_password"
poll_interval: 7
log_level: "info"
dashboard_token: ""
```


### Device identity fields

`id` is the stable technical slug used for MQTT topics and Home Assistant entity ids. `device_name` is only the friendly label shown in the dashboard. The add-on still accepts `name` as a legacy alias inside each device, but the default configuration uses `device_name` to avoid confusion with the add-on top-level `name`.

### Legacy single-device configuration

The 0.7.x options are still accepted as fallback:

```yaml
email: "your@email.com"
password: "yourpassword"
device_id: "main"
device_name: "Casa"
zone_1_name: "Barbecue"
zone_2_name: "Siepe"
```

For 0.8.x, using `devices:` is strongly recommended. Yes, even if humans enjoy migrating things twice.

## Webapp settings

The dashboard Settings tab imports two Stocker webapp functions:

1. **Zone settings** via `Set_Settings`
   - zone 1 nozzles
   - zone 1 tube length
   - zone 2 nozzles
   - zone 2 tube length
   - acoustic signal / buzzer state

2. **Tank settings** via `Set_Tank`
   - tank liquid name
   - dilution percentage
   - liquid type

Commands are routed through the selected device namespace, for example:

```text
geyser_pro/casa/cmd/set_geyser_settings
geyser_pro/casa/cmd/set_tank
```

### Strategy reload safety

The add-on now guards periodic strategy reloads: if Stocker temporarily returns an empty or malformed strategy page while cached strategies already exist, the add-on skips the reload instead of deleting retained MQTT discovery topics. This prevents strategies/cycles from disappearing from Home Assistant until the next add-on restart.

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

The token and device list are injected automatically via `dashboard_token` and `devices` in the add-on config.

### Cache-safe dashboard

From `0.8.3`, the dashboard is split into two files:

- `geyser_dashboard.html`: stable loader, used by Home Assistant / browser.
- `geyser_dashboard_app.html`: real dashboard app, fetched with cache-busting on every load.

Copy both files into `/config/www/`:

```text
/config/www/geyser_dashboard.html
/config/www/geyser_dashboard_app.html
```

This avoids stale browser cache on desktop and iOS/Companion App after dashboard updates.

### 0.8.5 dashboard note

Fixes the Settings tab visibility: `page-settings` is now a sibling of `page-dashboard`, not nested inside it. This matters because browsers, with admirable cruelty, hide children of hidden tabs too.

## License

MIT License.
