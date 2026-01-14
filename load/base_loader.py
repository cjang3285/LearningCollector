#!/usr/bin/env python3
"""
Base loader utilities: HTTP request wrapper, pagination, error handling.

Provide a small base class loaders can inherit to share request, paging,
and error handling logic. Keeps code DRY and easier to test.
"""
from typing import Optional, Dict, Any, List
import requests
import logging

logger = logging.getLogger(__name__)


class BaseLoader:
    def __init__(self, token: Optional[str] = None, base_url: str = '', headers: Optional[Dict[str, str]] = None, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/') if base_url else ''
        self.token = token
        self.session = session or requests.Session()
        self._default_headers = headers or {}

    def _merge_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = dict(self._default_headers)
        if headers:
            h.update(headers)
        return h

    def request_json(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, method: str = 'get') -> Any:
        full_headers = self._merge_headers(headers)
        resp = self.session.request(method, url, params=params, headers=full_headers)
        resp.raise_for_status()
        return resp.json()

    def request_text(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, method: str = 'get') -> str:
        full_headers = self._merge_headers(headers)
        resp = self.session.request(method, url, params=params, headers=full_headers)
        resp.raise_for_status()
        return resp.text

    def paginate(self, url: str, params: Optional[Dict[str, Any]] = None, per_page: int = 100, page_param: str = 'page') -> List[Any]:
        results = []
        page = 1
        base_params = dict(params) if params else {}
        while True:
            base_params.update({'per_page': per_page, page_param: page})
            data = self.request_json(url, params=base_params)
            if not data:
                break
            # If the endpoint returns a list, extend; otherwise return single object
            if isinstance(data, list):
                results.extend(data)
                page += 1
                continue
            else:
                # not a list: return what we got
                return data

        return results
