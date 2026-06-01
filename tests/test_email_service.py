import pytest
from unittest.mock import AsyncMock, patch

from services.email_service import send_contact_notification, send_cap_alert


@pytest.mark.asyncio
async def test_contact_notification_sends_when_configured():
    with patch("services.email_service.settings") as mock_s, \
         patch("services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_s.smtp_host = "smtp.test.com"
        mock_s.smtp_port = 587
        mock_s.smtp_user = "user@test.com"
        mock_s.smtp_pass = "secret"
        mock_s.owner_email = "owner@test.com"

        await send_contact_notification("Alice", "alice@test.com", "Hello!")
        mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_contact_notification_skips_when_not_configured():
    with patch("services.email_service.settings") as mock_s, \
         patch("services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_s.smtp_host = ""
        mock_s.smtp_user = ""
        mock_s.smtp_pass = ""
        mock_s.owner_email = ""

        await send_contact_notification("Bob", "bob@test.com", "Hi")
        mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_cap_alert_sends_when_configured():
    with patch("services.email_service.settings") as mock_s, \
         patch("services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_s.smtp_host = "smtp.test.com"
        mock_s.smtp_port = 587
        mock_s.smtp_user = "user@test.com"
        mock_s.smtp_pass = "secret"
        mock_s.owner_email = "owner@test.com"
        mock_s.daily_cost_cap_usd = 1.0

        await send_cap_alert(1.05)
        mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_email_handles_smtp_error_gracefully():
    import aiosmtplib
    with patch("services.email_service.settings") as mock_s, \
         patch("services.email_service.aiosmtplib.send", new_callable=AsyncMock,
               side_effect=aiosmtplib.SMTPException("connection refused")):
        mock_s.smtp_host = "smtp.test.com"
        mock_s.smtp_port = 587
        mock_s.smtp_user = "user@test.com"
        mock_s.smtp_pass = "secret"
        mock_s.owner_email = "owner@test.com"

        # Should not raise — errors are caught and logged
        await send_contact_notification("Eve", "eve@test.com", "Test")

