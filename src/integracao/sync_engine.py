# Sync engine for reusable functions that:

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient
from integracao.mappings.site_code_maps import SITE_CODE_MAPPING

logger = logging.getLogger(__name__)

V1_EVENT = os.getenv("V1_EVENT_NAME")

def get_participant_info(
    *, 
    record_id: str,
    redcap: RedcapClient,
    polotrial: PoloTrialClient,
    protocol_nickname: str
) -> Dict[str, Any]:
    """
    Retrieves essential participant IDs from the record_id.

    Returns:
    Dict with: co_voluntario, co_protocolo, co_participante
    """
    
    #1. Volunteer search
    volunteer = polotrial.find_volunteer_by_name(record_id)
    if not volunteer:
        raise RuntimeError(f"Volunteer not found in polotrial for record_id={record_id}")
    co_voluntario=int(volunteer['id'])
    
    # 2. Searching protocol site from V1
    v1_payload = redcap.export_record_eav(record_id, V1_EVENT)
    co_centro_raw = str(v1_payload.get('dados_pessoais_site')or '').strip()
    co_centro = SITE_CODE_MAPPING.get(co_centro_raw)
    if not co_centro:
        raise RuntimeError(f"Could not map centro = {co_centro_raw!r} to Polotrial")
    
    # 3. Searching protocol code from protocol nickname and site code
    protocol = polotrial.get_protocol(
        co_centro = co_centro,
        apelido_protocolo=protocol_nickname
    )
    if not protocol:
        raise RuntimeError(f"Protocol {protocol_nickname!r} not found for site {co_centro!r}")
    co_protocolo = int(protocol['id'])
    
    # 4. Identifying participant in protocol
    participant = polotrial.find_participant(
        co_voluntario = co_voluntario, 
        co_protocolo = co_protocolo
    )
    if not participant:
        raise RuntimeError(f"Participant not found for volunteer {co_voluntario!r} in protocol {co_protocolo!r}")
    co_participante = int(participant['id'])
    
    return {
        "co_voluntario": co_voluntario,
        "co_protocolo": co_protocolo,
        "co_participante": co_participante
    }

def update_visit_status(
    *,
    co_participante: int,
    nome_tarefa: str,
    visit_date: str,
    polotrial: PoloTrialClient
) -> int:
    """
    Updates the visit status in PoloTrial.

    Args:
        co_participante: Participant code in PoloTrial
        nome_tarefa: Task name to update
        visit_date: Date of the visit in 'YYYY-MM-DD' format
        polotrial: Instance of PoloTrialClient
    
    Returns:
        participante_visita_id: ID of the updated participant visit
    """
    
    visits = polotrial.list_participant_visits(co_participante = co_participante)
    visit = next((v for v in visits if v.get("nome_tarefa") == nome_tarefa), None)
    if not visit:
        raise RuntimeError(f"Participant visit with task name {nome_tarefa!r} not found for participant {co_participante!r} in Polotrial")
    
    participante_visita_id = int(visit['id'])
    
    desired={
        "data_estimada": visit_date,
        "data_realizada": visit_date,
        "status": 20 # 20 = Completed(realizada)
    }
    
    current = polotrial.get_participant_visit(participante_visita_id)
    if (
        str(current.get("data_realizada", ""))[:10] == str(desired["data_realizada"])[:10] and
        int(current.get("status", -1)) == desired["status"]
    ):
        logger.info("%s: already up to date (id=%s)", nome_tarefa, participante_visita_id)
    else:
        polotrial.update_participant_visit(participante_visita_id, desired)
        logger.info("%s: updated (id=%s)", nome_tarefa, participante_visita_id)
    
    return participante_visita_id

def sync_procedures(
    *,
    participante_visita_id: int,
    co_protocolo: int,
    procedures_map: List[Dict[str, Any]],
    redcap_payload: Dict[str, Any],
    polotrial: PoloTrialClient,
    visit_label: str,
) -> int:
    """
    Syncs procedures execution dates from Redcap to Polotrial
    
    Returns:
        count of procedures synced
    """
    
    # 1. Listing existing procedures in Polotrial for the visit
    pvp = polotrial.list_participant_visit_procedures(co_participante_visita=participante_visita_id)
    proto_proc = polotrial.list_protocol_procedures(co_protocolo=co_protocolo)
    
    pvp_df = pd.DataFrame(pvp)
    proto_df = pd.DataFrame(proto_proc)[["id", "co_procedimento", "nome_procedimento_estudo"]].rename(
        columns={
            "id": "co_protocolo_procedimento"
        }
    )
    
    merged = pd.merge(pvp_df, proto_df, on="co_protocolo_procedimento", how="left")
    
    total = 0
    for cfg in procedures_map:
        pattern = cfg["procedure_name"]
        # co_proc = cfg["co_procedimento"]
        check_field = cfg["redcap_check_field"]
        # The line `date_field = cfg["redcap_date_field"]` is attempting to access the value associated with the key "redcap_date_field" in the dictionary `cfg`.
        date_field = cfg["redcap_date_field"]
        
        if not (pattern and check_field and date_field):
            logger.warning("%s: Invalid procedure mapping config: %s. Skipping...", visit_label, cfg)
            continue
        
        to_sync = merged[
            merged["nome_procedimento_estudo"].str.contains(pattern, regex=True, na=False, flags=re.IGNORECASE) &
        (merged["data_executada"].isna() | (merged["data_executada"] == ""))
    ]
        
        if to_sync.empty:
            continue
    
        procedure_id = int(to_sync['id'].iloc[0])
        
        # Redcap date extraction
        redcap_date = get_date_from_redcap(redcap_payload, check_field, date_field)
        if not redcap_date:
            logger.info("%s: No date found in redcap for procedure %r", visit_label, pattern)
            continue
        
        # Format validation
        try:
            dt = datetime.strptime(redcap_date[:10], "%Y-%m-%d")
        except ValueError:
            logger.error("%s: Invalid date for %s: %r (expected format: YYYY-MM-DD)", visit_label, pattern, redcap_date)
            continue
        
        polotrial.update_participant_visit_procedure(
            procedure_id, 
            {"data_executada": dt.strftime("%Y-%m-%d")}
        )
        total += 1
        
    logger.info("%s: procedures synchronized: %d", visit_label, total)
    return total

def get_date_from_redcap(
    payload: Dict[str, Any],
    check_field: str,
    date_field: str
) -> Optional[str]:
    """
    Extracts the date from Redcap payload based on check and date fields.
    
    Returns:
        Date string in 'YYYY-MM-DD' format or None if not found/invalid
    """
    
    if date_field in payload and payload.get(date_field):
        check_value = str(payload.get(check_field, "")).strip().lower()
        
        if check_field != date_field and check_value in {"", "nao", "não", "0"}:
            logger.warning(
                "Date exists (%s) but check field %s indicates not done (value = %r). Skipping",
                date_field,
                check_field,
                check_value
            )
            return None
        return str(payload[date_field]).strip()
    return None


def sync_executor(
    *,
    merged_procedures_df: pd.DataFrame,
    redcap_payload: Dict[str, Any],
    executor_field: str,
    executor_date_field: str,
    procedure_pattern: str,
    polotrial: PoloTrialClient,
    visit_label: str
) -> None:
    """
    Syncs the executor information for a specific procedure.
    """
    
    executor_name = str(redcap_payload.get(executor_field, "")).strip()
    if not executor_name:
        logger.info("%s: %s is empty, skipping executor sync", visit_label, executor_field)
        return
    
    data_realizada = str(redcap_payload.get(executor_date_field) or "").strip()
    if not data_realizada:
        logger.info("%s: %s is empty, skipping executor sync", visit_label, executor_date_field)
        return
    
    proc = merged_procedures_df[
        merged_procedures_df["nome_procedimento_estudo"].astype(str).str.contains(procedure_pattern, regex=True, na=False, flags=re.IGNORECASE)
    ]
    if proc.empty:
        logger.warning("%s: No procedure found matching pattern %r for executor sync", visit_label, procedure_pattern)
        return
    
    procedure_id = int(proc['id'].iloc[0])
    if len(proc) > 1:
        logger.warning("%s: Multiple procedures found matching pattern %r. Using the first one (id=%s)", visit_label, procedure_pattern, procedure_id)
        
    # Searching executor name
    person = polotrial.find_person_by_name(executor_name)
    if not person:
        logger.error("%s: Executor %r not found in polotrial /pessoas endpoint", visit_label, executor_name)
        return
    executor_id = int(person['id'])
    
    # Verifying if the executor is already set
    existing_links = polotrial.list_procedure_executors(procedure_id)
    already_linked = any(int(x.get("executor", -1)) == executor_id for x in existing_links)
    if already_linked:
        logger.info(
            "%s: Executor %r (id=%s) already linked to procedure id=%s. Skipping...",
            visit_label,
            executor_name,
            executor_id,
            procedure_id
        )
        return
    
    # Creating the link
    payload = {
        "co_participante_visita_procedimento": procedure_id,
        "executor": executor_id,
        "data_realizada": data_realizada,
        "data_previsto_pagamento": "",
        "data_realizada_pagamento": "",
        "valor": "",
        "valor_total_procedimento": "",
        "observacoes": "",
    }
    
    created = polotrial.create_procedure_executor(payload)
    logger.info(
        "%s: executor atribuído. procedure_id = %s, executor_id = %s, response_id = %s",
        visit_label,
        procedure_id,
        executor_id,
        created.get("id"),
    )