# Changelog

All notable changes to the Geyser PRO Home Assistant add-on.

## [0.6.8] - 2026-06-06
### Added
- Orphan MQTT topic cleanup via broker subscription on startup
- Periodic strategy reload every 5 minutes to sync with webapp changes
- Sync button in dashboard for instant webapp synchronization
- Connection status dot next to title in dashboard header
- Strategy/cycle `strategy_id` and `cycle_id` as MQTT JSON attributes (enables delete buttons for all entities)

### Fixed
- Status badge moved to header center, larger size
- Days of week now displayed in correct LUN→DOM order
- Delete button now works for all cycles/strategies regardless of entity_id format

## [0.6.3] - 2026-06-05
### Added
- Zone 1 / Zone 2 filtering in dashboard (strategies and cycles)
- `output_valve` attribute published as MQTT JSON attribute per strategy
- `strategy_id` and `cycle_id` as MQTT JSON attributes for reliable delete operations

### Fixed
- Tank name (product) included in cycle label (e.g. "06:35 · 60s · ogni giorno · PIREKRAFT")
- Delete cycle API now uses correct field `geyser_treatment_id`
- Tank offset fix for cycle creation (tank 1=S1, 2=S2, 0=Pulizia)
- `Set_Cycle` duration in seconds (not milliseconds)

## [0.6.0] - 2026-06-05
### Added
- Full CRUD for strategies and cycles from dashboard
- Modal forms for creating strategies (name, zone) and cycles (time, duration, days, tank)
- Delete buttons on all strategies and cycles
- Auto-refresh after every action (toggle/create/delete)
- Orphan MQTT topic cleanup within session
- Weather webhook automations (wind, rain, meteo OK)

## [0.5.3] - 2026-06-05
### Added
- Strategy zone detection from HTML (`output_valve` per strategy)
- `Get_Cycle` API call to enrich cycle labels with time/duration/days
- Cycle labels format: `HH:MM · Xs · giorni`
- `Set_Cycle` API with correct payload (time_hours, time_minutes, duration, days_shifted)

## [0.4.4] - 2026-06-04
### Added
- Full strategy and cycle MQTT autodiscovery
- Cycle names from `Get_Cycle` API (time, duration, days of week)
- Strategy names from HTML page parsing
- Single Quick Start button with tank/zone/duration parameters
- Pulizia (cleaning) option in Quick Start

### Fixed
- `Set_CycleStatus` toggle for individual cycles
- `days_shifted` array order for cycle creation

## [0.4.0] - 2026-06-04
### Added
- Initial release
- MQTT autodiscovery for 12 base entities (sensors, binary sensors, button)
- Strategy toggle via `Set_StrategyStatus`
- Quick Start support
- Token-based authentication with auto-renewal
- Poll interval configurable (default 7s)
