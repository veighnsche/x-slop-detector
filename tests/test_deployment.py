"""Static guardrails only; live DNS/TLS/service checks are separately recorded."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def test_private_single_worker_launcher(self):
        script = (ROOT / "deploy/start-server.sh").read_text()
        self.assertIn('--host 127.0.0.1 --port 18767 --workers 1', script)
        self.assertIn('--no-access-log --no-proxy-headers', script)
        self.assertIn('CREDENTIALS_DIRECTORY', script)
        self.assertNotIn('set -x', script)

    def test_3060_offline_unprivileged_service(self):
        unit = (ROOT / "deploy/x-slop-detector.service").read_text()
        for line in (
            "User=xslop", "Group=xslop",
            "Environment=CUDA_VISIBLE_DEVICES=GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db",
            "Environment=DETECTOR_GPU_UUID=GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db",
            "Environment=DETECTOR_IDLE_SECONDS=600",
            "Environment=HF_HUB_OFFLINE=1", "NoNewPrivileges=yes",
            "IPAddressDeny=any", "IPAddressAllow=localhost",
            "LoadCredential=api-token:/etc/x-slop-detector/api-token",
        ):
            self.assertIn(line, unit.splitlines())
        self.assertNotIn("DETECTOR_API_TOKEN=", unit)
        self.assertNotIn("DETECTOR_WATERMARK_CONFIG=", unit)

    def test_proxy_filters_socket_peer_and_has_no_credentials(self):
        site = (ROOT / "deploy/slop-detection.caddy").read_text()
        self.assertIn("@outside not remote_ip", site)
        self.assertNotIn("client_ip", site)
        self.assertIn("respond @outside", site)
        self.assertLess(site.index("respond @outside"), site.index("reverse_proxy"))
        self.assertIn("192.168.2.0/24", site)
        self.assertIn("100.64.0.0/10", site)
        self.assertIn("reverse_proxy 127.0.0.1:18767", site)
        self.assertIn("output discard", site)
        self.assertNotIn("api_token", site)
        self.assertIn("import cloudflare_tls", site)
