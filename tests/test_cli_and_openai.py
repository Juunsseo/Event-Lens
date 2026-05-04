import base64

from event_lens.cli import main
from event_lens.services.inference import OpenAIImageInferenceService, _extract_json_payload


def _write_test_png(tmp_path, name: str = "test.png") -> str:
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    image_path = tmp_path / name
    image_path.write_bytes(png_bytes)
    return str(image_path)


def test_extract_json_payload_from_fenced_response() -> None:
    payload = _extract_json_payload("```json\n{\"objects\": []}\n```")
    assert payload == {"objects": []}


def test_openai_service_encodes_local_file_to_data_url(tmp_path) -> None:
    svc = OpenAIImageInferenceService.__new__(OpenAIImageInferenceService)
    data_url = svc._to_model_image_url(_write_test_png(tmp_path))

    assert data_url.startswith("data:image/")
    assert ";base64," in data_url


def test_cli_demo_command_runs_with_metadata_inference(tmp_path, capsys) -> None:
    image = _write_test_png(tmp_path, "demo.png")
    code = main(["demo", "--image", image, "--query", "find image", "--inference", "metadata"])

    out = capsys.readouterr().out
    assert code == 0
    assert "query_id" in out
    assert "results" in out
