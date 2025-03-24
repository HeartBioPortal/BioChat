"""
Base class for biological database API clients.
"""

from typing import Dict, Optional
from abc import ABC, abstractmethod
import json
import aiohttp
import asyncio
from ..utils.biochat_api_logging import BioChatLogger


class BioDatabaseAPI(ABC):
    """Abstract base class for biological database APIs."""
    
    def __init__(self, api_key: Optional[str] = None, tool: Optional[str] = None, email: Optional[str] = None):
        self.api_key = api_key
        self.tool = tool
        self.email = email
        self.base_url = ""
        self.headers = {"Content-Type": "application/json"}
        self.session: Optional[aiohttp.ClientSession] = None
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def _init_session(self):
        """Initialize aiohttp session if not exists"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            conn = aiohttp.TCPConnector(
                ssl=False,
                limit=10,
                force_close=True
            )
            self.session = aiohttp.ClientSession(
                connector=conn,
                timeout=timeout
            )

    async def _close_session(self):
        """Close aiohttp session if exists"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _make_request(self, endpoint: str, params: Dict = None, method: str = "GET", 
                           json_data: Dict = None, delay: float = 0.34) -> Dict:
        """Enhanced request method with support for different HTTP methods."""
        max_retries = 3
        retry_delay = 1
        session_created = False
        
        for attempt in range(max_retries):
            try:
                if not self.session or self.session.closed:
                    await self._init_session()
                    session_created = True
                    
                await asyncio.sleep(delay)
                url = f"{self.base_url}/{endpoint}"
                
                request_kwargs = {
                    "headers": self.headers,
                    "params": params,
                    "ssl": False
                }
                if json_data is not None:
                    request_kwargs["json"] = json_data
                
                if method.upper() == "GET":
                    async with self.session.get(url, **request_kwargs) as response:
                        await self._handle_response(response)
                        return await self._parse_response(response)
                elif method.upper() == "POST":
                    async with self.session.post(url, **request_kwargs) as response:
                        await self._handle_response(response)
                        return await self._parse_response(response)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                    
            except aiohttp.ClientError as e:
                BioChatLogger.log_error(f"API request error", e)
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (attempt + 1))
                
            except Exception as e:
                BioChatLogger.log_error(f"Unexpected error in API request", e)
                raise
                
            finally:
                if session_created and self.session and not self.session.closed:
                    await self._close_session()

    async def _handle_response(self, response: aiohttp.ClientResponse) -> None:
        """Handle common response scenarios."""
        if response.status == 429:
            retry_after = int(response.headers.get('Retry-After', 5))
            await asyncio.sleep(retry_after)
            raise aiohttp.ClientError("Rate limit exceeded")
        response.raise_for_status()

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Dict:
        """Parse response content based on content type."""
        content_type = response.headers.get('Content-Type', '')
        
        try:
            if 'application/json' in content_type:
                return await response.json()
            elif 'text/html' in content_type:
                text = await response.text()
                BioChatLogger.log_error("Received HTML response", Exception(text[:500]))
                raise ValueError("Received HTML response instead of expected JSON")
            else:
                text = await response.text()
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    BioChatLogger.log_error("Failed to decode the response", Exception(text[:500]))
                    raise ValueError("Failed to decode response")
                    
        except Exception as e:
            BioChatLogger.log_error("Response parsing error", e)
            raise

    @abstractmethod
    async def search(self, query: str) -> Dict:
        """Base search method to be implemented by child classes."""
        pass

    async def __aenter__(self):
        await self._init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()