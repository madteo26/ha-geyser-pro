# Geyser PRO - Home Assistant Add-on

[!\[Version](https://img.shields.io/badge/version-0.6.8-green.svg)](https://github.com/madteo26/ha-geyser-pro)
[!\[License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Home Assistant add-on for the **Stocker Geyser PRO** mosquito repellent system.

## Features

* 📡 **MQTT Autodiscovery** — all entities appear automatically in Home Assistant
* 🔄 **Real-time sync** — status updates every 7 seconds
* 🗓️ **Full strategy management** — create, toggle, and delete strategies and cycles
* 🌿 **Multi-zone support** — Zone 1 and Zone 2 output valves
* ⚡ **Quick Start** — trigger instant nebulization from HA
* 🌧️ **Weather automation ready** — webhook endpoints for IFTTT wind/rain triggers
* 📊 **Custom dashboard** — beautiful dark-mode HTML panel included

## Entities Created

|Entity|Type|Description|
|-|-|-|
|`sensor.geyser\_pro\_stato`|Sensor|Device status|
|`sensor.geyser\_pro\_batteria`|Sensor|Battery percentage|
|`sensor.geyser\_pro\_serbatoio\_1`|Sensor|Tank 1 level %|
|`sensor.geyser\_pro\_serbatoio\_2`|Sensor|Tank 2 level %|
|`sensor.geyser\_pro\_prossimo\_trattamento`|Sensor|Next treatment time|
|`binary\_sensor.geyser\_pro\_alert`|Binary Sensor|Active alarm|
|`binary\_sensor.geyser\_pro\_quick\_start\_disponibile`|Binary Sensor|Quick Start available|
|`button.geyser\_pro\_quick\_start`|Button|Trigger Quick Start|
|`switch.geyser\_pro\_strategia\_\*`|Switch|Per-strategy toggle|
|`switch.geyser\_pro\_\*\_ciclo\_\*`|Switch|Per-cycle toggle|

## Installation

### Prerequisites

* Home Assistant with Supervisor
* Mosquitto MQTT broker add-on installed and configured
* Stocker Geyser PRO device with active cloud account

### Add-on Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Click the **⋮** menu → **Repositories**
3. Add: `https://github.com/madteo26/ha-geyser-pro`
4. Find **Geyser PRO** and click **Install**

### Configuration

```yaml
email: "youraccountemail"
password: "yourpassword"
mqtt\_host: "core-mosquitto"
mqtt\_port: 1883
mqtt\_username: "your\_mqtt\_user"
mqtt\_password: "your\_mqtt\_password"
poll\_interval: 7
log\_level: "info"
```

|Option|Description|Default|
|-|-|-|
|`email`|Stocker cloud account email|—|
|`password`|Stocker cloud account password|—|
|`mqtt\_host`|MQTT broker hostname|`core-mosquitto`|
|`mqtt\_port`|MQTT broker port|`1883`|
|`mqtt\_username`|MQTT username|—|
|`mqtt\_password`|MQTT password|—|
|`poll\_interval`|Status polling interval (seconds, 3-300)|`7`|
|`log\_level`|Log verbosity|`info`|

## Dashboard

The add-on includes a custom HTML dashboard. To install it:

1. Copy `geyser\_dashboard.html` to `/config/www/geyser\_dashboard.html`
2. Generate a Long-Lived Access Token in HA (**Profile → Security → Create Token**)
3. Edit the file and replace `const TOKEN = ''` with your token
4. Add to `configuration.yaml`:

```yaml
panel\_custom:
  - name: geyser-pro
    sidebar\_title: Geyser PRO
    sidebar\_icon: mdi:spray
    url\_path: geyser-pro
    module\_url: /local/geyser\_dashboard.html
```

## Weather Automation (IFTTT)

The add-on is designed to work with IFTTT webhooks. Create automations in HA that listen to:

* `geyser\_vento\_forte` — disables strategies when wind is strong
* `geyser\_pioggia` — disables strategies when it rains
* `geyser\_meteo\_ok` — re-enables strategies when weather is OK

Webhook URL format:

```
https://YOUR-NABU-CASA-URL.ui.nabu.casa/api/webhook/geyser\_vento\_forte
```

## Support

* [Issues](https://github.com/madteo26/ha-geyser-pro/issues)
* [Home Assistant Community](https://community.home-assistant.io)

## License

MIT License — see [LICENSE](LICENSE) for details.

