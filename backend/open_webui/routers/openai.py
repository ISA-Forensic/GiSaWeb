import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal, Optional, overload

import aiohttp
from aiocache import cached
import requests


from fastapi import Depends, FastAPI, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
)
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    BYPASS_MODEL_ACCESS_CONTROL,
)
from open_webui.models.users import UserModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import ENV, SRC_LOG_LEVELS


from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
)

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])


##########################################
#
# Utility functions
#
##########################################


async def send_get_request(url, key=None, user: UserModel = None):
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                url,
                headers={
                    **({"Authorization": f"Bearer {key}"} if key else {}),
                    **(
                        {
                            "X-OpenWebUI-User-Name": user.name,
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS and user
                        else {}
                    ),
                },
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                return await response.json()
    except Exception as e:
        # Handle connection error here
        log.error(f"Connection error: {e}")
        return None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()


def openai_o_series_handler(payload):
    """
    Handle "o" series specific parameters
    """
    if "max_tokens" in payload:
        # Convert "max_tokens" to "max_completion_tokens" for all o-series models
        payload["max_completion_tokens"] = payload["max_tokens"]
        del payload["max_tokens"]

    # Handle system role conversion based on model type
    if payload["messages"][0]["role"] == "system":
        model_lower = payload["model"].lower()
        # Legacy models use "user" role instead of "system"
        if model_lower.startswith("o1-mini") or model_lower.startswith("o1-preview"):
            payload["messages"][0]["role"] = "user"
        else:
            payload["messages"][0]["role"] = "developer"

    return payload


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


class OpenAIConfigForm(BaseModel):
    ENABLE_OPENAI_API: Optional[bool] = None
    OPENAI_API_BASE_URLS: list[str]
    OPENAI_API_KEYS: list[str]
    OPENAI_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: OpenAIConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_OPENAI_API = form_data.ENABLE_OPENAI_API
    request.app.state.config.OPENAI_API_BASE_URLS = form_data.OPENAI_API_BASE_URLS
    request.app.state.config.OPENAI_API_KEYS = form_data.OPENAI_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(request.app.state.config.OPENAI_API_KEYS) != len(
        request.app.state.config.OPENAI_API_BASE_URLS
    ):
        if len(request.app.state.config.OPENAI_API_KEYS) > len(
            request.app.state.config.OPENAI_API_BASE_URLS
        ):
            request.app.state.config.OPENAI_API_KEYS = (
                request.app.state.config.OPENAI_API_KEYS[
                    : len(request.app.state.config.OPENAI_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (
                len(request.app.state.config.OPENAI_API_BASE_URLS)
                - len(request.app.state.config.OPENAI_API_KEYS)
            )

    request.app.state.config.OPENAI_API_CONFIGS = form_data.OPENAI_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.OPENAI_API_BASE_URLS))))
    request.app.state.config.OPENAI_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.OPENAI_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


@router.post("/audio/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    idx = None
    try:
        idx = request.app.state.config.OPENAI_API_BASE_URLS.index(
            "https://api.openai.com/v1"
        )

        body = await request.body()
        name = hashlib.sha256(body).hexdigest()

        SPEECH_CACHE_DIR = CACHE_DIR / "audio" / "speech"
        SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
        file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

        # Check if the file already exists in the cache
        if file_path.is_file():
            return FileResponse(file_path)

        url = request.app.state.config.OPENAI_API_BASE_URLS[idx]

        r = None
        try:
            r = requests.post(
                url=f"{url}/audio/speech",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {request.app.state.config.OPENAI_API_KEYS[idx]}",
                    **(
                        {
                            "HTTP-Referer": "https://openwebui.com/",
                            "X-Title": "Open WebUI",
                        }
                        if "openrouter.ai" in url
                        else {}
                    ),
                    **(
                        {
                            "X-OpenWebUI-User-Name": user.name,
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS
                        else {}
                    ),
                },
                stream=True,
            )

            r.raise_for_status()

            # Save the streaming content to a file
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            with open(file_body_path, "w") as f:
                json.dump(json.loads(body.decode("utf-8")), f)

            # Return the saved file
            return FileResponse(file_path)

        except Exception as e:
            log.exception(e)

            detail = None
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error']}"
                except Exception:
                    detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500,
                detail=detail if detail else "GiSa: Server Connection Error",
            )

    except ValueError:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.OPENAI_NOT_FOUND)


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    if not request.app.state.config.ENABLE_OPENAI_API:
        return []

    # Check if API KEYS length is same than API URLS length
    num_urls = len(request.app.state.config.OPENAI_API_BASE_URLS)
    num_keys = len(request.app.state.config.OPENAI_API_KEYS)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            new_keys = request.app.state.config.OPENAI_API_KEYS[:num_urls]
            request.app.state.config.OPENAI_API_KEYS = new_keys
        # if there are more urls than keys, add empty keys
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS):
        if (str(idx) not in request.app.state.config.OPENAI_API_CONFIGS) and (
            url not in request.app.state.config.OPENAI_API_CONFIGS  # Legacy support
        ):
            request_tasks.append(
                send_get_request(
                    f"{url}/models",
                    request.app.state.config.OPENAI_API_KEYS[idx],
                    user=user,
                )
            )
        else:
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            enable = api_config.get("enable", True)
            model_ids = api_config.get("model_ids", [])

            if enable:
                if len(model_ids) == 0:
                    request_tasks.append(
                        send_get_request(
                            f"{url}/models",
                            request.app.state.config.OPENAI_API_KEYS[idx],
                            user=user,
                        )
                    )
                else:
                    model_list = {
                        "object": "list",
                        "data": [
                            {
                                "id": model_id,
                                "name": model_id,
                                "owned_by": "openai",
                                "openai": {"id": model_id},
                                "urlIdx": idx,
                            }
                            for model_id in model_ids
                        ],
                    }

                    request_tasks.append(
                        asyncio.ensure_future(asyncio.sleep(0, model_list))
                    )
            else:
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*request_tasks)

    for idx, response in enumerate(responses):
        if response:
            url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            connection_type = api_config.get("connection_type", "external")
            prefix_id = api_config.get("prefix_id", None)
            tags = api_config.get("tags", [])

            for model in (
                response if isinstance(response, list) else response.get("data", [])
            ):
                if prefix_id:
                    model["id"] = f"{prefix_id}.{model['id']}"

                if tags:
                    model["tags"] = tags

                if connection_type:
                    model["connection_type"] = connection_type

    log.debug(f"get_all_models:responses() {responses}")
    return responses


async def get_filtered_models(models, user):
    # Filter models based on user access control
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    return filtered_models


@cached(ttl=1)
async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_OPENAI_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def merge_models_lists(model_lists):
        log.debug(f"merge_models_lists {model_lists}")
        merged_list = []

        for idx, models in enumerate(model_lists):
            if models is not None and "error" not in models:

                merged_list.extend(
                    [
                        {
                            **model,
                            "name": model.get("name", model["id"]),
                            "owned_by": "openai",
                            "openai": model,
                            "connection_type": model.get("connection_type", "external"),
                            "urlIdx": idx,
                        }
                        for model in models
                        if (model.get("id") or model.get("name"))
                        and (
                            "api.openai.com"
                            not in request.app.state.config.OPENAI_API_BASE_URLS[idx]
                            or not any(
                                name in model["id"]
                                for name in [
                                    "babbage",
                                    "dall-e",
                                    "davinci",
                                    "embedding",
                                    "tts",
                                    "whisper",
                                ]
                            )
                        )
                    ]
                )

        return merged_list

    models = {"data": merge_models_lists(map(extract_data, responses))}
    log.debug(f"models: {models}")

    request.app.state.OPENAI_MODELS = {model["id"]: model for model in models["data"]}
    return models


@router.get("/models")
@router.get("/models/{url_idx}")
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    models = {
        "data": [],
    }

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        url = request.app.state.config.OPENAI_API_BASE_URLS[url_idx]
        key = request.app.state.config.OPENAI_API_KEYS[url_idx]

        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(url_idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
        )

        r = None
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as session:
            try:
                headers = {
                    "Content-Type": "application/json",
                    **(
                        {
                            "X-OpenWebUI-User-Name": user.name,
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS
                        else {}
                    ),
                }

                if api_config.get("azure", False):
                    models = {
                        "data": api_config.get("model_ids", []) or [],
                        "object": "list",
                    }
                else:
                    headers["Authorization"] = f"Bearer {key}"

                    async with session.get(
                        f"{url}/models",
                        headers=headers,
                        ssl=AIOHTTP_CLIENT_SESSION_SSL,
                    ) as r:
                        if r.status != 200:
                            # Extract response error details if available
                            error_detail = f"HTTP Error: {r.status}"
                            res = await r.json()
                            if "error" in res:
                                error_detail = f"External Error: {res['error']}"
                            raise Exception(error_detail)

                        response_data = await r.json()

                        # Check if we're calling OpenAI API based on the URL
                        if "api.openai.com" in url:
                            # Filter models according to the specified conditions
                            response_data["data"] = [
                                model
                                for model in response_data.get("data", [])
                                if not any(
                                    name in model["id"]
                                    for name in [
                                        "babbage",
                                        "dall-e",
                                        "davinci",
                                        "embedding",
                                        "tts",
                                        "whisper",
                                    ]
                                )
                            ]

                        models = response_data
            except aiohttp.ClientError as e:
                # ClientError covers all aiohttp requests issues
                log.exception(f"Client error: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="GiSa: Server Connection Error"
                )
            except Exception as e:
                log.exception(f"Unexpected error: {e}")
                error_detail = f"Unexpected error: {str(e)}"
                raise HTTPException(status_code=500, detail=error_detail)

    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        models["data"] = await get_filtered_models(models, user)

    return models


@router.get("/knowledge-bases")
async def get_knowledge_bases(request: Request, user=Depends(get_verified_user)):
    """
    Get knowledge bases from external OpenAI-compatible API connections
    """
    # Import here to avoid circular imports
    from open_webui.models.knowledge import Knowledges
    
    # Get local knowledge bases first
    if user.role == "admin":
        local_knowledge_bases = Knowledges.get_knowledge_bases()
    else:
        local_knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "write")
    
    # Convert to the expected format
    knowledge_bases = []
    for kb in local_knowledge_bases:
        knowledge_bases.append({
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "source": "local",
            "knowledge_base_id": getattr(kb, 'knowledge_base_id', kb.id),
        })
    
    # Get external knowledge bases from OpenAI-compatible APIs
    if request.app.state.config.ENABLE_OPENAI_API:
        external_knowledge_bases = []
        
        # Fetch from each configured OpenAI API endpoint
        for idx, (url, key) in enumerate(zip(
            request.app.state.config.OPENAI_API_BASE_URLS,
            request.app.state.config.OPENAI_API_KEYS
        )):
            if not url or not key:
                continue
                
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(url, {})
            )
            
            # Skip if this API connection is disabled
            if not api_config.get("enable", True):
                continue
                
            try:
                # Handle Docker networking issues
                fetch_url = url
                if "host.docker.internal" in url:
                    # Try to replace with localhost for testing
                    test_url = url.replace("host.docker.internal", "localhost")
                    log.info(f"Trying Docker networking: {url} and fallback: {test_url}")
                
                log.info(f"Fetching knowledge bases from {fetch_url}/knowledge-bases")
                async with aiohttp.ClientSession(
                    trust_env=True,
                    timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
                ) as session:
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    }
                    
                    # Try to fetch knowledge bases from the API
                    async with session.get(
                        f"{fetch_url}/knowledge-bases",
                        headers=headers,
                        ssl=AIOHTTP_CLIENT_SESSION_SSL,
                    ) as response:
                        log.info(f"Knowledge bases API response: {response.status} from {fetch_url}")
                        if response.status == 200:
                            data = await response.json()
                            log.info(f"Received knowledge bases data: {data}")
                            
                            # Handle both array and object responses
                            kb_list = data if isinstance(data, list) else data.get("data", [])
                            
                            # Add external knowledge bases with proper formatting and permission filtering
                            for kb in kb_list:
                                external_kb = {
                                    "id": f"external_{idx}_{kb.get('id', kb.get('knowledge_base_id', kb.get('name', 'unknown')))}",
                                    "name": kb.get("name", kb.get("id", "Unknown Knowledge Base")),
                                    "description": kb.get("description", "External knowledge base"),
                                    "knowledge_base_id": kb.get("knowledge_base_id", "Unknown Knowledge Base"),
                                    "source": "external",
                                    "api_url": url,
                                    "api_idx": idx,
                                    "enabled": kb.get("enabled", True),
                                    "external": True,
                                    "access_control": kb.get("access_control"),  # Include access control from external KB
                                    "user_id": kb.get("user_id")  # Include user_id from external KB
                                }
                                
                                # Only add external knowledge bases that the user has access to
                                # Admins see all, non-admins only see ones they have read access to
                                if user.role == "admin":
                                    external_knowledge_bases.append(external_kb)
                                    log.info(f"Added external knowledge base for admin: {external_kb['name']}")
                                else:
                                    # Import here to avoid circular imports
                                    from open_webui.utils.access_control import has_access
                                    
                                    # Check if user has read access to this external knowledge base
                                    if (external_kb.get("user_id") == user.id or 
                                        has_access(user.id, "read", external_kb.get("access_control"))):
                                        external_knowledge_bases.append(external_kb)
                                        log.info(f"Added external knowledge base for user {user.id}: {external_kb['name']}")
                                    else:
                                        log.info(f"User {user.id} does not have access to external knowledge base: {external_kb['name']}")
                        elif response.status == 404:
                            log.info(f"Knowledge bases endpoint not found at {fetch_url}/knowledge-bases")
                        else:
                            log.warning(f"Failed to fetch knowledge bases from {fetch_url}: HTTP {response.status}")
                            
            except aiohttp.ClientError as e:
                log.warning(f"Network error fetching knowledge bases from {url}: {e}")
                continue
            except Exception as e:
                log.error(f"Unexpected error fetching knowledge bases from {url}: {e}")
                continue
        
        # Add external knowledge bases to the result
        knowledge_bases.extend(external_knowledge_bases)
    
    return {"data": knowledge_bases}


@router.post("/knowledge-bases/{id}/permissions")
async def update_external_knowledge_base_permissions(
    request: Request,
    id: str,
    permissions: dict,
    user=Depends(get_admin_user)
):
    """
    Update permissions for an external knowledge base.
    This forwards the permission update to all configured external providers.
    """
    success_count = 0
    failed_updates = []
    
    # Handle external knowledge base ID format
    external_prefix = "external_"
    if not id.startswith(external_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid external knowledge base ID format"
        )
    
    # Extract the actual knowledge base ID by removing the external prefix and api index
    parts = id.replace(external_prefix, "").split("_", 1)
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid external knowledge base ID format"
        )
    
    api_idx = parts[0]
    kb_id = parts[1]
    
    # Get the specific OpenAI API configuration
    try:
        api_idx_int = int(api_idx)
        if (api_idx_int >= len(request.app.state.config.OPENAI_API_BASE_URLS) or
            api_idx_int >= len(request.app.state.config.OPENAI_API_KEYS)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid API configuration index"
            )
        
        url = request.app.state.config.OPENAI_API_BASE_URLS[api_idx_int]
        key = request.app.state.config.OPENAI_API_KEYS[api_idx_int]
        
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid external knowledge base ID format"
        )
    
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API configuration not found"
        )
        
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            
            # Try to update permissions on external provider
            try:
                async with session.post(
                    f"{url}/knowledge-bases/{kb_id}/permissions",
                    headers=headers,
                    json=permissions,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        log.info(f"Successfully updated permissions for KB {kb_id} on {url}")
                        return result
                    else:
                        error_text = await response.text()
                        log.warning(f"Failed to update permissions for KB {kb_id} on {url}: {response.status}")
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"External API error: {error_text}"
                        )
                        
            except aiohttp.ClientError as e:
                log.warning(f"Network error updating permissions for KB {kb_id} on {url}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Network error: {str(e)}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating permissions for KB {kb_id} on {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/knowledge-bases/bulk-permissions")
async def bulk_update_external_knowledge_base_permissions(
    request: Request,
    bulk_data: dict,
    user=Depends(get_admin_user)
):
    """
    Bulk update permissions for multiple external knowledge bases.
    This forwards the bulk permission updates to all configured external providers.
    """
    knowledge_base_ids = bulk_data.get("knowledge_base_ids", [])
    access_control = bulk_data.get("access_control", {})
    
    total_success = 0
    all_failed_updates = []
    
    # Group knowledge base IDs by their API provider
    api_groups = {}
    external_prefix = "external_"
    
    for kb_id in knowledge_base_ids:
        if not kb_id.startswith(external_prefix):
            all_failed_updates.append({
                "id": kb_id,
                "error": "Invalid external knowledge base ID format"
            })
            continue
            
        # Extract API index and actual KB ID
        parts = kb_id.replace(external_prefix, "").split("_", 1)
        if len(parts) < 2:
            all_failed_updates.append({
                "id": kb_id,
                "error": "Invalid external knowledge base ID format"
            })
            continue
            
        api_idx = parts[0]
        actual_kb_id = parts[1]
        
        if api_idx not in api_groups:
            api_groups[api_idx] = []
        api_groups[api_idx].append({
            "external_id": kb_id,
            "actual_id": actual_kb_id
        })
    
    # Update permissions for each API provider group
    for api_idx, kb_group in api_groups.items():
        try:
            api_idx_int = int(api_idx)
            if (api_idx_int >= len(request.app.state.config.OPENAI_API_BASE_URLS) or
                api_idx_int >= len(request.app.state.config.OPENAI_API_KEYS)):
                for kb in kb_group:
                    all_failed_updates.append({
                        "id": kb["external_id"],
                        "error": "Invalid API configuration index"
                    })
                continue
            
            url = request.app.state.config.OPENAI_API_BASE_URLS[api_idx_int]
            key = request.app.state.config.OPENAI_API_KEYS[api_idx_int]
            
            if not url or not key:
                for kb in kb_group:
                    all_failed_updates.append({
                        "id": kb["external_id"],
                        "error": "API configuration not found"
                    })
                continue
                
        except (ValueError, IndexError):
            for kb in kb_group:
                all_failed_updates.append({
                    "id": kb["external_id"],
                    "error": "Invalid API configuration"
                })
            continue
        
        # Bulk update for this API provider
        actual_kb_ids = [kb["actual_id"] for kb in kb_group]
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                
                # Try to bulk update permissions on external provider
                try:
                    async with session.post(
                        f"{url}/knowledge-bases/bulk-permissions",
                        headers=headers,
                        json={
                            "knowledge_base_ids": actual_kb_ids,
                            "access_control": access_control
                        },
                        ssl=AIOHTTP_CLIENT_SESSION_SSL,
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            provider_success = result.get("success_count", 0)
                            total_success += provider_success
                            
                            # Map failures back to external IDs
                            provider_failures = result.get("failed_updates", [])
                            for failure in provider_failures:
                                # Find the external ID that corresponds to this actual ID
                                actual_id = failure.get("id")
                                external_id = None
                                for kb in kb_group:
                                    if kb["actual_id"] == actual_id:
                                        external_id = kb["external_id"]
                                        break
                                
                                all_failed_updates.append({
                                    "id": external_id or actual_id,
                                    "error": failure.get("error", "Unknown error"),
                                    "provider": url
                                })
                            
                            log.info(f"Bulk updated {provider_success} KBs on {url}")
                        else:
                            error_text = await response.text()
                            for kb in kb_group:
                                all_failed_updates.append({
                                    "id": kb["external_id"],
                                    "error": f"HTTP {response.status}: {error_text}",
                                    "provider": url
                                })
                            log.warning(f"Failed bulk update on {url}: {response.status}")
                            
                except aiohttp.ClientError as e:
                    for kb in kb_group:
                        all_failed_updates.append({
                            "id": kb["external_id"],
                            "error": f"Network error: {str(e)}",
                            "provider": url
                        })
                    log.warning(f"Network error during bulk update on {url}: {e}")
                    
        except Exception as e:
            for kb in kb_group:
                all_failed_updates.append({
                    "id": kb["external_id"],
                    "error": f"Internal error: {str(e)}",
                    "provider": url
                })
            log.error(f"Error during bulk update on {url}: {e}")
    
    return {
        "success_count": total_success,
        "total_requested": len(knowledge_base_ids),
        "failed_updates": all_failed_updates
    }


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str

    config: Optional[dict] = None


@router.post("/verify")
async def verify_connection(
    form_data: ConnectionVerificationForm, user=Depends(get_admin_user)
):
    url = form_data.url
    key = form_data.key

    api_config = form_data.config or {}

    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
    ) as session:
        try:
            headers = {
                "Content-Type": "application/json",
                **(
                    {
                        "X-OpenWebUI-User-Name": user.name,
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS
                    else {}
                ),
            }

            if api_config.get("azure", False):
                headers["api-key"] = key
                api_version = api_config.get("api_version", "") or "2023-03-15-preview"

                async with session.get(
                    url=f"{url}/openai/models?api-version={api_version}",
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    if r.status != 200:
                        # Extract response error details if available
                        error_detail = f"HTTP Error: {r.status}"
                        res = await r.json()
                        if "error" in res:
                            error_detail = f"External Error: {res['error']}"
                        raise Exception(error_detail)

                    response_data = await r.json()
                    return response_data
            else:
                headers["Authorization"] = f"Bearer {key}"

                async with session.get(
                    f"{url}/models",
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    if r.status != 200:
                        # Extract response error details if available
                        error_detail = f"HTTP Error: {r.status}"
                        res = await r.json()
                        if "error" in res:
                            error_detail = f"External Error: {res['error']}"
                        raise Exception(error_detail)

                    response_data = await r.json()
                    return response_data

        except aiohttp.ClientError as e:
            # ClientError covers all aiohttp requests issues
            log.exception(f"Client error: {str(e)}")
            raise HTTPException(
                status_code=500, detail="GiSa: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            error_detail = f"Unexpected error: {str(e)}"
            raise HTTPException(status_code=500, detail=error_detail)


def convert_to_azure_payload(
    url,
    payload: dict,
):
    model = payload.get("model", "")

    # Filter allowed parameters based on Azure OpenAI API
    allowed_params = {
        "messages",
        "temperature",
        "role",
        "content",
        "contentPart",
        "contentPartImage",
        "enhancements",
        "dataSources",
        "n",
        "stream",
        "stop",
        "max_tokens",
        "presence_penalty",
        "frequency_penalty",
        "logit_bias",
        "user",
        "function_call",
        "functions",
        "tools",
        "tool_choice",
        "top_p",
        "log_probs",
        "top_logprobs",
        "response_format",
        "seed",
        "max_completion_tokens",
    }

    # Special handling for o-series models
    if model.startswith("o") and model.endswith("-mini"):
        # Convert max_tokens to max_completion_tokens for o-series models
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload["max_tokens"]
            del payload["max_tokens"]

        # Remove temperature if not 1 for o-series models
        if "temperature" in payload and payload["temperature"] != 1:
            log.debug(
                f"Removing temperature parameter for o-series model {model} as only default value (1) is supported"
            )
            del payload["temperature"]

    # Filter out unsupported parameters
    payload = {k: v for k, v in payload.items() if k in allowed_params}

    url = f"{url}/openai/deployments/{model}"
    return url, payload


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    idx = 0

    payload = {**form_data}
    metadata = payload.pop("metadata", None)

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # Check model info and override the payload
    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        params = model_info.params.model_dump()

        if params:
            system = params.pop("system", None)

            payload = apply_model_params_to_body_openai(params, payload)
            payload = apply_model_system_prompt_to_body(system, payload, metadata, user)

        # Check if user has access to the model
        if not bypass_filter and user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Model not found",
            )

    await get_all_models(request, user=user)
    model = request.app.state.OPENAI_MODELS.get(model_id)
    if model:
        idx = model["urlIdx"]
    else:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # Get the API config for the model
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    # Add user info to the payload if the model is a pipeline
    if "pipeline" in model and model.get("pipeline"):
        payload["user"] = {
            "name": user.name,
            "id": user.id,
            "email": user.email,
            "role": user.role,
        }

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    # Check if model is from "o" series
    is_o_series = payload["model"].lower().startswith(("o1", "o3", "o4"))
    if is_o_series:
        payload = openai_o_series_handler(payload)
    elif "api.openai.com" not in url:
        # Remove "max_completion_tokens" from the payload for backward compatibility
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload["max_completion_tokens"]
            del payload["max_completion_tokens"]

    if "max_tokens" in payload and "max_completion_tokens" in payload:
        del payload["max_tokens"]

    # Convert the modified body back to JSON
    if "logit_bias" in payload:
        payload["logit_bias"] = json.loads(
            convert_logit_bias_input_to_json(payload["logit_bias"])
        )

    headers = {
        "Content-Type": "application/json",
        **(
            {
                "HTTP-Referer": "https://openwebui.com/",
                "X-Title": "Open WebUI",
            }
            if "openrouter.ai" in url
            else {}
        ),
        **(
            {
                "X-OpenWebUI-User-Name": user.name,
                "X-OpenWebUI-User-Id": user.id,
                "X-OpenWebUI-User-Email": user.email,
                "X-OpenWebUI-User-Role": user.role,
            }
            if ENABLE_FORWARD_USER_INFO_HEADERS
            else {}
        ),
    }

    if api_config.get("azure", False):
        request_url, payload = convert_to_azure_payload(url, payload)
        api_version = api_config.get("api_version", "") or "2023-03-15-preview"
        headers["api-key"] = key
        headers["api-version"] = api_version
        request_url = f"{request_url}/chat/completions?api-version={api_version}"
    else:
        request_url = f"{url}/chat/completions"
        headers["Authorization"] = f"Bearer {key}"

    payload = json.dumps(payload)

    r = None
    session = None
    streaming = False
    response = None

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        r = await session.request(
            method="POST",
            url=request_url,
            data=payload,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response = await r.json()
            except Exception as e:
                log.error(e)
                response = await r.text()

            r.raise_for_status()
            return response
    except Exception as e:
        log.exception(e)

        detail = None
        if isinstance(response, dict):
            if "error" in response:
                detail = f"{response['error']['message'] if 'message' in response['error'] else response['error']}"
        elif isinstance(response, str):
            detail = response

        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "GiSa: Server Connection Error",
        )
    finally:
        if not streaming and session:
            if r:
                r.close()
            await session.close()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    """
    Deprecated: proxy all requests to OpenAI API
    """

    body = await request.body()

    idx = 0
    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    r = None
    session = None
    streaming = False

    try:
        headers = {
            "Content-Type": "application/json",
            **(
                {
                    "X-OpenWebUI-User-Name": user.name,
                    "X-OpenWebUI-User-Id": user.id,
                    "X-OpenWebUI-User-Email": user.email,
                    "X-OpenWebUI-User-Role": user.role,
                }
                if ENABLE_FORWARD_USER_INFO_HEADERS
                else {}
            ),
        }

        if api_config.get("azure", False):
            headers["api-key"] = key
            headers["api-version"] = (
                api_config.get("api_version", "") or "2023-03-15-preview"
            )

            payload = json.loads(body)
            url, payload = convert_to_azure_payload(url, payload)
            body = json.dumps(payload).encode()

            request_url = f"{url}/{path}?api-version={api_config.get('api_version', '2023-03-15-preview')}"
        else:
            headers["Authorization"] = f"Bearer {key}"
            request_url = f"{url}/{path}"

        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method=request.method,
            url=request_url,
            data=body,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        r.raise_for_status()

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            response_data = await r.json()
            return response_data

    except Exception as e:
        log.exception(e)

        detail = None
        if r is not None:
            try:
                res = await r.json()
                log.error(res)
                if "error" in res:
                    detail = f"External: {res['error']['message'] if 'message' in res['error'] else res['error']}"
            except Exception:
                detail = f"External: {e}"
        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "GiSa: Server Connection Error",
        )
    finally:
        if not streaming and session:
            if r:
                r.close()
            await session.close()
