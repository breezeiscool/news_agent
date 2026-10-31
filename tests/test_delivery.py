import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from trendradar.ai.client import AIClient
from trendradar.notification.senders import send_to_email


class DeliveryTests(unittest.TestCase):
    def test_trailing_comma_does_not_create_empty_smtp_recipient(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.html"
            report.write_text("<html><body>测试报告</body></html>", encoding="utf-8")
            with patch("trendradar.notification.senders.smtplib.SMTP_SSL") as smtp:
                sent = send_to_email(
                    "sender@163.com", "test-password", "a@example.com, ",
                    "晨报", str(report),
                )
                self.assertTrue(sent)
                args, kwargs = smtp.return_value.send_message.call_args
                self.assertEqual(kwargs["to_addrs"], ["a@example.com"])
                self.assertEqual(args[0]["To"], "a@example.com")

    def test_deepseek_v4_summary_uses_non_thinking_mode(self):
        client = AIClient({"MODEL": "deepseek/deepseek-v4-flash", "API_KEY": "test-key"})
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="简报正文"), finish_reason="stop")],
            usage=SimpleNamespace(completion_tokens=12),
        )
        with patch("trendradar.ai.client._lazy_completion", return_value=response) as completion:
            self.assertEqual(client.chat([{"role": "user", "content": "总结"}]), "简报正文")
            kwargs = completion.call_args.kwargs
            self.assertEqual(kwargs["reasoning_effort"], "none")
            self.assertEqual(kwargs["extra_body"], {"thinking": {"type": "disabled"}})


if __name__ == "__main__":
    unittest.main()
