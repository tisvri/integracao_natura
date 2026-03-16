from __future__ import annotations

import logging
import json
from typing import Any, Dict, Optional

import pandas as pd
import re
from datetime import datetime
import time

# from integracao.events.v2_randomizacao import CENTER_FIELD
from integracao.mappings.site_code_maps import SITE_CODE_MAPPING
from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient

from integracao.mappings.status_maps import STATUS_CODE_MAPPING 

from integracao.sync_engine import V1_EVENT
from integracao.utils import get_date_from_redcap
import os
import dotenv


dotenv.load_dotenv(override=True)

logger = logging.getLogger(__name__)

#====================================================================================================
# Constants
#====================================================================================================

PARTICIPANT_STATUS_EVENT = os.getenv("PARTICIPANT_STATUS_EVENT_NAME")
PARTICIPANT_STATUS_FIELD = os.getenv("PARTICIPANT_STATUS")
V1_EVENT = os.getenv("V1_EVENT_NAME")
CENTER_FIELD = os.getenv("CENTRO")

#====================================================================================================
# Participant status update sync function
#====================================================================================================

def sync_participant_status_update(
    *,
    record_id: str,
    event_name: str,
    redcap: RedcapClient,
    polotrial: PoloTrialClient,
    protocol_nickname: str,
) -> None:

    """
    Sync participant status updates from REDCap to PoloTrial.
    This function retrieves participant status updates from REDCap, maps the status codes to PoloTrial's format,
    and updates the corresponding records in PoloTrial.
    Args:
        redcap (RedcapClient): An instance of the RedcapClient to interact with REDCap API.
        polotrial (PoloTrialClient): An instance of the PoloTrialClient to interact with PoloTrial API.
        protocol_nickname (str): The nickname of the protocol in PoloTrial.

    Steps:
        1. Retrieve participant status updates from REDCap using the specified event name.
        2. For each participant status update:
            a. Extract the participant ID and the new status code.
            b. Map the REDCap status code to the corresponding PoloTrial status code using STATUS_CODE_MAPPING.
            c. Update the participant's status in PoloTrial using the mapped status code.
    
    Returns:
        None
    """
    # Step 1: Get REDCap data from VS/V1
    redcap_payload = redcap.export_record_eav(record_id, event_name)
    logger.info(f"Retrieved REDCap data for record_id: {record_id}, event_name: {event_name}")

    v1_payload = redcap.export_record_eav(record_id, V1_EVENT)

    # Step 2: Mapping fields REDCap -> PoloTrial
    co_centro_raw = str(v1_payload.get(CENTER_FIELD) or "").strip()
    site_code = SITE_CODE_MAPPING.get(co_centro_raw)
    if not site_code:
        raise RuntimeError(
            f"Could not map {CENTER_FIELD}={co_centro_raw!r} "
            "to PoloTrial site code"
        )
    
    # Step 3: Volunteer (presupposes V1 already ran)
    volunteer = polotrial.find_volunteer_by_name(record_id)
    if not volunteer:
        raise RuntimeError(
            f"Volunteer not found in PoloTrial for record_id={record_id}. "
            "Cannot sync participant status update."
        )
    co_voluntario = int(volunteer["id"])
    logger.info("Volunteer found: %s -> id=%s", record_id, co_voluntario)

    # Step 4: Protocol
    protocol = polotrial.get_protocol(co_centro=site_code, apelido_protocolo = protocol_nickname)
    if not protocol:
        raise RuntimeError(
            f"Protocol {protocol_nickname!r} not found for site {site_code!r} in PoloTrial. Cannot sync participant status update."
        )
    co_protocolo = int(protocol["id"])
    logger.info("Protocol found: id=%s (site=%s)", co_protocolo, site_code)

    #Step 5: Participant
    participant = polotrial.find_participant(co_voluntario=co_voluntario, co_protocolo=co_protocolo)
    if not participant:
        raise RuntimeError(
            f"Participant not found in PoloTrial for volunteer id={co_voluntario}. Cannot sync participant status update."
        )
    co_participante = int(participant["id"])
    logger.info("Participant found: id=%s (volunteer id=%s)", co_participante, co_voluntario)

    # Step 6: Extract status from Redcap and map to Polotrial
    redcap_status_raw = str(redcap_payload.get(PARTICIPANT_STATUS_FIELD) or "").strip()
    if not redcap_status_raw:
        logger.info("No participant status found in REDCap for record_id=%s, event_name=%s. Skipping status update.", record_id, event_name)
        return
    polotrial_status_code = STATUS_CODE_MAPPING.get(redcap_status_raw)
    if not polotrial_status_code:
        logger.warning(
            f"Unmapped participant status code from REDCap: {redcap_status_raw!r} for record_id={record_id}, event_name={event_name}. Skipping status update."
        )
        return
    logger.info(f"Mapped REDCap status {redcap_status_raw!r} to PoloTrial status code {polotrial_status_code!r} for record_id={record_id}, event_name={event_name}")

    # Step 7: Update participant sztatus in Polotrial
    current_participant = polotrial.get_participant(co_participante)
    current_status = str(current_participant.get("status_participante", ""))

    if current_status == polotrial_status_code:
        logger.info(f"Participant status in PoloTrial already up-to-date for participant id={co_participante}. Current status: {current_status!r}. No update needed.")
        return 
    
    polotrial.update_participant(co_participante, {
        "status_participante": polotrial_status_code
    })
    logger.info(f"Updated participant id={co_participante} status in PoloTrial from {current_status!r} to {polotrial_status_code!r}.")
