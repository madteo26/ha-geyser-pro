# Changelog

## [0.8.6] - 2026-06-18
### Fixed
- Added a strategy reload safety guard: periodic reloads that return an empty strategy list while a previous non-empty cache exists are skipped, preventing Home Assistant from losing retained MQTT strategy/cycle entities.
- `get_strategies()` now returns `None` when the Stocker strategy page looks like a login/error/malformed page instead of treating it as a valid empty strategy list.
- Discovery cleanup no longer removes retained strategy/cycle topics on suspicious empty reloads.

## [0.8.5] - 2026-06-18
### Fixed
- Dashboard Settings tab is now visible: `page-settings` is no longer nested inside `page-dashboard`, so switching to Settings does not hide the settings content together with the dashboard page.
- Version bumped to `0.8.5`.

## [0.8.4] - 2026-06-18
### Added
- Imported operational Stocker webapp settings into the dashboard Settings tab.
- Added `Set_Settings` support for zone nozzle count, installed tube length and buzzer state.
- Added `Set_Tank` support for tank liquid name, dilution percentage and liquid type.
- Added per-device MQTT commands:
  - `geyser_pro/<device_id>/cmd/set_geyser_settings`
  - `geyser_pro/<device_id>/cmd/set_tank`
- Added MQTT discovery/state sensors for zone settings, buzzer state and tank settings.

### Changed
- Dashboard Settings tab now performs real device setting writes instead of showing diagnostics only.
- `sw_version` bumped to `0.8.4`.

## [0.8.3] - 2026-06-17
### Fixed
- Dashboard cache issue fixed with a stable loader (`geyser_dashboard.html`) and a cache-busted app file (`geyser_dashboard_app.html`).
- iOS / Home Assistant Companion App now fetches the dashboard app and token file with cache-busting instead of relying on stale WebView cache.
- Added `GEYSER_DASHBOARD_VERSION` to `/config/www/geyser_token.js` for frontend diagnostics.

### Changed
- `sw_version` bumped to `0.8.3`.
- Dashboard installation now requires copying both dashboard files to `/config/www/`.

## [0.8.1] - 2026-06-17
### Fixed
- Removed legacy top-level single-device fields from the add-on schema, so the configuration UI only exposes the `devices:` list.
- Dashboard now treats `GEYSER_DEVICES` as the single source of truth and ignores stale legacy `sensor.geyser_pro_stato` entities from 0.7.x, preventing duplicate/offline zombie tabs.
- Bumped backend software version to 0.8.1.

## [0.8.0] - 2026-06-17
### Added
- Multi-device architecture based on `devices:` list in add-on configuration.
- Each Geyser has its own Stocker account, `device_id`, friendly name, zone names, API session, strategy cache and local override cache.
- Per-device MQTT namespace: `geyser_pro/<device_id>/...`.
- Per-device Home Assistant entity prefix: `geyser_pro_<device_id>_*`.
- Dashboard device selector, shown automatically when multiple devices are detected.
- `/config/www/geyser_token.js` now exports `GEYSER_DEVICES` with device id, name, entity prefix and MQTT topic base.

### Changed
- Device friendly label field inside `devices:` renamed to `device_name` in default config/schema; `name` remains accepted as legacy alias.
- Add-on version bumped to `0.8.0`.
- MQTT client id changed to `geyser_pro_bridge`.
- Strategy/cycle retained discovery cleanup is now isolated per device.
- Quick Start, Sync, create/delete strategy and create/delete cycle commands are routed to the selected device namespace.

### Backward compatibility
- Legacy 0.7.x single-device options (`email`, `password`, `device_name`, `zone_1_name`, `zone_2_name`) are still accepted as fallback.
- Recommended configuration is now the `devices:` list.

## [0.7.14] - 2026-06-17
### Fixed
- Removed persistent `/data/device_name_override.txt` logic: `device_name` now has a single source of truth, the add-on configuration.
- Dashboard now prefers live Home Assistant state attributes over `GEYSER_DEVICE_NAME` from `geyser_token.js`, avoiding stale names such as `Casa` after config changes.
- Strategy and cycle labels now strip dynamic Home Assistant device prefixes like `Casa Strategia:` or `Matteo Strategia:`.

## [0.7.13] - 2026-06-17
### Fixed
- Device friendly name no longer depends on a dedicated MQTT sensor being created by Home Assistant.
- Dashboard loads `/local/geyser_token.js` with cache busting and reads `GEYSER_DEVICE_NAME` first.
- `sensor.geyser_pro_stato` now exposes `device_name` as a JSON attribute for a robust fallback.

## [0.7.11] - 2026-06-17
### Fixed
- `device_name` non ha più default forzato in `config.yaml`: il campo parte vuoto e non sovrascrive più il nome personalizzato durante rebuild/reload
- Aggiunto override persistente in `/data/device_name_override.txt`: se Home Assistant ripropone il default `Geyser PRO`, l'addon mantiene l'ultimo nome personalizzato salvato
- `geyser_token.js` viene scritto sempre con `GEYSER_DEVICE_NAME`, anche se il token dashboard è vuoto
- Log più esplicito: mostra `option_device_name`, override e `device_name` effettivo

## [0.7.10] - 2026-06-17
### Fixed
- Discovery MQTT del sensore device name forzato con `object_id: geyser_pro_device_name`, così Home Assistant non lo rinomina in base alla lingua/friendly name.
- Dashboard: fallback su `GEYSER_DEVICE_NAME` scritto in `/config/www/geyser_token.js`, oltre ai possibili entity_id `device_name`, `nome_device`, `nome_dispositivo`.
- Versione add-on allineata a `0.7.10`.

## [0.7.9] - 2026-06-17
### Fixed
- `device_name` pubblicato anche nel poll loop, non solo in autodiscovery, così la dashboard vede subito il nome configurato.
- Header dashboard: il titolo grande mostra il friendly name del device; il sottotitolo resta il modello/prodotto.

## [0.7.8] - 2026-06-17
### Added
- Friendly name configurabile per il device tramite opzione add-on `device_name`
- Nuovo sensore MQTT `sensor.geyser_pro_device_name`, pubblicato retained
- Dashboard: titolo dinamico letto dal sensore `device_name`, con fallback a `Geyser PRO`

### Changed
- Nome dispositivo MQTT autodiscovery ora usa `device_name`
- Versione software aggiornata a `0.7.8`

## [0.7.2] - 2026-06-08
### Fixed
- Dashboard no longer goes blank after extended uptime
- Periodic reload now skips update if API returns error (None) to preserve existing entities
- `get_strategies()` now returns `None` on error vs `[]` for truly empty (distinguishes API failure from user deleting all strategies)

## [0.7.1] - 2026-06-07
### Fixed
- Cycle active states now read from `Get_Cycle` API instead of unreliable HTML parsing
- All cycles now correctly reflect their actual ON/OFF state from the Stocker cloud

## [0.7.0] - 2026-06-07
### Fixed
- Strategy state no longer reverts to ON after periodic reload when turned OFF from HA
- Dashboard now uses explicit `turn_on`/`turn_off` commands instead of ambiguous `toggle`
- Local state overrides preserved for 10 minutes after manual toggle

## [0.6.9] - 2026-06-06
### Fixed
- Orphan MQTT topics now cleaned up on startup via broker subscription scan
- "Notte" and other orphan strategies removed correctly on restart

## [0.6.8] - 2026-06-06
### Added
- Sync button in dashboard header for instant webapp synchronization
- Connection status dot next to "Geyser PRO" title in header
- Status badge moved to header center, larger and more visible
- `strategy_id` and `cycle_id` published as MQTT JSON attributes

### Fixed
- Days of week now displayed in correct LUN→DOM order
- Delete buttons visible on all strategies and cycles regardless of entity_id format
- Bold group headers in cycles section

## [0.6.3] - 2026-06-05
### Added
- Zone 1 / Zone 2 filtering in dashboard
- `output_valve` attribute per strategy via MQTT JSON attributes
- Tank/product name included in cycle label (e.g. `06:35 · 60s · ogni giorno · PIREKRAFT`)

### Fixed
- `Delete_Cycle` API now uses correct field `geyser_treatment_id`
- `Set_Cycle` duration in seconds (not milliseconds)
- Tank mapping corrected (0=Pulizia, 1=S1, 2=S2)

## [0.6.0] - 2026-06-05
### Added
- Full CRUD for strategies and cycles from dashboard
- Modal forms for creating strategies (name, zone) and cycles (time, duration, days, tank)
- Delete buttons on all strategies and cycles with confirmation
- Auto-refresh after every action (1s for toggle, 3s+6s for create/delete)
- Orphan MQTT topic cleanup within session
- Weather webhook automations (wind, rain, meteo OK) via IFTTT

## [0.5.3] - 2026-06-05
### Added
- Strategy zone detection from HTML (`output_valve` per strategy)
- `Get_Cycle` enrichment for cycle labels: `HH:MM · Xs · giorni · PRODOTTO`
- Correct `Set_Cycle` API payload (time_hours, time_minutes, duration, days_shifted array)

## [0.4.4] - 2026-06-04
### Added
- Full strategy and cycle MQTT autodiscovery with names from API
- Single Quick Start button with tank/zone/duration parameters
- Pulizia (cleaning) option in Quick Start
- Individual cycle toggle via `Set_CycleStatus`

## [0.4.0] - 2026-06-04
### Added
- Initial release
- MQTT autodiscovery for 12 base entities
- Strategy toggle via `Set_StrategyStatus`
- Token-based authentication with auto-renewal (~26h)
- Configurable poll interval (default 7s)
