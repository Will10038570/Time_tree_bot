# 流程說明：
# 1. 在 LINE Developers Console 設定 Webhook URL 為 ngrok 提供的對外網址
# 2. ngrok 監聽該網址，收到請求後轉發到 localhost:5000
# 3. Flask 監聽 port 5000，收到 POST /callback 請求時執行 callback()
# 4. callback() 驗證請求簽名，通過後交給 LINE SDK 的 handler.handle()
# 5. SDK 判斷事件類型，若為文字訊息則分派到 handle_message()
# 6. handle_message() 解析指令、執行自動化，並透過 LINE API 回覆使用者

import os
import signal
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
from command_handler import handle

load_dotenv(Path(__file__).parent.parent / ".env")

app = Flask(__name__)
configuration = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])


def free_port(port: int):
    try:
        result = subprocess.check_output(
            f'netstat -ano | findstr :{port}', shell=True,
            text=True, encoding="utf-8", errors="ignore"
        )
        for line in result.splitlines():
            if "LISTENING" in line:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    if pid != str(os.getpid()):
                        subprocess.call(
                            f"taskkill /PID {pid} /F", shell=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
    except Exception:
        pass


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    print(f"[callback] 收到請求, signature={signature[:10]}...")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("[callback] 簽名驗證失敗")
        abort(400)
    print("[callback] 處理成功")
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    user_text = event.message.text.strip()
    print(f"[收到] {user_text}")
    reply = handle(user_text)
    print(f"[回覆] {reply}")
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)],
            )
        )


def _shutdown(*_):
    print("\n[bot] 關閉中...")
    os._exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    free_port(5000)
    app.run(port=5000, debug=False)
