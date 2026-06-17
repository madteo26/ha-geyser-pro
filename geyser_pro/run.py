"""
Geyser PRO - Home Assistant Addon v0.8.5
MQTT bridge con autodiscovery per Stocker Geyser PRO.
Multi-device ready: ogni device ha account Stocker, namespace MQTT, entity prefix,
cache strategie e override locali separati.
"""

import json
import logging
import os
import re
import signal
import sys
import time
from typing import Dict, List, Optional

import paho.mqtt.client as mqtt

from geyser import GeyserAPI

# ------------------------------------------------------------------
# Opzioni globali
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

MQTT_HOST = OPTIONS.get("mqtt_host", "core-mosquitto")
MQTT_PORT = int(OPTIONS.get("mqtt_port", 1883))
MQTT_USER = OPTIONS.get("mqtt_username", "")
MQTT_PASS = OPTIONS.get("mqtt_password", "")
POLL_INTERVAL = int(OPTIONS.get("poll_interval", 7))
DASHBOARD_TOKEN = OPTIONS.get("dashboard_token", "")
DISC_PREFIX = "homeassistant"
TOPIC_ROOT = "geyser_pro"
SW_VERSION = "0.8.5"
DEVICE_NAME_DEFAULT = "Geyser PRO"
_OVERRIDE_TTL = 600  # 10 minuti


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def slugify(value: str, fallback: str) -> str:
    raw = str(value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9_]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw or fallback


def _persist_ids_file(device_slug: str) -> str:
    return f"/data/published_ids_{device_slug}.json"


def _load_published_ids(device_slug: str) -> set:
    path = _persist_ids_file(device_slug)
    try:
        if os.path.exists(path):
            with open(path) as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def _save_published_ids(device_slug: str, ids: set):
    path = _persist_ids_file(device_slug)
    try:
        with open(path, "w") as f:
            json.dump(list(ids), f)
    except Exception as e:
        logger.warning("[%s] Impossibile salvare published_ids: %s", device_slug, e)


def normalize_devices(options: dict) -> List[dict]:
    """Supporta sia la nuova lista devices sia il vecchio schema single-device."""
    raw_devices = options.get("devices") or []
    devices: List[dict] = []

    if isinstance(raw_devices, list) and raw_devices:
        used_ids = set()
        for idx, d in enumerate(raw_devices, start=1):
            if not isinstance(d, dict):
                logger.warning("Device #%d ignorato: configurazione non valida", idx)
                continue
            email = str(d.get("email", "") or "").strip()
            password = str(d.get("password", "") or "")
            if not email or not password:
                logger.warning("Device #%d ignorato: email/password mancanti", idx)
                continue
            base_id = d.get("id") or d.get("device_id") or d.get("name") or f"device_{idx}"
            dev_id = slugify(base_id, f"device_{idx}")
            if dev_id in used_ids:
                dev_id = f"{dev_id}_{idx}"
            used_ids.add(dev_id)
            name = str(d.get("name") or d.get("device_name") or dev_id.title()).strip() or DEVICE_NAME_DEFAULT
            devices.append({
                "id": dev_id,
                "name": name,
                "email": email,
                "password": password,
                "zone_1_name": str(d.get("zone_1_name") or "Zona 1"),
                "zone_2_name": str(d.get("zone_2_name") or "Zona 2"),
            })

    if devices:
        return devices

    # Fallback legacy: mantiene compatibilità con la config 0.7.x.
    legacy_email = str(options.get("email", "") or "").strip()
    legacy_password = str(options.get("password", "") or "")
    if legacy_email and legacy_password:
        dev_id = slugify(options.get("device_id") or options.get("device_name") or "main", "main")
        name = str(options.get("device_name") or DEVICE_NAME_DEFAULT).strip() or DEVICE_NAME_DEFAULT
        devices.append({
            "id": dev_id,
            "name": name,
            "email": legacy_email,
            "password": legacy_password,
            "zone_1_name": str(options.get("zone_1_name") or "Zona 1"),
            "zone_2_name": str(options.get("zone_2_name") or "Zona 2"),
        })
        logger.warning(
            "Uso configurazione legacy single-device. Per multi-device usa options.devices. "
            "Entity prefix attuale: geyser_pro_%s", dev_id
        )

    return devices


class GeyserDeviceWorker:
    def __init__(self, cfg: dict):
        self.id = cfg["id"]
        self.name = cfg["name"]
        self.email = cfg["email"]
        self.password = cfg["password"]
        self.zone_1_name = cfg.get("zone_1_name", "Zona 1")
        self.zone_2_name = cfg.get("zone_2_name", "Zona 2")

        self.device_uid = f"geyser_pro_{self.id}"
        self.topic_base = f"{TOPIC_ROOT}/{self.id}"
        self.api: Optional[GeyserAPI] = None
        self.strategies_cache: List[dict] = []
        self.published_obj_ids = _load_published_ids(self.id)
        self.tank_names = {0: "Pulizia", 1: "S1", 2: "S2"}
        self.local_overrides: Dict[int, tuple] = {}

        self.device_info = {
            "identifiers": [self.device_uid],
            "name": self.name,
            "manufacturer": "Stocker",
            "model": "Geyser PRO",
            "sw_version": SW_VERSION,
        }

    # ------------------------------
    # Topic helpers
    # ------------------------------
    def disc_topic(self, component: str, obj_id: str) -> str:
        return f"{DISC_PREFIX}/{component}/{self.device_uid}/{obj_id}/config"

    def state_topic(self, obj_id: str) -> str:
        return f"{self.topic_base}/{obj_id}/state"

    def cmd_topic(self, obj_id: str) -> str:
        return f"{self.topic_base}/{obj_id}/cmd"

    def base_config(self, component: str, obj_id: str, config: dict) -> dict:
        final = dict(config)
        final.setdefault("unique_id", f"{self.device_uid}_{obj_id}")
        final.setdefault("object_id", f"{self.device_uid}_{obj_id}")
        final.setdefault("device", self.device_info)
        return final

    # ------------------------------
    # Discovery e stati
    # ------------------------------
    def publish_discovery(self, client: mqtt.Client):
        entities = [
            ("sensor", "stato", {
                "name": "Stato", "state_topic": self.state_topic("stato"),
                "json_attributes_topic": self.state_topic("stato") + "_attr",
                "icon": "mdi:spray",
            }),
            ("sensor", "device_name", {
                "name": "Nome Device", "state_topic": self.state_topic("device_name"),
                "icon": "mdi:rename-box",
            }),
            ("sensor", "device_id", {
                "name": "Device ID", "state_topic": self.state_topic("device_id"),
                "icon": "mdi:identifier",
            }),
            ("sensor", "batteria", {
                "name": "Batteria", "state_topic": self.state_topic("batteria"),
                "unit_of_measurement": "%", "device_class": "battery", "state_class": "measurement",
            }),
            ("sensor", "serbatoio_1", {
                "name": "Serbatoio 1", "state_topic": self.state_topic("serbatoio_1"),
                "unit_of_measurement": "%", "icon": "mdi:bottle-tonic", "state_class": "measurement",
            }),
            ("sensor", "serbatoio_2", {
                "name": "Serbatoio 2", "state_topic": self.state_topic("serbatoio_2"),
                "unit_of_measurement": "%", "icon": "mdi:bottle-tonic-outline", "state_class": "measurement",
            }),
            ("sensor", "liquido_1", {
                "name": "Liquido Serbatoio 1", "state_topic": self.state_topic("liquido_1"),
                "icon": "mdi:flask",
            }),
            ("sensor", "liquido_2", {
                "name": "Liquido Serbatoio 2", "state_topic": self.state_topic("liquido_2"),
                "icon": "mdi:flask-outline",
            }),
            ("sensor", "prossimo_trattamento", {
                "name": "Prossimo Trattamento", "state_topic": self.state_topic("prossimo_trattamento"),
                "icon": "mdi:clock-outline",
            }),
            ("sensor", "sincronizzato", {
                "name": "Ultimo Sync", "state_topic": self.state_topic("sincronizzato"),
                "icon": "mdi:sync",
            }),
            ("binary_sensor", "alert", {
                "name": "Allarme", "state_topic": self.state_topic("alert"),
                "payload_on": "ON", "payload_off": "OFF", "device_class": "problem",
            }),
            ("binary_sensor", "quickstart_disponibile", {
                "name": "Quick Start Disponibile", "state_topic": self.state_topic("quickstart_disponibile"),
                "payload_on": "ON", "payload_off": "OFF", "icon": "mdi:check-circle-outline",
            }),
            ("binary_sensor", "quickstart_attivo", {
                "name": "Quick Start Attivo", "state_topic": self.state_topic("quickstart_attivo"),
                "payload_on": "ON", "payload_off": "OFF", "icon": "mdi:play-circle",
            }),
            ("sensor", "zona_1_nome", {
                "name": "Zona 1 Nome", "state_topic": self.state_topic("zona_1_nome"),
                "icon": "mdi:map-marker",
            }),
            ("sensor", "zona_2_nome", {
                "name": "Zona 2 Nome", "state_topic": self.state_topic("zona_2_nome"),
                "icon": "mdi:map-marker",
            }),
            ("sensor", "zona_1_ugelli", {
                "name": "Zona 1 Ugelli", "state_topic": self.state_topic("zona_1_ugelli"),
                "icon": "mdi:sprinkler", "state_class": "measurement",
            }),
            ("sensor", "zona_1_tubo_m", {
                "name": "Zona 1 Tubo", "state_topic": self.state_topic("zona_1_tubo_m"),
                "unit_of_measurement": "m", "icon": "mdi:pipe", "state_class": "measurement",
            }),
            ("sensor", "zona_2_ugelli", {
                "name": "Zona 2 Ugelli", "state_topic": self.state_topic("zona_2_ugelli"),
                "icon": "mdi:sprinkler", "state_class": "measurement",
            }),
            ("sensor", "zona_2_tubo_m", {
                "name": "Zona 2 Tubo", "state_topic": self.state_topic("zona_2_tubo_m"),
                "unit_of_measurement": "m", "icon": "mdi:pipe", "state_class": "measurement",
            }),
            ("binary_sensor", "buzzer_off", {
                "name": "Buzzer Off", "state_topic": self.state_topic("buzzer_off"),
                "payload_on": "ON", "payload_off": "OFF", "icon": "mdi:volume-off",
            }),
            ("sensor", "tanica_1_nome", {
                "name": "Tanica 1 Nome", "state_topic": self.state_topic("tanica_1_nome"),
                "icon": "mdi:flask",
            }),
            ("sensor", "tanica_1_diluizione", {
                "name": "Tanica 1 Diluizione", "state_topic": self.state_topic("tanica_1_diluizione"),
                "unit_of_measurement": "%", "icon": "mdi:percent", "state_class": "measurement",
            }),
            ("sensor", "tanica_1_tipo", {
                "name": "Tanica 1 Tipo", "state_topic": self.state_topic("tanica_1_tipo"),
                "icon": "mdi:tag-outline",
            }),
            ("sensor", "tanica_2_nome", {
                "name": "Tanica 2 Nome", "state_topic": self.state_topic("tanica_2_nome"),
                "icon": "mdi:flask-outline",
            }),
            ("sensor", "tanica_2_diluizione", {
                "name": "Tanica 2 Diluizione", "state_topic": self.state_topic("tanica_2_diluizione"),
                "unit_of_measurement": "%", "icon": "mdi:percent", "state_class": "measurement",
            }),
            ("sensor", "tanica_2_tipo", {
                "name": "Tanica 2 Tipo", "state_topic": self.state_topic("tanica_2_tipo"),
                "icon": "mdi:tag-outline",
            }),
            ("button", "quickstart_cmd", {
                "name": "Quick Start", "command_topic": self.cmd_topic("quickstart"),
                "icon": "mdi:play-circle-outline",
            }),
        ]
        for component, obj_id, config in entities:
            client.publish(
                self.disc_topic(component, obj_id),
                json.dumps(self.base_config(component, obj_id, config)),
                retain=True,
            )

        logger.info("[%s] MQTT autodiscovery pubblicato (%d entità base)", self.id, len(entities))
        self.publish_static_states(client)

    def publish_static_states(self, client: mqtt.Client):
        client.publish(self.state_topic("device_name"), self.name, retain=True)
        client.publish(self.state_topic("device_id"), self.id, retain=True)
        client.publish(self.state_topic("zona_1_nome"), self.zone_1_name, retain=True)
        client.publish(self.state_topic("zona_2_nome"), self.zone_2_name, retain=True)
        self.publish_status_attributes(client)

    def publish_status_attributes(self, client: mqtt.Client, **extra):
        attrs = {
            "device_id": self.id,
            "device_name": self.name,
            "model": "Geyser PRO",
            "topic_base": self.topic_base,
            "entity_prefix": self.device_uid,
            "zone_1_name": self.zone_1_name,
            "zone_2_name": self.zone_2_name,
        }
        attrs.update(extra)
        client.publish(self.state_topic("stato") + "_attr", json.dumps(attrs), retain=True)

    def publish_strategy_discovery(self, client: mqtt.Client, strategies: list):
        new_obj_ids = set()
        count = 0
        for s in strategies:
            sid = s["id"]
            sname = s["name"]
            obj_id = f"strategia_{sid}"
            config = self.base_config("switch", obj_id, {
                "name": f"Strategia: {sname}",
                "state_topic": self.state_topic(obj_id),
                "command_topic": self.cmd_topic(obj_id),
                "payload_on": "ON", "payload_off": "OFF",
                "icon": "mdi:calendar-clock",
                "json_attributes_topic": self.state_topic(obj_id) + "_attr",
            })
            client.publish(self.disc_topic("switch", obj_id), json.dumps(config), retain=True)
            new_obj_ids.add(obj_id)
            count += 1

            for c in s.get("cycles", []):
                cid = c["id"]
                clabel = c.get("label", f"Ciclo {cid}")
                cobj = f"ciclo_{cid}"
                cconfig = self.base_config("switch", cobj, {
                    "name": f"{sname}: {clabel}",
                    "state_topic": self.state_topic(cobj),
                    "command_topic": self.cmd_topic(cobj),
                    "payload_on": "ON", "payload_off": "OFF",
                    "icon": "mdi:calendar-check",
                    "json_attributes_topic": self.state_topic(cobj) + "_attr",
                })
                client.publish(self.disc_topic("switch", cobj), json.dumps(cconfig), retain=True)
                client.publish(
                    self.state_topic(cobj) + "_attr",
                    json.dumps({"device_id": self.id, "cycle_id": cid, "strategy_id": sid}),
                    retain=True,
                )
                new_obj_ids.add(cobj)
                count += 1

        orphans = self.published_obj_ids - new_obj_ids
        for orphan in orphans:
            client.publish(self.disc_topic("switch", orphan), "", retain=True)
            client.publish(self.state_topic(orphan), "", retain=True)
            logger.info("[%s] Topic orfano rimosso: %s", self.id, orphan)

        self.published_obj_ids = new_obj_ids
        _save_published_ids(self.id, new_obj_ids)
        logger.info("[%s] Autodiscovery strategie pubblicato (%d switch)", self.id, count)

    def publish_strategy_states(self, client: mqtt.Client, strategies: list):
        now = time.time()
        for s in strategies:
            sid = s["id"]
            if sid in self.local_overrides:
                override_active, override_ts = self.local_overrides[sid]
                if now - override_ts < _OVERRIDE_TTL:
                    state = "ON" if override_active else "OFF"
                    logger.debug("[%s] Strategia %d: uso override locale (%s)", self.id, sid, state)
                    client.publish(self.state_topic(f"strategia_{sid}"), state, retain=True)
                    continue
                del self.local_overrides[sid]

            state = "ON" if s["active"] else "OFF"
            client.publish(self.state_topic(f"strategia_{sid}"), state, retain=True)
            attrs = json.dumps({
                "device_id": self.id,
                "output_valve": s.get("output_valve", 1),
                "strategy_name": s["name"],
                "strategy_id": s["id"],
            })
            client.publish(self.state_topic(f"strategia_{sid}") + "_attr", attrs, retain=True)
            for c in s.get("cycles", []):
                cstate = "ON" if c["active"] else "OFF"
                client.publish(self.state_topic(f"ciclo_{c['id']}"), cstate, retain=True)

    def publish_status(self, client: mqtt.Client, status: dict):
        stato_map = {0: "Offline", 1: "Attivo", 2: "In pausa", 3: "Nebulizzazione", 4: "Preparazione", 5: "Pulizia"}
        stato = stato_map.get(status.get("status", 0), status.get("status_text", "Sconosciuto"))
        alert = status.get("alert", {})
        alert_on = "ON" if alert.get("alert_status", 0) != 0 else "OFF"
        battery = max(0, int(status.get("battery_percent", 0)))
        tank1 = max(0, int(status.get("tank_1_fill", 0)))
        tank2 = max(0, int(status.get("tank_2_fill", 0)))
        next_t = status.get("next_treatment_formatted", "N/A")
        sync_at = status.get("synchronised_at", "N/A")
        qs_disabled = status.get("quickstart_disabled", True)
        qs_status = status.get("quickstart_status", 0)
        qs_avail = "OFF" if qs_disabled else "ON"
        qs_attivo = "ON" if qs_status == 1 else "OFF"

        payloads = {
            "device_name": self.name,
            "device_id": self.id,
            "stato": stato,
            "batteria": battery,
            "serbatoio_1": tank1,
            "serbatoio_2": tank2,
            "prossimo_trattamento": next_t,
            "sincronizzato": sync_at,
            "alert": alert_on,
            "quickstart_disponibile": qs_avail,
            "quickstart_attivo": qs_attivo,
        }
        for obj_id, value in payloads.items():
            client.publish(self.state_topic(obj_id), str(value), retain=True)

        self.publish_status_attributes(
            client,
            battery_percent=battery,
            tank_1_fill=tank1,
            tank_2_fill=tank2,
            quickstart_available=qs_avail,
            quickstart_active=qs_attivo,
        )

        logger.info(
            "[%s] Device: %s | Stato: %s | Batteria: %d%% | S1: %d%% | S2: %d%% | QS: avail=%s attivo=%s",
            self.id, self.name, stato, battery, tank1, tank2, qs_avail, qs_attivo,
        )

    def publish_tank_info(self, client: mqtt.Client, tank_num: int, info: dict):
        if not info:
            return
        liquid = info.get("tank_liquid", "N/A")
        tipo = info.get("tank_type", "")
        dil = info.get("tank_dilution", "")
        label = f"{liquid} ({tipo} {dil}%)".strip() if tipo else liquid
        client.publish(self.state_topic(f"liquido_{tank_num}"), label, retain=True)
        client.publish(self.state_topic(f"tanica_{tank_num}_nome"), str(liquid), retain=True)
        client.publish(self.state_topic(f"tanica_{tank_num}_diluizione"), str(dil), retain=True)
        client.publish(self.state_topic(f"tanica_{tank_num}_tipo"), str(tipo), retain=True)
        client.publish(self.state_topic(f"liquido_{tank_num}") + "_attr", json.dumps({
            "device_id": self.id,
            "tank": tank_num,
            "liquid": liquid,
            "dilution": dil,
            "type": tipo,
        }), retain=True)
        logger.info("[%s] Serbatoio %d: %s", self.id, tank_num, label)

    def publish_geyser_settings(self, client: mqtt.Client):
        settings = self.api.get_geyser_settings()
        if not settings:
            logger.warning("[%s] Impostazioni Geyser non disponibili.", self.id)
            return

        payloads = {
            "zona_1_ugelli": settings.get("nozzles"),
            "zona_1_tubo_m": settings.get("tube_length"),
            "zona_2_ugelli": settings.get("nozzles_2"),
            "zona_2_tubo_m": settings.get("tube_length_2"),
            "buzzer_off": "ON" if settings.get("buzzer_off") else "OFF",
        }
        for obj_id, value in payloads.items():
            if value is not None:
                client.publish(self.state_topic(obj_id), str(value), retain=True)

        self.publish_status_attributes(
            client,
            nozzles=settings.get("nozzles"),
            tube_length=settings.get("tube_length"),
            nozzles_2=settings.get("nozzles_2"),
            tube_length_2=settings.get("tube_length_2"),
            buzzer_off=settings.get("buzzer_off"),
        )

    def publish_all_tanks(self, client: mqtt.Client):
        for tank_num in [1, 2]:
            info = self.api.get_tank(tank_num)
            self.publish_tank_info(client, tank_num, info)
            if info:
                liquid = info.get("tank_liquid", "").split()[0] if info.get("tank_liquid") else f"S{tank_num}"
                self.tank_names[tank_num] = liquid

    def publish_device_settings(self, client: mqtt.Client):
        self.publish_geyser_settings(client)
        self.publish_all_tanks(client)

    # ------------------------------
    # API lifecycle
    # ------------------------------
    def login_until_ok(self):
        self.api = GeyserAPI(self.email, self.password)
        retries = 0
        while not self.api.login():
            retries += 1
            wait = min(30 * retries, 300)
            logger.error("[%s] Login fallito — riprovo tra %ds", self.id, wait)
            time.sleep(wait)

    def enrich_strategies(self, strategies: list):
        if strategies is None:
            return None
        all_days = "1111111"
        for s in strategies:
            for c in s.get("cycles", []):
                try:
                    detail = self.api.get_cycle(c["id"])
                    if not detail:
                        continue
                    time_str = detail.get("time", "")
                    dur = int(detail.get("nebulization", detail.get("duration", 0)))
                    days_raw = detail.get("days", "")
                    if days_raw == all_days:
                        days_label = "ogni giorno"
                    elif isinstance(days_raw, str) and len(days_raw) == 7:
                        labels = ["L", "M", "M", "G", "V", "S", "D"]
                        positions = [1, 2, 3, 4, 5, 6, 0]
                        active_days = "".join(labels[i] for i, pos in enumerate(positions) if days_raw[pos] == "1")
                        if active_days in ("LMMGVSD", ""):
                            days_label = "ogni giorno" if active_days else ""
                        elif active_days == "LMMGV":
                            days_label = "L→V"
                        elif active_days == "SD":
                            days_label = "S·D"
                        elif active_days == "LMMGVS":
                            days_label = "L→S"
                        else:
                            days_label = active_days
                    else:
                        days_label = ""

                    label = time_str or f"{int(detail.get('time_hour', 0)):02d}:{int(detail.get('time_minute', 0)):02d}"
                    if dur:
                        label += f" · {dur}s"
                    if days_label:
                        label += f" · {days_label}"
                    tank_num = int(detail.get("tank", 0))
                    tank_name = self.tank_names.get(tank_num, "")
                    if tank_name:
                        label += f" · {tank_name}"
                    c["active"] = bool(detail.get("active", True))
                    c["label"] = label
                except Exception as e:
                    logger.debug("[%s] Get_Cycle %s fallito: %s", self.id, c.get("id"), e)
        return strategies

    def initial_load(self, client: mqtt.Client):
        self.publish_device_settings(client)

        self.strategies_cache = self.api.get_strategies()
        if self.strategies_cache is None:
            logger.warning("[%s] Lettura strategie fallita durante initial_load.", self.id)
            return
        self.enrich_strategies(self.strategies_cache)
        self.publish_strategy_discovery(client, self.strategies_cache)
        self.publish_strategy_states(client, self.strategies_cache)
        if not self.strategies_cache:
            logger.warning("[%s] Nessuna strategia trovata.", self.id)

    def reload_strategies(self, client: mqtt.Client):
        logger.info("[%s] Ricaricamento strategie...", self.id)
        new_strategies = self.api.get_strategies()
        if new_strategies is None:
            logger.warning("[%s] get_strategies() ha fallito (None) — skip reload per preservare entità.", self.id)
            return
        self.enrich_strategies(new_strategies)
        self.strategies_cache = new_strategies
        self.publish_strategy_discovery(client, new_strategies)
        self.publish_strategy_states(client, new_strategies)
        logger.info("[%s] Strategie ricaricate: %d", self.id, len(new_strategies))
        client.publish(f"{self.topic_base}/strategies/updated", "1", retain=False)

    def poll_once(self, client: mqtt.Client):
        try:
            status = self.api.get_status()
            if status:
                self.publish_status(client, status)
            else:
                logger.warning("[%s] Nessuno stato ricevuto dal Geyser.", self.id)
                client.publish(self.state_topic("stato"), "Offline", retain=True)
        except Exception as e:
            logger.error("[%s] Errore nel poll: %s", self.id, e)

    # ------------------------------
    # Comandi MQTT
    # ------------------------------
    def handle_message(self, client: mqtt.Client, suffix_parts: list, payload: str):
        suffix = "/".join(suffix_parts)
        logger.info("[%s] CMD ricevuto: %s → %s", self.id, suffix, payload)

        if suffix == "quickstart/cmd":
            self.handle_quickstart(client, payload)
            return

        m = re.match(r"strategia_(\d+)/cmd$", suffix)
        if m:
            self.handle_strategy_toggle(client, int(m.group(1)), payload)
            return

        m = re.match(r"ciclo_(\d+)/cmd$", suffix)
        if m:
            self.handle_cycle_toggle(client, int(m.group(1)), payload)
            return

        if suffix == "cmd/delete_strategy":
            self.handle_delete_strategy(client, payload)
            return

        if suffix == "cmd/delete_cycle":
            self.handle_delete_cycle(client, payload)
            return

        if suffix == "cmd/create_strategy":
            self.handle_create_strategy(client, payload)
            return

        if suffix == "cmd/create_cycle":
            self.handle_create_cycle(client, payload)
            return

        if suffix == "cmd/set_geyser_settings":
            self.handle_set_geyser_settings(client, payload)
            return

        if suffix == "cmd/set_tank":
            self.handle_set_tank(client, payload)
            return

        if suffix == "cmd/reload":
            self.publish_device_settings(client)
            self.reload_strategies(client)
            return

        logger.warning("[%s] Comando non riconosciuto: %s", self.id, suffix)

    def handle_set_geyser_settings(self, client: mqtt.Client, payload: str):
        try:
            data = json.loads(payload) if payload else {}
            nozzles = int(data.get("nozzles"))
            tube_length = str(data.get("tube_length", "")).strip()
            nozzles_2_raw = data.get("nozzles_2", None)
            tube_length_2_raw = data.get("tube_length_2", None)
            nozzles_2 = int(nozzles_2_raw) if nozzles_2_raw not in (None, "") else None
            tube_length_2 = str(tube_length_2_raw).strip() if tube_length_2_raw not in (None, "") else None
            buzzer_off = bool(data.get("buzzer_off", False))

            if not (20 <= nozzles <= 60):
                logger.error("[%s] nozzles zona 1 fuori range 20-60: %s", self.id, nozzles); return
            if nozzles_2 is not None and not (20 <= nozzles_2 <= 60):
                logger.error("[%s] nozzles zona 2 fuori range 20-60: %s", self.id, nozzles_2); return
            if not tube_length:
                logger.error("[%s] tube_length zona 1 vuoto", self.id); return

            ok = self.api.set_geyser_settings(nozzles, tube_length, nozzles_2, tube_length_2, buzzer_off)
            if ok:
                logger.info("[%s] Impostazioni zone aggiornate.", self.id)
                self.publish_geyser_settings(client)
                self.poll_once(client)
            else:
                logger.error("[%s] Set_Settings fallito.", self.id)
        except Exception as e:
            logger.error("[%s] handle_set_geyser_settings errore: %s", self.id, e)

    def handle_set_tank(self, client: mqtt.Client, payload: str):
        try:
            data = json.loads(payload) if payload else {}
            tank = int(data.get("tank"))
            liquid = str(data.get("liquid", "")).strip()
            dilution = str(data.get("dilution", "")).replace(",", ".").strip()
            type_ = str(data.get("type", "")).strip()

            if tank not in (1, 2):
                logger.error("[%s] tank deve essere 1 o 2: %s", self.id, tank); return
            if not liquid:
                logger.error("[%s] liquid vuoto per tanica %d", self.id, tank); return
            try:
                dilution_f = float(dilution)
                if dilution_f <= 0 or dilution_f > 100:
                    logger.error("[%s] dilution fuori range 0-100: %s", self.id, dilution); return
            except Exception:
                logger.error("[%s] dilution non numerica: %s", self.id, dilution); return

            ok = self.api.set_tank(tank, liquid, dilution, type_)
            if ok:
                logger.info("[%s] Tanica %d aggiornata.", self.id, tank)
                info = self.api.get_tank(tank)
                self.publish_tank_info(client, tank, info)
                self.poll_once(client)
                self.reload_strategies(client)
            else:
                logger.error("[%s] Set_Tank fallito per tanica %d.", self.id, tank)
        except Exception as e:
            logger.error("[%s] handle_set_tank errore: %s", self.id, e)

    def handle_quickstart(self, client: mqtt.Client, payload: str):
        status = self.api.get_status()
        if status and status.get("quickstart_disabled", False):
            logger.warning("[%s] Quick Start non disponibile (trattamento in corso).", self.id)
            client.publish(self.state_topic("quickstart_disponibile"), "OFF", retain=True)
            return

        try:
            params = json.loads(payload) if payload else {}
        except Exception:
            params = {}

        tank = int(params.get("tank", 1))
        nebulization = int(params.get("nebulization", 30))
        output_valve = int(params.get("output_valve", 1))
        type_ = int(params.get("type", 1))

        if not (0 <= tank <= 2):
            logger.error("[%s] tank deve essere 0, 1 o 2", self.id); return
        if not (0 <= nebulization <= 150):
            logger.error("[%s] nebulization deve essere 0-150", self.id); return
        if not (1 <= output_valve <= 2):
            logger.error("[%s] output_valve deve essere 1 o 2", self.id); return

        logger.info("[%s] Avvio Quick Start: tank=%d, durata=%ds, zona=%d", self.id, tank, nebulization, output_valve)
        ok = self.api.set_quickstart(tank=tank - 1 if tank > 0 else 0, nebulization=nebulization,
                                     output_valve=output_valve, type_=type_)
        if ok:
            client.publish(self.state_topic("quickstart_attivo"), "ON", retain=True)
        else:
            logger.error("[%s] Quick Start fallito.", self.id)

    def handle_strategy_toggle(self, client: mqtt.Client, strategy_id: int, payload: str):
        active = payload.strip().upper() == "ON"
        ok = self.api.set_strategy_status(strategy_id, active)
        if ok:
            state = "ON" if active else "OFF"
            client.publish(self.state_topic(f"strategia_{strategy_id}"), state, retain=True)
            for s in self.strategies_cache:
                if s["id"] == strategy_id:
                    s["active"] = active
            self.local_overrides[strategy_id] = (active, time.time())
            logger.info("[%s] Strategia %d → %s", self.id, strategy_id, state)
        else:
            logger.error("[%s] Set_StrategyStatus fallito per strategia %d", self.id, strategy_id)

    def handle_cycle_toggle(self, client: mqtt.Client, cycle_id: int, payload: str):
        active = payload.strip().upper() == "ON"
        ok = self.api.set_cycle_status(cycle_id, active)
        if ok:
            state = "ON" if active else "OFF"
            client.publish(self.state_topic(f"ciclo_{cycle_id}"), state, retain=True)
            for s in self.strategies_cache:
                for c in s.get("cycles", []):
                    if c["id"] == cycle_id:
                        c["active"] = active
            logger.info("[%s] Ciclo %d → %s", self.id, cycle_id, state)
        else:
            logger.error("[%s] Set_CycleStatus fallito per ciclo %d", self.id, cycle_id)

    def handle_delete_strategy(self, client: mqtt.Client, payload: str):
        try:
            data = json.loads(payload)
            sid = int(data["strategy_id"])
            ok = self.api.delete_strategy(sid)
            if ok:
                logger.info("[%s] Strategia %d eliminata.", self.id, sid)
                self.reload_strategies(client)
            else:
                logger.error("[%s] Eliminazione strategia %d fallita.", self.id, sid)
        except Exception as e:
            logger.error("[%s] handle_delete_strategy errore: %s", self.id, e)

    def handle_delete_cycle(self, client: mqtt.Client, payload: str):
        try:
            data = json.loads(payload)
            cid = int(data["cycle_id"])
            ok = self.api.delete_cycle(cid)
            if ok:
                logger.info("[%s] Ciclo %d eliminato.", self.id, cid)
                self.reload_strategies(client)
            else:
                logger.error("[%s] Eliminazione ciclo %d fallita.", self.id, cid)
        except Exception as e:
            logger.error("[%s] handle_delete_cycle errore: %s", self.id, e)

    def handle_create_strategy(self, client: mqtt.Client, payload: str):
        try:
            data = json.loads(payload)
            name = data["name"]
            output_valve = int(data.get("output_valve", 1))
            result = self.api.create_strategy(name, output_valve)
            if result:
                logger.info("[%s] Strategia creata: %s", self.id, result)
                self.reload_strategies(client)
            else:
                logger.error("[%s] Creazione strategia fallita.", self.id)
        except Exception as e:
            logger.error("[%s] handle_create_strategy errore: %s", self.id, e)

    def handle_create_cycle(self, client: mqtt.Client, payload: str):
        try:
            data = json.loads(payload)
            strategy_id = int(data["strategy_id"])
            tank = int(data.get("tank", 1))
            time_hour = int(data.get("hour", 8))
            time_minute = int(data.get("minute", 0))
            nebulization = int(data.get("nebulization", 60))
            days_shifted = data.get("days_shifted", [1, 1, 1, 1, 1, 1, 1])
            result = self.api.create_cycle(strategy_id, tank, time_hour, time_minute, nebulization, days_shifted)
            if result:
                logger.info("[%s] Ciclo creato: %s", self.id, result)
                self.reload_strategies(client)
            else:
                logger.error("[%s] Creazione ciclo fallita.", self.id)
        except Exception as e:
            logger.error("[%s] handle_create_cycle errore: %s", self.id, e)


DEVICE_CONFIGS = normalize_devices(OPTIONS)
WORKERS: List[GeyserDeviceWorker] = [GeyserDeviceWorker(cfg) for cfg in DEVICE_CONFIGS]
WORKERS_BY_ID: Dict[str, GeyserDeviceWorker] = {w.id: w for w in WORKERS}


# ------------------------------------------------------------------
# MQTT callbacks
# ------------------------------------------------------------------

def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    topic = msg.topic
    parts = topic.split("/")

    if len(parts) < 3 or parts[0] != TOPIC_ROOT:
        logger.warning("CMD ignorato, topic fuori namespace: %s", topic)
        return

    device_id = parts[1]
    worker = WORKERS_BY_ID.get(device_id)
    if not worker:
        logger.warning("CMD ignorato, device_id sconosciuto: %s topic=%s", device_id, topic)
        return

    worker.handle_message(client, parts[2:], payload)


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        logger.info("MQTT connesso a %s:%d", MQTT_HOST, MQTT_PORT)
        client.subscribe(f"{TOPIC_ROOT}/+/+/cmd")
        client.subscribe(f"{TOPIC_ROOT}/+/cmd/#")
        for worker in WORKERS:
            worker.publish_discovery(client)
    else:
        logger.error("MQTT connessione fallita, rc=%s", reason_code)


def write_dashboard_vars():
    devices_payload = [
        {
            "id": w.id,
            "name": w.name,
            "entity_prefix": w.device_uid,
            "topic_base": w.topic_base,
        }
        for w in WORKERS
    ]
    for www in ["/config/www", "/homeassistant/www", "/share/www"]:
        try:
            os.makedirs(www, exist_ok=True)
            with open(f"{www}/geyser_token.js", "w") as tf:
                tf.write(f"var GEYSER_TOKEN = '{DASHBOARD_TOKEN}';\n")
                tf.write(f"var GEYSER_DEVICES = {json.dumps(devices_payload, ensure_ascii=False)};\n")
                tf.write(f"var GEYSER_DASHBOARD_VERSION = {json.dumps(SW_VERSION)};\n")
                first_name = devices_payload[0]["name"] if devices_payload else DEVICE_NAME_DEFAULT
                tf.write(f"var GEYSER_DEVICE_NAME = {json.dumps(first_name, ensure_ascii=False)};\n")
            logger.info("geyser_token.js scritto in %s (%d device)", www, len(devices_payload))
            return
        except Exception as e:
            logger.warning("Scrittura in %s fallita: %s", www, e)


# ------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------

def main():
    if not WORKERS:
        logger.error("Nessun device configurato. Aggiungi options.devices oppure email/password legacy.")
        sys.exit(1)

    logger.info("=== Geyser PRO Addon v%s avviato ===", SW_VERSION)
    logger.info("Device configurati: %s", ", ".join(f"{w.id}={w.name}" for w in WORKERS))
    logger.info("Poll interval: %d sec", POLL_INTERVAL)
    write_dashboard_vars()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="geyser_pro_bridge")
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    # Last will non può coprire ogni device singolarmente, quindi pubblichiamo offline in shutdown.
    logger.info("Connessione MQTT a %s:%d...", MQTT_HOST, MQTT_PORT)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    def shutdown(sig, frame):
        logger.info("Shutdown richiesto.")
        for worker in WORKERS:
            client.publish(worker.state_topic("stato"), "Offline", retain=True)
        client.loop_stop()
        client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    for worker in WORKERS:
        worker.login_until_ok()
        worker.initial_load(client)

    reload_counter = 0
    reload_every = max(1, 300 // POLL_INTERVAL)
    restart_counter = 0
    restart_every = max(1, 14400 // POLL_INTERVAL)

    while True:
        for worker in WORKERS:
            worker.poll_once(client)

        reload_counter += 1
        if reload_counter >= reload_every:
            reload_counter = 0
            for worker in WORKERS:
                worker.publish_device_settings(client)
                worker.reload_strategies(client)

        restart_counter += 1
        if restart_counter >= restart_every:
            logger.info("Riavvio automatico programmato (ogni 4 ore) — arrivederci!")
            for worker in WORKERS:
                client.publish(worker.state_topic("stato"), "Offline", retain=True)
            client.loop_stop()
            client.disconnect()
            sys.exit(0)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
