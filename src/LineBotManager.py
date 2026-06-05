import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

load_dotenv(Path(__file__).parent.parent / ".env")


class LineBotManager:
    def __init__(self, worker):
        self._worker = worker
        self._app = Flask(__name__)
        self._configuration = Configuration(
            access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
        )
        self._handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])
        self._register_routes()

    def _register_routes(self):
        app = self._app
        sdk_handler = self._handler
        configuration = self._configuration
        worker = self._worker

        @app.route("/callback", methods=["POST"])
        def callback():
            signature = request.headers.get("X-Line-Signature", "")
            body = request.get_data(as_text=True)
            try:
                sdk_handler.handle(body, signature)
            except InvalidSignatureError:
                abort(400)
            return "OK"

        @sdk_handler.add(MessageEvent, message=TextMessageContent)
        def handle_message(event: MessageEvent):
            user_id = event.source.user_id
            user_text = event.message.text.strip()
            print(f"[LineBotManager] 收到 (user_id={user_id})：{user_text}")

            with ApiClient(configuration) as api_client:
                MessagingApi(api_client).reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="⏳ 處理中...")],
                    )
                )

            worker.enqueue(user_id, user_text)

    def start(self, port: int = 5000):
        self._free_port(port)
        self._app.run(port=port, debug=False)

    def stop(self):
        pass

    def _free_port(self, port: int):
        try:
            result = subprocess.check_output(
                f"netstat -ano | findstr :{port}", shell=True,
                text=True, encoding="utf-8", errors="ignore",
            )
            for line in result.splitlines():
                if "LISTENING" in line:
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        if pid != str(os.getpid()):
                            subprocess.call(
                                f"taskkill /PID {pid} /F", shell=True,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
        except Exception:
            pass
