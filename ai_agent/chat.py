import os
import yaml
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"
_AGENT_MD = Path(__file__).parent / "AI_AGENT.md"
DEFAULT_SYSTEM = _AGENT_MD.read_text(encoding="utf-8") if _AGENT_MD.exists() else "You are a helpful assistant."

_SCHEMA_YML = Path(__file__).parent.parent / "configs" / "json_example.yml"


def _build_schema(d: dict) -> types.Schema:
    type_map = {
        "string": types.Type.STRING,
        "integer": types.Type.INTEGER,
        "boolean": types.Type.BOOLEAN,
        "object": types.Type.OBJECT,
        "array": types.Type.ARRAY,
    }
    kwargs: dict = {"type": type_map[d["type"]]}
    if "enum" in d:
        kwargs["enum"] = d["enum"]
    if "nullable" in d:
        kwargs["nullable"] = d["nullable"]
    if "description" in d:
        kwargs["description"] = d["description"]
    if "properties" in d:
        kwargs["properties"] = {k: _build_schema(v) for k, v in d["properties"].items()}
    if "required" in d:
        kwargs["required"] = d["required"]
    return types.Schema(**kwargs)


def _load_response_schema() -> types.Schema | None:
    if not _SCHEMA_YML.exists():
        return None
    with open(_SCHEMA_YML, encoding="utf-8") as f:
        return _build_schema(yaml.safe_load(f))


_RESPONSE_SCHEMA = _load_response_schema()


class GeminiChat:
    def __init__(self, model: str = DEFAULT_MODEL, system: str = DEFAULT_SYSTEM):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._system = system
        self._history: list[types.Content] = []

    def send(self, message: str) -> str:
        self._history.append(types.Content(role="user", parts=[types.Part(text=message)]))

        config = types.GenerateContentConfig(
            system_instruction=self._system,
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=self._history,
            config=config,
        )

        reply = response.text
        self._history.append(types.Content(role="model", parts=[types.Part(text=reply)]))
        return reply

    def reset(self):
        self._history.clear()
