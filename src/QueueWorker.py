import os
import queue
import threading
from pathlib import Path
from dotenv import load_dotenv
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    PushMessageRequest, TextMessage,
)

load_dotenv(Path(__file__).parent.parent / ".env")


class QueueWorker:
    def __init__(self, gemini_mgr, operator):
        self._gemini = gemini_mgr
        self._operator = operator
        self._configuration = Configuration(
            access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
        )
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[QueueWorker] 啟動完成")

    def stop(self):
        self._running = False
        self._queue.put(None)
        print("[QueueWorker] 已停止")

    def enqueue(self, user_id: str, text: str):
        self._queue.put({"user_id": user_id, "text": text})
        print(f"[QueueWorker] 加入佇列 (user_id={user_id})：{text}")

    def _loop(self):
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            user_id = item["user_id"]
            text = item["text"]
            print(f"[QueueWorker] 開始處理 (user_id={user_id})：{text}")
            try:
                cmd = self._gemini.parse(user_id, text)
                print(f"[QueueWorker] 送出指令：{cmd}")
                reply = self._operator.run(cmd) or "✅ 完成"
            except Exception as e:
                reply = f"❌ {e}"
            self._push(user_id, reply)

    def _push(self, user_id: str, message: str):
        try:
            with ApiClient(self._configuration) as api_client:
                MessagingApi(api_client).push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=message)],
                    )
                )
            print(f"[QueueWorker] Push 完成 (user_id={user_id})")
        except Exception as e:
            print(f"[QueueWorker] Push 失敗 (user_id={user_id})：{e}")
