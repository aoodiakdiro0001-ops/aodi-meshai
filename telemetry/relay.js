#!/usr/bin/env node
/**
 * Aodı-MeshAI — telemetry relay (Node, zero dependencies).
 * يستقبل /emit {task_id,level,message} ويحوله إلى إشعارات Telegram Bot API فعلياً.
 * متغيرات البيئة: TELEGRAM_TOKEN, TELEGRAM_CHAT, PORT (افتراضي 7242)
 * واللوحة تقرأ /last آخر 40 حدثاً (بدون أمان الحفظ للماضي بعيد).
 */
const http = require("http");
const https = require("https");
const PORT = process.env.PORT || 7242;
const TOKEN = process.env.TELEGRAM_TOKEN || "";
const CHAT = process.env.TELEGRAM_CHAT || "";
const buf = [];   // آخر 40 حدثاً

function sendTelegram(text) {
  if (!TOKEN || !CHAT) return Promise.resolve({skipped: true});
  return new Promise((resolve) => {
    const q = `/bot${TOKEN}/sendMessage?chat_id=${encodeURIComponent(CHAT)}&text=${encodeURIComponent(text)}`;
    const r = https.request({hostname: "api.telegram.org", path: q, method: "POST"},
      (res) => { res.resume(); resolve({status: res.statusCode}); });
    r.on("error", (e) => resolve({error: String(e)}));
    r.end();
  });
}

http.createServer((req, res) => {
  const p = req.url.split("?")[0];
  if (p === "/emit" && req.method === "POST") {
    let b = "";
    req.on("data", (c) => (b += c.slice ? c : ""));
    req.on("end", async () => {
      try {
        const ev = JSON.parse(b || "{}");
        const e = {ts: new Date().toISOString(),
          task_id: ev.task_id || "", level: ev.level || "info",
          message: (ev.message || "").slice(0, 280)};
        buf.unshift(e);
        if (buf.length > 40) buf.pop();
        const tg = await sendTelegram(`[${e.level.toUpperCase()}] MeshAI#${e.task_id}\n${e.message}`);
        res.writeHead(200, {"Content-Type": "application/json"});
        res.end(JSON.stringify({ok: true, telegram: tg.skipped ? "skipped" : tg.status ?? "sent"}));
      } catch (e) {
        res.writeHead(400, {"Content-Type": "application/json"});
        res.end(JSON.stringify({ok: false, error: String(e)}));
      }
    });
  } else if (p === "/last") {
    res.writeHead(200, {"Content-Type": "application/json"});
    res.end(JSON.stringify({events: buf}));
  } else if (p === "/health") {
    res.writeHead(200, {"Content-Type": "application/json"});
    res.end(JSON.stringify({service: "meshai.telemetry", version: "1.0.0",
      telegram_configured: !!(TOKEN && CHAT), buffered: buf.length}));
  } else {
    res.writeHead(404, {"Content-Type": "application/json"});
    res.end(JSON.stringify({error: "no route"}));
  }
}).listen(PORT, () => console.log(`meshai.telemetry listening :${PORT}  telegram=${TOKEN ? "on" : "off"}`));
