// Minimal pluggable SMS sender. Configure via environment variables:
//   SMS_PROVIDER = fast2sms | msg91 | (empty = disabled)
//   SMS_API_KEY  = your gateway API key
//   SMS_SENDER_ID / SMS_TEMPLATE_ID = provider-specific (msg91 needs a DLT template)
// In India an SMS gateway account + DLT template approval is required to deliver OTPs.
const PROVIDER = (process.env.SMS_PROVIDER || '').toLowerCase();
const KEY = process.env.SMS_API_KEY || '';

async function sendOtp(phone, code) {
  if (!PROVIDER || !KEY) {
    const e = new Error('SMS gateway not configured. Set SMS_PROVIDER and SMS_API_KEY.');
    e.code = 'SMS_NOT_CONFIGURED';
    throw e;
  }
  if (PROVIDER === 'fast2sms') {
    const url = 'https://www.fast2sms.com/dev/bulkV2?authorization=' + encodeURIComponent(KEY) +
      '&route=otp&variables_values=' + encodeURIComponent(code) + '&flash=0&numbers=' + encodeURIComponent(phone);
    const r = await fetch(url);
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.return === false) throw new Error(j.message || 'Failed to send OTP');
    return true;
  }
  if (PROVIDER === 'msg91') {
    const tmpl = process.env.SMS_TEMPLATE_ID || '';
    const r = await fetch('https://control.msg91.com/api/v5/otp?template_id=' + encodeURIComponent(tmpl) +
      '&mobile=91' + encodeURIComponent(phone) + '&otp=' + encodeURIComponent(code), {
      method: 'POST', headers: { authkey: KEY, 'Content-Type': 'application/json' },
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.type === 'error') throw new Error(j.message || 'Failed to send OTP');
    return true;
  }
  throw new Error('Unknown SMS_PROVIDER: ' + PROVIDER);
}

module.exports = { sendOtp };
