const router = require('express').Router();
const bcrypt = require('bcryptjs');
const prisma = require('../db');
const { sign, userAuth } = require('../middleware/auth');

function publicUser(u) {
  return { id: u.id, phone: u.phone, name: u.name, balance: u.balance };
}

// POST /auth/register  { phone, name, password }
router.post('/register', async (req, res) => {
  const { phone, name, password } = req.body || {};
  if (!phone || !name || !password) {
    return res.status(400).json({ error: 'phone, name and password are required' });
  }
  const exists = await prisma.user.findUnique({ where: { phone } });
  if (exists) return res.status(409).json({ error: 'This mobile number is already registered' });

  const user = await prisma.user.create({
    data: { phone, name, password: await bcrypt.hash(password, 10) },
  });
  const token = sign({ sub: user.id, role: 'user' });
  res.json({ token, user: publicUser(user) });
});

// POST /auth/login  { phone, password }   (no OTP)
router.post('/login', async (req, res) => {
  const { phone, password } = req.body || {};
  if (!phone || !password) return res.status(400).json({ error: 'phone and password are required' });

  const user = await prisma.user.findUnique({ where: { phone } });
  if (!user || !(await bcrypt.compare(password, user.password))) {
    return res.status(401).json({ error: 'Invalid mobile number or password' });
  }
  const token = sign({ sub: user.id, role: 'user' });
  res.json({ token, user: publicUser(user) });
});

// POST /auth/forgot  { phone }  -> generates an OTP and sends it via SMS gateway
const { sendOtp } = require('../sms');
router.post('/forgot', async (req, res) => {
  const phone = String(req.body?.phone || '').replace(/\D/g, '');
  if (!phone) return res.status(400).json({ error: 'Enter your registered mobile number' });
  const user = await prisma.user.findUnique({ where: { phone } });
  if (!user) return res.status(404).json({ error: 'No account found with this mobile number' });

  const code = String(Math.floor(100000 + Math.random() * 900000)); // 6-digit
  const codeHash = await bcrypt.hash(code, 10);
  const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 min
  await prisma.otp.deleteMany({ where: { phone } });
  await prisma.otp.create({ data: { phone, codeHash, expiresAt } });

  try {
    await sendOtp(phone, code);
  } catch (e) {
    if (e.code === 'SMS_NOT_CONFIGURED') {
      return res.status(503).json({ error: 'OTP service is not set up yet. Please contact support.' });
    }
    return res.status(502).json({ error: 'Could not send OTP. Try again shortly.' });
  }
  res.json({ ok: true, message: 'An OTP has been sent to your mobile number.' });
});

// POST /auth/reset  { phone, otp, password }  -> verifies OTP and sets new password
router.post('/reset', async (req, res) => {
  const phone = String(req.body?.phone || '').replace(/\D/g, '');
  const otp = String(req.body?.otp || '').trim();
  const password = String(req.body?.password || '');
  if (!phone || !otp || !password) return res.status(400).json({ error: 'phone, otp and new password are required' });
  if (password.length < 4) return res.status(400).json({ error: 'Password must be at least 4 characters' });

  const rec = await prisma.otp.findFirst({ where: { phone }, orderBy: { createdAt: 'desc' } });
  if (!rec) return res.status(400).json({ error: 'Please request a new OTP' });
  if (rec.expiresAt < new Date()) return res.status(400).json({ error: 'OTP expired. Request a new one.' });
  if (!(await bcrypt.compare(otp, rec.codeHash))) return res.status(400).json({ error: 'Incorrect OTP' });

  await prisma.user.update({ where: { phone }, data: { password: await bcrypt.hash(password, 10) } });
  await prisma.otp.deleteMany({ where: { phone } });
  res.json({ ok: true, message: 'Password updated. You can now log in.' });
});

// GET /auth/me
router.get('/me', userAuth, async (req, res) => {
  const user = await prisma.user.findUnique({ where: { id: req.userId } });
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json({ user: publicUser(user) });
});

module.exports = router;
