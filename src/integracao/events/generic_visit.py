from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient
from integracao.sync_engine import (
    get_participant_info,
    update_visit_status,
    sync_procedures,
    sync_executor
)

from integracao.visits_catalog import VisitConfig

logger = logging.getLogger(__name__)

def sync_generic_visit(
    *,
    record_id: str,
    event_name: str,
    visit_config: VisitConfig,
    redcap: RedcapClient,
    polotrial: PoloTrialClient,
    protocol_nickname: str,
) -> None:
    """
    Generic handler to synchronize V3 or Visita não programada.
    
    """
    
    #1. Check if the visit requires PK.
    if visit_config.requires_pk is not None:
        pp_randomized = get_pp_randomized_from_v2(record_id, redcap)
        if visit_config.requires_pk and not pp_randomized:
            logger.info(
                        "%s: Skipping (requires PK = True, but participant pp_randomized = %s)",
                        visit_config.polotrial_visit_name,
                        pp_randomized,
                        )
            return
        if not visit_config.requires_pk and pp_randomized:
            logger.info(
                "%s: Skipping (requires PK = False, but participant pp_randomized = %s)",
                visit_config.polotrial_visit_name,
                pp_randomized,
            )
    #2. Get participant info from PoloTrial.
    redcap_payload = redcap.export_record_eav(record_id, event_name)
    
    #3. Get visit date from REDCap data.
    visit_date = str(redcap_payload.get(visit_config.date_field) or "").strip()
    if not visit_date:
        logger.info(
            "%s: date field %s is empty. Skipping sync",
            visit_config.polotrial_visit_name,
            visit_config.date_field,
        )
        return
    
    #4. Get participant ID
    info = get_participant_info(
        record_id=record_id,
        redcap=redcap,
        polotrial=polotrial,
        protocol_nickname=protocol_nickname,
    )
    
    #5. Update visit status and date in Polotrial
    participant_visit_id = update_visit_status(
        co_participante=info["co_participante"],
        nome_tarefa=visit_config.polotrial_visit_name,
        visit_date=visit_date,
        polotrial=polotrial,
    )
    
    #6. Sync procedures
    sync_procedures(
        participante_visita_id=participant_visit_id,
        co_protocolo=info["co_protocolo"],
        procedures_map=visit_config.procedures_map,
        redcap_payload=redcap_payload,
        polotrial=polotrial,
        visit_label=visit_config.polotrial_visit_name,
    )
    
    #7. Sync executor
    if visit_config.executor_config:
        #load merged_procedures_df
        pvp=polotrial.list_participant_visit_procedures(
            co_participante_visita=participant_visit_id
        )
        proto_proc=polotrial.list_protocol_procedures(
            co_protocolo=info["co_protocolo"]
        )
        pvp_df=pd.DataFrame(pvp)
        proto_df=pd.DataFrame(proto_proc)[["id", "co_procedimento", "nome_procedimento_estudo"]].rename(
            columns={"id": "co_protocolo_procedimento"}
        )
        merged=pd.merge(pvp_df, proto_df, on='co_protocolo_procedimento', how='left')
        
        sync_executor(
            merged_procedures_df=merged,
            redcap_payload=redcap_payload,
            executor_field=visit_config.executor_config["field"],
            executor_date_field=visit_config.executor_config["date_field"],
            procedure_pattern=visit_config.executor_config["procedure_pattern"],
            polotrial=polotrial,
            visit_label=visit_config.polotrial_visit_name,
        )
        
        

def get_pp_randomized_from_v2(record_id: str, redcap: RedcapClient) -> Optional[bool]:
    """
    Fetches the 'is PK' information from the V2 visit data in REDCap.
    Args:
        record_id (str): The participant's record ID.
        redcap (RedcapClient): An instance of the RedcapClient to interact with REDCap.
    Returns:
        Optional[bool]: True if PK, False if not PK, None if unknown.   
    """
    
    v2_payload = redcap.export_record_eav(record_id, "vrv2_arm_1")
    value = v2_payload.get("rando_q8_v2")
    
    if value is None:
        return None
    
    s = str(value).strip().lower()
    if not s:
        return None
    if s in ("1", "não", "nao", "no", "false"):
        return False
    if s in ("2", "sim", "yes", "true"):
        return True
    
    return None