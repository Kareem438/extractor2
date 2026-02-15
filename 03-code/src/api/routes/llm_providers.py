"""
LLM Providers API Routes

CRUD endpoints for managing LLM provider configurations
used by V2 cloud extraction.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.services.llm_provider_service import LLMProviderService
from src.utils.logging_config import logger

router = APIRouter()
service = LLMProviderService()


class CreateProviderRequest(BaseModel):
    """Request body for creating/updating a provider."""
    provider_name: str
    display_name: Optional[str] = None
    api_key: str
    model_name: str
    base_url: Optional[str] = None
    auth_header_style: str = "bearer"


class UpdateProviderRequest(BaseModel):
    """Request body for updating provider fields."""
    display_name: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    auth_header_style: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("/llm-providers")
async def list_providers():
    """List all configured LLM providers."""
    try:
        providers = service.list_providers()
        return {"providers": providers}
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-providers/defaults")
async def get_provider_defaults():
    """Get default configurations for supported providers."""
    return {"defaults": service.PROVIDER_DEFAULTS}


@router.get("/llm-providers/enabled")
async def list_enabled_providers():
    """List only enabled providers (for dropdown selection)."""
    try:
        providers = service.get_enabled_providers()
        return {"providers": providers}
    except Exception as e:
        logger.error(f"Error listing enabled providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-providers/{provider_id}")
async def get_provider(provider_id: int):
    """Get a single provider by ID."""
    provider = service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/llm-providers")
async def create_provider(request: CreateProviderRequest):
    """Create or update an LLM provider configuration."""
    try:
        result = service.create_provider(
            provider_name=request.provider_name,
            display_name=request.display_name or "",
            api_key=request.api_key,
            model_name=request.model_name,
            base_url=request.base_url,
            auth_header_style=request.auth_header_style
        )
        return {"message": "Provider saved", **result}
    except Exception as e:
        logger.error(f"Error creating provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/llm-providers/{provider_id}")
async def update_provider(provider_id: int, request: UpdateProviderRequest):
    """Update specific fields of a provider."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    success = service.update_provider(provider_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider updated"}


@router.delete("/llm-providers/{provider_id}")
async def delete_provider(provider_id: int):
    """Delete a provider configuration."""
    success = service.delete_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider deleted"}


@router.post("/llm-providers/{provider_name}/test")
async def test_provider_connection(provider_name: str):
    """Test connection to an LLM provider."""
    try:
        result = await service.test_connection(provider_name)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing provider {provider_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
