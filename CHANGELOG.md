# Changelog

## [0.7.7] - 2026-06-16
### Added
- Token HA configurabile nelle opzioni addon (`dashboard_token`) — scritto automaticamente in `/config/www/geyser_token.js` all'avvio, nessuna modifica manuale all'HTML
- Nomi zona configurabili nelle opzioni addon (`zone_1_name`, `zone_2_name`) — pubblicati come sensori MQTT e letti dalla dashboard in tempo reale
- Filtro cicli per zona tramite `strategy_id` → `output_valve` (robusto anche con strategie con stesso nome su zone diverse)
- Cicli visivamente "grayed" (opacità 35%) quando la strategia padre è disabilitata

### Changed
- `map: config:rw` in config.yaml per permettere scrittura in `/config/www/`
- Versione bump a 0.7.7

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

## [0.6.0] - 2026-06-05
### Added
- Full CRUD for strategies and cycles from dashboard
- Modal forms for creating strategies (name, zone) and cycles (time, duration, days, tank)
- Delete buttons on all strategies and cycles with confirmation
- Auto-refresh after every action

## [0.5.3] - 2026-06-05
### Added
- Strategy zone detection from HTML (`output_valve` per strategy)
- `Get_Cycle` enrichment for cycle labels: `HH:MM · Xs · giorni · PRODOTTO`

## [0.4.0] - 2026-06-04
### Added
- Initial release
- MQTT autodiscovery for 12 base entities
- Strategy toggle via `Set_StrategyStatus`
- Token-based authentication with auto-renewal (~26h)
- Configurable poll interval (default 7s)
