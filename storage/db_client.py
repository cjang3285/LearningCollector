#!/usr/bin/env python3
"""
Lightweight DB client shim. Centralizes DB connection creation.
"""
from typing import Dict
import psycopg2


def get_connection(db_config: Dict):
    """Return a new psycopg2 connection using provided config."""
    return psycopg2.connect(**db_config)
