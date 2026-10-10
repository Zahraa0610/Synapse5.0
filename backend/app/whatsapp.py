"""Send verification codes on WhatsApp through Twilio.

Configure in backend/.env:
    TWILIO_ACCOUNT_SID=ACxxxxxxxx
    TWILIO_AUTH_TOKEN=xxxxxxxx
    TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   # Twilio sandbox number, or your approved sender
    TWILIO_CONTENT_SID=HXxxxxxxxx                # optional: an approved "authentication" template
                                                 # (needed outside the sandbox / 24-hour window)

Without these settings the code is printed in the server console instead, so the
app still works on a developer's machine.
"""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

from flask import current_app

TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class WhatsAppError(Exception):
    pass


def code_message(code):
    return (
        f"Your Ma'ak verification code is {code}. It expires in 10 minutes. Do not share it.\n"
        f"رمز التحقق في معك: {code}. صالح لمدة 10 دقائق. لا تشاركه مع أحد."
    )


def is_configured():
    config = current_app.config
    return bool(config.get("TWILIO_ACCOUNT_SID") and config.get("TWILIO_AUTH_TOKEN") and config.get("TWILIO_WHATSAPP_FROM"))


def send_code(phone, code):
    """Returns "whatsapp" when sent, or "console" when WhatsApp is not configured."""
    if not is_configured():
        print(f" * WhatsApp is not configured. Verification code for {phone}: {code}")
        return "console"

    config = current_app.config
    sender = config["TWILIO_WHATSAPP_FROM"]
    if not sender.startswith("whatsapp:"):
        sender = "whatsapp:" + sender
    fields = {"From": sender, "To": "whatsapp:" + phone}
    if config.get("TWILIO_CONTENT_SID"):
        # Approved WhatsApp template whose first variable {{1}} is the code
        fields["ContentSid"] = config["TWILIO_CONTENT_SID"]
        fields["ContentVariables"] = json.dumps({"1": code})
    else:
        fields["Body"] = code_message(code)
    body = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(TWILIO_URL.format(sid=config["TWILIO_ACCOUNT_SID"]), data=body, method="POST")
    auth = base64.b64encode(f"{config['TWILIO_ACCOUNT_SID']}:{config['TWILIO_AUTH_TOKEN']}".encode()).decode()
    request.add_header("Authorization", f"Basic {auth}")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode() or "{}")
        except ValueError:
            detail = {}
        current_app.logger.warning("Twilio error %s: %s", detail.get("code"), detail.get("message"))
        if detail.get("code") == 63015:
            raise WhatsAppError(
                "This number has not joined the WhatsApp sandbox yet. Send the 'join' message to the Twilio number first."
            ) from exc
        if detail.get("code") == 63016:
            raise WhatsAppError(
                "WhatsApp only allows this message within 24 hours of your last message to us. "
                "Send any message to the Twilio number, then try again."
            ) from exc
        raise WhatsAppError("We could not send the WhatsApp message. Check the number and try again.") from exc
    except urllib.error.URLError as exc:
        raise WhatsAppError("WhatsApp is unreachable right now. Try again in a minute.") from exc
    return "whatsapp"
