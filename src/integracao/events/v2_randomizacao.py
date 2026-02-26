from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient
from integracao.mappings.procedures_maps import V2_POLOTRIAL_PROCEDURES_MAP
from integracao.mappings.site_code_maps import SITE_CODE_MAPPING
from integracao.utils import get_date_from_redcap

import re
from datetime import datetime
import time

logger = logging.getLogger(__name__)

V1_EVENT = "vsv1_arm_1"
CENTER_FIELD = "dados_pessoais_site"

V2_EVENT = "vrv2_arm_1"
V2_DATE_FIELD = "revisao_dt_visita"

RANDOMIZATION_FIELD = "randomizacao_q3"

ARM_MAPPING: Dict[str, int] = {
    "1": 1,
    "grupo 1 - sérum ultra repositor": 1,
    "2": 2,
    "grupo 2 - hidratante ultra refrescante e hidratante íntimo": 2,
    "3": 3,
    "grupo 3 - tratamento intensivo noturno": 3,
}

ARM_POLOTRIAL_PATTERNS: Dict[int, Dict[str, str]] = {
    1: {
        "pattern": r"Grupo.*S[eé]rum Ultra Repositor",
        "label": "Grupo 1 - Sérum Ultra Repositor",
    },
    2: {
        "pattern": r"Grupo.*Hidra.*Ultra Refres.*Hidra.*[IÍií]ntimo",
        "label": "Grupo 2 - Hidratante Ultra Refrescante e Hidratante Íntimo",
    },
    3: {
        "pattern": r"Grupo.*Trat.*Intensivo Noturno",
        "label": "Grupo 3 - Tratamento Intensivo Noturno",
    },
}

def parse_randomization_group(value: str) -> Optional[int]:
    """
    Interprets the value of the randomizacao_q3 field from REDCap and returns the group number (1, 2, or 3), or None if not already filled.

    REDCap can return:

        - "1" / "Group 1 - Ultra Replenishing Serum"

        - "2" / "Group 2 - Ultra Refreshing Moisturizer and Intimate Moisturizer"

        - "3" / "Group 3 - Intensive Night Treatment"

        - empty / None
    """

    if value is None:
        return None
    
    s = str(value).strip().lower()
    if not s:
        return None
    
    group = ARM_MAPPING.get(s)
    if group is not None:
        return group
    
    #Unexpected value
    logger.warning(f"V2: Unexpected randomization value for %s: %r", RANDOMIZATION_FIELD, value)
    return None


def sync_v2_randomization(
        *,
        record_id: str, 
        event_name: str, 
        redcap: RedcapClient,
        polotrial: PoloTrialClient,
        protocol_nickname: str,
        v2_date_field: str,
) -> Optional[int]:
    """
    Synchronizes the V2 randomization data between REDCap and PoloTrial.

    Args:
        record_id: The ID of the record in REDCap.
        event_name: The name of the event in REDCap.
        redcap: An instance of the RedcapClient.
        polotrial: An instance of the PoloTrialClient.
        protocol_nickname: The nickname of the protocol in PoloTrial.
        v2_date_field: The name of the date field in V2.

    Returns:
        The group number (1, 2, or 3) if successfully synchronized, or None otherwise.

    Steps:
        1. Get the REDCap data for the given record_id and event_name.
        2. Determine the randomization group from the REDCap data.
        3. Recover the co_centro from the V1 event in REDCap.
        4. Find the volunteer in PoloTrial using the record_id and co_centro.
        5. Get the protocol in PoloTrial using the co_centro and protocol_nickname.
        6. Find the participant in PoloTrial using the volunteer and protocol.
        7. Update the V2 visit status and date in PoloTrial based on the REDCap data.
        8. Synchronize the executed dates of the procedures in PoloTrial based on the REDCap data.
        9. Update the participant arm in PoloTrial based on the randomization group, if available.
    """

    if event_name != V2_EVENT:
        raise ValueError(f"sync_v2_randomization called with unexpected event_name: {event_name=}")
    
    # 1. GET Redcap data (record_id and event_name)
    redcap_payload = redcap.export_record_eav(record_id=record_id, event_name=event_name)

    # 1b. Determine randomization group from REDCap
    randomization_group = parse_randomization_group(
        redcap_payload.get(RANDOMIZATION_FIELD)
    )
    if randomization_group is None:
        logger.info(f"V2: %s not yet filled in for record %s. "
                    "Continuing sync of VR/V2 visit anyway.",
                    RANDOMIZATION_FIELD, record_id)
    else:
        logger.info(
            f"V2: record %s -> randomizatoin_group=%s",
                    record_id, randomization_group
        )

    #DEBUG
    logger.debug(f"V2: Full REDCap payload for record_id={record_id}, event_name={event_name}: {redcap_payload}")

    # 2. Recover co_centro (essential to find prticipant in Polotrial)
    v1_payload = redcap.export_record_eav(record_id=record_id, event_name=V1_EVENT)
    co_centro_raw = str(v1_payload.get(CENTER_FIELD) or "").strip()
    co_centro = SITE_CODE_MAPPING.get(co_centro_raw)

    if not co_centro:
        raise ValueError(f"V2: Could not map {CENTER_FIELD}={co_centro_raw!r} "
                         "to PoloTrial site code")
    
    #DEBUG
    logger.debug(f"V2: Mapped {CENTER_FIELD}={co_centro_raw!r} to PoloTrial site code {co_centro!r}")

    # 3. Recover volunteer/participant in PoloTrial using co_centro and record_id
    volunteer = polotrial.find_volunteer_by_name(record_id)
    if not volunteer:
        raise ValueError(f"Volunteer not found in PoloTrial for record_id={record_id}. "
                         "Cannot sync V2 randomization.")
    co_voluntario = int(volunteer["id"])

    protocol = polotrial.get_protocol(
        co_centro=co_centro,
        apelido_protocolo=protocol_nickname,
    )
    if not protocol:
        raise RuntimeError(
            f"V2: Protocol {protocol_nickname} not found for site {co_centro}"
        )
    co_protocolo = int(protocol["id"])

    participant = polotrial.find_participant(
        co_voluntario=co_voluntario,
        co_protocolo=co_protocolo
    )
    if not participant:
        raise RuntimeError(
            f"V2: Participant not found in polotrial for volunteer "
            f" {co_voluntario!r} and protocol {co_protocolo!r}"
        )
    co_participante = int(participant["id"])

    #DEBUG
    logger.debug(f"V2: Found participant in PoloTrial with co_participante={co_participante} for volunteer {co_voluntario} and protocol {co_protocolo}")

    # 4. Update V2 visit status and date
    v2_date = str(redcap_payload.get(v2_date_field) or "").strip()
    if not v2_date:
        logger.info(
            "V2: date field %s is empty. Not updating visit date for participant %s in Polotrial.", 
            v2_date_field, co_participante
        )
        return randomization_group
    
    visits = polotrial.list_participant_visits(co_participante=co_participante)
    v2 = next(
        (
            v for v in visits if v.get("nome_tarefa") == "VR/V2"
        ),
        None
    )
    if not v2:
        raise RuntimeError(
            f" V2: Participant visit 'VR/V2' not found in PoloTrial for participant {co_participante!r}"
        )
    participante_visita_id = int(v2["id"])

    desired = {
        "data_realizada": v2_date,
        "status": 20,
    }

    current = polotrial.get_participant_visit(participante_visita_id)
    if (
        str(current.get("data_realizada", ""))[:10] == str(desired["data_realizada"])[:10] and int(current.get("status", -1)) == desired["status"]
        ):
        logger.info(
            "V2: VR/V2 already up to date (id=%s). No update needed.",
            participante_visita_id,
        )

    else:
        polotrial.update_participant_visit(
            participante_visita_id,
            desired
        )
        logger.info(
            "V2: VR/V2 updated (id=%s).", participante_visita_id
        )
    
    #DEBUG
    logger.debug(f"V2: Updated VR/V2 visit for participant {co_participante} with data_realizada={v2_date} and status=20")


    # 5. Procedures: load participant visit procedure + names

    pvp = polotrial.list_participant_visit_procedures(
        co_participante_visita=participante_visita_id
    )
    proto_proc = polotrial.list_protocol_procedures(co_protocolo=co_protocolo)

    #7. Update visit task (VR/V2)
    time.sleep(20)
    visits = polotrial.list_participant_visits(co_participante = co_participante)
    v1 = next((v for v in visits if v.get("nome_tarefa","") == "VR/V2"), None)
    if not v1:
        raise RuntimeError("Participant visit VR/V2 not found in Polotrial")
    
    participante_visita_id = int(v1["id"])
    desired = {
        "data_estimada": redcap_payload .get("dados_sociodemograficos_dt"),
        "data_realizada": redcap_payload.get("dados_sociodemograficos_dt"),
        "status": 20,
    }
    
    current = polotrial.get_participant_visit(participante_visita_id)
    #Compare only what matters.
    if str(current.get("data_realizada",""))[:10] == str(desired["data_realizada"])[:10] and int(current.get("status", -1)) == int(desired["status"]):
        logger.info("VR/V2 already up to date (id=%s).", participante_visita_id)
    else:
        polotrial.update_participant_visit(
            participante_visita_id,
            desired
        )
        logger.info("VR/V2 updated (id=%s).", participante_visita_id)
    
    #8. Procedures: load participant visit procedure + names
    pvp_df = sync_v1_procedures(
        participante_visita_id=participante_visita_id,
        co_protocolo=co_protocolo,
        redcap_payload=redcap_payload,
        polotrial=polotrial
    )
    
    sync_consulta_medica_executor(
        merged_procedures_df=pvp_df,
        volunteer_payload=redcap_payload,
        polotrial=polotrial
    )

    logger.info("V1 sync completed for record_id=%s", record_id)



def sync_v1_procedures(
        *,
        participante_visita_id: int,
        co_protocolo: int,
        redcap_payload: Dict[str, Any],
        polotrial: PoloTrialClient
)-> pd.DataFrame:
    """
    Docstring for sync_v1_procedures
    
    :param participante_visita_id: Description
    :type participante_visita_id: int
    :param co_protocolo: Description
    :type co_protocolo: int
    :param redcap_payload: Description
    :type redcap_payload: Dict[str, Any]
    :param polotrial: Description
    :type polotrial: PoloTrialClient
    :return: Description
    :rtype: DataFrame
    """

    from integracao.mappings.procedures_maps import V2_POLOTRIAL_PROCEDURES_MAP 
    from integracao.utils import get_date_from_redcap

    #1. Identify visita procedures (with nested=true to get the procedure name)
    pvp_raw = polotrial.list_participant_visit_procedures(
        co_participante_visita = participante_visita_id
    )

    #2. Converting to DataFrame and name procedures extraction 
    pvp_df = pd.DataFrame(pvp_raw)

    # Extract 'procedure_procedure_study' from the field in this 'data_protocol_procedure'
    if 'dados_protocolo_procedimento' in pvp_df.columns:
        pvp_df['nome_procedimento_estudo'] = pvp_df['dados_protocolo_procedimento'].apply(
            lambda x: x.get('nome_procedimento_estudo') if isinstance(x, dict) else None
        )
    else:
        # Fallback: try to extract from 'dados_protocolo_procedimento' string if it's not already a dict
        logger.warning("dados_protocolo_procedimento not in response, fetching from /protocolo_procedimento")
        proto_proc = polotrial.list_protocol_procedures(co_protocolo = co_protocolo)
        proto_df = pd.DataFrame(proto_proc)[['id', 'nome_procedimento_estudo']].rename(
            columns={"id": "co_protocolo_procedimento"}
        )
        pvp_df = pd.merge(pvp_df, proto_df, on="co_protocolo_procedimento", how="left")
    # Add mapping fields to dataframe
    #Convert mapping to DataFrame
    mapping_df = pd.DataFrame(V2_POLOTRIAL_PROCEDURES_MAP)

    # Add regex match colum to help with merge
    pvp_df['redcap_check_field'] = None
    pvp_df['redcap_date_field'] = None
    pvp_df['procedure_pattern'] = None

    # Match procedures with mapping using regex
    matched_count = 0
    unmatched_procedures = []


    for idx, row in pvp_df.iterrows():
        proc_name = str(row.get('nome_procedimento_estudo', '')).strip()
        matched = False

        # Find matching pattern in mapping
        for cfg in V2_POLOTRIAL_PROCEDURES_MAP:
            pattern = cfg['procedure_name']
            if re.search(pattern, proc_name, re.IGNORECASE):
                pvp_df.at[idx, 'redcap_check_field'] = cfg['redcap_check_field']
                pvp_df.at[idx, 'redcap_date_field'] = cfg['redcap_date_field']
                pvp_df.at[idx, 'procedure_pattern'] = pattern
                matched = True
                matched_count += 1
                break # Stop at first match

        if not matched:
            unmatched_procedures.append(proc_name)
    
    # DEBUG: Show procedures with mapping info
    logger.info("DEBUG: Available procedures in VR/V2:")
    for idx, row in pvp_df.iterrows():
        check_field = row.get('redcap_check_field')
        date_field = row.get('redcap_date_field')
        
        # Get actual values from REDCap
        check_value = redcap_payload.get(check_field, 'N/A') if check_field else 'N/A'
        date_value = redcap_payload.get(date_field, 'N/A') if date_field else 'N/A'
        
        logger.info(
            " - ID: %s | Proc: %s | Data exec: %s | Check field: %s=%s | Date field: %s=%s", 
            row['id'], 
            row.get('nome_procedimento_estudo'), 
            row.get('data_executada'),
            check_field,
            check_value,  # ← VALOR do campo
            date_field,
            date_value    # ← VALOR da data
        )
    logger.info("DEBUG: Procedure mapping summary:")
    logger.info("  Total procedures in PoloTrial: %d", len(pvp_df))
    logger.info("  Matched with mapping: %d", matched_count)
    logger.info("  Unmatched: %d", len(unmatched_procedures))

    if unmatched_procedures:
        logger.warning("DEBUG: Unmatched procedures (no mapping found):")
        for proc in unmatched_procedures:
            logger.warning("  - '%s'", proc)

    # 3. For each procedure in mapping, search and update
    total_synced = 0

    for cfg in V2_POLOTRIAL_PROCEDURES_MAP:
        pattern = cfg['procedure_name']
        check_field = cfg['redcap_check_field']
        date_field = cfg['redcap_date_field']

        if not (pattern and check_field and date_field):
            logger.warning("Invalid procedure config: %s. Skipping...", cfg)
            continue

        # Filter procedures that do not yet have a date_executed
        to_sync = pvp_df[
            pvp_df["nome_procedimento_estudo"].str.contains(pattern, regex=True, na=False, flags=re.IGNORECASE) & (pvp_df["data_executada"].isna() | (pvp_df["data_executada"] == ""))
        ]

        if to_sync.empty:
            logger.info("No procedure to sync for pattern %s", pattern)
            continue

        if len(to_sync) > 1:
            logger.warning("Multiple procedures matched pattern %s, using first: %s",pattern, to_sync.iloc[0]['nome_procedimento_estudo'])
        
        procedure_id = int(to_sync["id"].iloc[0])
        procedure_name = to_sync["nome_procedimento_estudo"].iloc[0]

        # Get date from REDCap
        redcap_date = get_date_from_redcap(redcap_payload, check_field, date_field)
        if not redcap_date:
            logger.info("No date in REDCap for procedure '%s' (check_field=%s)", procedure_name, check_field)
            continue

        #Clean and normalize date
        redcap_date = str(redcap_date).strip()

        # Validate and extract date (handles both YYYY-MM-DD and YYYY-MM-DD HH:MM)
        try:
            # try to extract YYYY-MM-DD part using regex
            date_match = re.match(r'(\d{4}-\d{2}-\d{2})', redcap_date)
            if not date_match:
                raise ValueError(f"Coud not extract date from: {redcap_date}")
            
            formatted_date = date_match.group(1)
            
            # Validate it's a real date
            datetime.strptime(formatted_date, "%Y-%m-%d")
        
        except ValueError as e:
            logger.error("Invalid date format in REDCAP for procedure '%s': %s (error: %s)", procedure_name, redcap_date, str(e))
            continue

        # Update procedure in PoloTrial
        polotrial.update_participant_visit_procedure(
            procedure_id,
            {"data_executada": formatted_date}
        )
        logger.info("✅s Procedure updated successfully. procedure_id=%s date=%s", procedure_id, formatted_date)
        total_synced += 1

    logger.info("V2 procedures synchronized: %d/%d", total_synced, len(V2_POLOTRIAL_PROCEDURES_MAP))

    # return pvp_df

    # 6. Synchronize executed dates
    
    total = 0
    
    for cfg in V2_POLOTRIAL_PROCEDURES_MAP:
        pattern = cfg["procedure_name"]
        co_proc = cfg["co_procedimento"]
        check_field = cfg["redcap_check_field"]
        date_field = cfg["redcap_date_field"]

        if not (pattern and co_proc and check_field and date_field):
            logger.warning(
                "Invalid procedure mapping config: %s. Skipping...", cfg,
            )
            continue

        to_sync = merged[
            merged[
                "nome_procedimento_estudo"
            ].str.contains(
                pattern,
                regex=True,
                na=False,
                flags=re.IGNORECASE,
            )
            & (merged["co_procedimento"].astype(str) == str(co_proc))
            & (merged["data_executada"].isna() | (merged["data_executada"] == ""))
        ]

        if to_sync.empty:
            logger.info(
                "No date to sync from REDCap for procedure %r (record_id=%s)", pattern, record_id
            )
            continue

        procedure_id = int(to_sync["id"].iloc[0])
        redcap_date = get_date_from_redcap(redcap_payload, check_field, date_field)
        if not redcap_date:
            logger.info(
                "No date to sync from REDCap for procedure %r (record_id=%s)", pattern, record_id
            )
            continue

        try:
            dt = datetime.strptime(redcap_date, "%Y-%m-%d")
        except ValueError:
            logger.error(
                "Invalid date for %s: %r (expected format YYYY-MM-DD). Skipping date sync for procedure %r (record_id=%s)",
                date_field, redcap_date, pattern, record_id
            )
            continue

        polotrial.update_participant_visit_procedure(
            procedure_id, 
            {"data_executada": dt.strftime("%Y-%m-%d")},
        )
        total += 1
    logger.info(
        "VR/V2 procedures synchronized: %d", total
    )

    #DEBUG
    logger.debug(f"V2: Total procedures synchronized: {total}")

    sync_consulta_medica_executor(
        merged_procedures_df=merged,
        volunteer_payload=redcap_payload,
        polotrial=polotrial,
    )

    # 7. Update participant arm based on randomization group, if available
    if randomization_group is not None:
        update_participant_arm_if_needed(
            randomization_group=randomization_group,
            co_participant=co_participante,
            co_protocolo=co_protocolo,
            polotrial=polotrial,
        )
    else:
        logger.info(
            "VR/V2: randomization_group not yet defined for record %s. "
            " Arm will not be updated at this time.",
            record_id,
        )

    return randomization_group



def sync_consulta_medica_executor(
        *,
        merged_procedures_df: pd.DataFrame,
        volunteer_payload: Dict[str, Any],
        polotrial: PoloTrialClient,
) -> None:
    """
    Sync executor for 'Consulta médica' procedure in VR/V2, based on the 'consulta_nome_medico' field in REDCap.
    
    This is a special case because the executor is not being synced through the usual procedure mapping, but through a specific field in REDCap.
    
        The function will look for a procedure in the VR/V2 visit that matches "Consulta médica" and will try to link the executor based on the name provided in REDCap. If the executor is already linked, it will skip. If the executor name is missing or if no matching procedure is found, it will log a warning and skip without raising an error, since this is not critical for the main purpose of syncing the visit and procedures.

    Args:
        merged_procedures_df: A DataFrame containing the merged participant visit procedures and protocol procedures for the VR/V2 visit.
        volunteer_payload: The REDCap data for the volunteer, containing the 'consulta_nome_medico' and 'consulta_dt' fields.
        polotrial: An instance of the PoloTrialClient to interact with the PoloTrial API.
    
    Steps:
        1. Extract the executor name from the 'consulta_nome_medico' field in REDCap. If it's empty, log a message and skip syncing the executor.
        2. Extract the date of the consultation from the 'consulta_dt' field in REDCap. If it's empty, log a message and skip syncing the executor.
        3. Find the procedure in the merged DataFrame that matches "Consulta médica". If not found, log a warning and skip syncing the executor.
        4. Find the executor in PoloTrial by name. If not found, log an error and skip syncing the executor.
        5. Check if the executor is already linked to the procedure. If yes, log a message and skip.
        6. If not linked, create a new procedure executor link in PoloTrial with the extracted date and log the action.


    """
    executor_name = str(
        volunteer_payload.get("consulta_nome_medico") or ""
    ).strip()
    if not executor_name:
        logger.info(
            "VR/V2: consulta_nome_medico is empty; "
            " Can not sync executor for 'Consulta médica' procedure. Skipping..."
        )
        return
    
    data_realizada = str(volunteer_payload.get("consulta_dt") or "").strip()
    if not data_realizada:
        logger.info(
            "VR/V2: consulta_dt is empty; "
            " Can not sync date for 'Consulta médica' procedure. Skipping..."
        )
        return
    
    cm = merged_procedures_df[
        merged_procedures_df["nome_procedimento_estudo"].astype(str).str.contains(r"Consulta [mM][ée]dica", regex=True, na=False)
    ]

    if cm.empty:
        logger.warning(
            "VR/V2: No 'Consulta médica' procedure found for participant %s. Cannot sync executor.", volunteer_payload.get("record_id")
        )
        return
    
    procedure_id = int(cm["id"].iloc[0])
    if len(cm) > 1:
        logger.warning(
            "VR/V2: múltiplos 'Consulta Médica' encontrados; "
            "usando o primeiro id=%s",
            procedure_id,
        )

    person = polotrial.find_person_by_name(executor_name)
    if not person:
        logger.error(
            "VR/V2: executor %r not found in Polotrial. "
            "Cannot sync executor for 'Consulta médica' procedure.", executor_name
        )
        return
    
    executor_id = int(person["id"].iloc[0])

    existing_links = polotrial.list_procedure_executors(procedure_id)
    already_linked = any(
        int(x.get("executor", -1)) == executor_id for x in existing_links
    )

    if already_linked:
        logger.info(
            "VR/V2: executor já está vinculado à Consulta Médica. "
            "procedure_id=%s executor_id=%s",
            procedure_id, executor_id,
        )
        return

    payload = {
        "co_participante_visita_procedimento": procedure_id,
        "executor": executor_id,
        "data_realizada": data_realizada,
        "data_previsto_pagamento": "",
        "data_realizado_pagamento": "",
        "valor": "",
        "valor_total_procedimento": "",
        "observacoes": "",
    }

    created = polotrial.create_procedure_executor(payload)
    logger.info(
        "VR/V2: executor atribuído em Consulta Médica. "
        "procedure_id=%s executor_id=%s response_id=%s",
        procedure_id, executor_id, created.get("id"),
    )

def update_participant_arm_if_needed(
    *,
    randomization_group: int,
    co_participante: int,
    co_protocolo: int,
    polotrial: PoloTrialClient,
) -> None:
    """
    Update participant arm after V2 randomization.

    randomizacao_q3 == 1  → Grupo 1 - Sérum Ultra Repositor
    randomizacao_q3 == 2  → Grupo 2 - Hidratante Ultra Refrescante e Hidratante Íntimo
    randomizacao_q3 == 3  → Grupo 3 - Tratamento Intensivo Noturno

    Participants always start in the screening arm at V1.



    Args: 
        randomization_group: The randomization group number (1, 2, or 3) determined from REDCap.
        co_participante: The ID of the participant in PoloTrial.
        co_protocolo: The ID of the protocol in PoloTrial.
        polotrial: An instance of the PoloTrialClient to interact with the PoloTrial API.
    
    Steps:
        1. Determine the target arm pattern and label based on the randomization group.
        2. Get all arms for the protocol from PoloTrial.
        3. Find the target arm that matches the pattern for the randomization group.
        4. Check the current arm of the participant.
        5. If the current arm is different from the target arm, update the participant's arm in PoloTrial and log the change. If it's the same, log that no update is needed.
    """
    arm_info = ARM_POLOTRIAL_PATTERNS.get(randomization_group)
    if not arm_info:
        raise ValueError(
            f"Unknown randomization_group={randomization_group}. "
            "Expected 1, 2 or 3."
        )

    target_arm_pattern = arm_info["pattern"]
    arm_label = arm_info["label"]

    # 1. Get arms for this protocol
    all_arms = polotrial.list_arms()
    protocol_arms = [
        arm for arm in all_arms
        if int(arm.get("co_protocolo", -1)) == co_protocolo
    ]

    if not protocol_arms:
        raise RuntimeError(
            f"Could not find any arms for protocol {co_protocolo}"
        )

    # 2. Find desired arm
    target_arm = next(
        (
            arm for arm in protocol_arms
            if re.search(
                target_arm_pattern,
                str(arm.get("nome", "")),
                re.IGNORECASE,
            )
        ),
        None,
    )

    if not target_arm:
        raise RuntimeError(
            f"Could not find target arm {arm_label!r} for protocol "
            f"{co_protocolo}. Available arms: "
            f"{[arm.get('nome') for arm in protocol_arms]}"
        )

    co_braco_desired = int(target_arm["id"])

    # 3. Check current arm
    participant = polotrial.get_participant(co_participante)
    current_arm_id = int(participant.get("co_braco", -1))

    if current_arm_id == co_braco_desired:
        logger.info(
            "VR/V2: participant %s already in desired arm %s (%s). "
            "No update needed.",
            co_participante, co_braco_desired, arm_label,
        )
        return

    # 4. Update arm
    payload = {
        "co_braco": co_braco_desired,
        "atualizar_agenda": "1",  # Update schedule
    }

    polotrial.update_participant(co_participante, payload)
    logger.info(
        "VR/V2: participant %s arm updated from %s to %s (%s).",
        co_participante, current_arm_id, co_braco_desired, arm_label,
    )
