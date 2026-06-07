# Changelog

All notable changes to the Geyser PRO Home Assistant add-on.

## [0.7.1] - 2026-06-07
### Fixed
- Cycle active states now read from `Get_Cycle` API instead of HTML parsing (HTML uses JavaScript for toggle states, making static parsing unreliable)
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
