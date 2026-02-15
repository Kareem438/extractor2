"""
LLM Provider Service

Manages LLM provider configurations (CRUD operations, API key handling,
provider-agnostic API call wrapper) for V2 cloud extraction.
"""

import base64
import time
import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from src.database.connection import engine
from src.utils.logging_config import logger


class LLMProviderService:
    """Service for managing LLM provider configurations and making API calls."""

    # Default provider configurations
    PROVIDER_DEFAULTS = {
        "openai": {
            "display_name": "OpenAI ChatGPT",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o",
            "auth_header_style": "bearer"
        },
        "dashscope": {
            "display_name": "DashScope Qwen",
            "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "model_name": "qwen-vl-max",
            "auth_header_style": "bearer"
        },
        "anthropic": {
            "display_name": "Anthropic Claude",
            "base_url": "https://api.anthropic.com/v1",
            "model_name": "claude-sonnet-4-20250514",
            "auth_header_style": "x-api-key"
        },
        "google": {
            "display_name": "Google Gemini",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "model_name": "gemini-2.0-flash",
            "auth_header_style": "x-goog-api-key"
        }
    }

    def _obfuscate_key(self, api_key: str) -> str:
        """Simple base64 obfuscation for API keys stored in DB."""
        return base64.b64encode(api_key.encode()).decode()

    def _deobfuscate_key(self, obfuscated: str) -> str:
        """Reverse base64 obfuscation."""
        return base64.b64decode(obfuscated.encode()).decode()

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all configured LLM providers."""
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT id, provider_name, display_name, api_key, base_url, "
                "model_name, auth_header_style, enabled, created_at, updated_at "
                "FROM llm_providers ORDER BY id"
            ))
            rows = result.fetchall()

        providers = []
        for row in rows:
            providers.append({
                "id": row[0],
                "provider_name": row[1],
                "display_name": row[2],
                "api_key_masked": self._mask_key(row[3]),
                "base_url": row[4],
                "model_name": row[5],
                "auth_header_style": row[6],
                "enabled": row[7],
                "created_at": str(row[8]) if row[8] else None,
                "updated_at": str(row[9]) if row[9] else None
            })
        return providers

    def _mask_key(self, obfuscated_key: str) -> str:
        """Return masked version of API key for display."""
        try:
            real_key = self._deobfuscate_key(obfuscated_key)
            if len(real_key) > 8:
                return real_key[:4] + "****" + real_key[-4:]
            return "****"
        except Exception:
            return "****"

    def get_provider(self, provider_id: int) -> Optional[Dict[str, Any]]:
        """Get a single provider by ID."""
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT id, provider_name, display_name, api_key, base_url, "
                "model_name, auth_header_style, enabled "
                "FROM llm_providers WHERE id = :id"
            ), {"id": provider_id})
            row = result.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "provider_name": row[1],
            "display_name": row[2],
            "api_key_masked": self._mask_key(row[3]),
            "base_url": row[4],
            "model_name": row[5],
            "auth_header_style": row[6],
            "enabled": row[7]
        }

    def get_provider_by_name(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get a provider by name (with real API key for internal use)."""
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT id, provider_name, display_name, api_key, base_url, "
                "model_name, auth_header_style, enabled "
                "FROM llm_providers WHERE provider_name = :name"
            ), {"name": provider_name})
            row = result.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "provider_name": row[1],
            "display_name": row[2],
            "api_key": self._deobfuscate_key(row[3]),
            "base_url": row[4],
            "model_name": row[5],
            "auth_header_style": row[6],
            "enabled": row[7]
        }

    def create_provider(self, provider_name: str, display_name: str,
                        api_key: str, model_name: str,
                        base_url: Optional[str] = None,
                        auth_header_style: str = "bearer") -> Dict[str, Any]:
        """Create or update an LLM provider configuration."""
        # Use defaults if not provided
        defaults = self.PROVIDER_DEFAULTS.get(provider_name, {})
        if not base_url:
            base_url = defaults.get("base_url", "")
        if not display_name:
            display_name = defaults.get("display_name", provider_name)

        obfuscated_key = self._obfuscate_key(api_key)

        with engine.connect() as conn:
            # Upsert (insert or update on conflict)
            result = conn.execute(text("""
                INSERT INTO llm_providers 
                    (provider_name, display_name, api_key, base_url, model_name, auth_header_style)
                VALUES (:provider_name, :display_name, :api_key, :base_url, :model_name, :auth_header_style)
                ON CONFLICT (provider_name) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    api_key = EXCLUDED.api_key,
                    base_url = EXCLUDED.base_url,
                    model_name = EXCLUDED.model_name,
                    auth_header_style = EXCLUDED.auth_header_style,
                    updated_at = NOW()
                RETURNING id
            """), {
                "provider_name": provider_name,
                "display_name": display_name,
                "api_key": obfuscated_key,
                "base_url": base_url,
                "model_name": model_name,
                "auth_header_style": auth_header_style
            })
            conn.commit()
            provider_id = result.scalar()

        logger.info(f"LLM provider created/updated: {provider_name} (id={provider_id})")
        return {"id": provider_id, "provider_name": provider_name}

    def update_provider(self, provider_id: int, updates: Dict[str, Any]) -> bool:
        """Update specific fields of a provider."""
        allowed_fields = {"display_name", "api_key", "base_url", "model_name",
                          "auth_header_style", "enabled"}
        
        set_clauses = []
        params = {"id": provider_id}

        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            if field == "api_key":
                value = self._obfuscate_key(value)
            set_clauses.append(f"{field} = :{field}")
            params[field] = value

        if not set_clauses:
            return False

        set_clauses.append("updated_at = NOW()")
        sql = f"UPDATE llm_providers SET {', '.join(set_clauses)} WHERE id = :id"

        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            conn.commit()
            return result.rowcount > 0

    def delete_provider(self, provider_id: int) -> bool:
        """Delete a provider configuration."""
        with engine.connect() as conn:
            result = conn.execute(text(
                "DELETE FROM llm_providers WHERE id = :id"
            ), {"id": provider_id})
            conn.commit()
            return result.rowcount > 0

    async def test_connection(self, provider_name: str) -> Dict[str, Any]:
        """Test connection to an LLM provider by sending a minimal request."""
        provider = self.get_provider_by_name(provider_name)
        if not provider:
            return {"success": False, "error": f"Provider '{provider_name}' not found"}

        if not provider["enabled"]:
            return {"success": False, "error": f"Provider '{provider_name}' is disabled"}

        try:
            headers = self._build_headers(provider)
            base_url = provider["base_url"].rstrip("/")

            # OpenAI-compatible test (works for openai, dashscope)
            if provider["auth_header_style"] in ("bearer", "x-api-key"):
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if provider["provider_name"] == "anthropic":
                        # Anthropic uses different API format
                        resp = await client.post(
                            f"{base_url}/messages",
                            headers=headers,
                            json={
                                "model": provider["model_name"],
                                "max_tokens": 10,
                                "messages": [{"role": "user", "content": "Hi"}]
                            }
                        )
                    elif provider["provider_name"] == "google":
                        # Google Gemini uses different format
                        resp = await client.post(
                            f"{base_url}/models/{provider['model_name']}:generateContent",
                            headers=headers,
                            json={
                                "contents": [{"parts": [{"text": "Hi"}]}],
                                "generationConfig": {"maxOutputTokens": 10}
                            }
                        )
                    else:
                        # OpenAI-compatible (openai, dashscope)
                        resp = await client.post(
                            f"{base_url}/chat/completions",
                            headers=headers,
                            json={
                                "model": provider["model_name"],
                                "max_tokens": 10,
                                "messages": [{"role": "user", "content": "Hi"}]
                            }
                        )

                    if resp.status_code in (200, 201):
                        return {"success": True, "message": f"Connected to {provider['display_name']}"}
                    else:
                        error_body = resp.text[:500]
                        return {"success": False, "error": f"HTTP {resp.status_code}: {error_body}"}

        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timed out (30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_headers(self, provider: Dict[str, Any]) -> Dict[str, str]:
        """Build HTTP headers for a provider."""
        headers = {"Content-Type": "application/json"}
        style = provider["auth_header_style"]
        api_key = provider["api_key"]

        if style == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        elif style == "x-api-key":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        elif style == "x-goog-api-key":
            headers["x-goog-api-key"] = api_key

        return headers

    async def call_llm(self, provider_name: str, messages: List[Dict],
                       max_tokens: int = 4096, temperature: float = 0.1,
                       images: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Make a provider-agnostic LLM API call.

        Args:
            provider_name: Name of the configured provider
            messages: List of message dicts (role, content)
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            images: Optional list of base64-encoded images

        Returns:
            Dict with: content, input_tokens, output_tokens, 
                       input_tokens_cached, model, provider, processing_time_ms
        """
        provider = self.get_provider_by_name(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found")
        if not provider["enabled"]:
            raise ValueError(f"Provider '{provider_name}' is disabled")

        headers = self._build_headers(provider)
        base_url = provider["base_url"].rstrip("/")
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                if provider["provider_name"] == "anthropic":
                    resp_data = await self._call_anthropic(
                        client, base_url, headers, provider, messages, max_tokens, temperature, images
                    )
                elif provider["provider_name"] == "google":
                    resp_data = await self._call_google(
                        client, base_url, headers, provider, messages, max_tokens, temperature, images
                    )
                else:
                    # OpenAI-compatible (openai, dashscope)
                    resp_data = await self._call_openai_compatible(
                        client, base_url, headers, provider, messages, max_tokens, temperature, images
                    )

            elapsed_ms = int((time.time() - start_time) * 1000)
            resp_data["processing_time_ms"] = elapsed_ms
            resp_data["provider"] = provider_name
            resp_data["model"] = provider["model_name"]
            return resp_data

        except httpx.TimeoutException:
            raise TimeoutError(f"LLM call timed out after 120s ({provider_name})")
        except Exception as e:
            logger.error(f"LLM call failed ({provider_name}): {e}")
            raise

    async def _call_openai_compatible(self, client, base_url, headers, provider,
                                       messages, max_tokens, temperature, images):
        """Call OpenAI-compatible API (OpenAI, DashScope)."""
        # Build messages with images if provided
        api_messages = self._build_openai_messages(messages, images)

        resp = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": provider["model_name"],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": api_messages
            }
        )

        if resp.status_code != 200:
            raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        usage = data.get("usage", {})

        return {
            "content": data["choices"][0]["message"]["content"],
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "input_tokens_cached": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
        }

    def _build_openai_messages(self, messages, images):
        """Build OpenAI-format messages with optional image content."""
        if not images:
            return messages

        api_messages = []
        for msg in messages:
            if msg["role"] == "user" and images:
                # Build multimodal content
                content = []
                for img_b64 in images:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                    })
                content.append({"type": "text", "text": msg["content"]})
                api_messages.append({"role": "user", "content": content})
                images = None  # Only attach images to first user message
            else:
                api_messages.append(msg)
        return api_messages

    async def _call_anthropic(self, client, base_url, headers, provider,
                               messages, max_tokens, temperature, images):
        """Call Anthropic Claude API."""
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                continue  # Anthropic handles system separately
            if msg["role"] == "user" and images:
                content = []
                for img_b64 in images:
                    content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": img_b64}
                    })
                content.append({"type": "text", "text": msg["content"]})
                api_messages.append({"role": "user", "content": content})
                images = None
            else:
                api_messages.append(msg)

        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)

        body = {
            "model": provider["model_name"],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages
        }
        if system_msg:
            body["system"] = system_msg

        resp = await client.post(f"{base_url}/messages", headers=headers, json=body)

        if resp.status_code != 200:
            raise RuntimeError(f"Anthropic API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        usage = data.get("usage", {})

        return {
            "content": data["content"][0]["text"],
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "input_tokens_cached": usage.get("cache_read_input_tokens", 0),
        }

    async def _call_google(self, client, base_url, headers, provider,
                            messages, max_tokens, temperature, images):
        """Call Google Gemini API."""
        contents = []
        for msg in messages:
            parts = []
            if msg["role"] == "user" and images:
                for img_b64 in images:
                    parts.append({"inline_data": {"mime_type": "image/png", "data": img_b64}})
                images = None
            parts.append({"text": msg["content"]})
            role = "user" if msg["role"] in ("user", "system") else "model"
            contents.append({"role": role, "parts": parts})

        resp = await client.post(
            f"{base_url}/models/{provider['model_name']}:generateContent",
            headers=headers,
            json={
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature
                }
            }
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Google API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        usage = data.get("usageMetadata", {})

        return {
            "content": data["candidates"][0]["content"]["parts"][0]["text"],
            "input_tokens": usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0),
            "input_tokens_cached": usage.get("cachedContentTokenCount", 0),
        }

    def get_enabled_providers(self) -> List[Dict[str, Any]]:
        """Get list of enabled providers (for dropdown selection)."""
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT id, provider_name, display_name, model_name "
                "FROM llm_providers WHERE enabled = true ORDER BY provider_name"
            ))
            return [
                {"id": r[0], "provider_name": r[1], "display_name": r[2], "model_name": r[3]}
                for r in result.fetchall()
            ]
