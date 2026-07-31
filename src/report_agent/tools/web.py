"""Bounded web search and page fetching helpers."""

import asyncio
import ipaddress
import os
import socket
from typing import cast
from urllib.parse import urljoin, urlparse

import httpx

from report_agent.config import Settings
from report_agent.models import Source
from report_agent.retry import with_retry


class WebTools:
    """Tavily search client plus safe HTTP page fetching."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    LOW_QUALITY_HOSTS = {
        "namu.wiki",
        "wikipedia.org",
        "blog.naver.com",
        "medium.com",
        "tistory.com",
    }
    ALLOWED_CONTENT_TYPES = (
        "text/html",
        "text/plain",
        "application/json",
        "application/xhtml+xml",
    )

    @classmethod
    def _is_allowed_source(cls, url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return bool(hostname) and not any(
            hostname == blocked or hostname.endswith(f".{blocked}")
            for blocked in cls.LOW_QUALITY_HOSTS
        )

    @staticmethod
    def _is_public_ip(value: str) -> bool:
        return ipaddress.ip_address(value).is_global

    @classmethod
    async def _validate_public_url(cls, url: str) -> None:
        """Reject credentials, local names, and non-public DNS destinations."""

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme not in {"http", "https"} or not hostname:
            raise ValueError("Only absolute HTTP(S) URLs are allowed")
        if parsed.username or parsed.password:
            raise ValueError("Credentials in URLs are not allowed")
        if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
            raise ValueError("Local network destinations are not allowed")

        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address is not None:
            if not address.is_global:
                raise ValueError("Non-public IP destinations are not allowed")
            return

        def resolve() -> set[str]:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            return {
                cast(str, result[4][0])
                for result in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
            }

        addresses = await asyncio.to_thread(resolve)
        if not addresses or not all(cls._is_public_ip(item) for item in addresses):
            raise ValueError("URL resolves to a non-public network destination")

    async def search(self, query: str, *, max_results: int = 5) -> list[Source]:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY is required for live web research")

        async def call_search() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "advanced",
                        "include_answer": False,
                    },
                )
                response.raise_for_status()
                return response

        response = await with_retry(
            call_search,
            attempts=self.settings.max_api_retries,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
        )
        sources = [
            Source(
                title=item.get("title") or item["url"],
                url=item["url"],
                snippet=item.get("content", ""),
                relevance_score=float(item.get("score", 0.0)),
            )
            for item in response.json().get("results", [])
            if self._is_allowed_source(item["url"])
            and float(item.get("score", 0.0)) >= self.settings.minimum_source_score
        ]
        return sorted(sources, key=lambda source: source.relevance_score, reverse=True)

    async def fetch(self, url: str, *, max_chars: int = 12_000) -> str:
        async def call_fetch() -> str:
            async with httpx.AsyncClient(
                timeout=self.settings.request_timeout_seconds,
                follow_redirects=False,
                headers={"User-Agent": "ReportAgent/0.1"},
            ) as client:
                current_url = url
                for redirect_count in range(self.settings.max_fetch_redirects + 1):
                    await self._validate_public_url(current_url)
                    async with client.stream("GET", current_url) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise RuntimeError("Redirect response did not include Location")
                            if redirect_count >= self.settings.max_fetch_redirects:
                                raise RuntimeError("Maximum redirect count exceeded")
                            current_url = urljoin(current_url, location)
                            continue
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").lower()
                        if not any(kind in content_type for kind in self.ALLOWED_CONTENT_TYPES):
                            raise ValueError(
                                f"Unsupported content type: {content_type or 'unknown'}"
                            )
                        declared_size = int(response.headers.get("content-length", "0") or 0)
                        if declared_size > self.settings.max_fetch_bytes:
                            raise ValueError("Response exceeds the configured size limit")
                        payload = bytearray()
                        async for chunk in response.aiter_bytes():
                            payload.extend(chunk)
                            if len(payload) > self.settings.max_fetch_bytes:
                                raise ValueError("Response exceeds the configured size limit")
                        return payload.decode(response.encoding or "utf-8", errors="replace")[
                            :max_chars
                        ]
                raise RuntimeError("Fetch terminated without a response")

        return await with_retry(
            call_fetch,
            attempts=self.settings.max_api_retries,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
        )
