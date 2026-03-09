from __future__ import annotations
import logging
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient
from integracao.utils import get_date_from_redcap
from integracao.mappings.procedures_maps import V1_POLOTRIAL_PROCEDURES_MAP
from integracao.mappings.site_code_maps import SITE_CODE_MAPPING
from integracao.mappings.race_code_maps import RACE_CODE_MAPPING
from integracao.mappings.gender_maps import GENDER_MAPPING 
import time

logger = logging.getLogger(__name__)



def sync_v1_screening(
    *,
    record_id: str,
    event_name: str,
    redcap: RedcapClient,
    polotrial: PoloTrialClient,
    protocol_nickname: str
) -> None:
    # 1. Get Redcap data (record and event)
    redcap_payload  = redcap.export_record_eav(
        record_id,
        event_name
        )
    
    # 2. Mapping fields REDCap -> PoloTrial
    gender_code = GENDER_MAPPING.get(str(redcap_payload .get("dados_pessoais_q5","")).strip(), None)
    site_code = SITE_CODE_MAPPING.get(str(redcap_payload .get("dados_pessoais_site","")).strip(), None)
    race_code = RACE_CODE_MAPPING.get(str(redcap_payload .get("dados_pessoais_q9","")).strip(), None)
    
    volunteer_payload = {
        "nome": redcap_payload.get("record_id") or record_id,
        "iniciais": redcap_payload.get("dados_pessoais_q12"),
        "data_nascimento": redcap_payload.get("dados_pessoais_q4"),
        "sexo": gender_code,
        "email": redcap_payload.get("informacoes_contato_q5"),
        "data_inclusao": redcap_payload.get("dados_sociodemograficos_dt"),
        "centro": site_code,
        "raca_cor": race_code,
        "contatos": "11111111111",
    }
    
    if not site_code:
        raise RuntimeError("Could not map site (dados_pessoais_site) to polotrial co_centro")
    
    #3. Volunteer
    existing = polotrial.find_volunteer_by_name(volunteer_payload["nome"])
    if existing:
        co_voluntario = int(existing["id"])
        logger.info("Volunteer exists: %s -> id=%s", record_id, co_voluntario)
    else:
        created = polotrial.create_volunteer(volunteer_payload)
        co_voluntario = int(created["id"])
        logger.info("Volunteer created: %s -> id=%s", record_id, co_voluntario)
        
    #4. Site Protocol
    logger.info("DEBUG: Searching protocol - co_centro=%s, apelido_protocolo=%s", site_code, protocol_nickname)
    protocol = polotrial.get_protocol(co_centro = site_code, apelido_protocolo = protocol_nickname)
    if not protocol:
        raise RuntimeError(f"Protocol not found for co_centro={site_code} and apelido_protocolo = {protocol_nickname}")
    co_protocolo = int(protocol["id"])
    logger.info("Protocol found: id=%s (site=%s)", co_protocolo, site_code)
    
    #5. Protocol Arm
    arms = polotrial.list_arms(co_protocolo)
    arm_match = next(
        (
            a for a in arms
            if re.search(r"Prot. V2", str(a.get("nome", "")), re.IGNORECASE)
        ),
        None,
    )
    if not arm_match:
        raise RuntimeError(f"Arm Triagem not found for protocol {co_protocolo}")
    co_braco = int(arm_match["id"])
    
    #6. Guarantee participant
    participant = polotrial.find_participant(co_voluntario = co_voluntario, co_protocolo = co_protocolo)
    if participant:
        co_participante = int(participant["id"])
        logger.info("Participant exists: id=%s", co_participante)
    else:
        # The `participant_payload` dictionary is being used to store information related to a participant in a clinical trial. Here is a breakdown of what each key in the dictionary represents:
        participant_payload = {
            "co_voluntario": co_voluntario,
            "co_protocolo": co_protocolo,
            "data_inclusao": redcap_payload .get("dados_sociodemograficos_dt"),
            "id_participante": redcap_payload.get("record_id") or record_id,
            "numero_de_screening": redcap_payload.get("record_id") or record_id,
            "status_participante": "540",
            "co_braco": co_braco,
            "atualizar_agenda": "1",
            "apagar_visitas_pendentes": "0",
        }
        # DEBUG
        logger.info("DEBUG: Sending participant payload:\n%s", json.dumps(participant_payload, indent=2))

        
        created = polotrial.create_participant(participant_payload)
        
        # DEBUG
        logger.info("DEBUG: Received participant response:\n%s", json.dumps(created, indent=2))

        co_participante = int(created["id"])
        logger.info("Participant created: id=%s", co_participante)
    
    #7. Update visit task (VS/V1)
    time.sleep(20)
    visits = polotrial.list_participant_visits(co_participante = co_participante)
    v1 = next((v for v in visits if v.get("nome_tarefa","") == "VS/V1"), None)
    if not v1:
        raise RuntimeError("Participant visit VS/V1 not found in Polotrial")
    
    participante_visita_id = int(v1["id"])
    desired = {
        "data_estimada": redcap_payload .get("dados_sociodemograficos_dt"),
        "data_realizada": redcap_payload.get("dados_sociodemograficos_dt"),
        "status": 20,
    }
    
    current = polotrial.get_participant_visit(participante_visita_id)
    #Compare only what matters.
    if str(current.get("data_realizada",""))[:10] == str(desired["data_realizada"])[:10] and int(current.get("status", -1)) == int(desired["status"]):
        logger.info("VS/V1 already up to date (id=%s).", participante_visita_id)
    else:
        polotrial.update_participant_visit(
            participante_visita_id,
            desired
        )
        logger.info("VS/V1 updated (id=%s).", participante_visita_id)
    
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
    mapping_df = pd.DataFrame(V1_POLOTRIAL_PROCEDURES_MAP)

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
        for cfg in V1_POLOTRIAL_PROCEDURES_MAP:
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
    logger.info("DEBUG: Available procedures in VS/V1:")
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

    for cfg in V1_POLOTRIAL_PROCEDURES_MAP:
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

    logger.info("V1 procedures synchronized: %d/%d", total_synced, len(V1_POLOTRIAL_PROCEDURES_MAP))

    return pvp_df
                    

def sync_consulta_medica_executor(
    *,
    merged_procedures_df: pd.DataFrame,
    volunteer_payload: Dict[str, Any],
    polotrial: PoloTrialClient,
) -> None:
    executor_name = str(volunteer_payload.get("consulta_nome_medico") or "").strip()
    if not executor_name:
        logger.info("V1: consulta_nome_medico vazio; não é possível atribuir executor (Consulta Médica).")
        return

    data_realizada = str(volunteer_payload.get("consulta_dt") or "").strip()
    if not data_realizada:
        logger.info("V1: consulta_dt vazio; não é possível atribuir executor (Consulta Médica).")
        return

    cm = merged_procedures_df[
        merged_procedures_df["nome_procedimento_estudo"]
        .astype(str)
        .str.contains(r"^Consulta [Mm][eéEÉ]dica$", regex=True, na=False)
    ]
    if cm.empty:
        logger.warning("V1: procedimento 'Consulta Médica' não encontrado na visita (PoloTrial).")
        return

    procedure_id = int(cm["id"].iloc[0])
    if len(cm) > 1:
        logger.warning("V1: múltiplos 'Consulta Médica' encontrados; usando o primeiro id=%s", procedure_id)
    
    #1. locate the procedure "Consulta Médica"
    person = polotrial.find_person_by_name(executor_name)
    if not person:
        logger.error("V1: executor não encontrado em /pessoas para ds_nome=%r", executor_name)
        return
    executor_id = int(person["id"])    
    
    #2. Find executor in Polotrial /pessoas endpoint
    existing_links = polotrial.list_procedure_executors(procedure_id)

    already_linked = any(int(x.get("executor", -1)) == executor_id for x in existing_links)
    if already_linked:
        logger.info(
            "V1: executor já está vinculado à Consulta Médica. procedure_id=%s executor_id=%s",
            procedure_id,
            executor_id,
        )
        return
    
    #3. create executor link -> procedure
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
        "V1: executor atribuído em Consulta Médica. procedure_id=%s executor_id=%s response_id=%s",
        procedure_id,
        executor_id,
        created.get("id"),
    )