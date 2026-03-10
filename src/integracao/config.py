from __future__ import annotations

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    # Redcap enviroment variables
    redcap_api_url: str
    redcap_api_key: str
    
    #Polotrial enviroment variables
    polotrial_api_url: str
    polotrial_username: str
    polotrial_password: str
    
    # Protocol name
    protocol_nickname: str = "NATURA"
    
    @staticmethod
    def from_env() -> "Settings":
        def must(name: str) -> str:
            value = os.getenv(name)
            if not value:
                raise RuntimeError(f"Environment variable {name} is required")
            return value
        
        return Settings(
            redcap_api_url=must("REDCAP_API_URL"),
            redcap_api_key=must("REDCAP_API_KEY"),
            polotrial_api_url=must("POLOTRIAL_API_URL"),
            # polotrial_username=must("POLOTRIAL_PLAYGROUND_USERNAME"),
            # polotrial_password=must("POLOTRIAL_PLAYGROUND_PASSWORD"),
            polotrial_username=must("POLOTRIAL_API_USERNAME"),
            polotrial_password=must("POLOTRIAL_API_PASSWORD"),
            protocol_nickname=os.getenv("POLOTRIAL_PROTOCOL_NICKNAME", "NATURA"),
        )