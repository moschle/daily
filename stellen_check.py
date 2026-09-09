#!/usr/bin/env python3
"""
Stellen-Monitor: tägliche Suche nach passenden Wissenschafts-/Behörden-Stellen.
Quellen:
  DE: H-Soz-Kult (Atom), kultweet.de (HTML), UniBwM (HTML), service.bund.de (RSS)
  Internationale Erweiterung: arthist.net (RSS), jobs.ac.uk × 3 Fachbereiche (RSS)
Filter: Score-basiert mit Wortgrenzen-Matching + Hard-Blacklist.
Output: HTML-Mail an GMAIL_ADDRESS, wenn neue Treffer da sind.
State: stellen_seen.json mit gesehenen IDs (Aufräumen nach 90 Tagen).
"""

import os
import sys
import json
import re
import smtplib
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from stellen_quellen_extra import (
    fetch_interamt, fetch_bpb_infodienst,
    fetch_landesportale, fetch_giz, ist_leiche,
)

BERLIN_TZ = ZoneInfo("Europe/Berlin")
USER_AGENT = "StellenMonitor/2.0 (+https://github.com/moschle/daily)"
SEEN_FILE = Path(__file__).parent / "stellen_seen.json"
SEEN_TTL_DAYS = 90

MIN_SCORE = 3
