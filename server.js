'use strict';
const express = require('express');
const cors    = require('cors');
const https   = require('https');

const app = express();
app.use(cors());
app.use(express.json());

const PORT        = process.env.PORT               || 3000;
const OPENAI_KEY  = process.env.OPENAI_API_KEY      || '';
const TG_TOKEN    = process.env.TELEGRAM_BOT_TOKEN  || '';
const ADMIN_ID    = process.env.TELEGRAM_ADMIN_ID   || '';
const APF_KEY     = process.env.API_FOOTBALL_KEY    || '';
const STATPAL_KEY = process.env.STATPAL_API_KEY     || '98e5c7b5-5b16-412c-a270-c3196e4ef98f';

// ── In-memory store ─────────────────────────────────────────────────────────────
let store = { matches: {}, preds: {} };

// ── Conversation state per user ──────────────────────────────────────────────
const userState = {};

function matchKey(home, away) {
    return `${(home || '').trim().toLowerCase()}|${(away || '').trim().toLowerCase()}`;
}

function setState(chatId, step, data = {}) { userState[chatId] = { step, data }; }
function clearState(chatId)                { delete userState[chatId]; }
function getState(chatId)                  { return userState[chatId] || null; }

// ── Telegram API helpers ─────────────────────────────────────────────────────────
function tgPost(method, data) {
    if (!TG_TOKEN) return;
    const body = JSON.stringify(data);
    const req  = https.request({
        hostname: 'api.telegram.org',
        path:     `/bot${TG_TOKEN}/${method}`,
        method:   'POST',
        headers:  { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    });
    req.on('error', () => {});
    req.write(body);
    req.end();
}

const reply   = (chatId, text) =>
    tgPost('sendMessage', { chat_id: chatId, text, parse_mode: 'HTML' });

const replyKb = (chatId, text, keyboard) =>
    tgPost('sendMessage', { chat_id: chatId, text, parse_mode: 'HTML', reply_markup: { inline_keyboard: keyboard } });

const answerCb = (id) =>
    tgPost('answerCallbackQuery', { callback_query_id: id });

// ── Main menu keyboard ────────────────────────────────────────────────────────────────
const MAIN_KB = [
    [
        { text: '🔴  Live Matches',    callback_data: 'btn_live'     },
        { text: '✅  Finished',        callback_data: 'btn_finished' },
    ],
    [
        { text: '🔵  Upcoming',        callback_data: 'btn_upcoming' },
        { text: '👁  Preview',         callback_data: 'btn_preview'  },
    ],
    [
        { text: '🔄  Sync API: Today', callback_data: 'btn_sync'     },
        { text: '✏️  Edit / Delete',   callback_data: 'btn_edit'     },
    ],
];

function showMainMenu(chatId) {
    const count = Object.keys(store.matches).length;
    replyKb(chatId,
        `🎯 <b>Magic Analysis Bot</b>\n\n📦 ${count} match(es) stored.\n\nWhat would you like to do?`,
        MAIN_KB
    );
}

// ── HTTPS helpers for outbound API calls ───────────────────────────────────────────
function httpsGet(hostname, path, headers) {
    return new Promise((resolve, reject) => {
        const req = https.request({
            hostname, path, method: 'GET',
            headers: Object.assign({ 'User-Agent': 'MagicBot/1.0' }, headers || {}),
        }, res => {
            let raw = '';
            res.on('data', c => { raw += c; });
            res.on('end', () => {
                try { resolve(JSON.parse(raw)); }
                catch (e) { reject(new Error('httpsGet JSON parse error')); }
            });
        });
        req.on('error', reject);
        req.end();
    });
}

function httpsPostJson(hostname, path, body, headers) {
    const bodyStr = JSON.stringify(body);
    return new Promise((resolve, reject) => {
        const req = https.request({
            hostname, path, method: 'POST',
            headers: Object.assign({
                'Content-Type':   'application/json',
                'Content-Length': Buffer.byteLength(bodyStr),
            }, headers || {}),
        }, res => {
            let raw = '';
            res.on('data', c => { raw += c; });
            res.on('end', () => {
                try { resolve(JSON.parse(raw)); }
                catch (e) { reject(new Error('httpsPostJson JSON parse error')); }
            });
        });
        req.on('error', reject);
        req.write(bodyStr);
        req.end();
    });
}

// ── Sync API: Today ──────────────────────────────────────────────────────────────────
async function syncTodayMatches(chatId) {
    const today = new Date().toISOString().split('T')[0];
    let converted = [];

    reply(chatId, '⏳ Fetching today\'s matches from API...');

    // 1. API-Football — try first if key is set
    if (APF_KEY) {
        try {
            const data = await httpsGet(
                'v3.football.api-sports.io',
                `/fixtures?date=${today}`,
                { 'x-apisports-key': APF_KEY }
            );
            const fixtures = data.response || [];
            if (fixtures.length > 0) {
                converted = fixtures.map(f => ({
                    id:         String(f.fixture.id),
                    date:       today,
                    time:       f.fixture.date ? f.fixture.date.split('T')[1].substring(0, 5) : '',
                    leagueName: f.league.name  || 'Unknown',
                    country:    f.league.country || '',
                    home:       { name: f.teams.home.name, score: null },
                    away:       { name: f.teams.away.name, score: null },
                    status:     'NS',
                    manual_prediction: null,
                }));
                console.log(`Sync: API-Football returned ${converted.length} fixtures`);
            }
        } catch (e) { console.error('APF sync failed:', e.message); }
    }

    // 2. StatPal fallback
    if (!converted.length) {
        try {
            const data = await httpsGet(
                'statpal.io',
                `/api/v1/soccer/livescores?access_key=${STATPAL_KEY}`
            );
            const leagues = data && data.livescore && data.livescore.league;
            if (leagues) {
                const lgArr = Array.isArray(leagues) ? leagues : [leagues];
                lgArr.forEach(lg => {
                    const items = Array.isArray(lg.match) ? lg.match : (lg.match ? [lg.match] : []);
                    items.forEach(m => {
                        converted.push({
                            id:         String(m.id || matchKey(m.home && m.home.name, m.away && m.away.name)),
                            date:       today,
                            time:       m.match_start || m.time || '',
                            leagueName: lg.name || '',
                            country:    typeof lg.country === 'string' ? lg.country : ((lg.country && lg.country.name) || ''),
                            home:       { name: (m.home && m.home.name) || '', score: null },
                            away:       { name: (m.away && m.away.name) || '', score: null },
                            status:     'NS',
                            manual_prediction: null,
                        });
                    });
                });
                console.log(`Sync: StatPal returned ${converted.length} matches`);
            }
        } catch (e) { console.error('StatPal sync failed:', e.message); }
    }

    if (!converted.length) {
        reply(chatId, '⚠️ No matches found for today from any API source.');
        return;
    }

    reply(chatId, `📥 Found <b>${converted.length}</b> match(es).${OPENAI_KEY ? '\n🧠 Generating AI predictions...' : ''}`);

    // ── OpenAI auto-prediction (with predicted scores) ──────────────────────────────
    if (OPENAI_KEY && converted.length > 0) {
        try {
            const matchList = converted.map((m, i) =>
                `${i + 1}. ${m.home.name} vs ${m.away.name} (${m.leagueName}, ${m.date} ${m.time})`
            ).join('\n');

            const aiResult = await httpsPostJson(
                'api.openai.com',
                '/v1/chat/completions',
                {
                    model: 'gpt-4o-mini',
                    messages: [
                        {
                            role: 'system',
                            content: [
                                'You are a professional football betting analyst. For each upcoming match, provide:',
                                '- A 1X2 prediction: "1", "X", or "2"',
                                '- A predicted correct score (e.g., "2-1")',
                                '- Percentage probabilities for Home, Draw, and Away that add up to 100.',
                                '',
                                'Return a JSON object with a key "predictions" that is an array. Each element must have:',
                                '- "match": the original match description (exactly as provided)',
                                '- "prediction": "1", "X", or "2"',
                                '- "pScore": the predicted correct score (e.g., "2-1")',
                                '- "probabilityHome", "probabilityDraw", "probabilityAway": numbers 0-100, sum = 100',
                            ].join('\n'),
                        },
                        {
                            role: 'user',
                            content: `Here are the matches:\n${matchList}\n\nPlease return your predictions in JSON.`,
                        },
                    ],
                    response_format: { type: 'json_object' },
                    temperature: 0.7,
                    max_tokens: 1500,
                },
                { 'Authorization': `Bearer ${OPENAI_KEY}` }
            );

            const predictions = JSON.parse(aiResult.choices[0].message.content).predictions || [];
            predictions.forEach((pred, idx) => {
                if (idx < converted.length) {
                    const tip    = pred.prediction || '';
                    const pScore = pred.pScore     || '';
                    // Format exactly as screenshot upload: "prediction (pScore)", e.g. "1 (2-1)"
                    converted[idx].manual_prediction = `${tip} (${pScore})`.trim();
                    const h = Math.round(Number(pred.probabilityHome) || 33);
                    const d = Math.round(Number(pred.probabilityDraw) || 33);
                    const a = 100 - h - d;
                    const k = matchKey(converted[idx].home.name, converted[idx].away.name);
                    store.preds[k] = {
                        h, d, a,
                        score:      pScore || null,
                        advice:     tip === '1' ? 'Home Win' : tip === '2' ? 'Away Win' : 'Draw',
                        confidence: Math.round(Math.max(h, d, a) / 10) / 10,
                        sources:    ['openai'],
                        aiUsed:     true,
                    };
                }
            });
        } catch (e) {
            console.error('OpenAI sync prediction error:', e.message);
            reply(chatId, '⚠️ AI prediction failed, saving matches without predictions.');
        }
    }

    // Store all matches
    for (const m of converted) {
        const k = matchKey(m.home.name, m.away.name);
        store.matches[k] = {
            id:                m.id,
            home:              { name: m.home.name, score: null },
            away:              { name: m.away.name, score: null },
            leagueName:        m.leagueName,
            country:           m.country,
            time:              m.time,
            status:            'NS',
            manual_prediction: m.manual_prediction || null,
        };
    }

    const hasPreds = converted.filter(m => m.manual_prediction).length;
    reply(chatId, [
        `✅ Synced <b>${converted.length}</b> match(es) for today.`,
        hasPreds
            ? `🧠 <b>${hasPreds}</b> predictions generated (format: \"1 (2-1)\").`
            : 'No predictions generated (set OPENAI_API_KEY to enable).',
        '',
        'Use 👁 Preview to review.',
    ].join('\n'));
    showMainMenu(chatId);
}

// ── Preview ───────────────────────────────────────────────────────────────────────────
function showPreview(chatId) {
    const keys = Object.keys(store.matches);
    if (!keys.length) {
        replyKb(chatId, '📋 No matches stored yet.', [[{ text: '⬅️ Back', callback_data: 'back_main' }]]);
        return;
    }
    const lines = keys.map((k, i) => {
        const m    = store.matches[k];
        const p    = store.preds[k];
        const sc   = m.home.score != null && m.away.score != null ? ` <b>${m.home.score}–${m.away.score}</b>` : '';
        const icon = m.status === 'FT' ? '✅' : m.status === 'NS' ? '🔵' : '🔴';
        const time = m.time ? ` @ ${m.time}` : '';
        const pred = p
            ? `   ↳ ${p.h}% / ${p.d}% / ${p.a}%${p.score ? ' · ' + p.score : ''}${p.advice ? '\n   ↳ ' + p.advice : ''}`
            : '   ↳ No prediction';
        const tip  = m.manual_prediction ? `\n   ↳ Tip: ${m.manual_prediction}` : '';
        return `${i + 1}. ${icon} <b>${m.home.name} vs ${m.away.name}</b>${sc}\n   ${m.leagueName}${m.country ? ' · ' + m.country : ''}${time}\n${pred}${tip}`;
    });
    replyKb(chatId,
        `<b>👁 Preview — ${keys.length} match(es)</b>\n\n${lines.join('\n\n')}`,
        [[{ text: '⬅️ Back to Menu', callback_data: 'back_main' }]]
    );
}

// ── Edit list ───────────────────────────────────────────────────────────────────────
function showEditList(chatId) {
    const keys = Object.keys(store.matches);
    if (!keys.length) {
        replyKb(chatId, '📋 No matches to edit.', [[{ text: '⬅️ Back', callback_data: 'back_main' }]]);
        return;
    }
    const rows = keys.map((k, i) => {
        const m = store.matches[k];
        const icon = m.status === 'FT' ? '✅' : m.status === 'NS' ? '🔵' : '🔴';
        return [
            { text: `${icon} ${i + 1}. ${m.home.name} vs ${m.away.name}`, callback_data: `edit_sel_${k}` },
            { text: '🗑️', callback_data: `del_${k}` },
        ];
    });
    rows.push([{ text: '⬅️ Back to Menu', callback_data: 'back_main' }]);
    replyKb(chatId, '<b>✏️ Edit / Delete Matches</b>\n\nTap a match to edit, or 🗑️ to delete:', rows);
}

// ── Process state input (text typed after pressing a button) ────────────────────────
function handleStateInput(chatId, text, state) {
    const args = text.split('|').map(s => s.trim());

    if (state.step === 'live_input') {
        const [home, away, hg, ag, min] = args;
        if (!home || !away) { reply(chatId, '❌ Format: Home | Away | HomeGoals | AwayGoals | Minute'); return; }
        const k = matchKey(home, away);
        if (!store.matches[k]) { reply(chatId, `❌ Match not found: <b>${home} vs ${away}</b>\nAdd it first via 🔵 Upcoming.`); return; }
        store.matches[k].home.score = parseInt(hg) || 0;
        store.matches[k].away.score = parseInt(ag) || 0;
        store.matches[k].status     = min ? String(parseInt(min) || 'LIVE') : 'LIVE';
        clearState(chatId);
        reply(chatId, `🔴 Live updated: <b>${home} ${hg}–${ag} ${away}</b>${min ? ' (' + min + '\')' : ''}`);
        showMainMenu(chatId);
        return;
    }

    if (state.step === 'finished_input') {
        const [home, away, hg, ag] = args;
        if (!home || !away) { reply(chatId, '❌ Format: Home | Away | HomeGoals | AwayGoals'); return; }
        const k = matchKey(home, away);
        if (!store.matches[k]) { reply(chatId, `❌ Match not found: <b>${home} vs ${away}</b>`); return; }
        store.matches[k].home.score = parseInt(hg) || 0;
        store.matches[k].away.score = parseInt(ag) || 0;
        store.matches[k].status     = 'FT';
        clearState(chatId);
        reply(chatId, `✅ Full Time: <b>${home} ${hg}–${ag} ${away}</b>`);
        showMainMenu(chatId);
        return;
    }

    if (state.step === 'upcoming_input') {
        const [home, away, league, country, time, hp, dp, ap, score, advice, protip] = args;
        if (!home || !away) { reply(chatId, '❌ Minimum required: Home | Away'); return; }
        const k = matchKey(home, away);
        store.matches[k] = {
            id:                k,
            home:              { name: home, score: null },
            away:              { name: away, score: null },
            leagueName:        league  || 'Unknown League',
            country:           country || '',
            time:              time    || '',
            status:            'NS',
            manual_prediction: protip  || null,
        };
        const h = parseInt(hp) || 0, d = parseInt(dp) || 0, a = parseInt(ap) || 0;
        if (h || d || a) {
            const total = h + d + a || 100;
            store.preds[k] = {
                h:          Math.round(h * 100 / total),
                d:          Math.round(d * 100 / total),
                a:          Math.round(a * 100 / total),
                score:      score  || null,
                advice:     advice || null,
                confidence: Math.round(Math.max(h, d, a) * 10 / total) / 10,
                sources:    ['manual'],
                aiUsed:     false,
            };
        }
        clearState(chatId);
        const tot = h + d + a || 100;
        reply(chatId, [
            `✅ Added: <b>${home} vs ${away}</b>`,
            `${league || 'Unknown League'}${country ? ' · ' + country : ''}${time ? ' @ ' + time : ''}`,
            (h || d || a) ? `Prediction: ${Math.round(h*100/tot)}% / ${Math.round(d*100/tot)}% / ${Math.round(a*100/tot)}%${score ? ' · ' + score : ''}` : 'No prediction added.',
            protip ? `⭐ Pro Tip: ${protip}` : '',
        ].filter(Boolean).join('\n'));
        showMainMenu(chatId);
        return;
    }

    if (state.step === 'edit_input') {
        const { key } = state.data;
        const existing = store.matches[key];
        if (!existing) { reply(chatId, '❌ Match no longer exists.'); clearState(chatId); showMainMenu(chatId); return; }
        const [home, away, league, country, time, hp, dp, ap, score, advice, protip] = args;
        store.matches[key] = {
            ...existing,
            home:              { ...existing.home, name: home || existing.home.name },
            away:              { ...existing.away, name: away || existing.away.name },
            leagueName:        league  || existing.leagueName,
            country:           country || existing.country,
            time:              time    || existing.time,
            manual_prediction: protip  !== undefined ? (protip || null) : existing.manual_prediction,
        };
        const h = parseInt(hp) || 0, d = parseInt(dp) || 0, a = parseInt(ap) || 0;
        if (h || d || a) {
            const total = h + d + a || 100;
            store.preds[key] = {
                h:          Math.round(h * 100 / total),
                d:          Math.round(d * 100 / total),
                a:          Math.round(a * 100 / total),
                score:      score  || null,
                advice:     advice || null,
                confidence: Math.round(Math.max(h, d, a) * 10 / total) / 10,
                sources:    ['manual'],
                aiUsed:     false,
            };
        }
        clearState(chatId);
        reply(chatId, `✅ Updated: <b>${store.matches[key].home.name} vs ${store.matches[key].away.name}</b>`);
        showMainMenu(chatId);
        return;
    }
}

// ── Handle button presses ─────────────────────────────────────────────────────────────────
function handleCallbackQuery(cq) {
    const chatId = cq.message && cq.message.chat && cq.message.chat.id;
    const data   = cq.data || '';
    if (!chatId) return;
    answerCb(cq.id);

    if (ADMIN_ID && String(cq.from && cq.from.id) !== String(ADMIN_ID)) return;

    if (data === 'btn_live') {
        setState(chatId, 'live_input');
        replyKb(chatId, [
            '🔴 <b>Update Live Score</b>',
            '',
            'Type in this format:',
            '<code>Home | Away | HomeGoals | AwayGoals | Minute</code>',
            '',
            'Example:',
            '<code>Arsenal | Chelsea | 1 | 0 | 67</code>',
            '',
            'The match must already be added via 🔵 Upcoming first.',
        ].join('\n'), [[{ text: '❌ Cancel', callback_data: 'back_main' }]]);
        return;
    }

    if (data === 'btn_finished') {
        setState(chatId, 'finished_input');
        replyKb(chatId, [
            '✅ <b>Mark Match as Finished</b>',
            '',
            'Type in this format:',
            '<code>Home | Away | HomeGoals | AwayGoals</code>',
            '',
            'Example:',
            '<code>Arsenal | Chelsea | 2 | 1</code>',
        ].join('\n'), [[{ text: '❌ Cancel', callback_data: 'back_main' }]]);
        return;
    }

    if (data === 'btn_upcoming') {
        setState(chatId, 'upcoming_input');
        replyKb(chatId, [
            '🔵 <b>Add Upcoming Match + Prediction</b>',
            '',
            'Type in this format:',
            '<code>Home | Away | League | Country | Time | H% | D% | A% | Score | Advice | Pro Tip</code>',
            '',
            'Example:',
            '<code>Arsenal | Chelsea | Premier League | England | 20:00 | 60 | 25 | 15 | 2-1 | Arsenal look strong | Home Win @ 1.80</code>',
            '',
            'Only Home and Away are required. Pro Tip (last field) shows as a gold "Verified Pro Tip" on the website.',
        ].join('\n'), [[{ text: '❌ Cancel', callback_data: 'back_main' }]]);
        return;
    }

    if (data === 'btn_preview') {
        clearState(chatId);
        showPreview(chatId);
        return;
    }

    if (data === 'btn_sync') {
        clearState(chatId);
        syncTodayMatches(chatId).catch(e => {
            console.error('Sync error:', e.message);
            reply(chatId, `❌ Sync failed: ${e.message}`);
        });
        return;
    }

    if (data === 'btn_edit') {
        clearState(chatId);
        showEditList(chatId);
        return;
    }

    if (data === 'back_main') {
        clearState(chatId);
        showMainMenu(chatId);
        return;
    }

    // Edit a specific match
    if (data.startsWith('edit_sel_')) {
        const key = data.slice('edit_sel_'.length);
        const m   = store.matches[key];
        const p   = store.preds[key];
        if (!m) { reply(chatId, '❌ Match not found.'); return; }
        setState(chatId, 'edit_input', { key });
        replyKb(chatId, [
            `✏️ <b>Editing: ${m.home.name} vs ${m.away.name}</b>`,
            `League: ${m.leagueName}${m.country ? ' · ' + m.country : ''}${m.time ? ' @ ' + m.time : ''}`,
            p ? `Prediction: ${p.h}% / ${p.d}% / ${p.a}%${p.score ? ' · ' + p.score : ''}${p.advice ? '\nAdvice: ' + p.advice : ''}` : 'No prediction yet.',
            '',
            'Send updated data in the same format:',
            '<code>Home | Away | League | Country | Time | H% | D% | A% | Score | Advice</code>',
            '',
            '(You can skip fields you don\'t want to change by leaving them blank)',
        ].join('\n'), [[{ text: '❌ Cancel', callback_data: 'back_main' }]]);
        return;
    }

    // Delete a specific match
    if (data.startsWith('del_')) {
        const key = data.slice('del_'.length);
        const m   = store.matches[key];
        if (m) {
            delete store.matches[key];
            delete store.preds[key];
            reply(chatId, `🗑️ Deleted: <b>${m.home.name} vs ${m.away.name}</b>`);
        }
        showEditList(chatId);
        return;
    }
}

// ── Handle text messages ────────────────────────────────────────────────────────────────
function handleMessage(msg) {
    const chatId = msg.chat && msg.chat.id;
    const text   = (msg.text || '').trim();
    if (!chatId) return;

    if (ADMIN_ID && String(msg.from && msg.from.id) !== String(ADMIN_ID)) {
        reply(chatId, '⛔ Unauthorized');
        return;
    }

    if (text === '/cancel' || text === '/start') {
        clearState(chatId);
        showMainMenu(chatId);
        return;
    }

    const state = getState(chatId);
    if (state && !text.startsWith('/')) {
        handleStateInput(chatId, text, state);
        return;
    }

    if (!text.startsWith('/')) return;

    const spaceIdx = text.indexOf(' ');
    const cmd      = (spaceIdx === -1 ? text : text.slice(0, spaceIdx)).toLowerCase();
    const rawArgs  = spaceIdx === -1 ? '' : text.slice(spaceIdx + 1);
    const args     = rawArgs.split('|').map(s => s.trim());

    switch (cmd) {

        case '/help': {
            replyKb(chatId, [
                '<b>Magic Analysis Bot</b>',
                '',
                'Use the buttons below, or type commands directly:',
                '',
                '/tip Home | Away | League | Country | Time | H% | D% | A% | Score | Advice',
                '/live Home | Away | HomeGoals | AwayGoals | Minute',
                '/ft Home | Away | HomeGoals | AwayGoals',
                '/pred Home | Away | H% | D% | A% | Score | Advice',
                '/del Home | Away',
                '/clear — clear all matches',
                '/list — list all matches',
            ].join('\n'), MAIN_KB);
            break;
        }

        case '/tip': {
            const [home, away, league, country, time, hp, dp, ap, score, advice, protip] = args;
            if (!home || !away) { reply(chatId, '❌ Minimum: /tip Home | Away'); return; }
            const k = matchKey(home, away);
            store.matches[k] = {
                id:                k,
                home:              { name: home, score: null },
                away:              { name: away, score: null },
                leagueName:        league  || 'Unknown League',
                country:           country || '',
                time:              time    || '',
                status:            'NS',
                manual_prediction: protip  || null,
            };
            const h = parseInt(hp)||0, d = parseInt(dp)||0, a = parseInt(ap)||0;
            if (h || d || a) {
                const total = h + d + a || 100;
                store.preds[k] = {
                    h: Math.round(h*100/total), d: Math.round(d*100/total), a: Math.round(a*100/total),
                    score: score || null, advice: advice || null,
                    confidence: Math.round(Math.max(h,d,a)*10/total)/10, sources: ['manual'], aiUsed: false,
                };
            }
            const tot = h+d+a||100;
            reply(chatId, [
                `✅ <b>${home} vs ${away}</b>`,
                `${league||''}${country?' · '+country:''}${time?' @ '+time:''}`,
                (h||d||a)?`Pred: ${Math.round(h*100/tot)}% / ${Math.round(d*100/tot)}% / ${Math.round(a*100/tot)}%`:'No prediction',
                protip ? `⭐ Pro Tip: ${protip}` : '',
            ].filter(Boolean).join('\n'));
            break;
        }

        case '/protip': {
            const [home, away, ...tipParts] = args;
            if (!home || !away || !tipParts.length) { reply(chatId, '❌ Usage: /protip Home | Away | Pro tip text\nExample: /protip Arsenal | Chelsea | Home Win @ 1.80'); return; }
            const k = matchKey(home, away);
            if (!store.matches[k]) { reply(chatId, `❌ Not found: ${home} vs ${away}\nAdd the match first with /tip`); return; }
            store.matches[k].manual_prediction = tipParts.join('|').trim();
            reply(chatId, `⭐ Pro Tip set: <b>${home} vs ${away}</b>\n${store.matches[k].manual_prediction}`);
            break;
        }

        case '/live': {
            const [home, away, hg, ag, min] = args;
            if (!home || !away) { reply(chatId, '❌ Usage: /live Home | Away | HomeGoals | AwayGoals | Minute'); return; }
            const k = matchKey(home, away);
            if (!store.matches[k]) { reply(chatId, `❌ Not found: ${home} vs ${away}`); return; }
            store.matches[k].home.score = parseInt(hg)||0;
            store.matches[k].away.score = parseInt(ag)||0;
            store.matches[k].status     = min ? String(parseInt(min)||'LIVE') : 'LIVE';
            reply(chatId, `🔴 Live: <b>${home} ${hg}–${ag} ${away}</b>${min?' ('+min+'\')':''}`);
            break;
        }

        case '/ft': {
            const [home, away, hg, ag] = args;
            if (!home || !away) { reply(chatId, '❌ Usage: /ft Home | Away | HomeGoals | AwayGoals'); return; }
            const k = matchKey(home, away);
            if (!store.matches[k]) { reply(chatId, `❌ Not found: ${home} vs ${away}`); return; }
            store.matches[k].home.score = parseInt(hg)||0;
            store.matches[k].away.score = parseInt(ag)||0;
            store.matches[k].status     = 'FT';
            reply(chatId, `✅ FT: <b>${home} ${hg}–${ag} ${away}</b>`);
            break;
        }

        case '/pred': {
            const [home, away, hp, dp, ap, score, ...advParts] = args;
            if (!home || !away) { reply(chatId, '❌ Usage: /pred Home | Away | H% | D% | A% | Score | Advice'); return; }
            const k = matchKey(home, away);
            if (!store.matches[k]) { reply(chatId, `⚠️ Not found: ${home} vs ${away}. Add it first.`); return; }
            const h = parseInt(hp)||0, d = parseInt(dp)||0, a = parseInt(ap)||0;
            const total = h+d+a||100;
            store.preds[k] = {
                h: Math.round(h*100/total), d: Math.round(d*100/total), a: Math.round(a*100/total),
                score: score||null, advice: advParts.join('|').trim()||null,
                confidence: Math.round(Math.max(h,d,a)*10/total)/10, sources: ['manual'], aiUsed: false,
            };
            reply(chatId, `✅ Prediction: <b>${home} vs ${away}</b>\n${Math.round(h*100/total)}% / ${Math.round(d*100/total)}% / ${Math.round(a*100/total)}%${score?' · '+score:''}`);
            break;
        }

        case '/del': {
            const [home, away] = args;
            if (!home || !away) { reply(chatId, '❌ Usage: /del Home | Away'); return; }
            const k = matchKey(home, away);
            const existed = !!store.matches[k];
            delete store.matches[k]; delete store.preds[k];
            reply(chatId, existed ? `🗑️ Removed: <b>${home} vs ${away}</b>` : `⚠️ Not found: ${home} vs ${away}`);
            break;
        }

        case '/clear': {
            const count = Object.keys(store.matches).length;
            store = { matches: {}, preds: {} };
            reply(chatId, `🗑️ Cleared ${count} match(es).`);
            showMainMenu(chatId);
            break;
        }

        case '/list': {
            const keys = Object.keys(store.matches);
            if (!keys.length) { reply(chatId, '📋 No matches stored.'); return; }
            const lines = keys.map((k, i) => {
                const m = store.matches[k], p = store.preds[k];
                const sc = m.home.score != null && m.away.score != null ? ` ${m.home.score}–${m.away.score}` : '';
                const icon = m.status==='FT'?'✅':m.status==='NS'?'🔵':'🔴';
                return `${i+1}. ${icon} <b>${m.home.name} vs ${m.away.name}</b>${sc}${p?` [${p.h}/${p.d}/${p.a}]`:' [no pred]'}\n   ${m.leagueName}${m.time?' @ '+m.time:''}`;
            });
            reply(chatId, `<b>Matches (${keys.length}):</b>\n\n${lines.join('\n\n')}`);
            break;
        }

        default:
            replyKb(chatId, 'Use the buttons or type /help for commands.', MAIN_KB);
    }
}

// ── POST /telegram — webhook ──────────────────────────────────────────────────────────────
app.post('/telegram', (req, res) => {
    res.sendStatus(200);
    const { message, callback_query } = req.body;
    if (message)        handleMessage(message);
    if (callback_query) handleCallbackQuery(callback_query);
});

// ── GET /api/scores ──────────────────────────────────────────────────────────────────────
app.get('/api/scores', (req, res) => {
    const byLeague = {};
    for (const m of Object.values(store.matches)) {
        const lg = m.leagueName || 'Other';
        if (!byLeague[lg]) byLeague[lg] = { name: lg, country: m.country || '', match: [] };
        byLeague[lg].match.push({
            id: m.id, home: { name: m.home.name, score: m.home.score },
            away: { name: m.away.name, score: m.away.score },
            status: m.status, time: m.time, leagueName: m.leagueName, country: m.country,
            manual_prediction: m.manual_prediction || null,
        });
    }
    res.json({ livescore: { league: Object.values(byLeague) } });
});

// ── GET /api/get-predictions ──────────────────────────────────────────────────────────────
app.get('/api/get-predictions', (req, res) => {
    const k = matchKey(req.query.home || '', req.query.away || '');
    const p = store.preds[k];
    const m = store.matches[k];
    if (!p) {
        return res.json({
            response: [{ predictions: { percent: { home: null, draw: null, away: null }, goals: null, advice: null } }],
            meta: { confidence: 0, sources: [], aiUsed: false },
        });
    }
    const goalMatch = (p.score || '').match(/(\d+)\D+(\d+)/);
    const winner    = p.h >= p.d && p.h >= p.a
        ? `${(m && m.home.name) || 'Home'} to win`
        : p.a > p.h && p.a >= p.d
            ? `${(m && m.away.name) || 'Away'} to win`
            : 'Draw likely';
    res.json({
        response: [{ predictions: {
            percent: { home: `${p.h}%`, draw: `${p.d}%`, away: `${p.a}%` },
            goals:   goalMatch ? { home: goalMatch[1], away: goalMatch[2] } : null,
            advice:  p.advice || winner,
        }}],
        meta: { confidence: p.confidence || 0.5, sources: p.sources || ['manual'], aiUsed: p.aiUsed || false },
    });
});

// ── GET /api/upcoming ──────────────────────────────────────────────────────────────────
app.get('/api/upcoming', (req, res) => res.json({ matches: [] }));

// ── GET /api/match-analysis (OpenAI — optional) ──────────────────────────────────────
app.get('/api/match-analysis', async (req, res) => {
    if (!OPENAI_KEY) return res.json({ analysis: null });
    const { home, away, league, status, score } = req.query;
    try {
        const prompt = `Football analyst. 2 sentences max. ${home} vs ${away} (${league}). Status: ${status}. Score: ${score}. Tactical insight + likely outcome.`;
        const body   = JSON.stringify({ model: 'gpt-3.5-turbo', messages: [{ role: 'user', content: prompt }], max_tokens: 100, temperature: 0.7 });
        const apiRes = await new Promise((resolve, reject) => {
            const r = https.request({
                hostname: 'api.openai.com', path: '/v1/chat/completions', method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${OPENAI_KEY}`, 'Content-Length': Buffer.byteLength(body) },
            }, resolve);
            r.on('error', reject); r.write(body); r.end();
        });
        let raw = ''; for await (const c of apiRes) raw += c;
        res.json({ analysis: JSON.parse(raw).choices && JSON.parse(raw).choices[0] && JSON.parse(raw).choices[0].message && JSON.parse(raw).choices[0].message.content.trim() || null });
    } catch (e) { res.json({ analysis: null }); }
});

// ── GET /api/team-logo ─────────────────────────────────────────────────────────────────────
app.get('/api/team-logo', async (req, res) => {
    const { name } = req.query;
    if (!name) return res.json({ logo: null });
    try {
        const apiRes = await new Promise((resolve, reject) => {
            const r = https.request({
                hostname: 'www.thesportsdb.com',
                path: `/api/v1/json/3/searchteams.php?t=${encodeURIComponent(name)}`,
                method: 'GET', headers: { 'User-Agent': 'Mozilla/5.0' },
            }, resolve);
            r.on('error', reject); r.end();
        });
        let raw = ''; for await (const c of apiRes) raw += c;
        res.json({ logo: JSON.parse(raw).teams && JSON.parse(raw).teams[0] && JSON.parse(raw).teams[0].strBadge || null });
    } catch (e) { res.json({ logo: null }); }
});

// ── GET /api/admin/data ────────────────────────────────────────────────────────────────────
app.get('/api/admin/data', (req, res) => res.json(store));

// ── GET /health ────────────────────────────────────────────────────────────────────────────
app.get('/health', (req, res) => res.json({ ok: true, matches: Object.keys(store.matches).length }));

app.listen(PORT, () => console.log(`Magic Analysis on port ${PORT}`));
