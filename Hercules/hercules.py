import asyncio
from typing import Optional, Tuple

import aiohttp


class Hercules:
    """Wrapper for Hercules API providing the same interface as the local implementation."""

    def __init__(self, logger=None, base_url: str = "http://localhost:5000", api_key: str = None):
        self.logger = logger
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._methods_cache = None

        self._verify_connection()

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _verify_connection(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            connected, api_info = loop.run_until_complete(self._check_connection())

            if not connected:
                loop.close()
                if self.logger:
                    self.logger.critical(
                        f"Failed to connect to Hercules API at {self.base_url}. "
                        "Ensure the API is running and accessible."
                    )
                raise ConnectionError(f"Cannot connect to Hercules API at {self.base_url}")

            _, methods_data = loop.run_until_complete(self._make_request("GET", "/api/methods"))
            self._methods_cache = methods_data.get('methods', [])
            loop.close()

            if api_info.get("has_api_key_configured"):
                if api_info.get("api_key_valid"):
                    if self.logger:
                        self.logger.info("API key is valid")
                else:
                    if self.logger:
                        self.logger.warning(
                            "API key is configured but invalid. "
                            "The API may reject requests."
                        )
            else:
                if self.logger:
                    self.logger.info("No API key configured (rate limiting inactive)")

            if self.logger:
                self.logger.info(
                    f"Connected to Hercules API v{api_info.get('version', 'unknown')} "
                    f"(Obfuscator v{api_info.get('obfuscator_version', 'unknown')})"
                )
        except Exception as e:
            if self.logger:
                self.logger.critical(f"Failed to verify API connection: {e}")
            raise

    async def _check_connection(self) -> Tuple[bool, dict]:
        try:
            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                async with session.get(
                    f"{self.base_url}/api/info",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data = await response.json()
                    return response.status == 200, data
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Connection check failed: {e}")
            return False, {"error": str(e)}

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, dict]:
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=30), **kwargs
                ) as response:
                    data = await response.json()
                    if self.logger and endpoint == "/api/obfuscate":
                        self.logger.info(f"API response status: {response.status}")
                    return response.status == 200, data
        except Exception as e:
            if self.logger:
                self.logger.error(f"API request failed: {e}")
            return False, {"error": str(e)}

    async def _request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, dict]:
        return await self._make_request(method, endpoint, **kwargs)

    @property
    def methods(self) -> list:
        if self._methods_cache is None:
            self._methods_cache = []
        return self._methods_cache

    async def get_preset_methods(self, preset_name: str) -> list:
        success, data = await self._request("GET", "/api/presets")
        if success:
            presets = data.get('presets', {})
            preset = presets.get(preset_name.lower())
            if preset:
                return preset.get('methods', [])
        return []

    async def obfuscate(self, file_path: str, bitkey: int) -> Tuple[bool, str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Could not read file {file_path}: {e}")
            return False, f"Could not read file: {e}"

        payload = {"code": code, "bitkey": bitkey}
        if self.logger:
            self.logger.info(f"API obfuscate request - bitkey: {bitkey}, payload methods: {payload}")

        success, data = await self._request("POST", "/api/obfuscate", json=payload)
        if success:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data.get("obfuscated_code", ""))
            return True, data.get("obfuscated_code", "")
        return False, data.get("details", data.get("error", "Unknown error"))

    async def isValidLUASyntax(self, code: str) -> Tuple[bool, str]:
        success, data = await self._request("POST", "/api/validate", json={"code": code})
        if success:
            return data.get("valid", False), data.get("output", "")
        return False, data.get("error", "Unknown error")
