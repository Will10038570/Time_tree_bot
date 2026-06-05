import os
from pyngrok import ngrok, conf


class WebhookManager:
    def __init__(self, port: int = 5000):
        self.port = port
        self._tunnel = None
        authtoken = os.getenv("NGROK_AUTHTOKEN")
        if authtoken:
            conf.get_default().auth_token = authtoken

    def start(self) -> str:
        ngrok.kill()
        self._tunnel = ngrok.connect(self.port)
        url = self._tunnel.public_url.replace("http://", "https://")
        print(f"[WebhookManager] Tunnel 已啟動：{url}/callback")
        return url

    def stop(self):
        if self._tunnel:
            ngrok.disconnect(self._tunnel.public_url)
        ngrok.kill()
        self._tunnel = None
