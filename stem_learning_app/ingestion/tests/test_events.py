import json

import pytest

from config import sse
from ingestion.models import Upload

pytestmark = pytest.mark.django_db


def parse(chunk):
    """Bloc SSE → (événement, données)."""
    fields = dict(line.split(": ", 1) for line in chunk.decode().strip().split("\n"))
    return fields["event"], json.loads(fields["data"])


def make_upload(user, status=Upload.Status.PENDING):
    return Upload.objects.create(user=user, file_type="image", file_size=1, file_hash="h", status=status)


def open_stream(client, upload, accept="text/event-stream"):
    return client.get(f"/api/uploads/{upload.id}/events/", HTTP_ACCEPT=accept)


class TestUploadEvents:
    def test_streams_each_status_until_extracted(self, auth_client, user):
        upload = make_upload(user)
        response = open_stream(auth_client, upload)

        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"
        assert response["Cache-Control"] == "no-cache"
        chunks = iter(response.streaming_content)
        assert next(chunks) == b"retry: 3000\n\n"
        assert parse(next(chunks))[0] == "pending"

        Upload.objects.filter(pk=upload.pk).update(status=Upload.Status.READING)
        assert parse(next(chunks))[0] == "reading"

        Upload.objects.filter(pk=upload.pk).update(status=Upload.Status.EXTRACTED)
        name, data = parse(next(chunks))
        assert name == "extracted"
        assert (data["id"], data["status"], data["exercises"]) == (str(upload.id), "extracted", [])
        assert list(chunks) == []

    def test_finished_upload_sends_its_state_and_closes(self, auth_client, user):
        upload = make_upload(user, Upload.Status.ERROR)
        Upload.objects.filter(pk=upload.pk).update(error_message="Document illisible.")

        chunks = list(open_stream(auth_client, upload).streaming_content)

        assert len(chunks) == 2
        name, data = parse(chunks[1])
        assert (name, data["error_message"]) == ("error", "Document illisible.")

    def test_deleted_upload_ends_the_stream(self, auth_client, user):
        upload = make_upload(user)
        chunks = iter(open_stream(auth_client, upload).streaming_content)
        next(chunks), next(chunks)

        upload.delete()

        assert parse(next(chunks))[0] == "gone"
        assert list(chunks) == []

    def test_other_students_cannot_follow(self, other_client, user):
        response = open_stream(other_client, make_upload(user))

        assert response.status_code == 404
        assert json.loads(response.content)["detail"]

    def test_requires_authentication(self, api_client, user):
        response = open_stream(api_client, make_upload(user), accept="application/json")

        assert response.status_code == 401
        assert response["Content-Type"] == "application/json"


class TestStreamLimits:
    def test_stream_closes_after_max_duration(self, settings):
        settings.SSE_MAX_SECONDS = 0

        chunks = list(sse.status_events(lambda: ("reading", {}), terminal={"extracted"}))

        assert chunks == ["retry: 3000\n\n", 'event: reading\ndata: {}\n\n']

    def test_heartbeat_while_nothing_changes(self, settings):
        settings.SSE_HEARTBEAT_SECONDS = 0
        events = sse.status_events(lambda: ("reading", {}), terminal={"extracted"})

        assert [next(events) for _ in range(3)] == ["retry: 3000\n\n", 'event: reading\ndata: {}\n\n', ": ping\n\n"]

    def test_data_is_json_with_dates_and_accents(self):
        assert sse.format_event("ready", {"title": "Équation"}) == 'event: ready\ndata: {"title": "Équation"}\n\n'
