'use strict';
const express = require('express');
const cors    = require('cors');
const https   = require('https');

const app = express();
app.use(cors());
app.use(express.json());

const PORT       = process.env.PORT               || 3000;
const OPENAI_KEY = process.env.OPENAI_API_KEY      || '';
const TG_TOKEN   = process.env.TELEGRAM_BOT_TOKEN  || '';
const ADMIN_ID   = process.env.TELEGRAM_ADMIN_ID   || '';

// ── In-memory store ───────────────────────────────────────────────────────────
// matches: { [key]: { id, home:{name,score}, away:{name,score}, leagueName, country, time, status } }
// preds:   { [key]: { h, d, a, score, advice, confidence, sources, aiUsed } }
let store = { matches: {}, preds: {} };

function matchKey(home, away) {
    return `${(home || '').trim().toLowerCase()}|${(away || '').trim().toLowerCase()}`;
}

// ── Telegram helpers ──────────────────────────────────────────────────────────
function tgPost(path, data) {
    if (!TG_TOKEN) return;
    const body = JSON.stringify(data);
    const req  = https.request({
        hostname: 'api.telegram.org',
        path:     `/bot${TG_TOKEN}/${path}`,
        method:   'POST',
        headers:  { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    });
    req.on('error', () => {});
    req.write(body);
    req.end();
}

const reply = (chatId, text) =>
    tgPost('sendMessage', { chat_id: chatId, text, parse_mode: 'HTML' });

// ── Telegram command handler ──────────────────────────────────────────────────
/*
  Commands:
    /tip  Home | Away | League | Country | KickoffTime | H% | D% | A% | PredScore | Advice
    /pred Home | Away | H% | D% | A% | PredScore | Advice
    /live Home | Away | HomeGoals | AwayGoals | Minute
    /ft   Home | Away | HomeGoals | AwayGoals
    /del  Home | Away
    /clear
    /list
    /help
*/
function handleMessage(msg) {
    const chatId = msg.chat?.id;
    const text   = (msg.text || '').trim();
    if (!chatId || !text.startsWith('/')) return;

    if (ADMIN_ID && String(msg.from?.id) !== String(ADMIN_ID)) {
        reply(chatId, '⛔ Unauthorized');
        return;
    }

    const spaceIdx = text.indexOf(' ');
    const cmd      = (spaceIdx === -1 ? text : text.slice(0, spaceIdx)).toLowerCase();
    const rawArgs  = spaceIdx === -1 ? '' : text.slice(spaceIdx + 1);
    const args     = rawArgs.split('|').map(s => s.trim());

    switch (cmd) {

        case '/help': {
            reply(chatId, [
                '<b>Magic Analysis Bot Commands</b>',
                '',
                '<b>Add match + prediction:</b>',
                '/tip Home | Away | League | Country | Time | H% | D% | A% | Score | Advice',
                '<i>Example: /tip Arsenal | Chelsea | Premier League | England | 20:00 | 60 | 25 | 15 | 2-1 | Arsenal to win</i>',
                '',
                '<b>Add/update prediction only:</b>',
                '/pred Home | Away | H% | D% | A% | Score | Advice',
                '',
                '<b>Update live score:</b>',
                '/live Home | Away | HomeGoals | AwayGoals | Minute',
                '<i>Example: /live Arsenal | Chelsea | 1 | 0 | 67</i>',
                '',
                '<b>Mark finished:</b>',
                '/ft Home | Away | HomeGoals | AwayGoals',
                '',
                '<b>Remove a match:</b>',
                '/del Home | Away',
                '',
                '<b>Clear all matches:</b>',
                '/clear',
                '',
                '<b>List all matches:</b>',
                '/list',
            ].join('\n'));
            break;
        }

        case '/tip': {
            // /tip Home | Away | League | Country | Time | H% | D% | A% | Score | Advice
            const [home, away, league, country, time, hp, dp, ap, score, ...advParts] = args;
            if (!home || !away) {
                reply(chatId, '❌ Minimum: /tip Home | Away\nFull: /tip Home | Away | League | Country | Time | H% | D% | A% | Score | Advice');
                return;
            }
            const k = matchKey(home, away);
            store.matches[k] = {
                id:         k,
                home:       { name: home.trim(), score: null },
                away:       { name: away.trim(), score: null },
                leagueName: league  || 'Unknown League',
                country:    country || '',
                time:       time    || '',
                status:     'NS',
            };
            const h = parseInt(hp) || 0;
            const d = parseInt(dp) || 0;
            const a = parseInt(ap) || 0;
            if (h || d || a) {
                const total = h + d + a || 100;
                store.preds[k] = {
                    h:          Math.round(h * 100 / total),
                    d:          Math.round(d * 100 / total),
                    a:          Math.round(a * 100 / total),
                    score:      score       || null,
                    advice:     advParts.join('|').trim() || null,
                    confidence: Math.round(Math.max(h, d, a) * 10 / total) / 10,
                    sources:    ['manual'],
                    aiUsed:     false,
                };
            }
            const tot = h + d + a || 100;
            const predTxt = (h || d || a)
                ? `Prediction: ${Math.round(h*100/tot)}% / ${Math.round(d*100/tot)}% / ${Math.round(a*100/tot)}%${score ? ' · ' + score : ''}`
                : 'No prediction yet — use /pred to add one';
            reply(chatId, [
                `✅ <b>${home} vs ${away}</b>`,
                `${league || 'Unknown League'}${country ? ' · ' + country : ''}${time ? ' @ ' + time : ''}`,
                predTxt,
            ].join('\n'));
            break;
        }

        case '/pred': {
            // /pred Home | Away | H% | D% | A% | Score | Advice
            const [home, away, hp, dp, ap, score, ...advParts] = args;
            if (!home || !away) {
                reply(chatId, '❌ Usage: /pred Home | Away | H% | D% | A% | Score | Advice');
                return;
            }
            const k = matchKey(home, away);
            if (!store.matches[k]) {
                reply(chatId, `⚠️ Match not found: ${home} vs ${away}\nAdd it first with /tip`);
                return;
            }
            const h = parseInt(hp) || 0;
            const d = parseInt(dp) || 0;
            const a = parseInt(ap) || 0;
            const total = h + d + a || 100;
            store.preds[k] = {
                h:          Math.round(h * 100 / total),
                d:          Math.round(d * 100 / total),
                a:          Math.round(a * 100 / total),
                score:      score       || null,
                advice:     advParts.join('|').trim() || null,
                confidence: Math.round(Math.max(h, d, a) * 10 / total) / 10,
                sources:    ['manual'],
                aiUsed:     false,
            };
            reply(chatId, `✅ Prediction updated: <b>${home} vs ${away}</b>\n${Math.round(h*100/total)}% / ${Math.round(d*100/total)}% / ${Math.round(a*100/total)}%${score ? ' · ' + score : ''}`);
            break;
        }

        case '/live': {
            // /live Home | Away | HomeGoals | AwayGoals | Minute
            const [home, away, hg, ag, min] = args;
            if (!home || !away) {
                reply(chatId, '❌ Usage: /live Home | Away | HomeGoals | AwayGoals | Minute');
                return;
            }
            const k = matchKey(home, away);
            if (!store.matches[k]) {
                reply(chatId, `❌ Match not found: ${home} vs ${away}\nAdd it first with /tip`);
                return;
            }
            store.matches[k].home.score = parseInt(hg) || 0;
            store.matches[k].away.score = parseInt(ag) || 0;
            store.matches[k].status     = min ? String(parseInt(min) || 'LIVE') : 'LIVE';
            reply(chatId, `🔴 Live: <b>${home} ${hg}-${ag} ${away}</b>${min ? ' (' + min + "\')" : ''}`);
            break;
        }

        case '/ft': {
            // /ft Home | Away | HomeGoals | AwayGoals
            const [home, away, hg, ag] = args;
            if (!home || !away) {
                reply(chatId, '❌ Usage: /ft Home | Away | HomeGoals | AwayGoals');
                return;
            }
            const k = matchKey(home, away);
            if (!store.matches[k]) {
                reply(chatId, `❌ Match not found: ${home} vs ${away}`);
                return;
            }
            store.matches[k].home.score = parseInt(hg) || 0;
            store.matches[k].away.score = parseInt(ag) || 0;
            store.matches[k].status     = 'FT';
            reply(chatId, `✅ Full Time: <b>${home} ${hg}-${ag} ${away}</b>`);
            break;
        }

        case '/del': {
            const [home, away] = args;
            if (!home || !away) {
                reply(chatId, '❌ Usage: /del Home | Away');
                return;
            }
            const k = matchKey(home, away);
            const existed = !!store.matches[k];
            delete store.matches[k];
            delete store.preds[k];
            reply(chatId, existed
                ? `🗑️ Removed: <b>${home} vs ${away}</b>`
                : `⚠️ Not found: ${home} vs ${away}`);
            break;
        }

        case '/clear': {
            const count = Object.keys(store.matches).length;
            store = { matches: {}, preds: {} };
            reply(chatId, `🗑️ Cleared all ${count} match(es). Ready for today's fixtures.`);
            break;
        }

        case '/list': {
            const keys = Object.keys(store.matches);
            if (!keys.length) {
                reply(chatId, '📋 No matches stored.\nAdd one with /tip');
                return;
            }
            const lines = keys.map((k, i) => {
                const m   = store.matches[k];
                const p   = store.preds[k];
                const sc  = m.home.score != null && m.away.score != null
                    ? ` ${m.home.score}-${m.away.score}` : '';
                const icon = m.status === 'FT' ? '✅' : m.status === 'NS' ? '🔵' : '🔴';
                const pred = p ? ` [${p.h}/${p.d}/${p.a}]` : ' [no pred]';
                return `${i + 1}. ${icon} <b>${m.home.name} vs ${m.away.name}</b>${sc}${pred}\n   ${m.leagueName}${m.time ? ' @ ' + m.time : ''}`;
            });
            reply(chatId, `<b>Stored matches (${keys.length}):</b>\n\n${lines.join('\n\n')}`);
            break;
        }

        default:
            reply(chatId, 'Unknown command. Type /help for the full list.');
    }
}

// ── POST /telegram — Telegram webhook ────────────────────────────────────────
app.post('/telegram', (req, res) => {
    res.sendStatus(200); // always acknowledge immediately
    if (req.body?.message) handleMessage(req.body.message);
});

// ── GET /api/scores — serve matches grouped by league ────────────────────────
app.get('/api/scores', (req, res) => {
    const byLeague = {};
    for (const m of Object.values(store.matches)) {
        const lg = m.leagueName || 'Other';
        if (!byLeague[lg]) byLeague[lg] = { name: lg, country: m.country || '', match: [] };
        byLeague[lg].match.push({
            id:         m.id,
            home:       { name: m.home.name, score: m.home.score },
            away:       { name: m.away.name, score: m.away.score },
            status:     m.status,
            time:       m.time,
            leagueName: m.leagueName,
            country:    m.country,
        });
    }
    res.json({ livescore: { league: Object.values(byLeague) } });
});

// ── GET /api/get-predictions — serve prediction from store ────────────────────
app.get('/api/get-predictions', (req, res) => {
    const k = matchKey(req.query.home || '', req.query.away || '');
    const p = store.preds[k];
    const m = store.matches[k];

    if (!p) {
        return res.json({
            response: [{ predictions: { percent: { home: null, draw: null, away: null }, goals: null, advice: null } }],
            meta:     { confidence: 0, sources: [], aiUsed: false },
        });
    }

    const goalMatch = (p.score || '').match(/(\d+)\D+(\d+)/);
    const winner    = p.h >= p.d && p.h >= p.a
        ? `${m?.home.name || 'Home'} to win`
        : p.a > p.h && p.a >= p.d
            ? `${m?.away.name || 'Away'} to win`
            : 'Draw likely';

    res.json({
        response: [{
            predictions: {
                percent: { home: `${p.h}%`, draw: `${p.d}%`, away: `${p.a}%` },
                goals:   goalMatch ? { home: goalMatch[1], away: goalMatch[2] } : null,
                advice:  p.advice || winner,
            },
        }],
        meta: {
            confidence: p.confidence || 0.5,
            sources:    p.sources    || ['manual'],
            aiUsed:     p.aiUsed     || false,
        },
    });
});

// ── GET /api/upcoming — matches already served via /api/scores ────────────────
app.get('/api/upcoming', (req, res) => res.json({ matches: [] }));

// ── GET /api/match-analysis — OpenAI (optional, only if key set) ──────────────
app.get('/api/match-analysis', async (req, res) => {
    if (!OPENAI_KEY) return res.json({ analysis: null });
    const { home, away, league, status, score } = req.query;
    try {
        const prompt = `Football analyst. 2 sentences max. ${home} vs ${away} (${league}). Status: ${status}. Score: ${score}. Tactical insight + likely outcome.`;
        const body   = JSON.stringify({
            model:       'gpt-3.5-turbo',
            messages:    [{ role: 'user', content: prompt }],
            max_tokens:  100,
            temperature: 0.7,
        });
        const apiRes = await new Promise((resolve, reject) => {
            const r = https.request({
                hostname: 'api.openai.com',
                path:     '/v1/chat/completions',
                method:   'POST',
                headers:  {
                    'Content-Type':   'application/json',
                    'Authorization':  `Bearer ${OPENAI_KEY}`,
                    'Content-Length': Buffer.byteLength(body),
                },
            }, resolve);
            r.on('error', reject);
            r.write(body);
            r.end();
        });
        let raw = '';
        for await (const chunk of apiRes) raw += chunk;
        const analysis = JSON.parse(raw).choices?.[0]?.message?.content?.trim() || null;
        res.json({ analysis });
    } catch {
        res.json({ analysis: null });
    }
});

// ── GET /api/team-logo — TheSportsDB (free, no key needed) ───────────────────
app.get('/api/team-logo', async (req, res) => {
    const { name } = req.query;
    if (!name) return res.json({ logo: null });
    try {
        const apiRes = await new Promise((resolve, reject) => {
            const r = https.request({
                hostname: 'www.thesportsdb.com',
                path:     `/api/v1/json/3/searchteams.php?t=${encodeURIComponent(name)}`,
                method:   'GET',
                headers:  { 'User-Agent': 'Mozilla/5.0' },
            }, resolve);
            r.on('error', reject);
            r.end();
        });
        let raw = '';
        for await (const chunk of apiRes) raw += chunk;
        const logo = JSON.parse(raw).teams?.[0]?.strBadge || null;
        res.json({ logo });
    } catch {
        res.json({ logo: null });
    }
});

// ── GET /api/admin/data — view full store (debugging) ────────────────────────
app.get('/api/admin/data', (req, res) => res.json(store));

// ── GET /health ───────────────────────────────────────────────────────────────
app.get('/health', (req, res) => res.json({ ok: true, matches: Object.keys(store.matches).length }));

app.listen(PORT, () => console.log(`Magic Analysis on port ${PORT}`));
