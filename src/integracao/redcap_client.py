from __future__ import annotations
import logging
from typing import Any, Dict, Optional
import requests

# Set up logger
logger = logging.getLogger(__name__)

class RedcapClient:
    def __init__(self, api_url: str, api_token: str, timeout: int = 30):
        self.api_url = api_url
        self.api_token = api_token
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (compatible; redcap-client/1.0)",
            "Accept": "application/json",
        })
        
    def export_record_eav(
        self, 
        record_id: str,
        event_name: str,
        *,
        raw_or_label: str = 'label',
        raw_or_label_headers: str = 'label',
    ) -> Dict[str, Any]:
        """
        Returns the record as a dict {field_name: value} using export EAV.
        Filters by record_id and event (longitudinal project).

        """
        
        payload = {
            "token": self.api_token,
            "content": "record",
            "format": "json",
            "type": "eav",
            "records": [record_id],
            "events": [event_name],
            "rawOrLabel": raw_or_label,
            "rawOrLabelHeaders": raw_or_label_headers,
            "exportCheckboxLabel": "false",
            "returnFormat": "json",
        }
        
        redcap_request = self.session.post(self.api_url, data = payload, timeout=self.timeout)
        #==================================================================================================
        # Temporary DEBUG: log the full response if the request fails, to help with debugging
        #==================================================================================================
        print("INÍCIO DEBUG REDCAP RESPONSE")
        logger.info("DEBUG REDCAP URL: %s", self.api_url)
        logger.info("DEBUG REDCAP TOKEN (FIRST 8 CHARS): %s...", self.api_token[:8] if self.api_token else "NO TOKEN")
        logger.info("DEBUG REDCAP STATUS: %s", redcap_request.status_code)
        logger.info("DEBUG REDCAP RESPONSE (FIRST 200 CHARS): %s", redcap_request.text[:200])
        print("FIM DEBUG REDCAP RESPONSE")

        #==================================================================================================
        # End of temporary DEBUG logging
        #==================================================================================================


        redcap_request.raise_for_status()
        
        data = redcap_request.json()
        if not isinstance(data, list):
            raise RuntimeError(f" Unexpected REDCap response (expected list), got: {type(data)}")
        
        out: Dict[str, Any] = {}
        for entry in data:
            # entry: {record, field_name, value, event_name, ...}
            field_name = entry.get("field_name")
            value = entry.get("value")
            if field_name:
                out[field_name] = value
                
        logger.info("REDCap: exported record %s for event %s with %d fields", record_id, event_name, len(out))
        return out
    
    def list_events(self) -> Any:
        """
        Lists all events in the REDCap project.
        """
        payload = {
            "token": self.api_token,
            "content": "event",
            "format": "json",
            "returnFormat": "json",
        }
        redcap_request = self.session.post(self.api_url, data=payload, timeout=self.timeout)
        redcap_request.raise_for_status()
        return redcap_request.json()