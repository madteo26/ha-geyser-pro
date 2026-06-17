# Changelog

## [0.7.14] - 2026-06-17
### Fixed
- Removed persistent `/data/device_name_override.txt` logic: `device_name` now has a single source of truth, the add-on configuration.
- Dashboard now prefers live Home Assistant state attributes over `GEYSER_DEVICE_NAME` from `geyser_token.js`, avoiding stale names such as `Casa` after config changes.
- Strategy and cycle labels now strip dynamic Home Assistant device prefixes like `Casa Strategia:` or `Matteo Strategia:`.

# Changelog

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

All notable changes to the Geyser PRO Home Assistant add-on.

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
