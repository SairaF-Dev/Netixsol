function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);
    const expectedToken = PropertiesService.getScriptProperties().getProperty("RELAY_TOKEN");

    if (!expectedToken || payload.token !== expectedToken) {
      return jsonResponse({ ok: false, error: "unauthorized" });
    }

    const recipient = String(payload.to || "").trim();
    const subject = String(payload.subject || "");
    const text = String(payload.text || "");
    const html = String(payload.html || "");

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient)) {
      return jsonResponse({ ok: false, error: "invalid_recipient" });
    }
    if (!subject || subject.length > 200 || text.length > 30000 || html.length > 30000) {
      return jsonResponse({ ok: false, error: "invalid_message" });
    }
    if (MailApp.getRemainingDailyQuota() < 1) {
      return jsonResponse({ ok: false, error: "daily_recipient_quota_exceeded" });
    }

    const options = {
      to: recipient,
      subject: subject,
      body: text || " ",
      name: "Netixsol Property Assistant"
    };
    if (html) {
      options.htmlBody = html;
    }

    MailApp.sendEmail(options);
    return jsonResponse({ ok: true });
  } catch (error) {
    console.error("Gmail relay failed: " + String(error));
    return jsonResponse({ ok: false, error: "email_delivery_failed" });
  }
}

function jsonResponse(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
