/* SPEC_ui-dynamique UI-8 — the ONE front script, vanilla JS, no build, no CDN.
 *
 * Three pages share this file (document.body.dataset.page selects the
 * renderer): index (overview by level), strategy (drill-down), services.
 * All data comes from the read-only JSON API via polling fetch — 5 s for
 * the strategy views, 10 s for /services.  When the API stops answering,
 * the #conn indicator turns red (UI-8); the last rendered data stays on
 * screen (better a dated truth than a blank page).
 */
"use strict";

/* ── tiny helpers ─────────────────────────────────────────────────────── */
function esc(v) {
  return String(v == null ? "" : v)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmtNum(v, digits) {
  if (v == null || isNaN(v)) return "—";
  return Number(v).toLocaleString("fr-CH",
    { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function signed(v, digits, unit) {
  if (v == null || isNaN(v)) return "—";
  const cls = v >= 0 ? "pos" : "neg";
  const txt = (v >= 0 ? "+" : "") + fmtNum(v, digits) + (unit ? " " + unit : "");
  return '<span class="' + cls + '">' + esc(txt) + "</span>";
}

function fmtAge(sec) {
  if (sec == null) return "jamais";
  if (sec < 90) return "il y a " + Math.round(sec) + " s";
  if (sec < 5400) return "il y a " + Math.round(sec / 60) + " min";
  if (sec < 172800) return "il y a " + (sec / 3600).toFixed(1) + " h";
  return "il y a " + Math.round(sec / 86400) + " j";
}

function fmtBytes(n) {
  if (n == null) return "—";
  if (n < 1024) return n + " o";
  if (n < 1048576) return (n / 1024).toFixed(1) + " Ko";
  if (n < 1073741824) return (n / 1048576).toFixed(1) + " Mo";
  return (n / 1073741824).toFixed(2) + " Go";
}

/* SVG polyline curve (D-UI-3) — points: [[iso_utc, value], …]. */
function curveSvg(points, w, h, opts) {
  opts = opts || {};
  if (!points || points.length < 2) {
    return '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + " " + h +
      '"><text x="4" y="' + (h / 2 + 4) + '" fill="rgba(216,226,236,.35)" ' +
      'font-size="10" font-family="monospace">pas de courbe</text></svg>';
  }
  const vals = points.map(p => p[1]);
  const min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
  const span = (max - min) || 1;
  const pad = 3;
  const coords = points.map((p, i) => {
    const x = pad + i * (w - 2 * pad) / (points.length - 1);
    const y = h - pad - (p[1] - min) * (h - 2 * pad) / span;
    return x.toFixed(1) + "," + y.toFixed(1);
  });
  const up = vals[vals.length - 1] >= vals[0];
  const color = up ? "#7fd18c" : "#ff6b6b";
  let axis = "";
  if (opts.labels) {
    axis = '<text x="' + pad + '" y="10" fill="rgba(216,226,236,.45)" font-size="9" ' +
      'font-family="monospace">' + esc(fmtNum(max, 2)) + "</text>" +
      '<text x="' + pad + '" y="' + (h - 2) + '" fill="rgba(216,226,236,.45)" ' +
      'font-size="9" font-family="monospace">' + esc(fmtNum(min, 2)) + "</text>";
  }
  return '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + " " + h + '">' +
    axis + '<polyline points="' + coords.join(" ") + '" fill="none" stroke="' +
    color + '" stroke-width="1.4"/></svg>';
}

/* ── connectivity + banner (UI-6, UI-8) ───────────────────────────────── */
function setConn(ok) {
  const el = document.getElementById("conn");
  if (!el) return;
  el.className = ok ? "ok" : "down";
  el.textContent = ok ? "live" : "API INJOIGNABLE";
}

function setStamp(data) {
  const el = document.getElementById("stamp");
  if (el) el.textContent = "données réelles · " + data.generated +
    " · v" + data.version;
}

async function fetchJSON(url) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 4000);
  try {
    const r = await fetch(url, { signal: ctl.signal });
    const body = await r.json();
    setConn(true);
    return { status: r.status, body: body };
  } catch (e) {
    setConn(false);
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function poll(fn, ms) { fn(); setInterval(fn, ms); }

/* ── overview page (UI-2, UI-3) ───────────────────────────────────────── */
function instanceLine(inst) {
  let body;
  if (inst.state === "never") {
    body = '<span class="never">jamais passée — en attente du premier tick</span>';
  } else if (inst.state === "unreadable") {
    body = '<span class="broken">status.json illisible</span>';
  } else {
    const pos = inst.open_position
      ? ' <span class="badge open-pos">position ' + esc(inst.open_position.side || "?") + "</span>" : "";
    const err = inst.error
      ? ' <span class="broken">' + esc(inst.error) + "</span>" : "";
    const last = inst.alive
      ? '<span class="badge alive">vivante</span>'
      : '<span class="stale">dernier passage ' + esc(fmtAge(inst.age_sec)) + "</span>";
    body =
      '<span class="num">' + esc(String(inst.n_closed_total)) + " clos</span>" +
      '<span class="num">' + signed(inst.cum_r, 2, "R") + "</span>" +
      '<span class="num">' + signed(inst.pnl_chf, 2, "CHF") + "</span>" +
      pos + err + last +
      curveSvg(inst.equity, 110, 26);
  }
  return '<div class="instance"><span class="iid">' + esc(inst.instance) +
    "</span>" + body + "</div>";
}

function strategyCard(card, level) {
  const badgeCls = card.declared === "LIVE" ? "live"
    : card.declared === "PAPER" ? "paper" : "";
  let body;
  if (card.manifest_error) {
    body = '<div class="manifest-error">' + esc(card.manifest_error) + "</div>";
  } else if (!card.instances.length) {
    body = '<div class="instance"><span class="never">aucune instance déclarée</span></div>';
  } else {
    body = card.instances.map(instanceLine).join("");
  }
  return '<div class="card ' + (level === "prod" ? "prod" : "") + '">' +
    '<h3><a href="/strategy/' + esc(card.short) + '">' + esc(card.short) +
    " — " + esc(card.name) + '</a> <span class="badge ' + badgeCls + '">' +
    esc(card.declared) + "</span></h3>" +
    '<div class="meta">' + esc(card.id) + " · magic " + esc(card.magic) + "</div>" +
    body + "</div>";
}

function renderLevel(elId, ids, byId, emptyHtml, level) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (!ids.length) { el.innerHTML = emptyHtml || ""; return; }
  el.innerHTML = '<div class="cards">' +
    ids.map(id => strategyCard(byId[id], level)).join("") + "</div>";
}

async function refreshIndex() {
  const res = await fetchJSON("/api/state");
  if (!res) return;
  const data = res.body;
  setStamp(data);
  const byId = {};
  data.strategies.forEach(c => { byId[c.id] = c; });
  const n = data.niveaux;

  const div = document.getElementById("divergences");
  if (n.divergences.length) {
    div.style.display = "";
    div.innerHTML = "<b>DIVERGENCE déclaré / réel</b><br>" +
      n.divergences.map(esc).join("<br>");
  } else {
    div.style.display = "none";
  }

  renderLevel("prod", n.prod, byId,
    '<div class="empty-prod">Aucune stratégie armée en argent réel. ' +
    "L'armement est un geste d'Adrian (R10), jamais automatique.</div>", "prod");
  renderLevel("paper", n.paper, byId,
    '<div class="subtitle">aucune stratégie en validation paper</div>', "paper");
  renderLevel("dev", n.dev, byId,
    '<div class="subtitle">aucune stratégie en développement</div>', "dev");

  const retired = document.getElementById("retired-content");
  const retiredCount = document.getElementById("retired-count");
  if (retiredCount) retiredCount.textContent = n.retired.length;
  if (retired) {
    retired.innerHTML = n.retired.length
      ? '<div class="cards">' + n.retired.map(id => strategyCard(byId[id], "retired")).join("") + "</div>"
      : '<div class="subtitle">aucune stratégie retirée</div>';
  }
}

/* ── strategy drill-down (UI-4) ───────────────────────────────────────── */
function aggTable(rows, label) {
  if (!rows || !rows.length) return '<div class="subtitle">aucun trade clos</div>';
  return '<table class="grid"><tr><th>' + esc(label) +
    "</th><th>devise</th><th>trades</th><th>brut</th><th>comm.</th><th>swap</th><th>net</th></tr>" +
    rows.map(r =>
      "<tr><td>" + esc(r[label]) + "</td><td>" + esc(r.currency) + "</td><td>" +
      esc(r.n_trades) + "</td><td>" + signed(r.gross, 2) + "</td><td>" +
      fmtNum(r.commission, 2) + "</td><td>" + fmtNum(r.swap, 2) + "</td><td>" +
      signed(r.net, 2) + "</td></tr>").join("") + "</table>";
}

function tradesTable(rows) {
  if (!rows || !rows.length) return '<div class="subtitle">aucun trade clos au ledger</div>';
  return '<table class="grid"><tr><th>clos</th><th>instance</th><th>mode</th>' +
    "<th>symbole</th><th>sens</th><th>lots</th><th>entrée</th><th>sortie</th>" +
    "<th>raison</th><th>net</th></tr>" +
    rows.map(t =>
      "<tr><td>" + esc(t.close_time) + "</td><td>" + esc(t.instance_id) +
      "</td><td>" + esc(t.mode) + "</td><td>" + esc(t.symbol) + "</td><td>" +
      esc(t.side) + "</td><td>" + esc(t.volume_lots) + "</td><td>" +
      esc(t.open_price) + "</td><td>" + esc(t.close_price) + "</td><td>" +
      esc(t.exit_reason) + "</td><td>" + signed(t.net_pnl, 2, t.currency) +
      "</td></tr>").join("") + "</table>";
}

async function refreshStrategy() {
  const sid = location.pathname.split("/").pop();
  const res = await fetchJSON("/api/strategy/" + encodeURIComponent(sid));
  if (!res) return;
  const data = res.body;
  setStamp(data);
  const main = document.getElementById("content");
  if (res.status === 404) {
    main.innerHTML = '<section class="panel"><h2>STRATÉGIE INCONNUE</h2>' +
      '<div class="err-line">' + esc(data.error) + "</div></section>";
    return;
  }
  const card = data.card;
  document.title = card.short + " — supervision";
  document.getElementById("page-title").textContent =
    card.short + " — " + card.name;

  let html = "";

  /* errors first — a supervision page leads with what is broken */
  if (data.errors.length) {
    html += '<section class="panel"><h2>ERREURS RÉCENTES</h2>' +
      data.errors.map(e => '<div class="err-line">[' + esc(e.source) + "] " +
        esc(e.error) + "</div>").join("") + "</section>";
  }

  /* instances (§3.1 metrics) */
  html += '<section class="panel"><h2>INSTANCES</h2>' +
    '<div class="subtitle">statut ' + esc(card.declared) +
    " (manifeste, R7) — métriques status.json par instance, confrontées au réel</div>";
  if (!card.instances.length) {
    html += '<div class="subtitle">aucune instance déclarée ni découverte</div>';
  } else {
    html += '<table class="grid"><tr><th>instance</th><th>état</th><th>mode</th>' +
      "<th>trades clos</th><th>R cumulé</th><th>PnL CHF</th><th>capital</th>" +
      "<th>position</th><th>dernière barre</th><th>dernier passage</th></tr>" +
      card.instances.map(i => {
        const etat = i.state === "never" ? "jamais passée"
          : i.state === "unreadable" ? "status illisible"
          : (i.alive ? "vivante" : "périmée");
        const pos = i.open_position
          ? esc(i.open_position.side) + " @ " + esc(i.open_position.entry_price)
          : "—";
        return "<tr><td>" + esc(i.instance) + "</td><td>" + esc(etat) +
          "</td><td>" + esc(i.mode || "—") + "</td><td>" +
          esc(i.n_closed_total != null ? i.n_closed_total : "—") + "</td><td>" +
          (i.state === "ok" ? signed(i.cum_r, 2, "R") : "—") + "</td><td>" +
          (i.state === "ok" ? signed(i.pnl_chf, 2) : "—") + "</td><td>" +
          esc(i.capital != null ? fmtNum(i.capital, 2) : "—") + "</td><td>" +
          pos + "</td><td>" + esc(i.last_bar_time || "—") + "</td><td>" +
          esc(i.generated_at_utc ? fmtAge(i.age_sec) : "jamais") + "</td></tr>";
      }).join("") + "</table>";
  }
  html += "</section>";

  /* equity curves — per instance and cumulated (ledger, fallback §3.2) */
  html += '<section class="panel"><h2>COURBES DE GAINS / PERTES</h2>' +
    '<div class="subtitle">source ledger (equity_snapshots ; repli : cumul des net_pnl clos)</div>';
  html += '<div class="curve-block"><div class="curve-title">cumulée — ' +
    esc(card.short) + "</div>" + curveSvg(data.equity.cumulative, 560, 120, { labels: true }) + "</div>";
  card.instances.forEach(i => {
    html += '<div class="curve-block"><div class="curve-title">' +
      esc(i.instance) + "</div>" +
      curveSvg(data.equity[i.instance], 560, 90, { labels: true }) + "</div>";
  });
  html += "</section>";

  /* ledger aggregates */
  html += '<section class="panel"><h2>AGRÉGATS LEDGER</h2>' +
    "<h4>par jour</h4>" + aggTable(data.aggregates.day, "day") +
    "<h4>par semaine ISO</h4>" + aggTable(data.aggregates.week, "week") +
    "<h4>par mois</h4>" + aggTable(data.aggregates.month, "month") +
    "<h4>par année</h4>" + aggTable(data.aggregates.year, "year") +
    "</section>";

  /* last 50 closed trades */
  html += '<section class="panel"><h2>50 DERNIERS TRADES CLOS</h2>' +
    tradesTable(data.trades) + "</section>";

  /* full manifest */
  html += '<section class="panel"><h2>MANIFESTE</h2>';
  if (data.manifest) {
    html += '<dl class="kv">' + Object.keys(data.manifest).map(k =>
      "<dt>" + esc(k) + "</dt><dd>" +
      esc(JSON.stringify(data.manifest[k])) + "</dd>").join("") + "</dl>";
  } else {
    html += '<div class="err-line">' + esc(data.manifest_error || "manifest absent") + "</div>";
  }
  html += "</section>";

  main.innerHTML = html;
}

/* ── services page (UI-5) ─────────────────────────────────────────────── */
function renderFactory(f) {
  const state = f.alive
    ? '<span class="ok-line">VIVANTE</span> <span class="subtitle">verrou touché ' +
      esc(fmtAge(f.lock_age_sec)) + (f.lock_holder ? " · " + esc(f.lock_holder) : "") + "</span>"
    : '<span class="err-line">MORTE</span> <span class="subtitle">' +
      (f.lock_age_sec == null ? "aucun verrou" : "verrou périmé, touché " +
        esc(fmtAge(f.lock_age_sec))) + "</span>";

  let panel;
  if (!f.panel.present) {
    panel = '<div class="warn-line">panneau introuvable (' + esc(f.panel.file) +
      ") — tous les workers OFF</div>";
  } else if (!f.panel.workers.length) {
    panel = '<div class="warn-line">' + esc(f.panel.error || "panneau vide") + "</div>";
  } else {
    panel = '<table class="grid"><tr><th>worker</th><th>état</th><th>cadence</th>' +
      "<th>dernier résultat (logs)</th></tr>" +
      f.panel.workers.map(w => {
        const last = f.last_by_worker[w.worker];
        const res = last ? esc(last.ts + " " + last.event + " " + last.detail).slice(0, 110)
          : '<span class="subtitle">aucun depuis le démarrage</span>';
        const etat = w.auto_off
          ? '<span class="err-line">AUTO-OFF</span>'
          : (w.on ? '<span class="ok-line">on</span>' : '<span class="subtitle">off</span>');
        const note = w.auto_off ? '<div class="err-line">' + esc(w.comment) + "</div>" : "";
        return "<tr><td>" + esc(w.worker) + "</td><td>" + etat + note + "</td><td>" +
          esc(w.cadence != null ? w.cadence + " s" : "catalogue") + "</td><td>" +
          res + "</td></tr>";
      }).join("") + "</table>";
  }

  const tail = f.recent.length
    ? '<div class="log-tail">' + f.recent.map(e => {
        const cls = (e.event === "INCIDENT" || e.event === "ERREUR" ||
                     e.event === "TIMEOUT") ? "auto-off" : "";
        return '<span class="' + cls + '">[' + esc(e.ts) + "] " + esc(e.event) +
          " [" + esc(e.worker) + "] " + esc(e.detail) + "</span>";
      }).join("\n") + "</div>"
    : '<div class="subtitle">aucun événement worker dans les logs</div>';

  return state + panel + tail;
}

function renderEtude(e) {
  let body;
  if (e.erreur) body = '<span class="err-line">' + esc(e.erreur) + "</span>";
  else if (!e.vivante && e.mesure === "jamais")
    body = '<span class="subtitle">en attente du premier passage</span>';
  else if (e.verdicts != null)
    body = "<b>" + esc(e.news) + "</b> news · <b>" + esc(e.verdicts) + "</b> verdicts";
  else
    body = "<b>" + esc(e.trades) + "</b> trade(s) clos · " + signed(e.cum_r, 2, "R") +
      (e.capital != null ? " · capital " + esc(fmtNum(e.capital, 2)) : "") +
      (e.position ? ' · <span class="badge open-pos">position ouverte</span>' : "");
  return '<div class="card"><h3>' + esc(e.libelle) + "</h3>" +
    '<div class="meta">' + esc(e.dossier) +
    (e.strategie ? " · instancie " + esc(e.strategie) : "") +
    " · dernier passage " + esc(e.mesure) +
    (!e.vivante && e.mesure !== "jamais"
      ? ' · <span class="stale">périmé</span>' : "") + "</div>" +
    '<div style="font-size:12.5px">' + body + "</div></div>";
}

async function refreshServices() {
  const res = await fetchJSON("/api/services");
  if (!res) return;
  const data = res.body;
  setStamp(data);

  document.getElementById("factory-content").innerHTML = renderFactory(data.factory);

  const tg = data.telegram;
  document.getElementById("telegram-content").innerHTML =
    '<table class="grid"><tr><th>canal</th><th>token</th><th>état</th><th>dernier état écrit</th></tr>' +
    [["notifier", tg.notifier], ["gateway", tg.gateway]].map(([name, c]) =>
      "<tr><td>" + name + "</td><td>" +
      (c.token_present ? '<span class="ok-line">présent</span>'
        : '<span class="warn-line">absent</span>') + "</td><td>" +
      (c.state ? esc(JSON.stringify(c.state).slice(0, 160))
        : '<span class="subtitle">pas de state.json</span>') + "</td><td>" +
      esc(c.state_modified || "—") + "</td></tr>").join("") + "</table>";

  const datas = data.datas;
  document.getElementById("datas-content").innerHTML = datas.length
    ? '<table class="grid"><tr><th>dataset</th><th>type</th><th>fichiers</th>' +
      "<th>taille</th><th>modifié</th></tr>" +
      datas.map(d => "<tr><td>" + esc(d.name) + "</td><td>" + esc(d.kind) +
        "</td><td>" + esc(d.n_files) + "</td><td>" + esc(fmtBytes(d.size_bytes)) +
        "</td><td>" + esc(d.modified || "—") + "</td></tr>").join("") + "</table>"
    : '<div class="subtitle">aucun dataset sous la db</div>';

  document.getElementById("backup-content").innerHTML = data.backup
    ? '<pre class="log-tail">' + esc(JSON.stringify(data.backup, null, 1)) + "</pre>"
    : '<div class="subtitle">pas de status.json de backup</div>';

  /* watcher: section shown ONLY if the file exists (SPEC_prod-watcher) */
  const watcherSection = document.getElementById("watcher");
  if (data.watcher) {
    watcherSection.style.display = "";
    document.getElementById("watcher-content").innerHTML =
      '<pre class="log-tail">' + esc(JSON.stringify(data.watcher, null, 1)) + "</pre>";
  } else {
    watcherSection.style.display = "none";
  }

  const tk = data.tickets;
  document.getElementById("tickets-content").innerHTML =
    '<div class="subtitle">' + tk.n_open + " ouvert(s) dont " +
    tk.n_blocking_open + " bloquant(s)</div>" +
    (tk.tickets.length
      ? '<table class="grid"><tr><th>id</th><th>de</th><th>à</th><th>statut</th>' +
        "<th>sujet</th><th>créé</th></tr>" +
        tk.tickets.map(t => {
          const cls = (t.status === "open" && t.blocking) ? "ticket-blocking"
            : t.status === "open" ? "ticket-open" : "ticket-done";
          return '<tr class="' + cls + '"><td>' + esc(t.id) +
            (t.blocking && t.status === "open" ? " ⛔" : "") + "</td><td>" +
            esc(t.from) + "</td><td>" + esc(t.to) + "</td><td>" + esc(t.status) +
            "</td><td>" + esc(t.title) + "</td><td>" + esc(t.created || "—") +
            "</td></tr>";
        }).join("") + "</table>"
      : '<div class="subtitle">aucun ticket</div>');

  document.getElementById("etudes-content").innerHTML =
    '<div class="cards">' + data.etudes.map(renderEtude).join("") + "</div>";
}

/* ── boot ─────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "index") poll(refreshIndex, 5000);          /* UI-8: 5 s */
  else if (page === "strategy") poll(refreshStrategy, 5000);
  else if (page === "services") poll(refreshServices, 10000); /* 10 s */
});
