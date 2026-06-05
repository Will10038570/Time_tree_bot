import os
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).parent.parent / ".env")

_AGENT_MD = Path(__file__).parent.parent / "ai_agent" / "AI_AGENT.md"
_SCHEMA_YML = Path(__file__).parent.parent / "configs" / "json_example.yml"
_DEFAULTS_YML = Path(__file__).parent.parent / "configs" / "defaults.yml"
DEFAULT_MODEL = "gemini-2.5-flash"


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


class GeminiManager:
    def __init__(self, model: str = DEFAULT_MODEL):
        self._model = model
        self._client = None
        self._system: str = ""
        self._schema: types.Schema | None = None
        self._sessions: dict[str, list[types.Content]] = {}

    def start(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("[GeminiManager] GEMINI_API_KEY 未設定")
        self._client = genai.Client(api_key=api_key)
        defaults = {}
        if _DEFAULTS_YML.exists():
            with open(_DEFAULTS_YML, encoding="utf-8") as f:
                defaults = yaml.safe_load(f)
        raw = _AGENT_MD.read_text(encoding="utf-8") if _AGENT_MD.exists() else ""
        self._system = raw.format(**defaults) if defaults else raw
        if _SCHEMA_YML.exists():
            with open(_SCHEMA_YML, encoding="utf-8") as f:
                self._schema = _build_schema(yaml.safe_load(f))
        print(f"[GeminiManager] 啟動完成 (model={self._model}, defaults={defaults})")

    def stop(self):
        self._sessions.clear()
        self._client = None
        print("[GeminiManager] 已停止")

    def parse(self, user_id: str, text: str) -> dict:
        if user_id not in self._sessions:
            print(f"[GeminiManager] 建立新 session (user_id={user_id})")
            self._sessions[user_id] = []

        history = self._sessions[user_id]
        history.append(types.Content(role="user", parts=[types.Part(text=text)]))
        print(f"[GeminiManager] 解析中 (user_id={user_id})：{text}")

        config = types.GenerateContentConfig(
            system_instruction=self._system,
            response_mime_type="application/json",
            response_schema=self._schema,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=history,
            config=config,
        )

        reply = response.text
        history.append(types.Content(role="model", parts=[types.Part(text=reply)]))
        result = json.loads(reply)
        print(f"[GeminiManager] 解析結果：{result}")
        return result

    def reset_session(self, user_id: str):
        self._sessions.pop(user_id, None)
        print(f"[GeminiManager] session 已重置 (user_id={user_id})")
