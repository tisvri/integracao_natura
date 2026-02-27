from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Form, Response, status
from dotenv import load_dotenv

from integracao.config import Settings
from integracao.dispatch import dispatch_event
from integracao.logging_conf import setup_logging
from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient



#============================================================================================================================
# Logging
#============================================================================================================================

logger = logging.getLogger(__name__)

#============================================================================================================================
#Global Objects (Initialized in lifespan of the app)
#============================================================================================================================

_settings: Settings | None = None
_redcap: RedcapClient | None = None
_polotrial: PoloTrialClient | None = None


#============================================================================================================================
# Context Managers
#============================================================================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application. 
    Initializes global settings and clients for Redcap and PoloTrial.

        This function is called when the FastAPI application starts up and is responsible for setting up the necessary environment for the webhook to function. It loads environment variables, configures logging, and initializes the Redcap and PoloTrial clients using the settings loaded from the environment.

        Args:
            app (FastAPI): The FastAPI application instance.
        
        Steps:
            1. Load environment variables from a .env file using `load_dotenv()`.
            2. Set up logging configuration using `setup_logging()`.
            3. Create a `Settings` instance by loading configuration from environment variables.
            4. Initialize the `RedcapClient` with the API URL and API key from the settings.
            5. Initialize the `PoloTrialClient` with the API URL, username, and password from the settings.
            6. Log a message indicating that the webhook has been initialized for the specified protocol.
            7. Yield control back to the FastAPI application to allow it to run.
            8. After the application is done (on shutdown), log a message indicating that the webhook is shutting down for the specified protocol.
    """
    global _settings, _redcap, _polotrial

    # Load environment variables from .env file
    load_dotenv(override=True)
    setup_logging()


    _settings = Settings.from_env()
    _redcap = RedcapClient(_settings.redcap_api_url, _settings.redcap_api_key)
    _polotrial = PoloTrialClient(
        _settings.polotrial_api_url,
        _settings.polotrial_username,
        _settings.polotrial_password,
    )
    logger.info("Webhook initialized for protocol: %s", _settings.protocol_nickname)
    yield
    logger.info("Shutting down webhook for protocol: %s", _settings.protocol_nickname)

#============================================================================================================================
# FastAPI Application
#============================================================================================================================
app = FastAPI(
    title="Natura Integration - Redcap DET webhook",
    version="0.1.1",
    lifespan=lifespan,
)

#============================================================================================================================
# Health Check Endpoint
#============================================================================================================================
@app.get("/health")
async def health():
    """
    Health check endpoint to verify that the webhook is running.
    
    Returns:
        dict: A simple JSON response indicating the status of the webhook.
    
    Steps:
        1. Define a GET endpoint at the path "/health".
        2. When this endpoint is accessed, it returns a JSON response with a key "status" and a value of "ok", indicating that the webhook is healthy and running.
    """
    return {"status": "ok"}


#============================================================================================================================
# Endpiont to receive Redcap DET events
#============================================================================================================================

@app.post("/redcap-det", status_code=status.HTTP_200_OK)
async def redcap_det(
    
    background_tasks: BackgroundTasks,

    # data sended by Redcap (x-www-form-urlencoded)
    project_id: str = Form(...),
    username: str = Form(default=""),
    instrument: str = Form(default=""),
    record: str = Form(...),
    redcap_event_name: str = Form(default=""),
    redcap_data_access_group: str = Form(default=""),
    redcap_repeat_instance: Optional[str] = Form(default=None),
    redcap_repeat_instrument: Optional[str] = Form(default=None),
    redcap_url: str = Form(default=""),
    project_url: str = Form(default=""),
):
    """
    Endpoint to receive Redcap Data Entry Trigger (DET) events. 
    This endpoint is designed to handle POST requests sent by Redcap when a DET event occurs. It processes the incoming data and dispatches it for further handling in the background.

        Args:
            background_tasks (BackgroundTasks): FastAPI's BackgroundTasks instance for scheduling background tasks.
            project_id (str): The ID of the Redcap project that triggered the event.
            username (str, optional): The username of the person who triggered the event. Defaults to an empty string if not provided.
            instrument (str, optional): The name of the instrument associated with the event. Defaults to an empty string if not provided.
            record (str): The record ID associated with the event.
            redcap_event_name (str, optional): The name of the Redcap event that triggered the DET. Defaults to an empty string if not provided.
            redcap_data_access_group (str, optional): The data access group associated with the event. Defaults to an empty string if not provided.
            redcap_repeat_instance (Optional[str], optional): The repeat instance number if the instrument is part of a repeating group. Defaults to None if not provided.
            redcap_repeat_instrument (Optional[str], optional): The name of the repeating instrument if applicable. Defaults to None if not provided.
            redcap_url (str, optional): The URL of the Redcap instance that sent the DET. Defaults to an empty string if not provided.
            project_url (str, optional): The URL of the Redcap project associated with the event. Defaults to an empty string if not provided.

        Returns:
            Response: A FastAPI Response object indicating that the request was received successfully.

        Steps:
            1. Define a POST endpoint at the path "/redcap-det" that accepts form data.
            2. Extract relevant information from the incoming form data, such as project ID, username, instrument name, record ID, event name, data access group, repeat instance information, and URLs.
            3. Schedule a background task using `background_tasks.add_task()` to process the DET event asynchronously by calling `dispatch_event()` with the extracted information and global clients for Redcap and PoloTrial.
            4. Return a response indicating that the request was received successfully with a status code of 200 OK.
    """
    # basic filters
    if not redcap_event_name or not record:
        logger.warning(
            "DET ignored due to missing required fields: redcap_event_name=%s, record=%s",
            redcap_event_name,
            record,
        )
        return Response(status_code=status.HTTP_200_OK)
    
    logger.info(
        "Received DET: project_id=%s, username=%s, instrument=%s, record=%s, event_name=%s, data_access_group=%s, repeat_instance=%s, repeat_instrument=%s",
        project_id,
        username,
        instrument,
        record,
        redcap_event_name,
        redcap_data_access_group,
        redcap_repeat_instance,
        redcap_repeat_instrument,
    )

    # Schedule a heavy task to process the DET in the background, so we can return a response to Redcap immediately
    background_tasks.add_task(
        _run_sync,
        record_id=record,
        event_name=redcap_event_name,
    )

    return {"message": "DET received successfully"}

#============================================================================================================================
# Background worker
#============================================================================================================================

def _run_sync(
        *,
        record_id: str,
        event_name: str
) -> None:
    """
    Background worker function to process the DET event synchronously.
    This function is designed to be run in the background after a DET event is received. It uses the global clients for Redcap and PoloTrial to dispatch the event for further processing.

        Args:
            record_id (str): The record ID associated with the DET event.
            event_name (str): The name of the Redcap event that triggered the DET.
        Returns:
            None: This function does not return any value. It performs its operations and logs the results.
         Steps:
            1. Assert that the global clients for Redcap and PoloTrial, as well as the settings, have been initialized. This ensures that the necessary environment is set up before processing the event.
            2. Use a try-except block to handle any exceptions that may occur during the processing of the DET event.
            3. Inside the try block, call the `dispatch_event()` function with the record ID, event name, and the initialized clients for Redcap and PoloTrial, along with the protocol nickname from the settings. This function is responsible for handling the logic of processing the DET event based on the provided information.
            4. If the event is processed successfully, log an informational message indicating that the DET was processed successfully for the given record ID and event name.
            5. If an exception occurs during the processing, log an error message with the details of the exception.
    """
    assert _redcap is not None and _polotrial is not None and _settings is not None

    try:
        dispatch_event(
            record_id=record_id,
            event_name=event_name,
            redcap=_redcap,
            polotrial=_polotrial,
            protocol_nickname=_settings.protocol_nickname,
        )
        logger.info("Successfully processed DET for record_id=%s, event_name=%s", record_id, event_name)
    except Exception:
        logger.exception("Error processing DET for record_id=%s, event_name=%s", record_id, event_name)