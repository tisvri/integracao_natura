from __future__ import annotations

import logging
import os
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

from integracao.mappings.v3_visit_name_maps import parse_randomziation_group

logger = logging.getLogger(__name__)

#====================================================================================================
# Constants
#====================================================================================================
V2_EVENT = os.getenv("REDCAP_EVENT_V2")
RANDOMIZATION_FIELD = "randomizacao_q3"

def resolve_polotrial_visit_name(
        visit_config: VisitConfig,
        record_id: str,
        redcap: RedcapClient,
) -> str:
    """
    Resolves the PoloTrial visit name based on the VisitConfig and REDCap data.
    This function checks if the visit has group-specific names. If it does, it retrieves the randomization group from the V2 visit data in REDCap and returns the corresponding visit name. If there are no group-specific names, it returns the default visit name from the VisitConfig.
    Args:
    - visit_config (VisitConfig): The configuration for the visit, which may include group-specific visit names.
    - record_id (str): The participant's record ID in REDCap.
    - redcap (RedcapClient): An instance of the RedcapClient to interact with REDCap.
    Returns:
    - str: The resolved PoloTrial visit name to be used for synchronization.

    """
    
    # 1. If visit name by group is not defined, return the default visit name
    if not visit_config.visit_name_by_group:
        return visit_config.polotrial_visit_name # If no group-specific visit names, return the default visit name (e.g., Não Programada)
    
    # 2. Get randomization group from V2 visit
    v2_payload = redcap.export_record_eav(record_id, V2_EVENT)
    raw_value = v2_payload.get(RANDOMIZATION_FIELD)
    group = parse_randomziation_group(raw_value)

    # 2.1. If group is None, it means we couldn't determine the randomization group. This could be due to missing or unexpected values in the randomization field. In this case, we should log a warning and skip the visit synchronization for this record, since we won't know which visit name to use.
    if group is None:
        raise RuntimeError(
            f"V3: Não foi possível determinar o grupo de randomização para "
            f"record_id={record_id}. Campo {RANDOMIZATION_FIELD} no evento "
            f"{V2_EVENT} está vazio ou com valor inesperado: {raw_value!r}"
        )
    # 3. Get visit name by group
    visit_name = visit_config.visit_name_by_group(group)
    if not visit_name:
        raise RuntimeError(
            f"V3: Grupo de randomização {group} não possui nome de visita "
            f" mapeado em visit_name_by_group. Valores disponíveis: "
            f"{list(visit_config. visit_name_by_group.keys())}"
        )
    # 3. Log the resolved visit name for debugging purposes
    logger.info(
        "V3: record_id+%s randomizacao_q3=%r -> grupo=%s -> visita=%s",
        record_id,
        raw_value,
        group,
        visit_name,
    )
    return visit_name

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
    
    Args:
    - record_id (str): The participant's record ID in REDCap.
    - event_name (str): The name of the REDCap event.
    - visit_config (VisitConfig): The configuration for the visit.
    - redcap (RedcapClient): An instance of the RedcapClient to interact with REDCap.
    - polotrial (PoloTrialClient): An instance of the PoloTrialClient to interact with PoloTrial.
    - protocol_nickname (str): The nickname of the protocol.
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

    # 4.5. Resolve PoloTrial visit name (this is necessary for V3 since the visit name depends on the randomization group)
    polotrial_visit_name = resolve_polotrial_visit_name(
        visit_config=visit_config,
        record_id=record_id,
        redcap=redcap,
    )
    
    #5. Update visit status and date in Polotrial
    participant_visit_id = update_visit_status(
        co_participante=info["co_participante"],
        nome_tarefa=polotrial_visit_name,
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