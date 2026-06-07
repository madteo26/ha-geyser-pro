"""
Geyser PRO - Home Assistant Addon v0.6.0
MQTT bridge con autodiscovery per Stocker Geyser PRO
"""

import json
import logging
import re
import time
import signal
import sys

import paho.mqtt.client as mqtt
import os

PERSIST_IDS_FILE = "/data/published_ids.json"

def _load_published_ids():
    try:
        if os.path.exists(PERSIST_IDS_FILE):
            with open(PERSIST_IDS_FILE) as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()

def _save_published_ids(ids):
    try:
        with open(PERSIST_IDS_FILE, 'w') as f:
            json.dump(list(ids), f)
    except Exception as e:
        logger.warning("Impossibile salvare published_ids: %s", e)

from geyser import GeyserAPI

# ------------------------------------------------------------------
# Opzioni
# ------------------------------------------------------------------

OPTIONS_FILE = "/data/options.json"
with open(OPTIONS_FILE) as f:
    OPTIONS = json.load(f)

LOG_LEVEL = OPTIONS.get("log_level", "info").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("geyser_pro")

EMAIL         = OPTIONS["email"]
PASSWORD      = OPTIONS["password"]
MQTT_HOST     = OPTIONS.get("mqtt_host", "core-mosquitto")
MQTT_PORT     = int(OPTIONS.get("mqtt_port", 1883))
MQTT_USER     = OPTIONS.get("mqtt_username", "")
MQTT_PASS     = OPTIONS.get("mqtt_password", "")
POLL_INTERVAL = int(OPTIONS.get("poll_interval", 7))

DEVICE_ID   = "geyser_pro"
TOPIC_BASE  = "geyser_pro"
DISC_PREFIX = "homeassistant"

DEVICE_INFO = {
    "identifiers":  [DEVICE_ID],
    "name":         "Geyser PRO",
    "manufacturer": "Stocker",
    "model":        "Geyser PRO",
    "sw_version": "0.7.1",
}

# Cache strategie, topic pubblicati e nomi serbatoi
_strategies_cache = []
_published_obj_ids = _load_published_ids()  # carica da disco per cleanup orfani
_tank_names = {0: "Pulizia", 1: "S1", 2: "S2"}
# Stati impostati localmente da HA (non sovrascrivere durante reload per 10 minuti)
_local_overrides = {}  # {strategy_id: (active, timestamp)}
_OVERRIDE_TTL = 600    # 10 minuti

# ------------------------------------------------------------------
# Topic helpers
# ------------------------------------------------------------------

def disc_topic(component: str, obj_id: str) -> str:
    return f"{DISC_PREFIX}/{component}/{DEVICE_ID}/{obj_id}/config"

def state_topic(obj_id: str) -> str:
    return f"{TOPIC_BASE}/{obj_id}/state"

def cmd_topic(obj_id: str) -> str:
    return f"{TOPIC_BASE}/{obj_id}/cmd"

# ------------------------------------------------------------------
# Discovery
# ------------------------------------------------------------------

def publish_discovery(client: mqtt.Client):
    entities = [
        ("sensor", "stato", {
            "name": "Stato", "state_topic": state_topic("stato"),
            "icon": "mdi:spray", "unique_id": f"{DEVICE_ID}_stato", "device": DEVICE_INFO,
        }),
        ("sensor", "batteria", {
            "name": "Batteria", "state_topic": state_topic("batteria"),
            "unit_of_measurement": "%", "device_class": "battery",
            "state_class": "measurement", "unique_id": f"{DEVICE_ID}_batteria", "device": DEVICE_INFO,
        }),
        ("sensor", "serbatoio_1", {
            "name": "Serbatoio 1", "state_topic": state_topic("serbatoio_1"),
            "unit_of_measurement": "%", "icon": "mdi:bottle-tonic",
            "state_class": "measurement", "unique_id": f"{DEVICE_ID}_serbatoio_1", "device": DEVICE_INFO,
        }),
        ("sensor", "serbatoio_2", {
            "name": "Serbatoio 2", "state_topic": state_topic("serbatoio_2"),
            "unit_of_measurement": "%", "icon": "mdi:bottle-tonic-outline",
            "state_class": "measurement", "unique_id": f"{DEVICE_ID}_serbatoio_2", "device": DEVICE_INFO,
        }),
        ("sensor", "liquido_1", {
            "name": "Liquido Serbatoio 1", "state_topic": state_topic("liquido_1"),
            "icon": "mdi:flask", "unique_id": f"{DEVICE_ID}_liquido_1", "device": DEVICE_INFO,
        }),
        ("sensor", "liquido_2", {
            "name": "Liquido Serbatoio 2", "state_topic": state_topic("liquido_2"),
            "icon": "mdi:flask-outline", "unique_id": f"{DEVICE_ID}_liquido_2", "device": DEVICE_INFO,
        }),
        ("sensor", "prossimo_trattamento", {
            "name": "Prossimo Trattamento", "state_topic": state_topic("prossimo_trattamento"),
            "icon": "mdi:clock-outline", "unique_id": f"{DEVICE_ID}_prossimo_trattamento", "device": DEVICE_INFO,
        }),
        ("sensor", "sincronizzato", {
            "name": "Ultimo Sync", "state_topic": state_topic("sincronizzato"),
            "icon": "mdi:sync", "unique_id": f"{DEVICE_ID}_sincronizzato", "device": DEVICE_INFO,
        }),
        ("binary_sensor", "alert", {
            "name": "Allarme", "state_topic": state_topic("alert"),
            "payload_on": "ON", "payload_off": "OFF", "device_class": "problem",
            "unique_id": f"{DEVICE_ID}_alert", "device": DEVICE_INFO,
        }),
        ("binary_sensor", "quickstart_disponibile", {
            "name": "Quick Start Disponibile", "state_topic": state_topic("quickstart_disponibile"),
            "payload_on": "ON", "payload_off": "OFF", "icon": "mdi:check-circle-outline",
            "unique_id": f"{DEVICE_ID}_quickstart_disponibile", "device": DEVICE_INFO,
        }),
        ("binary_sensor", "quickstart_attivo", {
            "name": "Quick Start Attivo", "state_topic": state_topic("quickstart_attivo"),
            "payload_on": "ON", "payload_off": "OFF", "icon": "mdi:play-circle",
            "unique_id": f"{DEVICE_ID}_quickstart_attivo", "device": DEVICE_INFO,
        }),
        ("button", "quickstart_cmd", {
            "name": "Quick Start", "command_topic": cmd_topic("quickstart"),
            "icon": "mdi:play-circle-outline",
            "unique_id": f"{DEVICE_ID}_quickstart_cmd", "device": DEVICE_INFO,
        }),
    ]
    for component, obj_id, config in entities:
        client.publish(disc_topic(component, obj_id), json.dumps(config), retain=True)
    logger.info("MQTT autodiscovery pubblicato (%d entità base)", len(entities))


def publish_strategy_discovery(client: mqtt.Client, strategies: list):
    global _published_obj_ids
    new_obj_ids = set()
    count = 0
    for s in strategies:
        sid   = s["id"]
        sname = s["name"]
        obj_id = f"strategia_{sid}"
        config = {
            "name":          f"Strategia: {sname}",
            "state_topic":   state_topic(obj_id),
            "command_topic": cmd_topic(obj_id),
            "payload_on":    "ON", "payload_off": "OFF",
            "icon":          "mdi:calendar-clock",
            "unique_id":     f"{DEVICE_ID}_{obj_id}",
            "device":        DEVICE_INFO,
            "json_attributes_topic": state_topic(obj_id) + "_attr",
        }
        client.publish(disc_topic("switch", obj_id), json.dumps(config), retain=True)
        new_obj_ids.add(obj_id)
        count += 1

        # Switch per ogni ciclo
        for c in s.get("cycles", []):
            cid    = c["id"]
            clabel = c["label"]
            cobj   = f"ciclo_{cid}"
            cconfig = {
                "name":          f"{sname}: {clabel}",
                "state_topic":   state_topic(cobj),
                "command_topic": cmd_topic(cobj),
                "payload_on":    "ON", "payload_off": "OFF",
                "icon":          "mdi:calendar-check",
                "unique_id":     f"{DEVICE_ID}_{cobj}",
                "device":        DEVICE_INFO,
                "json_attributes_topic": state_topic(cobj) + "_attr",
            }
            client.publish(disc_topic("switch", cobj), json.dumps(cconfig), retain=True)
            # Pubblica cycle_id come attributo
            client.publish(state_topic(cobj) + "_attr",
                           json.dumps({"cycle_id": cid, "strategy_id": sid}), retain=True)
            new_obj_ids.add(cobj)
            count += 1

    # Pulisci topic orfani (presenti nella sessione precedente ma non in quella corrente)
    orphans = _published_obj_ids - new_obj_ids
    for orphan in orphans:
        client.publish(disc_topic("switch", orphan), "", retain=True)
        client.publish(state_topic(orphan), "", retain=True)
        logger.info("Topic orfano rimosso: %s", orphan)

    _published_obj_ids = new_obj_ids
    _save_published_ids(new_obj_ids)
    logger.info("Autodiscovery strategie pubblicato (%d switch)", count)


def publish_strategy_states(client: mqtt.Client, strategies: list):
    now = time.time()
    for s in strategies:
        sid = s["id"]
        # Controlla override locale: se impostato da HA negli ultimi _OVERRIDE_TTL secondi, non sovrascrivere
        if sid in _local_overrides:
            override_active, override_ts = _local_overrides[sid]
            if now - override_ts < _OVERRIDE_TTL:
                state = "ON" if override_active else "OFF"
                logger.debug("Strategia %d: uso override locale (%s)", sid, state)
                client.publish(state_topic(f"strategia_{sid}"), state, retain=True)
                continue
            else:
                del _local_overrides[sid]
        state = "ON" if s["active"] else "OFF"
        logger.debug("Reload strategia %d → %s (webapp)", sid, state)
        client.publish(state_topic(f"strategia_{sid}"), state, retain=True)
        # Pubblica output_valve come attributo JSON
        attrs = json.dumps({
            "output_valve": s.get("output_valve", 1),
            "strategy_name": s["name"],
            "strategy_id": s["id"]
        })
        client.publish(state_topic(f"strategia_{s['id']}") + "_attr", attrs, retain=True)
        for c in s.get("cycles", []):
            cstate = "ON" if c["active"] else "OFF"
            client.publish(state_topic(f"ciclo_{c['id']}"), cstate, retain=True)

# ------------------------------------------------------------------
# Publish status
# ------------------------------------------------------------------

def publish_status(client: mqtt.Client, status: dict):
    stato_map = {0: "Offline", 1: "Attivo", 2: "In pausa",
                 3: "Nebulizzazione", 4: "Preparazione", 5: "Pulizia"}
    stato     = stato_map.get(status.get("status", 0), status.get("status_text", "Sconosciuto"))
    alert     = status.get("alert", {})
    alert_on  = "ON" if alert.get("alert_status", 0) != 0 else "OFF"
    battery   = max(0, int(status.get("battery_percent", 0)))
    tank1     = max(0, int(status.get("tank_1_fill", 0)))
    tank2     = max(0, int(status.get("tank_2_fill", 0)))
    next_t    = status.get("next_treatment_formatted", "N/A")
    sync_at   = status.get("synchronised_at", "N/A")
    qs_disabled = status.get("quickstart_disabled", True)
    qs_status   = status.get("quickstart_status", 0)
    qs_avail    = "OFF" if qs_disabled else "ON"
    qs_attivo   = "ON" if qs_status == 1 else "OFF"

    payloads = {
        "stato": stato, "batteria": battery,
        "serbatoio_1": tank1, "serbatoio_2": tank2,
        "prossimo_trattamento": next_t, "sincronizzato": sync_at,
        "alert": alert_on, "quickstart_disponibile": qs_avail,
        "quickstart_attivo": qs_attivo,
    }
    for obj_id, value in payloads.items():
        client.publish(state_topic(obj_id), str(value), retain=True)

    logger.info("Stato: %s | Batteria: %d%% | S1: %d%% | S2: %d%% | QS: avail=%s attivo=%s",
                stato, battery, tank1, tank2, qs_avail, qs_attivo)


def publish_tank_info(client: mqtt.Client, tank_num: int, info: dict):
    if not info:
        return
    liquid = info.get("tank_liquid", "N/A")
    tipo   = info.get("tank_type", "")
    dil    = info.get("tank_dilution", "")
    label  = f"{liquid} ({tipo} {dil}%)".strip() if tipo else liquid
    client.publish(state_topic(f"liquido_{tank_num}"), label, retain=True)
    logger.info("Serbatoio %d: %s", tank_num, label)

# ------------------------------------------------------------------
# MQTT callbacks
# ------------------------------------------------------------------

geyser_api: GeyserAPI = None


def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    topic   = msg.topic
    logger.info("CMD ricevuto: %s → %s", topic, payload)

    if topic == cmd_topic("quickstart"):
        handle_quickstart(client, payload)
        return

    # Toggle strategia
    m = re.match(r'geyser_pro/strategia_(\d+)/cmd', topic)
    if m:
        handle_strategy_toggle(client, int(m.group(1)), payload)
        return

    # Toggle ciclo
    m = re.match(r'geyser_pro/ciclo_(\d+)/cmd', topic)
    if m:
        handle_cycle_toggle(client, int(m.group(1)), payload)
        return

    # Elimina strategia
    m = re.match(r'geyser_pro/cmd/delete_strategy', topic)
    if m:
        handle_delete_strategy(client, payload)
        return

    # Elimina ciclo
    m = re.match(r'geyser_pro/cmd/delete_cycle', topic)
    if m:
        handle_delete_cycle(client, payload)
        return

    # Crea strategia
    m = re.match(r'geyser_pro/cmd/create_strategy', topic)
    if m:
        handle_create_strategy(client, payload)
        return

    # Crea ciclo
    m = re.match(r'geyser_pro/cmd/create_cycle', topic)
    if m:
        handle_create_cycle(client, payload)
        return

    # Reload manuale
    if topic == f'{TOPIC_BASE}/cmd/reload':
        reload_strategies(client)
        return


def handle_quickstart(client: mqtt.Client, payload: str):
    # Verifica disponibilità dallo stato corrente
    status = geyser_api.get_status()
    if status and status.get("quickstart_disabled", False):
        logger.warning("Quick Start non disponibile (trattamento in corso).")
        client.publish(state_topic("quickstart_disponibile"), "OFF", retain=True)
        return

    params = {}
    try:
        params = json.loads(payload)
    except Exception:
        pass

    tank         = int(params.get("tank", 1))
    nebulization = int(params.get("nebulization", 30))
    output_valve = int(params.get("output_valve", 1))
    type_        = int(params.get("type", 1))

    if not (0 <= tank <= 2):
        logger.error("tank deve essere 0, 1 o 2"); return
    if not (0 <= nebulization <= 150):
        logger.error("nebulization deve essere 0-150"); return
    if not (1 <= output_valve <= 2):
        logger.error("output_valve deve essere 1 o 2"); return

    logger.info("Avvio Quick Start: tank=%d, durata=%ds, zona=%d", tank, nebulization, output_valve)
    ok = geyser_api.set_quickstart(tank=tank - 1 if tank > 0 else 0, nebulization=nebulization,
                                    output_valve=output_valve, type_=type_)
    if ok:
        client.publish(state_topic("quickstart_attivo"), "ON", retain=True)
    else:
        logger.error("Quick Start fallito.")


def handle_strategy_toggle(client: mqtt.Client, strategy_id: int, payload: str):
    active = payload.strip().upper() == "ON"
    logger.info("Toggle strategia %d → %s", strategy_id, payload)
    ok = geyser_api.set_strategy_status(strategy_id, active)
    if ok:
        state = "ON" if active else "OFF"
        client.publish(state_topic(f"strategia_{strategy_id}"), state, retain=True)
        for s in _strategies_cache:
            if s["id"] == strategy_id:
                s["active"] = active
        # Registra override locale per evitare sovrascrittura dal reload
        _local_overrides[strategy_id] = (active, time.time())
        logger.info("Strategia %d → %s", strategy_id, state)
    else:
        logger.error("Set_StrategyStatus fallito per strategia %d", strategy_id)


def handle_cycle_toggle(client: mqtt.Client, cycle_id: int, payload: str):
    active = payload.strip().upper() == "ON"
    logger.info("Toggle ciclo %d → %s", cycle_id, payload)
    ok = geyser_api.set_cycle_status(cycle_id, active)
    if ok:
        state = "ON" if active else "OFF"
        client.publish(state_topic(f"ciclo_{cycle_id}"), state, retain=True)
        for s in _strategies_cache:
            for c in s.get("cycles", []):
                if c["id"] == cycle_id:
                    c["active"] = active
        logger.info("Ciclo %d → %s", cycle_id, state)
    else:
        logger.error("Set_CycleStatus fallito per ciclo %d", cycle_id)


def handle_delete_strategy(client: mqtt.Client, payload: str):
    try:
        data = json.loads(payload)
        sid  = int(data["strategy_id"])
        logger.info("Eliminazione strategia %d...", sid)
        ok = geyser_api.delete_strategy(sid)
        if ok:
            logger.info("Strategia %d eliminata.", sid)
            reload_strategies(client)
        else:
            logger.error("Eliminazione strategia %d fallita.", sid)
    except Exception as e:
        logger.error("handle_delete_strategy errore: %s", e)


def handle_delete_cycle(client: mqtt.Client, payload: str):
    try:
        data = json.loads(payload)
        cid  = int(data["cycle_id"])
        logger.info("Eliminazione ciclo %d...", cid)
        ok = geyser_api.delete_cycle(cid)
        if ok:
            logger.info("Ciclo %d eliminato.", cid)
            reload_strategies(client)
        else:
            logger.error("Eliminazione ciclo %d fallita.", cid)
    except Exception as e:
        logger.error("handle_delete_cycle errore: %s", e)


def handle_create_strategy(client: mqtt.Client, payload: str):
    try:
        data         = json.loads(payload)
        name         = data["name"]
        output_valve = int(data.get("output_valve", 1))
        logger.info("Creazione strategia '%s' zona %d...", name, output_valve)
        result = geyser_api.create_strategy(name, output_valve)
        if result:
            logger.info("Strategia creata: %s", result)
            reload_strategies(client)
        else:
            logger.error("Creazione strategia fallita.")
    except Exception as e:
        logger.error("handle_create_strategy errore: %s", e)


def handle_create_cycle(client: mqtt.Client, payload: str):
    try:
        data         = json.loads(payload)
        strategy_id  = int(data["strategy_id"])
        tank         = int(data.get("tank", 1))
        time_hour    = int(data.get("hour", 8))
        time_minute  = int(data.get("minute", 0))
        nebulization = int(data.get("nebulization", 60))
        # days_shifted: array [L,M,M,G,V,S,D] come interi 0/1
        days_shifted = data.get("days_shifted", [1,1,1,1,1,1,1])
        logger.info("Creazione ciclo strategia %d alle %02d:%02d...", strategy_id, time_hour, time_minute)
        result = geyser_api.create_cycle(strategy_id, tank, time_hour, time_minute, nebulization, days_shifted)
        if result:
            logger.info("Ciclo creato: %s", result)
            reload_strategies(client)
        else:
            logger.error("Creazione ciclo fallita.")
    except Exception as e:
        logger.error("handle_create_cycle errore: %s", e)


def _cleanup_orphans_via_mqtt(client: mqtt.Client):
    """Sottoscrive i topic di discovery e pulisce i retained orfani."""
    import threading
    found_ids = set()
    event = threading.Event()

    def _on_retained(c, userdata, msg):
        if msg.retain and msg.payload:
            parts = msg.topic.split('/')
            if len(parts) == 5:
                found_ids.add(parts[3])

    client.message_callback_add(f"{DISC_PREFIX}/switch/{DEVICE_ID}/+/config", _on_retained)
    client.subscribe(f"{DISC_PREFIX}/switch/{DEVICE_ID}/+/config")
    time.sleep(1.5)  # Attendi i retained messages
    client.unsubscribe(f"{DISC_PREFIX}/switch/{DEVICE_ID}/+/config")
    client.message_callback_remove(f"{DISC_PREFIX}/switch/{DEVICE_ID}/+/config")

    # Gli ID attuali verranno popolati da publish_strategy_discovery
    # Per ora puliamo tutto quello che non inizia con i prefix base noti
    logger.debug("Topic discovery trovati: %s", found_ids)
    # Salva per il confronto successivo
    global _published_obj_ids
    _published_obj_ids = found_ids
    logger.info("Pre-cleanup: trovati %d topic discovery esistenti", len(found_ids))


def reload_strategies(client: mqtt.Client):
    """Ricarica strategie da API, pulisce orfani, pubblica nuovo autodiscovery."""
    global _strategies_cache
    logger.info("Ricaricamento strategie...")
    new_strategies = geyser_api.get_strategies()
    if new_strategies is not None:
        # Arricchisci cicli con Get_Cycle
        ALL_DAYS = '1111111' 
        for s in new_strategies:
            for c in s.get("cycles", []):
                try:
                    detail = geyser_api.get_cycle(c["id"])
                    if detail:
                        time_str = detail.get("time", "")
                        dur      = int(detail.get("nebulization", detail.get("duration", 0)))
                        days_raw = detail.get("days", "")
                        if days_raw == ALL_DAYS:
                            days_label = "ogni giorno"
                        elif isinstance(days_raw, str) and len(days_raw) == 7:
                            # API order: pos0=DOM,pos1=LUN,pos2=MAR,pos3=MER,pos4=GIO,pos5=VEN,pos6=SAB
                            # Display in standard LUN→DOM order
                            _DAY_LABELS = ["L","M","M","G","V","S","D"]
                            _DAY_POS    = [1, 2, 3, 4, 5, 6, 0]
                            active_days = "".join(_DAY_LABELS[di] for di, pos in enumerate(_DAY_POS) if days_raw[pos] == "1")
                            if active_days == "LMMGVS":
                                days_label = "L→S"
                            elif active_days == "LMMGVSD":
                                days_label = "ogni giorno"
                            elif active_days == "SD":
                                days_label = "S·D"
                            elif active_days == "LMMGV":
                                days_label = "L→V"
                            else:
                                days_label = active_days
                        else:
                            days_label = ""
                        label = time_str or f"{int(detail.get('time_hour',0)):02d}:{int(detail.get('time_minute',0)):02d}"
                        if dur:
                            label += f" · {dur}s"
                        if days_label:
                            label += f" · {days_label}"
                        # Aggiungi nome prodotto
                        tank_num = int(detail.get("tank", 0))
                        tank_name = _tank_names.get(tank_num, "")
                        if tank_name:
                            label += f" · {tank_name}"
                        c["active"] = bool(detail.get("active", True))
                        c["label"] = label
                        logger.debug("Ciclo %d: %s (active=%s)", c["id"], label, c["active"])
                except Exception as e:
                    logger.debug("Get_Cycle %d fallito: %s", c["id"], e)
        # Log per debug label cicli
        for s in new_strategies:
            for c in s.get("cycles", []):
                logger.debug("Ciclo %d label finale: %s", c["id"], c.get("label","???"))
        _strategies_cache = new_strategies
        publish_strategy_discovery(client, new_strategies)
        publish_strategy_states(client, new_strategies)
        logger.info("Strategie ricaricate: %d", len(new_strategies))
        # Notifica la dashboard via MQTT
        client.publish(f"{TOPIC_BASE}/strategies/updated", "1", retain=False)
    else:
        logger.error("Errore nel ricaricamento strategie")


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        logger.info("MQTT connesso a %s:%d", MQTT_HOST, MQTT_PORT)
        client.subscribe(f"{TOPIC_BASE}/+/cmd")
        client.subscribe(f"{TOPIC_BASE}/cmd/#")
        publish_discovery(client)
    else:
        logger.error("MQTT connessione fallita, rc=%s", reason_code)

# ------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------

def main():
    global geyser_api, _strategies_cache

    logger.info("=== Geyser PRO Addon v0.7.1 avviato ===")
    logger.info("Poll interval: %d sec", POLL_INTERVAL)

    geyser_api = GeyserAPI(EMAIL, PASSWORD)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEVICE_ID)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.will_set(state_topic("stato"), "Offline", retain=True)

    logger.info("Connessione MQTT a %s:%d...", MQTT_HOST, MQTT_PORT)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    def shutdown(sig, frame):
        logger.info("Shutdown richiesto.")
        client.publish(state_topic("stato"), "Offline", retain=True)
        client.loop_stop()
        client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT,  shutdown)

    # Login iniziale
    retries = 0
    while not geyser_api.login():
        retries += 1
        wait = min(30 * retries, 300)
        logger.error("Login fallito — riprovo tra %ds", wait)
        time.sleep(wait)

    # Info serbatoi
    global _tank_names
    for tank_num in [1, 2]:
        info = geyser_api.get_tank(tank_num)
        publish_tank_info(client, tank_num, info)
        if info:
            liquid = info.get("tank_liquid", "").split()[0] if info.get("tank_liquid") else f"S{tank_num}"
            _tank_names[tank_num] = liquid

    # Strategie e cicli
    _strategies_cache = geyser_api.get_strategies()
    if _strategies_cache:
        # Arricchisci ogni ciclo con orario e durata da Get_Cycle
        # days stringa 7 bit: posizione 0=DOM, 1=SAB, 2=VEN, 3=GIO, 4=MER, 5=MAR, 6=LUN
        # quindi reverse per avere LUN...DOM
        ALL_DAYS = '1111111' 

        for s in _strategies_cache:
            for c in s.get("cycles", []):
                try:
                    detail = geyser_api.get_cycle(c["id"])
                    if detail:
                        time_str = detail.get("time", "")
                        dur      = int(detail.get("nebulization", detail.get("duration", 0)))
                        days_raw = detail.get("days", "")

                        # Giorni: API pos0=DOM,1=LUN,2=MAR,3=MER,4=GIO,5=VEN,6=SAB
                        # Mostra in ordine LUN→DOM
                        if days_raw == ALL_DAYS:
                            days_label = "ogni giorno"
                        elif isinstance(days_raw, str) and len(days_raw) == 7:
                            _DL = ["L","M","M","G","V","S","D"]
                            _DP = [1, 2, 3, 4, 5, 6, 0]
                            _ad = "".join(_DL[di] for di, pos in enumerate(_DP) if days_raw[pos] == "1")
                            if _ad in ("LMMGVSD",""):
                                days_label = "ogni giorno" if _ad else ""
                            elif _ad == "LMMGV":
                                days_label = "L→V"
                            elif _ad == "SD":
                                days_label = "S·D"
                            else:
                                days_label = _ad
                        else:
                            days_label = ""

                        label = time_str or f"{int(detail.get('time_hour',0)):02d}:{int(detail.get('time_minute',0)):02d}"
                        if dur:
                            label += f" · {dur}s"
                        if days_label:
                            label += f" · {days_label}"
                        # Aggiungi nome prodotto
                        tank_num = int(detail.get("tank", 0))
                        tank_name = _tank_names.get(tank_num, "")
                        if tank_name:
                            label += f" · {tank_name}"
                        c["active"] = bool(detail.get("active", True))
                        c["label"] = label
                        logger.debug("Ciclo %d: %s (active=%s)", c["id"], label, c["active"])
                except Exception as e:
                    logger.debug("Get_Cycle %d fallito: %s", c["id"], e)
        publish_strategy_discovery(client, _strategies_cache)
        publish_strategy_states(client, _strategies_cache)
    else:
        logger.warning("Nessuna strategia trovata.")

    # Poll loop
    _reload_counter = 0
    _RELOAD_EVERY   = max(1, 300 // POLL_INTERVAL)  # ogni ~5 minuti
    while True:
        try:
            status = geyser_api.get_status()
            if status:
                publish_status(client, status)
            else:
                logger.warning("Nessuno stato ricevuto dal Geyser.")
                client.publish(state_topic("stato"), "Offline", retain=True)
            # Reload periodico strategie per sincronizzare con modifiche dalla webapp
            _reload_counter += 1
            if _reload_counter >= _RELOAD_EVERY:
                _reload_counter = 0
                logger.debug("Reload periodico strategie...")
                reload_strategies(client)
        except Exception as e:
            logger.error("Errore nel poll loop: %s", e)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()