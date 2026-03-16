from __future__ import annotations

import logging
import json
from typing import Any, Dict, Optional

import pandas as pd
import re
from datetime import datetime
import time
import os

from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient
from integracao.mappings.procedures_maps import V2_POLOTRIAL_PROCEDURES_MAP
from integracao.mappings.site_code_maps import SITE_CODE_MAPPING
from integracao.utils import get_date_from_redcap

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────
V1_EVENT = "vsv1_arm_1"
CENTER_FIELD = os.getenv("CENTRO")

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
    # 2: {
    #     "pattern": r"Grupo Hidra. Ultra. Refres. e Hidra. Intimo",
    #     "label": "Grupo 2 - Hidratante Ultra Refrescante e Hidratante Íntimo",
    # },

    3: {
        "pattern": r"Grupo.*Trat.*Intensivo Noturno",
        "label": "Grupo 3 - Tratamento Intensivo Noturno",
    },
}


# ── Helpers ────────────────────────────────────────────────────────────
def parse_randomization_group(value: Any) -> Optional[int]:
    """
    Interpreta o campo randomizacao_q3 do REDCap.

    Retorna 1, 2 ou 3 conforme o grupo, ou None se ainda vazio.
    """
    if value is None:
        return None

    s = str(value).strip().lower()
    if not s:
        return None

    group = ARM_MAPPING.get(s)
    if group is not None:
        return group

    logger.warning(
        "V2: Unexpected randomization value for %s: %r",
        RANDOMIZATION_FIELD, value,
    )
    return None


# ── Main sync function ─────────────────────────────────────────────────
def sync_v2_randomization(
    *,
    record_id: str,
    event_name: str,
    redcap: RedcapClient,
    polotrial: PoloTrialClient,
    protocol_nickname: str,
    v2_date_field: str,
) -> None:
    """
    Synchronizes Visit 2 (Randomization) in PoloTrial.

    Steps:
        1. Export REDCap data for record + V2 event, and V1 event for co_centro.
        2. Map dados_pessoais_site -> site_code via SITE_CODE_MAPPING.
        3. Locate volunteer in PoloTrial (V1 must have already run).
        4. Locate protocol via get_protocol(co_centro, apelido_protocolo).
        5. Locate participant in PoloTrial.
        6. Update VR/V2 visit date and status.
        7. Sync procedure executed dates.
        8. Sync 'Consulta Médica' executor.
        9. Update participant arm + data_randomizacao based on randomization group.
    """
    # 1. Get REDCap data (V2 event + V1 event for co_centro)
    redcap_payload = redcap.export_record_eav(record_id, event_name)
    v1_payload = redcap.export_record_eav(record_id, V1_EVENT)

    # 2. Mapping fields REDCap -> PoloTrial
    co_centro_raw = str(v1_payload.get(CENTER_FIELD) or "").strip()
    site_code = SITE_CODE_MAPPING.get(co_centro_raw)
    if not site_code:
        raise RuntimeError(
            f"V2: Could not map {CENTER_FIELD}={co_centro_raw!r} "
            "to PoloTrial site code"
        )

    # 3. Volunteer (find only — V2 presupposes V1 already ran)
    volunteer = polotrial.find_volunteer_by_name(record_id)
    if not volunteer:
        raise RuntimeError(
            f"Volunteer not found in PoloTrial for record_id={record_id}. "
            "Cannot sync V2 randomization."
        )
    co_voluntario = int(volunteer["id"])
    logger.info("Volunteer found: %s -> id=%s", record_id, co_voluntario)

    # 4. Site Protocol (with DEBUG log identical to V1)
    logger.info("DEBUG: Searching protocol - co_centro=%s, apelido_protocolo=%s", site_code, protocol_nickname)
    protocol = polotrial.get_protocol(co_centro=site_code, apelido_protocolo=protocol_nickname)
    if not protocol:
        raise RuntimeError(
            f"V2: Protocol {protocol_nickname!r} not found for site {site_code}"
        )
    co_protocolo = int(protocol["id"])
    logger.info("Protocol found: id=%s (site=%s)", co_protocolo, site_code)

    # 5. Participant (find only — V2 presupposes V1 already ran)
    participant = polotrial.find_participant(co_voluntario=co_voluntario, co_protocolo=co_protocolo)
    if not participant:
        raise RuntimeError(
            f"V2: Participant not found for volunteer={co_voluntario} "
            f"protocol={co_protocolo}"
        )
    co_participante = int(participant["id"])
    logger.info("Participant found: id=%s", co_participante)

    # ── NOTA: data_randomizacao será enviada junto com o arm update
    #    no passo 9, pois o PUT /participantes/{id} retorna 404
    #    quando enviado sozinho sem co_braco.
    v2_date_for_participant = str(redcap_payload.get('randomizacao_q2') or "").strip()

    # 6. Update visit task (VR/V2)
    time.sleep(20)
    visits = polotrial.list_participant_visits(co_participante=co_participante)
    v2_visit = next((v for v in visits if v.get("nome_tarefa", "") == "VR/V2"), None)
    if not v2_visit:
        raise RuntimeError(
            f"V2: Visit 'VR/V2' not found in PoloTrial for participant {co_participante}"
        )

    participante_visita_id = int(v2_visit["id"])
    v2_date = str(redcap_payload.get("elegibilidade_dt") or "").strip()
    desired = {
        "data_realizada": v2_date,
        "status": 20,
    }
    logger.info("DEBUG: Desired VR/V2 visit update payload:\n%s", json.dumps(desired, indent=2))

    current = polotrial.get_participant_visit(participante_visita_id)
    # Compare only what matters
    if str(current.get("data_realizada", ""))[:10] == str(desired["data_realizada"])[:10] and int(current.get("status", -1)) == int(desired["status"]):
        logger.info("VR/V2 already up to date (id=%s).", participante_visita_id)
    else:
        polotrial.update_participant_visit(participante_visita_id, desired)
        logger.info("VR/V2 updated (id=%s).", participante_visita_id)

    logger.info(f"DEBUG: Current Date: {current.get('data_realizada')} | Desired Date: {desired['data_realizada']}")

    # 7. Procedures: load participant visit procedures + names
    pvp_df = sync_v2_procedures(
        participante_visita_id=participante_visita_id,
        co_protocolo=co_protocolo,
        redcap_payload=redcap_payload,
        polotrial=polotrial,
    )

    # 8. Sync 'Consulta Médica' executor
    sync_consulta_medica_executor(
        merged_procedures_df=pvp_df,
        volunteer_payload=redcap_payload,
        polotrial=polotrial,
    )

    # 9. Arm update + data_randomizacao (V2 particularity)
    #
    #    CORREÇÃO: data_randomizacao é enviada JUNTO com co_braco e
    #    atualizar_agenda no mesmo PUT /participantes/{id}.
    #    Enviar data_randomizacao sozinha causava 404
    #    ("ParticipanteVisita not found!").
    #
    randomization_group = parse_randomization_group(
        redcap_payload.get(RANDOMIZATION_FIELD),
    )
    if randomization_group is None:
        logger.info(
            "V2: %s not yet filled for record %s. "
            "Arm will not be updated at this time.",
            RANDOMIZATION_FIELD, record_id,
        )
    else:
        logger.info(
            "DEBUG: Updating participant arm - co_participante=%s randomization_group=%s",
            co_participante, randomization_group,
        )
        update_participant_arm_if_needed(
            randomization_group=randomization_group,
            co_participante=co_participante,
            co_protocolo=co_protocolo,
            polotrial=polotrial,
            data_randomizacao=v2_date_for_participant,  # ← passa a data junto
            # # Atualizar agenda
            # atualizar_agenda={"atualizar_agenda": "1"},
        )

    logger.info("V2 sync completed for record_id=%s", record_id)


# ── Procedures helpers ─────────────────────────────────────────────────
def sync_v2_procedures(
    *,
    participante_visita_id: int,
    co_protocolo: int,
    redcap_payload: Dict[str, Any],
    polotrial: PoloTrialClient,
) -> pd.DataFrame:
    """
    Loads participant visit procedures, matches them with V2_POLOTRIAL_PROCEDURES_MAP
    using regex, logs DEBUG details for each procedure, and syncs data_executada
    dates from REDCap to PoloTrial.
    """
    # 1. Identify visit procedures (with nested=true to get the procedure name)
    pvp_raw = polotrial.list_participant_visit_procedures(
        co_participante_visita=participante_visita_id,
    )

    # 2. Convert to DataFrame and extract procedure names
    pvp_df = pd.DataFrame(pvp_raw)

    # Extract 'nome_procedimento_estudo' from nested dict or fallback
    if "dados_protocolo_procedimento" in pvp_df.columns:
        pvp_df["nome_procedimento_estudo"] = pvp_df[
            "dados_protocolo_procedimento"
        ].apply(
            lambda x: x.get("nome_procedimento_estudo") if isinstance(x, dict) else None
        )
    else:
        # Fallback: join via protocol procedures endpoint
        logger.warning("dados_protocolo_procedimento not in response, fetching from /protocolo_procedimento")
        proto_proc = polotrial.list_protocol_procedures(co_protocolo=co_protocolo)
        proto_df = pd.DataFrame(proto_proc)[["id", "nome_procedimento_estudo"]].rename(
            columns={"id": "co_protocolo_procedimento"}
        )
        pvp_df = pd.merge(pvp_df, proto_df, on="co_protocolo_procedimento", how="left")

    # Add mapping columns
    pvp_df["redcap_check_field"] = None
    pvp_df["redcap_date_field"] = None
    pvp_df["procedure_pattern"] = None

    # Match procedures with mapping using regex
    matched_count = 0
    unmatched_procedures = []

    for idx, row in pvp_df.iterrows():
        proc_name = str(row.get("nome_procedimento_estudo", "")).strip()
        matched = False

        for cfg in V2_POLOTRIAL_PROCEDURES_MAP:
            pattern = cfg["procedure_name"]
            if re.search(pattern, proc_name, re.IGNORECASE):
                pvp_df.at[idx, "redcap_check_field"] = cfg["redcap_check_field"]
                pvp_df.at[idx, "redcap_date_field"] = cfg["redcap_date_field"]
                pvp_df.at[idx, "procedure_pattern"] = pattern
                matched = True
                matched_count += 1
                break

        if not matched:
            unmatched_procedures.append(proc_name)

    # DEBUG: Show procedures with mapping info
    logger.info("DEBUG: Available procedures in VR/V2:")
    for idx, row in pvp_df.iterrows():
        check_field = row.get("redcap_check_field")
        date_field = row.get("redcap_date_field")

        check_value = redcap_payload.get(check_field, "N/A") if check_field else "N/A"
        date_value = redcap_payload.get(date_field, "N/A") if date_field else "N/A"

        logger.info(
            " - ID: %s | Proc: %s | Data exec: %s | Check field: %s=%s | Date field: %s=%s",
            row["id"],
            row.get("nome_procedimento_estudo"),
            row.get("data_executada"),
            check_field,
            check_value,
            date_field,
            date_value,
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
        pattern = cfg["procedure_name"]
        check_field = cfg["redcap_check_field"]
        date_field = cfg["redcap_date_field"]

        if not (pattern and check_field and date_field):
            logger.warning("Invalid procedure config: %s. Skipping...", cfg)
            continue

        to_sync = pvp_df[
            pvp_df["nome_procedimento_estudo"].str.contains(pattern, regex=True, na=False, flags=re.IGNORECASE)
            & (pvp_df["data_executada"].isna() | (pvp_df["data_executada"] == ""))
        ]

        if to_sync.empty:
            logger.info("No procedure to sync for pattern %s", pattern)
            continue

        if len(to_sync) > 1:
            logger.warning("Multiple procedures matched pattern %s, using first: %s", pattern, to_sync.iloc[0]["nome_procedimento_estudo"])

        procedure_id = int(to_sync["id"].iloc[0])
        procedure_name = to_sync["nome_procedimento_estudo"].iloc[0]

        redcap_date = get_date_from_redcap(redcap_payload, check_field, date_field)
        if not redcap_date:
            logger.info("No date in REDCap for procedure '%s' (check_field=%s)", procedure_name, check_field)
            continue

        redcap_date = str(redcap_date).strip()

        try:
            date_match = re.match(r"(\d{4}-\d{2}-\d{2})", redcap_date)
            if not date_match:
                raise ValueError(f"Could not extract date from: {redcap_date}")

            formatted_date = date_match.group(1)
            datetime.strptime(formatted_date, "%Y-%m-%d")

        except ValueError as e:
            logger.error("Invalid date format in REDCap for procedure '%s': %s (error: %s)", procedure_name, redcap_date, str(e))
            continue

        polotrial.update_participant_visit_procedure(
            procedure_id, {"data_executada": formatted_date},
        )
        logger.info("✅ Procedure updated successfully. procedure_id=%s date=%s", procedure_id, formatted_date)
        total_synced += 1

    logger.info("V2 procedures synchronized: %d/%d", total_synced, len(V2_POLOTRIAL_PROCEDURES_MAP))

    return pvp_df


# ── Consulta Médica executor ──────────────────────────────────────────
def sync_consulta_medica_executor(
    *,
    merged_procedures_df: pd.DataFrame,
    volunteer_payload: Dict[str, Any],
    polotrial: PoloTrialClient,
) -> None:
    """
    Links the executor to the 'Consulta Médica' procedure based on
    the consulta_nome_medico field in REDCap.
    """
    executor_name = str(
        volunteer_payload.get("consulta_nome_medico") or "",
    ).strip()
    if not executor_name:
        logger.info(
            "VR/V2: consulta_nome_medico empty; skipping executor sync."
        )
        return

    data_realizada = str(
        volunteer_payload.get("consulta_dt") or "",
    ).strip()
    if not data_realizada:
        logger.info("VR/V2: consulta_dt empty; skipping executor sync.")
        return

    cm = merged_procedures_df[
        merged_procedures_df["nome_procedimento_estudo"]
        .astype(str)
        .str.contains(r"Consulta [mM][eéEÉ]dica", regex=True, na=False)
    ]
    if cm.empty:
        logger.warning(
            "VR/V2: 'Consulta Médica' procedure not found in visit."
        )
        return

    procedure_id = int(cm["id"].iloc[0])
    if len(cm) > 1:
        logger.warning(
            "VR/V2: multiple 'Consulta Médica' found; using id=%s",
            procedure_id,
        )

    person = polotrial.find_person_by_name(executor_name)
    if not person:
        logger.error(
            "VR/V2: executor %r not found in PoloTrial /pessoas.",
            executor_name,
        )
        return
    executor_id = int(person["id"])

    existing_links = polotrial.list_procedure_executors(procedure_id)
    if any(int(x.get("executor", -1)) == executor_id for x in existing_links):
        logger.info(
            "VR/V2: executor already linked. procedure=%s executor=%s",
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
        "VR/V2: executor linked to Consulta Médica. "
        "procedure=%s executor=%s response_id=%s",
        procedure_id, executor_id, created.get("id"),
    )


# ── Arm update ─────────────────────────────────────────────────────────
def update_participant_arm_if_needed(
    *,
    randomization_group: int,
    co_participante: int,
    co_protocolo: int,
    polotrial: PoloTrialClient,
    data_randomizacao: str = "",
) -> None:
    """
    Moves the participant to the correct arm after V2 randomization
    and sets data_randomizacao in the same PUT request.

        randomizacao_q3 == 1 → Grupo 1 - Sérum Ultra Repositor
        randomizacao_q3 == 2 → Grupo 2 - Hidratante Ultra Refrescante e Hidratante Íntimo
        randomizacao_q3 == 3 → Grupo 3 - Tratamento Intensivo Noturno
    """
    arm_info = ARM_POLOTRIAL_PATTERNS.get(randomization_group)
    if not arm_info:
        raise ValueError(
            f"Unknown randomization_group={randomization_group}. "
            "Expected 1, 2 or 3."
        )

    target_arm_pattern = arm_info["pattern"]
    arm_label = arm_info["label"]

    logger.info(
        "DEBUG: Looking for arm - randomization_group=%s pattern=%s label=%s",
        randomization_group, target_arm_pattern, arm_label,
    )

    all_arms = polotrial.list_arms(co_protocolo)
    protocol_arms = all_arms
    if not protocol_arms:
        raise RuntimeError(f"No arms found for protocol {co_protocolo} in PoloTrial.")

    target_arm = next(
        (
            a for a in protocol_arms
            if re.search(target_arm_pattern, str(a.get("nome", "")), re.IGNORECASE)
        ),
        None,
    )
    if not target_arm:
        raise RuntimeError(
            f"Target arm {arm_label!r} not found for protocol {co_protocolo}. "
            f"Available: {[a.get('nome') for a in protocol_arms]}"
        )

    co_braco_desired = int(target_arm["id"])

    participant = polotrial.get_participant(co_participante)
    current_arm_id = int(participant.get("co_braco", -1))

    # ── Build payload: co_braco + atualizar_agenda + data_randomizacao ──
    arm_payload: Dict[str, Any] = {
        "co_braco": co_braco_desired,
        "atualizar_agenda": "1",
    }
    if data_randomizacao:
        arm_payload["data_randomizacao"] = data_randomizacao

    if current_arm_id == co_braco_desired:
        # Braço já correto, mas ainda pode precisar atualizar data_randomizacao
        if data_randomizacao:
            current_data_rand = str(participant.get("data_randomizacao") or "")[:10]
            if current_data_rand == data_randomizacao[:10]:
                logger.info(
                    "VR/V2: participant %s already in arm %s (%s) "
                    "and data_randomizacao already set. No update.",
                    co_participante, co_braco_desired, arm_label,
                )
                return
            # Braço correto mas data_randomizacao diferente — atualiza
            logger.info(
                "VR/V2: participant %s already in arm %s (%s) "
                "but data_randomizacao needs update.",
                co_participante, co_braco_desired, arm_label,
            )
        else:
            logger.info(
                "VR/V2: participant %s already in arm %s (%s). No update.",
                co_participante, co_braco_desired, arm_label,
            )
            return

    logger.info("DEBUG: Sending arm update payload:\n%s", json.dumps(arm_payload, indent=2))
    polotrial.update_participant(co_participante, arm_payload)
    logger.info(
        "VR/V2: participant %s arm updated %s → %s (%s). data_randomizacao=%s",
        co_participante, current_arm_id, co_braco_desired, arm_label,
        data_randomizacao or "(not set)",
    )