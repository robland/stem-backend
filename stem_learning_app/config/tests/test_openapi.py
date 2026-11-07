"""Le front génère son client TypeScript depuis le schéma OpenAPI : il doit décrire ce que l'API fait vraiment."""

import pytest
from drf_spectacular.generators import SchemaGenerator


@pytest.fixture(scope="module")
def schema():
    return SchemaGenerator().get_schema(request=None, public=True)


def request_schema(schema, path, content_type="application/json"):
    ref = schema["paths"][path]["post"]["requestBody"]["content"][content_type]["schema"]["$ref"]
    return schema["components"]["schemas"][ref.rsplit("/", 1)[1]]


def response_schema(schema, path, method="post"):
    ref = schema["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    return schema["components"]["schemas"][ref.rsplit("/", 1)[1]]


def test_login_request_has_only_credentials_and_response_only_access(schema):
    request = request_schema(schema, "/api/auth/login/")
    response = response_schema(schema, "/api/auth/login/")

    assert set(request["properties"]) == {"phone", "password"}
    assert set(response["properties"]) == {"access"}  # le refresh part en cookie


def test_refresh_body_is_optional(schema):
    operation = schema["paths"]["/api/auth/refresh/"]["post"]
    request = request_schema(schema, "/api/auth/refresh/")
    response = response_schema(schema, "/api/auth/refresh/")

    assert not operation["requestBody"].get("required", False)  # web : body vide, refresh en cookie
    assert "required" not in request
    assert response["required"] == ["access"]


def test_upload_file_is_binary(schema):
    upload = request_schema(schema, "/api/uploads/", "multipart/form-data")

    assert upload["properties"]["file"]["format"] == "binary"


@pytest.mark.parametrize("component", ["ExerciseDetail", "ExerciseOffline"])
def test_exercise_content_is_nullable(schema, component):
    properties = schema["components"]["schemas"][component]["properties"]

    assert properties["content"]["nullable"] is True
    assert properties["current_attempt"]["nullable"] is True
