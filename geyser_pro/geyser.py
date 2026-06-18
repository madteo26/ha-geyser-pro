"""
Geyser PRO API Client
Handles login, token management and all API calls to app.stockergarden.com
"""

import requests
import logging
import time
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)

API_BASE = "https://app.stockergarden.com"
API_PHP  = f"{API_BASE}/api.php"
HEADERS  = {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


class GeyserAPI:
    def __init__(self, email: str, password: str):
        self.email       = email
        self.password    = password
        self.session     = requests.Session()
        self.token       = None
        self._last_login = 0

    def login(self) -> bool:
        logger.info("Login a MyGeyser come %s...", self.email)
        try:
            resp = self.session.post(
                f"{API_BASE}/index.php?login",
                data={
                    "email":        self.email,
                    "password":     self.password,
                    "submit_login": "LOG IN",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
                allow_redirects=True,
            )
            resp.raise_for_status()
            html = resp.text
            if "form-login-email" in html:
                logger.error("Login fallito — credenziali errate")
                return False
            match = re.search(r'var\s+oToken\s*=\s*(\{[^;]+\});', html)
            if match:
                self.token = json.loads(match.group(1))
                logger.info("Token estratto dall'HTML — geyser_id: %s", self.token.get("geyser_id"))
                self._last_login = time.time()
                return True
            data = self._call("Get_GeyserStatus", {})
            if data and data.get("error_code", 1) == 0:
                self._last_login = time.time()
                return True
            logger.error("Impossibile ottenere token dopo login")
            return False
        except Exception as e:
            logger.error("Login exception: %s", e)
            return False

    def _is_token_valid(self) -> bool:
        if not self.token:
            return False
        try:
            exp_str = self.token.get("expires_at") or self.token.get("expiration_timestamp")
            if not exp_str:
                return False
            exp = datetime.fromisoformat(str(exp_str))
            remaining = (exp - datetime.now()).total_seconds()
            logger.debug("Token scade tra %.0f secondi", remaining)
            return remaining > 60
        except Exception as e:
            logger.debug("Errore controllo scadenza token: %s", e)
            return False

    def _ensure_auth(self) -> bool:
        if not self._is_token_valid():
            return self.login()
        return True

    def _call(self, endpoint: str, data: dict, retries: int = 2):
        payload = {"data": data}
        if self.token:
            payload["token"] = self.token
        for attempt in range(retries + 1):
            try:
                resp = self.session.post(
                    f"{API_PHP}?{endpoint}",
                    json=payload,
                    headers=HEADERS,
                    timeout=15,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.debug("%s → error_code=%s", endpoint, result.get("error_code"))
                if "token" in result and isinstance(result["token"], dict):
                    self.token = result["token"]
                val = result.get("value", {})
                if isinstance(val, dict) and "token" in val:
                    self.token = val["token"]
                return result
            except Exception as e:
                if attempt < retries:
                    logger.debug("API call %s fallita (tentativo %d/%d): %s — riprovo...",
                                 endpoint, attempt + 1, retries + 1, e)
                    self.session = requests.Session()
                    time.sleep(1)
                else:
                    logger.error("API call %s fallita dopo %d tentativi: %s",
                                 endpoint, retries + 1, e)
                    return None

    def _auth_call(self, endpoint: str, data: dict):
        if not self._ensure_auth():
            return None
        return self._call(endpoint, data)

    def get_status(self):
        result = self._auth_call("Get_GeyserStatus", {})
        if result and result.get("error_code", 1) == 0:
            return result.get("value")
        return None

    def set_quickstart(self, tank: int = 0, nebulization: int = 32,
                       output_valve: int = 1, type_: int = 1) -> bool:
        result = self._auth_call("Set_Quickstart", {
            "type":         type_,
            "tank":         str(tank),
            "nebulization": nebulization,
            "output_valve": str(output_valve),
        })
        return result is not None and result.get("error_code", 1) == 0

    def check_quickstart(self):
        result = self._auth_call("Check_NewQuickStart", {})
        if result and result.get("error_code", 1) == 0:
            return result.get("value")
        return None

    def set_strategy_status(self, strategy_id: int, active: bool) -> bool:
        result = self._auth_call("Set_StrategyStatus", {
            "geyser_strategy_id": strategy_id,
            "active":             active,
        })
        return result is not None and result.get("error_code", 1) == 0

    def set_cycle_status(self, cycle_id: int, active: bool) -> bool:
        result = self._auth_call("Set_CycleStatus", {
            "cycle":  cycle_id,
            "active": active,
        })
        return result is not None and result.get("error_code", 1) == 0

    def set_tank_status(self, tank: int, active: bool) -> bool:
        result = self._auth_call("Set_TankStatus", {
            "tank":   tank,
            "active": active,
        })
        return result is not None and result.get("error_code", 1) == 0

    def get_tank(self, tank: int):
        result = self._auth_call("Get_Tank", {"tank": tank})
        if result and result.get("error_code", 1) == 0:
            return result.get("value")
        return None

    def get_strategies(self) -> list:
        """
        Carica strategie e cicli dalla pagina HTML ?id=2001.
        Ritorna lista di dict con:
          { id, name, active, output_valve, cycles: [{id, active, label}] }
        """
        if not self._ensure_auth():
            return []
        try:
            resp = self.session.get(f"{API_BASE}/index.php?id=2001", timeout=15)
            resp.raise_for_status()
            html = resp.text

            # Se Stocker ci rimanda al login o una pagina non contenente il markup strategie,
            # non trattarla come "zero strategie": è un errore temporaneo di sessione/parsing.
            # Se qui tornassimo [], il backend cancellerebbe i retained MQTT di strategie/cicli.
            if "form-login-email" in html or "submit_login" in html:
                logger.warning("Pagina strategie sembra login/non autenticata — ritorno None")
                return None
            if ("setstatusStrategy" not in html and
                "strategy-output_valve" not in html and
                "strategy-cycle" not in html):
                logger.warning("Pagina strategie senza marker attesi (len=%d) — ritorno None", len(html))
                return None

            # Determina la zona di ogni strategia cercando in quale tab appare
            zone_map = {}
            for valve in [1, 2]:
                m1 = "id='strategy-output_valve-" + str(valve) + "'"
                m2 = 'id="strategy-output_valve-' + str(valve) + '"'
                zs = html.find(m1)
                if zs == -1:
                    zs = html.find(m2)
                nm = "strategy-output_valve-" + str(3 - valve)
                ze = html.find(nm, zs + 10) if zs >= 0 else -1
                if zs >= 0:
                    zb = html[zs:ze if ze > 0 else zs + 50000]
                    import re as _re
                    for sid in _re.findall(r"setstatusStrategy\((\d+),", zb):
                        zone_map[sid] = valve
            logger.debug("Zone strategie: %s", zone_map)

            # --- Nomi strategie: cerca h2/div con classe strategy-title o simile
            # Pattern osservato: <div id="strategy-XXXX" ...> ... <h2>Nome</h2>
            # oppure: <input id="strategy-name-XXXX" ... value="Nome">
            strategy_name_map = {}

            # Cerca blocchi strategy con apici singoli o doppi
            # Pattern HTML: id='strategy-XXXX' o id="strategy-XXXX"
            strategy_blocks = re.findall(
                r'id=["\']strategy-(\d+)["\'][^>]*>(.*?)(?=id=["\']strategy-\d+["\']|id=["\']strategy-add|$)',
                html, re.DOTALL
            )
            for sid, block in strategy_blocks:
                # Nome: cerca h2 o h3 nel blocco
                h_match = re.search(r'<h[23][^>]*>\s*([^<]+)\s*</h[23]>', block)
                if h_match and h_match.group(1).strip():
                    strategy_name_map[sid] = h_match.group(1).strip()
                # Fallback: input value
                if sid not in strategy_name_map:
                    v_match = re.search(r'value=["\']([^"\'>]+)["\']', block)
                    if v_match:
                        strategy_name_map[sid] = v_match.group(1).strip()

            logger.debug("Nomi strategie: %s", strategy_name_map)

            # --- Strategie attive: setstatusStrategy(ID, false) = attiva
            status_calls = re.findall(
                r"setstatusStrategy\((\d+),(true|false)\)", html
            )

            strategies = []
            seen_strategy_ids = set()
            for sid, status_val in status_calls:
                if sid in seen_strategy_ids:
                    continue
                seen_strategy_ids.add(sid)
                active = (status_val == "false")  # false=Disable=attiva

                # --- Cicli di questa strategia
                # Cerca blocco strategy per trovare i cicli dentro
                cycles = []
                block_match = re.search(
                    r'id=["\']strategy-' + sid + r'["\'][^>]*>(.*?)(?=id=["\']strategy-\d+["\']|id=["\']strategy-add|$)',
                    html, re.DOTALL
                )
                if block_match:
                    block = block_match.group(1)
                    # Cerca strategy-cycle-toggle-CID con apici singoli o doppi
                    cycle_toggles = re.findall(
                        r'id=["\']strategy-cycle-toggle-(\d+)["\']', block
                    )
                    cycle_checked = set(re.findall(
                        r'id=["\']strategy-cycle-toggle-(\d+)["\'][^>]*checked', block
                    ))
                    # Cerca label del ciclo: ora/durata vicino al toggle
                    for cid in cycle_toggles:
                        cycle_active = cid in cycle_checked
                        # Cerca il blocco del ciclo nell'HTML
                        ctx = re.search(
                            r'id=["\']strategy-cycle-' + cid + r'["\'][^>]*>(.*?)(?=id=["\']strategy-cycle-\d+["\']|class=["\']strategy-add|</div>\s*</div>\s*</div>|$)',
                            block, re.DOTALL
                        )
                        label = f"Ciclo {cid}"
                        if ctx:
                            ctx_text = ctx.group(1)
                            # Cerca orario nel formato HH:MM
                            times = re.findall(r'\b(\d{2}:\d{2})\b', ctx_text)
                            if times:
                                label = times[0]
                            else:
                                # Cerca anche nel blocco circostante
                                pos = block.find(f'strategy-cycle-toggle-{cid}')
                                if pos >= 0:
                                    surrounding = block[max(0, pos-300):pos+100]
                                    times2 = re.findall(r'\b(\d{2}:\d{2})\b', surrounding)
                                    if times2:
                                        label = times2[0]
                        cycles.append({
                            "id":     int(cid),
                            "active": cycle_active,
                            "label":  label,
                        })

                strategies.append({
                    "id":           int(sid),
                    "name":         strategy_name_map.get(sid, f"Strategia {sid}"),
                    "active":       active,
                    "output_valve": zone_map.get(sid, 1),
                    "cycles":       cycles,
                })

            logger.info("Strategie trovate: %d (cicli totali: %d)",
                        len(strategies),
                        sum(len(s["cycles"]) for s in strategies))
            logger.debug("Strategie: %s", strategies)
            return strategies

        except Exception as e:
            logger.error("get_strategies fallito: %s", e)
            return None  # None = errore, [] = davvero vuoto

    def get_cycle(self, cycle_id: int):
        """Recupera i dettagli di un ciclo: orario, durata, giorni."""
        result = self._auth_call("Get_Cycle", {"cycle": cycle_id})
        if result and result.get("error_code", 1) == 0:
            return result.get("value")
        return None


    def get_geyser_settings(self):
        """
        Legge dalla pagina impostazioni della webapp Stocker:
          - nozzles / tube_length zona 1
          - nozzles_2 / tube_length_2 zona 2
          - buzzer_off
        La webapp non usa un endpoint Get_Settings: i valori sono renderizzati
        direttamente nell'HTML di index.php?id=4004. Sì, meraviglioso.
        """
        if not self._ensure_auth():
            return None
        try:
            resp = self.session.get(f"{API_BASE}/index.php?id=4004", timeout=15)
            resp.raise_for_status()
            html = resp.text

            def _input_value(field_id, default=None):
                m = re.search(
                    r'id=["\']' + re.escape(field_id) + r'["\'][^>]*\bvalue=["\']([^"\']*)["\']',
                    html,
                    re.IGNORECASE | re.DOTALL,
                )
                return m.group(1).strip() if m else default

            def _int_value(field_id, default=None):
                v = _input_value(field_id, default)
                if v is None or str(v).strip() == "":
                    return default
                try:
                    return int(float(str(v).replace(",", ".")))
                except Exception:
                    return default

            def _num_text(field_id, default=None):
                v = _input_value(field_id, default)
                return str(v).strip() if v is not None else default

            buzzer_m = re.search(
                r'id=["\']form-geyser-buzzer_off["\'][^>]*',
                html,
                re.IGNORECASE | re.DOTALL,
            )
            # Nella webapp: checkbox checked => segnale acustico attivo => buzzer_off=false.
            buzzer_off = None
            if buzzer_m:
                buzzer_off = "checked" not in buzzer_m.group(0).lower()

            data = {
                "nozzles": _int_value("form-geyser-nozzles"),
                "tube_length": _num_text("form-geyser-tube_length"),
                "nozzles_2": _int_value("form-geyser-nozzles_2"),
                "tube_length_2": _num_text("form-geyser-tube_length_2"),
                "buzzer_off": buzzer_off,
            }
            logger.debug("Impostazioni geyser lette da HTML: %s", data)
            return data
        except Exception as e:
            logger.error("get_geyser_settings fallito: %s", e)
            return None

    def set_geyser_settings(self, nozzles, tube_length, nozzles_2=None, tube_length_2=None, buzzer_off=False) -> bool:
        """
        Endpoint webapp: Set_Settings
        Payload osservato:
        {
          nozzles, tube_length, nozzles_2, tube_length_2, buzzer_off
        }
        """
        result = self._auth_call("Set_Settings", {
            "nozzles": nozzles,
            "tube_length": tube_length,
            "nozzles_2": nozzles_2,
            "tube_length_2": tube_length_2,
            "buzzer_off": bool(buzzer_off),
        })
        logger.debug("Set_Settings response: %s", result)
        return result is not None and result.get("error_code", 1) == 0

    def set_tank(self, tank, liquid, dilution, type_) -> bool:
        """
        Endpoint webapp: Set_Tank
        Payload osservato:
        {
          tank, liquid, dilution, type
        }
        """
        result = self._auth_call("Set_Tank", {
            "tank": str(tank),
            "liquid": liquid,
            "dilution": dilution,
            "type": type_,
        })
        logger.debug("Set_Tank response: %s", result)
        return result is not None and result.get("error_code", 1) == 0


    def delete_strategy(self, strategy_id: int) -> bool:
        result = self._auth_call("Delete_Strategy", {"geyser_strategy_id": str(strategy_id)})
        return result is not None and result.get("error_code", 1) == 0

    def delete_cycle(self, cycle_id: int) -> bool:
        result = self._auth_call("Delete_Cycle", {"geyser_treatment_id": str(cycle_id)})
        return result is not None and result.get("error_code", 1) == 0

    def create_strategy(self, name, output_valve=1):
        result = self._auth_call("Set_Strategy", {
            "name":         name,
            "output_valve": output_valve,
        })
        if result and result.get("error_code", 1) == 0:
            return result.get("value", {})
        return {}

    def create_cycle(self, strategy_id, tank, time_hour,
                     time_minute, nebulization, days_shifted):
        """
        days_shifted: lista di 7 interi 0/1, ordine [LUN, MAR, MER, GIO, VEN, SAB, DOM]
        duration: in millisecondi (nebulization secondi * 1000)
        """
        api_tank = tank  # API: 0=pulizia, 1=S1, 2=S2
        result = self._auth_call("Set_Cycle", {
            "geyser_treatment_id": 0,
            "geyser_strategy_id":  strategy_id,
            "type":                0,
            "tank":                api_tank,
            "time_hours":          time_hour,
            "time_minutes":        time_minute,
            "duration":            nebulization,
            "days_shifted":        days_shifted,
        })
        logger.debug("Set_Cycle response: %s", result)
        if result and result.get("error_code", 1) == 0:
            return result.get("value", {})
        logger.error("Set_Cycle errore: %s", result)
        return {}
