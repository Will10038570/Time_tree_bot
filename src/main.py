import os
import signal
from WebhookManager import WebhookManager
from GeminiManager import GeminiManager
from TimeTreeOperator import TimeTreeOperator
from QueueWorker import QueueWorker
from LineBotManager import LineBotManager

PORT = 5000


def main():
    print("[main] 啟動中...")

    print("[main] 初始化 WebhookManager...")
    webhook_mgr = WebhookManager(port=PORT)

    print("[main] 初始化 GeminiManager...")
    gemini_mgr = GeminiManager()

    print("[main] 初始化 TimeTreeOperator...")
    operator = TimeTreeOperator()

    print("[main] 初始化 QueueWorker...")
    worker = QueueWorker(gemini_mgr=gemini_mgr, operator=operator)

    print("[main] 初始化 LineBotManager...")
    linebot_mgr = LineBotManager(worker=worker)

    def _shutdown(*_):
        print("\n[main] 收到關閉訊號")
        print("[main] 停止 LineBotManager...")
        linebot_mgr.stop()
        print("[main] 停止 QueueWorker...")
        worker.stop()
        print("[main] 停止 GeminiManager...")
        gemini_mgr.stop()
        print("[main] 停止 WebhookManager (ngrok)...")
        webhook_mgr.stop()
        print("[main] 關閉完成")
        os._exit(0)

    print("[main] 註冊 signal handlers (SIGINT, SIGTERM)...")
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("[main] 啟動 WebhookManager (ngrok)...")
    webhook_mgr.start()

    print("[main] 啟動 GeminiManager...")
    gemini_mgr.start()

    print("[main] 啟動 QueueWorker...")
    worker.start()

    print(f"[main] 啟動 LineBotManager (port={PORT})...")
    linebot_mgr.start(port=PORT)


if __name__ == "__main__":
    main()
