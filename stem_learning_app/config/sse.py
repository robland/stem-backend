"""Suivi en direct d'un traitement asynchrone par Server-Sent Events (README §7).

Le flux interroge la base (une requête légère par seconde) : aucun broker de plus, et le
statut lu est exactement celui de l'API REST. Chaque connexion occupe un thread
(gunicorn gthread) : la durée est donc bornée (`SSE_MAX_SECONDS`), puis le client se
reconnecte et reçoit à nouveau l'état courant.
"""

import json
import time

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.http import StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse
from rest_framework.renderers import BaseRenderer


class EventStreamRenderer(BaseRenderer):
    """Accepte `Accept: text/event-stream` ; les réponses d'erreur (401, 404) restent du JSON."""

    media_type = "text/event-stream"
    format = "sse"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return json.dumps(data, ensure_ascii=False).encode()


def event_stream_response(description):
    return {(200, "text/event-stream"): OpenApiResponse(OpenApiTypes.STR, description=description)}


def format_event(name, data):
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False, cls=DjangoJSONEncoder)}\n\n"


def status_events(snapshot, terminal):
    """`snapshot()` → (statut, données) ou None si l'objet n'existe plus.

    Envoie l'état courant à la connexion, puis un événement à chaque changement de statut
    (nom de l'événement = statut) ; s'arrête sur un statut de `terminal`.
    """
    yield f"retry: {settings.SSE_RETRY_MS}\n\n"
    started = last_sent = time.monotonic()
    last_status = None
    while True:
        current = snapshot()
        _release_connection()
        if current is None:
            yield format_event("gone", {"detail": "Introuvable."})
            return
        status, data = current
        if status != last_status:
            yield format_event(status, data)
            last_status, last_sent = status, time.monotonic()
            if status in terminal:
                return
        now = time.monotonic()
        if now - started >= settings.SSE_MAX_SECONDS:
            return
        if now - last_sent >= settings.SSE_HEARTBEAT_SECONDS:
            yield ": ping\n\n"  # commentaire SSE : garde la connexion ouverte à travers les proxies
            last_sent = now
        time.sleep(settings.SSE_POLL_SECONDS)


def _release_connection():
    # Une connexion PostgreSQL par flux ouvert épuiserait vite le pool : on la rend entre deux lectures.
    if not connection.in_atomic_block:
        connection.close()


def stream(snapshot, terminal):
    response = StreamingHttpResponse(status_events(snapshot, terminal), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # pas de mise en tampon par un proxy nginx
    return response
