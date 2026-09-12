/* SPEC_ui-dynamique UI-8 — the ONE front script, vanilla JS, no build, no CDN.
 *
 * Four pages share this file (document.body.dataset.page selects the
 * renderer): index (overview by level), strategy (drill-down), services,
 * analytics (SPEC_analytics-trades — filtres, KPI, courbes, journal).
 * All data comes from the read-only JSON API via polling fetch — 5 s for
 * the strategy views, 10 s for /services and /analytics.  When the API stops answering,
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

/* One attached legacy study (sealed protocol) rendered on its strategy card. */
function studyLine(e) {
  const state = e.vivante ? '<span class="badge alive">vivante</span>'
    : e.mesure === "jamais"
      ? '<span class="never">en attente du premier passage</span>'
      : '<span class="stale">périmée — dernière mesure ' + esc(e.mesure) + "</span>";
  const nums = e.mesure !== "jamais"
    ? '<span class="num">' + esc(e.trades) + " clos</span>" +
      '<span class="num">' + signed(e.cum_r, 2, "R") + "</span>"
    : "";
  const pos = e.position
    ? ' <span class="badge open-pos">position ouverte</span>' : "";
  return '<div class="instance"><span class="iid">' + esc(e.libelle) +
    "</span>" + nums + pos + state + "</div>";
}

/* Minimal card (directive Adrian 2026-08-26) : identité + activité réelle.
 * Les instances jamais passées sont résumées en UNE ligne, jamais listées. */
function strategyCard(card, level) {
  const badgeCls = card.declared === "LIVE" ? "live"
    : card.declared === "PAPER" ? "paper" : "";
  let rows = [];
  if (card.manifest_error) {
    rows.push('<div class="manifest-error">' + esc(card.manifest_error) + "</div>");
  } else {
    const active = card.instances.filter(i => i.state !== "never");
    rows = active.map(instanceLine)
      .concat((card.etudes || []).map(studyLine));
    const nNever = card.instances.length - active.length;
    if (!rows.length) {
      rows.push('<div class="instance"><span class="never">aucune activité' +
        (card.instances.length
          ? " — " + card.instances.length + " instance(s) déclarée(s)" : "") +
        "</span></div>");
    } else if (nNever > 0) {
      rows.push('<div class="instance"><span class="never">+ ' + nNever +
        " instance(s) jamais passée(s)</span></div>");
    }
  }
  return '<div class="card ' + (level === "prod" ? "prod" : "") + '">' +
    '<h3><a href="/strategy/' + esc(card.short) + '">' + esc(card.short) +
    " — " + esc(card.name) + '</a> <span class="badge ' + badgeCls + '">' +
    esc(card.declared) + "</span></h3>" +
    rows.join("") + "</div>";
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

/* Mode d'analyse d'une stratégie d'après son niveau déclaré (R7) :
 * LIVE → LIVE, RESEARCH/BACKTESTED → BACKTEST, tout le reste (PAPER,
 * RETIRED, inconnu) → PAPER, le défaut de la page analyse (D-AN-5). */
function analyticsModeOf(declared) {
  const d = String(declared || "").toUpperCase();
  if (d === "LIVE") return "LIVE";
  if (d === "RESEARCH" || d === "BACKTESTED") return "BACKTEST";
  return "PAPER";
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

  /* AN-2 : drill-down de performance pré-filtré (mode courant de la stratégie) */
  const anMode = analyticsModeOf(card.declared);
  html += '<div class="subtitle"><a href="/analytics?mode=' + esc(anMode) +
    "&strategy=" + esc(card.short) + '">analyse détaillée</a></div>';

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
      "<th>position</th><th>dernière barre</th><th>dernier passage</th><th>analyse</th></tr>" +
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
          esc(i.generated_at_utc ? fmtAge(i.age_sec) : "jamais") + "</td><td>" +
          '<a href="/analytics?mode=' + esc(AN_MODES.includes(i.mode) ? i.mode : anMode) +
          "&strategy=" + esc(card.short) + "&instance=" + encodeURIComponent(i.instance) +
          '">analyse</a></td></tr>';
      }).join("") + "</table>";
  }
  html += "</section>";

  /* attached legacy studies (sealed protocol) — since 2026-08-26 they live
   * on the strategy, not in a separate world */
  if (card.etudes && card.etudes.length) {
    html += '<section class="panel"><h2>ÉTUDES (protocole scellé)</h2>' +
      '<table class="grid"><tr><th>étude</th><th>état</th><th>trades clos</th>' +
      "<th>R cumulé</th><th>capital</th><th>position</th><th>dernière mesure</th></tr>" +
      card.etudes.map(e => {
        const etat = e.vivante ? '<span class="ok-line">vivante</span>'
          : e.mesure === "jamais" ? "jamais passée"
          : '<span class="err-line">périmée</span>';
        return "<tr><td>" + esc(e.libelle) + " (" + esc(e.dossier) + ")</td><td>" +
          etat + "</td><td>" + esc(e.trades != null ? e.trades : "—") +
          "</td><td>" + (e.mesure !== "jamais" ? signed(e.cum_r, 2, "R") : "—") +
          "</td><td>" + esc(e.capital != null ? fmtNum(e.capital, 2) : "—") +
          "</td><td>" + (e.position ? "ouverte" : "—") + "</td><td>" +
          esc(e.mesure) + "</td></tr>";
      }).join("") + "</table></section>";
  }

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

/* ── page analyse (SPEC_analytics-trades, D-AN-13/14) ─────────────────── */
/* Tout le rendu de /analytics vit ici : filtres portés par l'URL, un seul
 * fetch par tick (10 s), re-rendu uniquement si le JSON diffère, graphiques
 * SVG maison (lineChart, areaChart, barChart, heatmapTable), tuiles KPI,
 * bloc SUMMARY, positions ouvertes, journal paginé côté serveur.
 * Aucune donnée brute n'entre dans le DOM sans esc() ou textContent — les
 * signal_reason viennent de fichiers. */

const AN_MULTI = ["strategy", "instance", "symbol", "side", "weekday",
                  "exit_reason", "arm", "magic"];
const AN_SINGLE_DEFAULTS = { source: "auto", curve_base: "auto",
                             weekday_key: "open", dist_unit: "r" };
const AN_SINGLE_DOMAINS = { source: ["auto", "ledger", "journals"],
                            curve_base: ["auto", "zero", "capital"],
                            weekday_key: ["open", "close"], dist_unit: ["r", "ccy"] };
const AN_MODES = ["BACKTEST", "PAPER", "LIVE"];
const AN_LABELS = {
  strategy: "stratégie", instance: "instance", symbol: "symbole", side: "sens",
  weekday: "jour", exit_reason: "sortie", arm: "arm", magic: "magic",
};
const AN_WEEKDAYS = { mon: "lun", tue: "mar", wed: "mer", thu: "jeu",
                      fri: "ven", sat: "sam", sun: "dim" };
const AN_WEEKDAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const AN_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                   "août", "septembre", "octobre", "novembre", "décembre"];
const AN_MONTHS_SHORT = ["JAN", "FÉV", "MAR", "AVR", "MAI", "JUN", "JUL", "AOÛ",
                         "SEP", "OCT", "NOV", "DÉC"];

/* État de la page : filtres courants, dernier JSON, journal, graphiques
 * survolables (points en pixels pour le tooltip). */
const AN = {
  filters: null,
  lastText: null,
  data: null,
  animate: true,          /* animation de tracé uniquement au changement de filtres */
  charts: {},             /* id svg → {xs, pts, kind, ccy} pour le tooltip des courbes */
  hoverSvg: null,         /* courbe survolée (curseur à effacer en sortie) */
  seq: 0,                 /* ids uniques (dégradés, svg) */
  reqSeq: 0,              /* garde anti-réponse périmée (poll vs changement de filtres) */
  journal: { page: 1, limit: 200, sort: null, dir: -1, q: "", lastText: null,
             data: null, reqSeq: 0 },
};

/* ── formats ── */
function fmtMoney(v, ccy, digits) {
  if (v == null || isNaN(v)) return "—";
  return fmtNum(v, digits == null ? 2 : digits) + (ccy ? " " + ccy : "");
}

function fmtSigned(v, digits, unit) {
  if (v == null || isNaN(v)) return "—";
  return (v > 0 ? "+" : "") + fmtNum(v, digits) + (unit ? " " + unit : "");
}

function fmtPct(v, digits) {
  if (v == null || isNaN(v)) return "—";
  return fmtNum(v * 100, digits == null ? 2 : digits) + " %";
}

function fmtSignedPct(v) {
  if (v == null || isNaN(v)) return "—";
  return (v > 0 ? "+" : "") + fmtNum(v * 100, 2) + " %";
}

function pad2(n) { return (n < 10 ? "0" : "") + n; }

/* iso UTC → Date locale du navigateur ; null si illisible. */
function toDate(iso) {
  if (!iso) return null;
  const t = Date.parse(iso);
  return isNaN(t) ? null : new Date(t);
}

function fmtDate(iso, style) {
  const d = toDate(iso);
  if (!d) return "—";
  const yy = pad2(d.getFullYear() % 100), mm = pad2(d.getMonth() + 1),
        dd = pad2(d.getDate());
  if (style === "axis") return yy + "." + mm + "." + dd;          /* yy.mm.dd */
  if (style === "full") return dd + "." + mm + "." + yy + " " +   /* dd.mm.yy HH:MM */
    pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  return dd + "." + mm + "." + yy;                                /* dd.mm.yy */
}

function fmtHours(h) {
  if (h == null || isNaN(h)) return "—";
  if (h < 48) return fmtNum(h, 1) + " h";
  return fmtNum(h / 24, 1) + " j";
}

function nTrades(n) {
  n = Number(n || 0);
  return fmtNum(n, 0) + " trade" + (n > 1 ? "s" : "");
}

function signCls(v) {
  if (v == null || isNaN(v) || v === 0) return "";
  return v > 0 ? "pos" : "neg";
}

/* ── filtres ↔ URL (D-AN-14) ── */
function filtersFromUrl() {
  const p = new URLSearchParams(location.search);
  const f = { mode: AN_MODES.includes(p.get("mode")) ? p.get("mode") : "PAPER",
              from: p.get("from") || "", to: p.get("to") || "" };
  AN_MULTI.forEach(k => { f[k] = p.getAll(k).filter(v => v !== ""); });
  Object.keys(AN_SINGLE_DEFAULTS).forEach(k => {
    /* valeur hors domaine dans une URL partagée : défaut plutôt qu'un 400 permanent */
    f[k] = AN_SINGLE_DOMAINS[k].includes(p.get(k)) ? p.get(k) : AN_SINGLE_DEFAULTS[k];
  });
  return f;
}

/* Query string API (sans page/limit) — les défauts implicites restent absents
 * pour garder une URL courte et partageable. */
function filtersQuery(f) {
  const p = new URLSearchParams();
  p.append("mode", f.mode);
  AN_MULTI.forEach(k => f[k].forEach(v => p.append(k, v)));
  if (f.from) p.append("from", f.from);
  if (f.to) p.append("to", f.to);
  Object.keys(AN_SINGLE_DEFAULTS).forEach(k => {
    if (f[k] && f[k] !== AN_SINGLE_DEFAULTS[k]) p.append(k, f[k]);
  });
  return p.toString();
}

function pushFiltersToUrl() {
  const qs = filtersQuery(AN.filters);
  history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
  const pu = document.getElementById("print-url");
  if (pu) pu.textContent = location.href;
}

/* Barre de filtres (AN-8) : structure construite une fois, options
 * dépendantes (AN-7) réécrites à chaque réponse sans perdre l'état ouvert
 * des <details>. */
function filterBar(el) {
  if (!el) return;
  const f = AN.filters;
  let html = '<div class="frow"><span class="flabel">mode</span>' +
    AN_MODES.map(m => '<label class="fradio"><input type="radio" name="mode" value="' +
      m + '"' + (f.mode === m ? " checked" : "") + "> " + m + "</label>").join("") +
    "</div>";
  html += '<div class="frow">' + AN_MULTI.map(k =>
    '<details class="fsel" data-key="' + k + '"><summary><span class="flabel">' +
    esc(AN_LABELS[k]) + '</span> <span class="fcount">tous</span></summary>' +
    '<div class="opts"></div></details>').join("") + "</div>";
  html += '<div class="frow">' +
    '<label class="fdate">du <input type="date" name="from" value="' + esc(f.from) + '"></label>' +
    '<label class="fdate">au <input type="date" name="to" value="' + esc(f.to) + '"></label>' +
    selectHtml("source", AN_SINGLE_DOMAINS.source, f.source, "source") +
    selectHtml("curve_base", AN_SINGLE_DOMAINS.curve_base, f.curve_base, "base courbe") +
    selectHtml("weekday_key", AN_SINGLE_DOMAINS.weekday_key, f.weekday_key, "jour clé") +
    selectHtml("dist_unit", AN_SINGLE_DOMAINS.dist_unit, f.dist_unit, "distribution") +
    '<button type="button" id="filters-clear">effacer les filtres</button>' +
    "</div>";
  el.innerHTML = html;
  el.addEventListener("change", onFilterChange);
  document.getElementById("filters-clear").addEventListener("click", () => {
    const keep = AN.filters.mode;
    AN.filters = { mode: keep, from: "", to: "" };
    AN_MULTI.forEach(k => { AN.filters[k] = []; });
    Object.assign(AN.filters, AN_SINGLE_DEFAULTS);
    syncFilterInputs(el);
    afterFilterChange();
  });
  refreshFilterOptions(el, {});
}

function selectHtml(name, values, current, label) {
  return '<label class="fselect">' + esc(label) + ' <select name="' + name + '">' +
    values.map(v => '<option value="' + v + '"' + (current === v ? " selected" : "") +
      ">" + v + "</option>").join("") + "</select></label>";
}

/* Réécrit les valeurs des contrôles simples depuis AN.filters (après « effacer »). */
function syncFilterInputs(el) {
  const f = AN.filters;
  el.querySelectorAll('input[name="mode"]').forEach(i => { i.checked = i.value === f.mode; });
  el.querySelector('input[name="from"]').value = f.from;
  el.querySelector('input[name="to"]').value = f.to;
  Object.keys(AN_SINGLE_DEFAULTS).forEach(k => {
    el.querySelector('select[name="' + k + '"]').value = f[k];
  });
  el.querySelectorAll(".fsel .opts input").forEach(i => { i.checked = false; });
  el.querySelectorAll(".fsel .fcount").forEach(s => { s.textContent = "tous"; });
}

/* Options dépendantes (AN-7, AN-9) : une valeur cochée absente des options
 * reste listée (sinon impossible de la décocher). */
function refreshFilterOptions(el, options) {
  options = options || {};
  AN_MULTI.forEach(k => {
    const det = el.querySelector('.fsel[data-key="' + k + '"]');
    if (!det) return;
    const chosen = AN.filters[k];
    const items = [];
    const seen = new Set();
    (options[k] || []).forEach(o => {
      const id = String(o && typeof o === "object" ? o.id : o);
      if (seen.has(id)) return;
      seen.add(id);
      let label = id;
      if (o && typeof o === "object") {
        if (o.display_name && o.display_name !== id) label += " · " + o.display_name;
        if (o.retired) label += " (retired)";
      } else if (k === "weekday") {
        label = AN_WEEKDAYS[id] || id;
      }
      items.push({ id: id, label: label });
    });
    chosen.forEach(v => { if (!seen.has(v)) { seen.add(v); items.push({ id: v, label: v + " (0 trade)" }); } });
    det.querySelector(".opts").innerHTML = items.length
      ? items.map(it => '<label><input type="checkbox" value="' + esc(it.id) + '"' +
          (chosen.includes(it.id) ? " checked" : "") + "> " + esc(it.label) + "</label>").join("")
      : '<span class="subtitle">aucune valeur</span>';
    det.querySelector(".fcount").textContent =
      chosen.length ? chosen.length + " choisi" + (chosen.length > 1 ? "s" : "") : "tous";
  });
}

function onFilterChange(e) {
  const t = e.target;
  const el = document.getElementById("filters");
  if (!t || !t.name && !t.closest(".fsel")) return;
  const f = AN.filters;
  if (t.name === "mode") f.mode = t.value;
  else if (t.name === "from" || t.name === "to") f[t.name] = t.value;
  else if (t.tagName === "SELECT") f[t.name] = t.value;
  else if (t.type === "checkbox") {
    const det = t.closest(".fsel");
    if (!det) return;
    const k = det.dataset.key;
    f[k] = Array.from(det.querySelectorAll(".opts input:checked")).map(i => i.value);
    det.querySelector(".fcount").textContent =
      f[k].length ? f[k].length + " choisi" + (f[k].length > 1 ? "s" : "") : "tous";
  } else return;
  if (el) el.classList.add("busy");
  afterFilterChange();
}

function afterFilterChange() {
  AN.animate = true;
  AN.journal.page = 1;
  pushFiltersToUrl();
  refreshAnalytics(true);
}

/* ── tooltip DOM partagé ── */
function tipEl() {
  let t = document.getElementById("tooltip");
  if (!t) {
    t = document.createElement("div");
    t.id = "tooltip";
    t.className = "tooltip";
    t.hidden = true;
    document.body.appendChild(t);
  }
  return t;
}

function tipShow(text, pageX, pageY) {
  const t = tipEl();
  t.textContent = text;
  t.hidden = false;
  const w = t.offsetWidth, vw = document.documentElement.clientWidth;
  let x = pageX + 14;
  if (x + w > window.scrollX + vw - 8) x = pageX - w - 14;
  t.style.left = x + "px";
  t.style.top = (pageY + 14) + "px";
}

function tipHide() { tipEl().hidden = true; }

/* Un seul écouteur : les éléments porteurs de data-tip (barres, cellules) et
 * les courbes (data-chart) partagent le même tooltip. */
function installTooltips() {
  document.addEventListener("mousemove", e => {
    const tgt = e.target instanceof Element ? e.target : null;
    if (!tgt) return;
    const svg = tgt.closest("svg[data-chart]");
    if (svg) { curveHover(svg, e); return; }
    if (AN.hoverSvg) {
      AN.hoverSvg.querySelectorAll(".cursor, .dot").forEach(x => { x.style.display = "none"; });
      AN.hoverSvg = null;
    }
    const tip = tgt.closest("[data-tip]");
    if (tip) tipShow(tip.dataset.tip, e.pageX, e.pageY);
    else tipHide();
  });
  document.addEventListener("mouseleave", tipHide);
}

function curveHover(svg, e) {
  const c = AN.charts[svg.dataset.chart];
  if (!c || !c.xs.length) { tipHide(); return; }
  AN.hoverSvg = svg;
  const rect = svg.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  let lo = 0, hi = c.xs.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (c.xs[mid] < mx) lo = mid + 1; else hi = mid;
  }
  if (lo > 0 && Math.abs(c.xs[lo - 1] - mx) < Math.abs(c.xs[lo] - mx)) lo -= 1;
  const cursor = svg.querySelector(".cursor"), dot = svg.querySelector(".dot");
  if (cursor) { cursor.setAttribute("x1", c.xs[lo]); cursor.setAttribute("x2", c.xs[lo]); cursor.style.display = ""; }
  if (dot) { dot.setAttribute("cx", c.xs[lo]); dot.setAttribute("cy", c.ys[lo]); dot.style.display = ""; }
  const p = c.pts[lo];
  const text = c.kind === "drawdown"
    ? fmtDate(p[0]) + " — drawdown " + fmtSigned(p[2], 2, c.ccy) +
      (p[3] != null ? " (" + fmtSignedPct(p[3]) + ")" : "")
    : fmtDate(p[0]) + " — solde " + fmtMoney(p[1], c.ccy);
  tipShow(text, e.pageX, e.pageY);
}

/* ── primitives SVG ── */
function svgText(x, y, s, anchor, cls) {
  return '<text x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '"' +
    (anchor ? ' text-anchor="' + anchor + '"' : "") +
    (cls ? ' class="' + cls + '"' : "") + ">" + esc(s) + "</text>";
}

function chartWidth(el) {
  return Math.max(320, (el && el.clientWidth ? el.clientWidth : 900) - 4);
}

/* Échelle temps → x : équirépartie par index si toutes les dates sont égales. */
function timeScale(pts, x0, x1) {
  const ts = pts.map(p => { const d = toDate(p[0]); return d ? d.getTime() : NaN; });
  const valid = ts.filter(t => !isNaN(t));
  const t0 = valid.length ? Math.min.apply(null, valid) : 0;
  const t1 = valid.length ? Math.max.apply(null, valid) : 0;
  const span = t1 - t0;
  const n = pts.length;
  const xs = ts.map((t, i) => {
    if (span > 0 && !isNaN(t)) return x0 + (t - t0) * (x1 - x0) / span;
    return n > 1 ? x0 + i * (x1 - x0) / (n - 1) : (x0 + x1) / 2;
  });
  return { xs: xs, t0: t0, t1: t1, span: span };
}

function axisDates(scale, x0, x1, yb) {
  if (!scale.t0 && !scale.t1) return "";          /* aucune date lisible : pas d'axe */
  if (!scale.span) {
    return svgText((x0 + x1) / 2, yb, fmtDate(new Date(scale.t0).toISOString(), "axis"), "middle");
  }
  let out = "";
  for (let k = 0; k < 8; k++) {
    const t = scale.t0 + scale.span * k / 7;
    const x = x0 + (x1 - x0) * k / 7;
    out += svgText(x, yb, fmtDate(new Date(t).toISOString(), "axis"),
      k === 0 ? "start" : k === 7 ? "end" : "middle");
  }
  return out;
}

/* Courbe de solde (AN-15) : aire dégradée bleue, ligne de base pointillée,
 * 5 graduations Y, 8 dates X, tooltip DOM. points = [[iso, balance, dd, dd_pct]]. */
function lineChart(pts, w, h, opts) {
  opts = opts || {};
  const id = "chart" + (++AN.seq);
  pts = (pts || []).filter(p => Array.isArray(p) && isFinite(Number(p[1])));
  if (!pts.length) {
    return '<svg class="chart" width="' + w + '" height="' + h + '"><text x="8" y="' +
      (h / 2) + '">rien à tracer</text></svg>';
  }
  const ml = 72, mr = 14, mt = 12, mb = 22;
  const x0 = ml, x1 = w - mr, y0 = mt, y1 = h - mb;
  const vals = pts.map(p => Number(p[1]));
  let min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
  if (opts.base != null) { min = Math.min(min, opts.base); max = Math.max(max, opts.base); }
  if (max === min) { max += 1; min -= 1; }
  const sc = timeScale(pts, x0, x1);
  const yOf = v => y1 - (v - min) * (y1 - y0) / (max - min);
  const ys = vals.map(yOf);
  const digits = (max - min) > 50 ? 0 : 2;
  let g = "";
  for (let k = 0; k < 5; k++) {
    const v = min + (max - min) * k / 4, y = yOf(v);
    g += '<line class="grid-line" x1="' + x0 + '" x2="' + x1 + '" y1="' + y.toFixed(1) +
      '" y2="' + y.toFixed(1) + '"/>' + svgText(ml - 6, y + 3, fmtNum(v, digits), "end");
  }
  const line = sc.xs.map((x, i) => x.toFixed(1) + "," + ys[i].toFixed(1)).join(" ");
  const area = "M" + sc.xs[0].toFixed(1) + "," + y1 + " L" + line + " L" +
    sc.xs[sc.xs.length - 1].toFixed(1) + "," + y1 + " Z";
  let base = "";
  if (opts.base != null) {
    const yb = yOf(opts.base);
    base = '<line class="baseline" x1="' + x0 + '" x2="' + x1 + '" y1="' + yb.toFixed(1) +
      '" y2="' + yb.toFixed(1) + '"/>' +
      svgText(x1, yb - 3, opts.base === 0 ? "0" : fmtMoney(opts.base, opts.ccy, 0), "end", "baselabel");
  }
  AN.charts[id] = { xs: sc.xs, ys: ys, pts: pts, kind: "balance", ccy: opts.ccy };
  return '<svg class="chart" data-chart="' + id + '" width="' + w + '" height="' + h + '">' +
    "<defs><linearGradient id=\"g" + id + '" x1="0" y1="0" x2="0" y2="1">' +
    '<stop offset="0" stop-color="#7cc0ff" stop-opacity=".35"/>' +
    '<stop offset="1" stop-color="#7cc0ff" stop-opacity=".02"/></linearGradient></defs>' +
    g + '<path class="area" fill="url(#g' + id + ')" d="' + area + '"/>' + base +
    '<polyline class="line' + (AN.animate ? " anim" : "") + '" points="' + line +
    '" fill="none" stroke="#7cc0ff" stroke-width="1.5"/>' +
    axisDates(sc, x0, x1, h - 6) +
    '<line class="cursor" style="display:none" y1="' + y0 + '" y2="' + y1 + '"/>' +
    '<circle class="dot" style="display:none" r="3"/></svg>';
}

/* Drawdown (AN-16) : aire rouge sous 0, axe Y négatif, tooltip avec dd_pct
 * relatif au pic. */
function areaChart(pts, w, h, opts) {
  opts = opts || {};
  const id = "chart" + (++AN.seq);
  pts = (pts || []).filter(p => Array.isArray(p) && isFinite(Number(p[2] == null ? 0 : p[2])));
  if (!pts.length) {
    return '<svg class="chart" width="' + w + '" height="' + h + '"><text x="8" y="' +
      (h / 2) + '">rien à tracer</text></svg>';
  }
  const ml = 72, mr = 14, mt = 12, mb = 22;
  const x0 = ml, x1 = w - mr, y0 = mt, y1 = h - mb;
  const vals = pts.map(p => Number(p[2] || 0));
  let min = Math.min(0, Math.min.apply(null, vals));
  if (min === 0) min = -1;
  const sc = timeScale(pts, x0, x1);
  const yOf = v => y0 + (0 - v) * (y1 - y0) / (0 - min);
  const ys = vals.map(yOf);
  const digits = (-min) > 50 ? 0 : 2;
  let g = "";
  for (let k = 0; k < 5; k++) {
    const v = min * k / 4, y = yOf(v);
    g += '<line class="grid-line" x1="' + x0 + '" x2="' + x1 + '" y1="' + y.toFixed(1) +
      '" y2="' + y.toFixed(1) + '"/>' + svgText(ml - 6, y + 3, fmtNum(v, digits), "end");
  }
  const line = sc.xs.map((x, i) => x.toFixed(1) + "," + ys[i].toFixed(1)).join(" ");
  const area = "M" + sc.xs[0].toFixed(1) + "," + y0 + " L" + line + " L" +
    sc.xs[sc.xs.length - 1].toFixed(1) + "," + y0 + " Z";
  AN.charts[id] = { xs: sc.xs, ys: ys, pts: pts, kind: "drawdown", ccy: opts.ccy };
  return '<svg class="chart" data-chart="' + id + '" width="' + w + '" height="' + h + '">' +
    g + '<path class="area" fill="rgba(255,107,107,.28)" d="' + area + '"/>' +
    '<polyline class="line' + (AN.animate ? " anim" : "") + '" points="' + line +
    '" fill="none" stroke="#ff6b6b" stroke-width="1.3"/>' +
    axisDates(sc, x0, x1, h - 6) +
    '<line class="cursor" style="display:none" y1="' + y0 + '" y2="' + y1 + '"/>' +
    '<circle class="dot" style="display:none" r="3"/></svg>';
}

/* Barres (AN-20…24) — items: [{label, value, tip, stack:[{label, value}]}].
 * opts.horizontal : une ligne par item (P&L par instance) ;
 * opts.plain : histogramme bleu non signé ; opts.stacked : sous-barres
 * signées empilées (positives vers le haut, négatives vers le bas) ;
 * opts.labelEvery : étiquette d'axe une barre sur n. */
function barChart(items, w, h, opts) {
  opts = opts || {};
  if (!items || !items.length) {
    return '<svg class="chart" width="' + w + '" height="' + (h || 60) + '"><text x="8" y="30">rien à tracer</text></svg>';
  }
  const every = opts.labelEvery || 1;
  const color = v => opts.plain ? "#7cc0ff" : (v >= 0 ? "#7fd18c" : "#ff6b6b");
  if (opts.horizontal) {
    const rowH = 22, ml = 150, mr = 120, mt = 6;
    h = mt * 2 + items.length * rowH;
    const vals = items.map(i => Number(i.value || 0));
    const max = Math.max(0, Math.max.apply(null, vals)), min = Math.min(0, Math.min.apply(null, vals));
    const span = (max - min) || 1;
    const x0 = ml, x1 = w - mr;
    const xOf = v => x0 + (v - min) * (x1 - x0) / span;
    const xz = xOf(0);
    let out = '<line class="zero" x1="' + xz.toFixed(1) + '" x2="' + xz.toFixed(1) + '" y1="' + mt + '" y2="' + (h - mt) + '"/>';
    items.forEach((it, i) => {
      const v = vals[i], y = mt + i * rowH;
      const xa = Math.min(xz, xOf(v)), bw = Math.max(1, Math.abs(xOf(v) - xz));
      out += '<rect x="' + xa.toFixed(1) + '" y="' + (y + 4) + '" width="' + bw.toFixed(1) +
        '" height="' + (rowH - 8) + '" fill="' + color(v) + '" data-tip="' + esc(it.tip || "") + '"/>' +
        svgText(ml - 8, y + rowH / 2 + 4, it.label, "end") +
        svgText(x1 + 8, y + rowH / 2 + 4, it.right || "", "start", signCls(v));
    });
    return '<svg class="chart" width="' + w + '" height="' + h + '">' + out + "</svg>";
  }
  const ml = 64, mr = 10, mt = 10, mb = 22;
  const x0 = ml, x1 = w - mr, y0 = mt, y1 = h - mb;
  const tops = items.map(it => opts.stacked
    ? (it.stack || []).reduce((s, x) => s + Math.max(0, Number(x.value || 0)), 0)
    : Math.max(0, Number(it.value || 0)));
  const bots = items.map(it => opts.stacked
    ? (it.stack || []).reduce((s, x) => s + Math.min(0, Number(x.value || 0)), 0)
    : Math.min(0, Number(it.value || 0)));
  let max = Math.max.apply(null, tops), min = Math.min.apply(null, bots);
  if (opts.stacked) {
    max = Math.max(max, Math.max.apply(null, items.map(i => Number(i.value || 0))));
    min = Math.min(min, Math.min.apply(null, items.map(i => Number(i.value || 0))));
  }
  if (max === min) max = min + 1;
  const yOf = v => y1 - (v - min) * (y1 - y0) / (max - min);
  const yz = yOf(0);
  const slot = (x1 - x0) / items.length, bw = Math.max(2, slot * 0.72);
  const digits = (max - min) > 50 ? 0 : 2;
  let out = "";
  for (let k = 0; k < 5; k++) {
    const v = min + (max - min) * k / 4, y = yOf(v);
    out += '<line class="grid-line" x1="' + x0 + '" x2="' + x1 + '" y1="' + y.toFixed(1) +
      '" y2="' + y.toFixed(1) + '"/>' + svgText(ml - 6, y + 3, fmtNum(v, digits), "end");
  }
  out += '<line class="zero" x1="' + x0 + '" x2="' + x1 + '" y1="' + yz.toFixed(1) + '" y2="' + yz.toFixed(1) + '"/>';
  items.forEach((it, i) => {
    const xa = x0 + i * slot + (slot - bw) / 2;
    if (opts.stacked && it.stack && it.stack.length) {
      let up = 0, down = 0;
      it.stack.forEach((s, j) => {
        const v = Number(s.value || 0);
        if (v === 0) return;
        const from = v > 0 ? up : down, to = from + v;
        const ya = Math.min(yOf(from), yOf(to)), hh = Math.max(1, Math.abs(yOf(to) - yOf(from)));
        out += '<rect x="' + xa.toFixed(1) + '" y="' + ya.toFixed(1) + '" width="' + bw.toFixed(1) +
          '" height="' + hh.toFixed(1) + '" fill="' + color(v) + '" fill-opacity="' +
          Math.max(0.35, 0.95 - j * 0.15).toFixed(2) + '" stroke="#0b1219" stroke-width=".6" data-tip="' +
          esc(s.tip || "") + '"/>';
        if (v > 0) up = to; else down = to;
      });
    } else {
      const v = Number(it.value || 0);
      const ya = Math.min(yz, yOf(v)), hh = Math.max(1, Math.abs(yOf(v) - yz));
      out += '<rect x="' + xa.toFixed(1) + '" y="' + ya.toFixed(1) + '" width="' + bw.toFixed(1) +
        '" height="' + hh.toFixed(1) + '" fill="' + color(v) + '" data-tip="' + esc(it.tip || "") + '"/>';
    }
    if (i % every === 0) out += svgText(xa + bw / 2, h - 6, it.label, "middle");
  });
  return '<svg class="chart" width="' + w + '" height="' + h + '">' + out + "</svg>";
}

/* Après insertion : animation de tracé stroke-dashoffset 400 ms, uniquement
 * sur les courbes marquées .anim (changement de filtres, D-AN-14). */
function animateLines(root) {
  root.querySelectorAll(".line.anim").forEach(p => {
    let len = 0;
    try { len = p.getTotalLength(); } catch (e) { len = 0; }
    if (!len) return;
    p.style.transition = "none";
    p.style.strokeDasharray = len;
    p.style.strokeDashoffset = len;
    p.getBoundingClientRect();
    requestAnimationFrame(() => {
      p.style.transition = "stroke-dashoffset .4s ease";
      p.style.strokeDashoffset = 0;
    });
  });
}

/* ── tuiles KPI (AN-13) ── */
function tile(label, value, sub, cls) {
  return '<div class="tile"><div class="tile-label">' + esc(label) + '</div>' +
    '<div class="tile-value ' + (cls || "") + '">' + esc(value) + '</div>' +
    '<div class="tile-sub">' + esc(sub || "") + "</div></div>";
}

function kpiTiles(k, ccy, reduced) {
  k = k || {};
  const n = k.total_trades || 0;
  const pf = k.profit_factor;
  const pfTxt = n === 0 ? "—" : pf == null ? ((k.losses || 0) === 0 && (k.wins || 0) > 0 ? "∞" : "—") : fmtNum(pf, 2);
  const tiles = [];
  tiles.push(tile("TRADES", String(n), "L " + (k.long || 0) + " · S " + (k.short || 0)));
  tiles.push(tile("TAUX DE GAIN", n ? fmtPct(k.win_rate, 1) : "—",
    (k.wins || 0) + " / " + (k.losses || 0) + ((k.zeros || 0) > 0 ? " · " + k.zeros + " à 0" : ""),
    n && k.win_rate >= 0.5 ? "pos" : ""));
  tiles.push(tile("P&L NET", n ? fmtSigned(k.net_pnl, 2, ccy) : "—",
    "Ø " + fmtSigned(k.avg_per_trade, 2) + " par trade", signCls(k.net_pnl)));
  tiles.push(tile("PROFIT FACTOR", pfTxt,
    fmtSigned(k.gross_profit, 2) + " / " + fmtSigned(k.gross_loss, 2),
    pf == null ? "" : pf >= 1 ? "pos" : "neg"));
  const dd = k.max_drawdown;
  tiles.push(tile("DRAWDOWN MAX", n ? fmtSigned(dd ? -dd : 0, 2, ccy) +
      (k.max_dd_pct != null && dd ? " (" + fmtSignedPct(-k.max_dd_pct) + ")" : "") : "—",
    k.recovery_factor != null ? "récup. x" + fmtNum(k.recovery_factor, 2) : "récup. —",
    dd ? "neg" : ""));
  if (!reduced) {
    const cd = k.current_drawdown;
    tiles.push(tile("DD COURANT", n ? fmtSigned(cd ? -cd : 0, 2, ccy) : "—",
      k.recovered_pct != null ? "récupéré " + fmtPct(k.recovered_pct, 0) : "récupéré —",
      cd ? "neg" : ""));
    tiles.push(tile("GAIN MOY. / PERTE MOY.",
      fmtSigned(k.avg_win, 2) + " / " + fmtSigned(k.avg_loss, 2), "par trade gagnant / perdant"));
    tiles.push(tile("ESPÉRANCE", n ? fmtSigned(k.expectancy, 2, ccy) : "—", "par trade",
      signCls(k.expectancy)));
  }
  tiles.push(tile("R MOYEN", k.avg_r != null ? fmtSigned(k.avg_r, 2, "R") : "—",
    "Σ " + fmtSigned(k.sum_r, 2, "R"), signCls(k.avg_r)));
  return tiles.join("");
}

/* ── heatmap mensuelle (AN-19) ── */
function heatClass(v, maxAbs) {
  if (!v || !maxAbs) return "";
  const r = Math.abs(v) / maxAbs;
  const lvl = r > 0.75 ? 4 : r > 0.5 ? 3 : r > 0.25 ? 2 : 1;
  return (v > 0 ? "pos" : "neg") + " heat-" + lvl;
}

function heatCell(c, tipPrefix, ccy, maxAbs) {
  if (!c || !c.n_trades) return '<td class="heat-cell empty">–</td>';
  const tip = tipPrefix + " · " + fmtSigned(c.net, 2, ccy) + " · " + nTrades(c.n_trades) +
    (c.sum_r != null ? " · " + fmtSigned(c.sum_r, 2, "R") : "");
  return '<td class="heat-cell ' + heatClass(c.net, maxAbs) + '" data-tip="' + esc(tip) + '">' +
    '<span class="h1">' + esc(fmtSigned(c.net, 0)) + "</span>" +
    '<span class="h2">' + esc(c.pct != null ? fmtSignedPct(c.pct) : "—") + "</span>" +
    '<span class="h3">' + esc(c.sum_r != null ? fmtSigned(c.sum_r, 1, "R") : "—") + "</span></td>";
}

function heatmapTable(hm, ccy) {
  hm = hm || {};
  const cells = hm.cells || {}, yt = hm.year_totals || {}, mt = hm.month_totals || {};
  const years = (hm.years || []).map(String).sort();
  if (!years.length) return '<div class="subtitle">aucun mois à afficher</div>';
  let maxAbs = 0;
  Object.keys(cells).forEach(k => { maxAbs = Math.max(maxAbs, Math.abs(Number((cells[k] || {}).net || 0))); });
  let html = '<div class="heat-wrap"><table class="grid heat"><tr><th></th>' +
    AN_MONTHS_SHORT.map(m => "<th>" + m + "</th>").join("") + "<th>TOTAL</th></tr>";
  years.forEach(y => {
    html += "<tr><th>" + esc(y) + "</th>";
    for (let m = 1; m <= 12; m++) {
      html += heatCell(cells[y + "-" + pad2(m)], y + " " + AN_MONTHS[m - 1], ccy, maxAbs);
    }
    html += heatCell(yt[y], y + " total", ccy, 0).replace('class="heat-cell', 'class="heat-cell total');
    html += "</tr>";
  });
  html += "<tr><th>TOTAL</th>";
  for (let m = 1; m <= 12; m++) {
    html += heatCell(mt[pad2(m)], AN_MONTHS[m - 1] + " (toutes années)", ccy, 0)
      .replace('class="heat-cell', 'class="heat-cell total');
  }
  html += heatCell(hm.total, "total", ccy, 0).replace('class="heat-cell', 'class="heat-cell total');
  return html + "</tr></table></div>";
}

/* ── SUMMARY (AN-25) ── */
const AN_SUMMARY_COLS = [
  ["VOLUME", "volume", [
    ["total", "trades", "int"], ["long", "long", "int"], ["short", "short", "int"],
    ["wins", "gagnants", "int"], ["losses", "perdants", "int"], ["zeros", "à zéro", "int"],
    ["win_rate", "taux de gain", "pct"], ["long_win_rate", "taux long", "pct"],
    ["short_win_rate", "taux short", "pct"]]],
  ["P&L", "pnl", [
    ["net", "net", "money"], ["gross_profit", "gains bruts", "money"],
    ["gross_loss", "pertes brutes", "money"], ["avg_win", "gain moyen", "money"],
    ["avg_loss", "perte moyenne", "money"], ["expectancy", "espérance", "money"],
    ["profit_factor", "profit factor", "ratio"], ["best_trade", "meilleur trade", "money"],
    ["worst_trade", "pire trade", "money"], ["best_r", "meilleur R", "r"],
    ["worst_r", "pire R", "r"], ["sum_r", "Σ R", "r"], ["avg_r", "R moyen", "r"],
    ["pct_trades_ge_1r", "trades ≥ 1 R", "pct"], ["sum_risk", "risque total", "money"]]],
  ["RISQUE", "risk", [
    ["max_drawdown", "drawdown max", "money"], ["max_dd_pct", "dd max %", "pct"],
    ["recovery_factor", "recovery factor", "ratio"], ["current_drawdown", "dd courant", "money"],
    ["recovered_pct", "récupéré", "pct"], ["dd_duration_days", "durée dd (j)", "int"],
    ["recovery_days", "récupération (j)", "int"], ["sharpe_r", "sharpe (R, par trade)", "ratio"],
    ["sharpe_r_annual", "sharpe annualisé", "ratio"], ["sortino_r", "sortino (R)", "ratio"]]],
  ["SÉRIES & DURÉE", "streaks", [
    ["max_win_streak", "série gains max", "int"], ["max_loss_streak", "série pertes max", "int"],
    ["current_streak", "série courante", "streak"], ["avg_holding_h", "durée moyenne", "hours"],
    ["median_holding_h", "durée médiane", "hours"], ["max_holding_h", "durée max", "hours"]]],
  ["SOLDE & COÛTS", "balance", [
    ["base", "capital initial", "money"], ["final_balance", "solde final", "money"],
    ["total_commission", "commissions", "money"], ["total_swap", "swaps", "money"],
    ["total_edge_cost", "coût de bord", "money"]]],
];

function fmtSummary(v, kind, ccy) {
  if (v == null) return "—";
  switch (kind) {
    case "int": return fmtNum(v, 0);
    case "pct": return fmtPct(v, 2);
    case "money": return fmtMoney(v, ccy);
    case "r": return fmtSigned(v, 2, "R");
    case "ratio": return fmtNum(v, 2);
    case "hours": return fmtHours(v);
    case "streak": return typeof v === "object"
      ? (v.kind === "win" ? "gain" : v.kind === "loss" ? "perte" : String(v.kind || "—")) +
        " × " + (v.len != null ? v.len : 0)
      : String(v);
    default: return String(v);
  }
}

function summaryBlock(s, ccy) {
  s = s || {};
  return '<div class="summary-grid">' + AN_SUMMARY_COLS.map(col => {
    const src = s[col[1]] || {};
    return '<div class="summary-col"><h4>' + esc(col[0]) + '</h4><dl class="kv">' +
      col[2].map(row => {
        const v = src[row[0]];
        const cls = (row[2] === "money" || row[2] === "r") && row[0] !== "base" &&
          row[0] !== "sum_risk" && row[0] !== "total_commission" && row[0] !== "total_swap" &&
          row[0] !== "total_edge_cost" && row[0] !== "max_drawdown" &&
          row[0] !== "current_drawdown" ? signCls(v) : "";
        return "<dt>" + esc(row[1]) + '</dt><dd class="' + cls + '">' +
          esc(fmtSummary(v, row[2], ccy)) + "</dd>";
      }).join("") + (col[1] === "risk"
        ? '<dd class="subtitle">sharpe / sortino : par trade (R) · annualisé sur ' +
          (s.risk && s.risk.trades_per_year != null ? esc(fmtNum(s.risk.trades_per_year, 0)) : "—") +
          ' trades/an · nul sous 20 trades</dd>' : "") +
      "</dl></div>";
  }).join("") + "</div>";
}

/* ── positions ouvertes (AN-30) ── */
function openPositions(rows) {
  if (!rows || !rows.length) return '<div class="subtitle">aucune</div>';
  return '<table class="grid"><tr><th>stratégie</th><th>instance</th><th>mode</th>' +
    "<th>symbole</th><th>sens</th><th>ouverture</th><th>prix ouv.</th><th>stop</th>" +
    "<th>cible</th><th>lots</th><th>risque</th><th>arm</th><th>âge</th><th>source</th></tr>" +
    rows.map(p => "<tr><td>" + esc(p.strategy_id) + "</td><td>" + esc(p.instance_id || "—") +
      "</td><td>" + esc(p.mode) + "</td><td>" + esc(p.symbol) + "</td><td>" + sideBadge(p.side) +
      "</td><td>" + esc(fmtDate(p.open_time, "full")) + "</td><td>" + esc(p.open_price) +
      "</td><td>" + esc(p.stop_price) + "</td><td>" + esc(p.target_price != null ? p.target_price : "—") +
      "</td><td>" + esc(p.volume_lots) + "</td><td>" + esc(fmtNum(p.risk_amount, 2)) +
      "</td><td>" + esc(p.arm || "—") + "</td><td>" + esc(fmtHours(p.age_h)) +
      "</td><td>" + esc(p.source) + "</td></tr>").join("") + "</table>";
}

function sideBadge(side) {
  const s = String(side || "?");
  return '<span class="badge side-' + (s === "LONG" ? "long" : "short") + '">' + esc(s) + "</span>";
}

/* ── journal (AN-29) ── */
const AN_JOURNAL_COLS = [
  ["ref", "id/ticket", r => r.ticket != null ? r.ticket : (r.source_ref != null ? r.source_ref : r.id)],
  ["instance_id", "instance", r => r.instance_id || r.symbol],
  ["side", "sens", r => r.side],
  ["volume_lots", "lots", r => r.volume_lots],
  ["open_time", "ouverture", r => r.open_time],
  ["close_time", "clôture", r => r.close_time],
  ["open_price", "prix ouv.", r => r.open_price],
  ["close_price", "prix clôt.", r => r.close_price],
  ["stop_price", "stop", r => r.stop_price],
  ["target_price", "cible", r => r.target_price],
  ["exit_reason", "sortie", r => r.exit_reason],
  ["gross_pnl", "brut", r => r.gross_pnl],
  ["commission", "comm.", r => r.commission],
  ["swap", "swap", r => r.swap],
  ["net_pnl", "net", r => r.net_pnl],
  ["pnl_r", "R", r => r.pnl_r],
  ["holding_h", "durée", r => r.holding_h],
  ["arm", "arm", r => r.arm],
  ["source", "source", r => r.source],
];

function journalCell(key, r) {
  const v = AN_JOURNAL_COLS.find(c => c[0] === key)[2](r);
  switch (key) {
    case "side": return sideBadge(v);
    case "open_time": case "close_time": return esc(fmtDate(v, "full"));
    case "gross_pnl": case "net_pnl": return signed(v, 2);
    case "commission": case "swap": return esc(fmtNum(v, 2));
    case "pnl_r": return v == null ? "—" : signed(v, 2);
    case "holding_h": return esc(fmtHours(v));
    case "source": return esc(v) + (r.magic_ok === false
      ? ' <span class="badge magic-bad" title="magic ≠ manifeste">magic ≠</span>' : "");
    default: return esc(v == null ? "—" : v);
  }
}

function journalRows() {
  const j = AN.journal;
  let rows = (j.data && j.data.rows) ? j.data.rows.slice() : [];
  const q = j.q.trim().toLowerCase();
  if (q) {
    rows = rows.filter(r => [r.instance_id, r.symbol, r.signal_reason]
      .some(v => v != null && String(v).toLowerCase().includes(q)));
  }
  if (j.sort) {
    const col = AN_JOURNAL_COLS.find(c => c[0] === j.sort);
    if (col) {
      rows.sort((a, b) => {
        const va = col[2](a), vb = col[2](b);
        if (va == null && vb == null) return 0;
        if (va == null) return 1;
        if (vb == null) return -1;
        const na = Number(va), nb = Number(vb);
        const cmp = (!isNaN(na) && !isNaN(nb) && typeof va !== "boolean")
          ? na - nb : String(va).localeCompare(String(vb));
        return cmp * j.dir;
      });
    }
  }
  return rows;
}

function tradesJournal() {
  const j = AN.journal, el = document.getElementById("journal-content");
  if (!el) return;
  const total = j.data ? (j.data.total || 0) : 0;
  const rows = journalRows();
  const range = document.getElementById("journal-range");
  if (range) {
    const first = total ? (j.page - 1) * j.limit + 1 : 0;
    const last = Math.min(total, j.page * j.limit);
    range.textContent = total ? first + "–" + last + " / " + fmtNum(total, 0) : "0 / 0";
  }
  const prev = document.getElementById("journal-prev"), next = document.getElementById("journal-next");
  if (prev) prev.disabled = j.page <= 1;
  if (next) next.disabled = j.page * j.limit >= total;
  if (!j.data) { el.innerHTML = '<div class="subtitle">chargement…</div>'; return; }
  if (!rows.length) { el.innerHTML = '<div class="subtitle">aucun trade sur cette page</div>'; return; }
  el.innerHTML = '<div class="scroll-x"><table class="grid journal"><tr>' +
    AN_JOURNAL_COLS.map(c => '<th class="sortable' + (j.sort === c[0] ? " sorted" : "") +
      '" data-sort="' + c[0] + '">' + esc(c[1]) +
      (j.sort === c[0] ? (j.dir > 0 ? " ▲" : " ▼") : "") + "</th>").join("") + "</tr>" +
    rows.map(r => '<tr title="' + esc(r.signal_reason || "") + '">' +
      AN_JOURNAL_COLS.map(c => "<td>" + journalCell(c[0], r) + "</td>").join("") + "</tr>").join("") +
    "</table></div>";
}

function installJournalControls() {
  const search = document.getElementById("journal-search");
  if (search) search.addEventListener("input", () => { AN.journal.q = search.value; tradesJournal(); });
  const prev = document.getElementById("journal-prev"), next = document.getElementById("journal-next");
  if (prev) prev.addEventListener("click", () => {
    if (AN.journal.page > 1) { AN.journal.page -= 1; refreshJournal(); }
  });
  if (next) next.addEventListener("click", () => { AN.journal.page += 1; refreshJournal(); });
  const content = document.getElementById("journal-content");
  if (content) content.addEventListener("click", e => {
    const th = e.target instanceof Element ? e.target.closest("th[data-sort]") : null;
    if (!th) return;
    const key = th.dataset.sort;
    if (AN.journal.sort === key) AN.journal.dir = -AN.journal.dir;
    else { AN.journal.sort = key; AN.journal.dir = 1; }
    tradesJournal();
  });
}

async function refreshJournal() {
  const j = AN.journal;
  const qs = filtersQuery(AN.filters) + "&page=" + j.page + "&limit=" + j.limit;
  const seq = ++j.reqSeq;
  const res = await fetchJSON("/api/analytics/trades?" + qs);
  if (!res || seq !== j.reqSeq) return;
  if (res.status !== 200) {
    j.data = { total: 0, rows: [] };
    j.lastText = null;
    const el = document.getElementById("journal-content");
    if (el) el.innerHTML = '<div class="err-line">' + esc((res.body && res.body.error) || ("réponse " + res.status)) + "</div>";
    return;
  }
  const txt = payloadText(res.body);
  if (txt === j.lastText) return;
  j.lastText = txt;
  j.data = res.body;
  /* le serveur borne page/limit (D-AN-15) : la pagination suit ses valeurs */
  if (Number(res.body.page) >= 1) j.page = Number(res.body.page);
  if (Number(res.body.limit) >= 1) j.limit = Number(res.body.limit);
  tradesJournal();
}

/* ── rendu de la page ── */
function renderHeader(data) {
  const h = data.header || {};
  const base = h.base && typeof h.base === "object" ? Object.keys(h.base).sort()
    .map(c => fmtNum(h.base[c], 0) + " " + c).join(", ") : "";
  const ccys = Object.keys(data.by_currency || {}).sort().join(", ") || "—";
  const parts = [h.mode || (AN.filters && AN.filters.mode) || "—",
    (h.n_strategies || 0) + " stratégie" + (h.n_strategies > 1 ? "s" : ""),
    (h.n_instances || 0) + " instance" + (h.n_instances > 1 ? "s" : ""),
    ccys, "capital initial " + (base || "inconnu"),
    (h.n_trades || 0) + " trades clos", "source " + (h.source_kind || "—")];
  const el = document.getElementById("an-header");
  if (el) el.textContent = parts.join(" · ");
  const s = data.source || {};
  const studies = s.studies || {};
  const stTxt = Object.keys(studies).sort().map(k => {
    const st = studies[k] || {};
    return k + " " + (st.strategy_id || "?") + " (" + (st.closed || 0) + " clos, " +
      (st.open || 0) + " ouv., chaîne " + (st.chain_ok === false ? "ROMPUE" : "ok") + ")";
  }).join(" · ");
  const src = document.getElementById("an-source");
  if (src) src.textContent = "ledger " + (s.ledger_present === false ? "absent" : (s.ledger_rows || 0) + " lignes") +
    " · journaux " + (s.journal_rows || 0) + " lignes · dédoublonnés " + (s.dedup || 0) +
    (stTxt ? " · " + stTxt : "");
}

function renderWarnings(data) {
  const el = document.getElementById("warnings-content");
  if (!el) return;
  const w = data.warnings || [];
  el.innerHTML = w.length
    ? w.map(x => '<div class="warn-line">' + esc(x) + "</div>").join("")
    : '<div class="subtitle">aucun avertissement</div>';
}

function currencyBlock(ccy, inner) {
  return '<div class="ccy-block"><div class="ccy-title">' + esc(ccy) + "</div>" + inner + "</div>";
}

function renderPerformance(data) {
  const el = document.getElementById("performance-content");
  if (!el) return;
  const showB = document.getElementById("show-balance"), showD = document.getElementById("show-drawdown");
  const wantB = !showB || showB.checked, wantD = !showD || showD.checked;
  const w = chartWidth(el);
  const bc = data.by_currency || {};
  const ccys = Object.keys(bc).sort();
  if (!ccys.length) { el.innerHTML = '<div class="subtitle">aucun trade clos pour ces filtres</div>'; return; }
  el.innerHTML = ccys.map(ccy => {
    const c = bc[ccy] || {}, curve = c.curve || {};
    const pts = curve.points || [];
    let inner = "";
    if (wantB) inner += '<div class="curve-block"><div class="curve-title">solde — base ' +
      esc(curve.base_kind === "capital" ? "capital " + fmtMoney(curve.base, ccy, 0) : "zéro (cumul net)") +
      (curve.decimated ? " · décimé (dernier solde du jour)" : "") + "</div>" +
      lineChart(pts, w, 260, { base: curve.base != null ? curve.base : 0, ccy: ccy }) + "</div>";
    if (wantD) inner += '<div class="curve-block"><div class="curve-title">drawdown (relatif au pic)</div>' +
      areaChart(pts, w, 160, { ccy: ccy }) + "</div>";
    if (!wantB && !wantD) inner = '<div class="subtitle chart-empty">rien à tracer</div>';
    return currencyBlock(ccy, inner);
  }).join("");
  animateLines(el);
}

function renderHeatmap(data) {
  const el = document.getElementById("heatmap-content");
  if (!el) return;
  const w = chartWidth(el);
  const bc = data.by_currency || {}, ccys = Object.keys(bc).sort();
  if (!ccys.length) { el.innerHTML = '<div class="subtitle">aucun trade clos pour ces filtres</div>'; return; }
  el.innerHTML = ccys.map(ccy => {
    const c = bc[ccy] || {};
    const months = (c.by_month || []).map(m => ({
      label: String(m.month || "").replace(/^(\d\d)(\d\d)-(\d\d)$/, "$2.$3"),
      value: m.net || 0,
      tip: monthLabel(m.month) + " · " + fmtSigned(m.net, 2, ccy) + " · " + nTrades(m.n_trades) +
        (m.sum_r != null ? " · " + fmtSigned(m.sum_r, 2, "R") : ""),
    }));
    return currencyBlock(ccy, heatmapTable(c.heatmap, ccy) +
      '<div class="curve-block"><div class="curve-title">P&L par mois</div>' +
      barChart(months, w, 180, { labelEvery: 2 }) + "</div>");
  }).join("");
}

function monthLabel(ym) {
  const m = /^(\d{4})-(\d{2})$/.exec(String(ym || ""));
  if (!m) return String(ym || "—");
  return (AN_MONTHS[Number(m[2]) - 1] || m[2]) + " " + m[1];
}

function renderInstances(data) {
  const el = document.getElementById("instances-content");
  if (!el) return;
  const w = chartWidth(el);
  const bc = data.by_currency || {}, ccys = Object.keys(bc).sort();
  if (!ccys.length) { el.innerHTML = '<div class="subtitle">aucun trade clos pour ces filtres</div>'; return; }
  el.innerHTML = ccys.map(ccy => {
    const rows = ((bc[ccy] || {}).by_instance || []).slice()
      .sort((a, b) => (b.net || 0) - (a.net || 0));
    if (!rows.length) return currencyBlock(ccy, '<div class="subtitle">aucune instance</div>');
    const items = rows.map(r => {
      const name = r.instance || r.instance_id || r.symbol || "?";
      return { label: name, value: r.net || 0,
        right: fmtSigned(r.net, 2) + " · " + (r.n_trades || 0) + " · " + fmtPct(r.win_rate, 0),
        tip: name + " · " + fmtSigned(r.net, 2, ccy) + " · " + nTrades(r.n_trades) + " · win " +
          fmtPct(r.win_rate, 0) };
    });
    const table = '<details><summary>tableau par instance</summary><table class="grid"><tr>' +
      "<th>instance</th><th>symbole</th><th>trades</th><th>taux</th><th>net</th><th>PF</th>" +
      "<th>Σ R</th><th>DD max</th></tr>" +
      rows.map(r => "<tr><td>" + esc(r.instance || r.instance_id || "—") + "</td><td>" + esc(r.symbol || "—") +
        "</td><td>" + esc(r.n_trades || 0) + "</td><td>" + esc(fmtPct(r.win_rate, 1)) + "</td><td>" +
        signed(r.net, 2) + "</td><td>" + esc(r.profit_factor == null ? "∞" : fmtNum(r.profit_factor, 2)) +
        "</td><td>" + signed(r.sum_r, 2, "R") + "</td><td>" + esc(fmtNum(r.max_drawdown, 2)) +
        "</td></tr>").join("") + "</table></details>";
    return currencyBlock(ccy, barChart(items, w, 0, { horizontal: true }) + table);
  }).join("");
}

function renderStrategies(data) {
  const el = document.getElementById("strategies-content");
  if (!el) return;
  const w = chartWidth(el);
  const bc = data.by_currency || {}, ccys = Object.keys(bc).sort();
  if (!ccys.length) { el.innerHTML = '<div class="subtitle">aucun trade clos pour ces filtres</div>'; return; }
  el.innerHTML = ccys.map(ccy => {
    const rows = (bc[ccy] || {}).by_strategy || [];
    if (!rows.length) return currencyBlock(ccy, '<div class="subtitle">aucune stratégie</div>');
    const items = rows.map(r => {
      const sid = r.strategy_id || "?";
      const label = r.display_name && r.display_name !== sid ? sid + " · " + r.display_name : sid;
      return { label: label, value: r.net || 0,
        tip: label + " · " + fmtSigned(r.net, 2, ccy) + " · " + nTrades(r.n_trades) +
          (r.sum_r != null ? " · " + fmtSigned(r.sum_r, 2, "R") : ""),
        stack: (r.instances || []).map(i => {
          const name = i.instance || i.instance_id || i.symbol || "?";
          return { label: name, value: i.net || 0,
            tip: label + " › " + name + " · " + fmtSigned(i.net, 2, ccy) + " · " + nTrades(i.n_trades) };
        }) };
    });
    return currencyBlock(ccy, barChart(items, w, 220, { stacked: true }));
  }).join("");
}

function renderWeekdayHour(data) {
  const elW = document.getElementById("weekday-content"), elH = document.getElementById("hour-content");
  const bc = data.by_currency || {}, ccys = Object.keys(bc).sort();
  const empty = '<div class="subtitle">aucun trade clos pour ces filtres</div>';
  if (elW) {
    const w = chartWidth(elW);
    elW.innerHTML = ccys.length ? ccys.map(ccy => {
      const by = {};
      ((bc[ccy] || {}).by_weekday || []).forEach(r => { by[r.weekday] = r; });
      const items = AN_WEEKDAY_ORDER.map(d => {
        const r = by[d] || {};
        return { label: AN_WEEKDAYS[d], value: r.net || 0,
          tip: AN_WEEKDAYS[d] + " · " + fmtSigned(r.net || 0, 2, ccy) + " · " + nTrades(r.n_trades) +
            " · win " + fmtPct(r.win_rate, 0) + (r.sum_r != null ? " · " + fmtSigned(r.sum_r, 2, "R") : "") };
      });
      return currencyBlock(ccy, barChart(items, w, 180, {}));
    }).join("") : empty;
  }
  if (elH) {
    const w = chartWidth(elH);
    elH.innerHTML = ccys.length ? ccys.map(ccy => {
      const by = {};
      ((bc[ccy] || {}).by_hour || []).forEach(r => { by[Number(r.hour != null ? r.hour : r.key)] = r; });
      const items = [];
      for (let h = 0; h < 24; h++) {
        const r = by[h] || {};
        items.push({ label: pad2(h) + "h", value: r.net || 0,
          tip: pad2(h) + ":00 · " + fmtSigned(r.net || 0, 2, ccy) + " · " + nTrades(r.n_trades) +
            " · win " + fmtPct(r.win_rate, 0) });
      }
      return currencyBlock(ccy, barChart(items, w, 180, { labelEvery: 2 }));
    }).join("") : empty;
  }
}

function binLabel(b, unit) {
  if (b.lo == null) return "< " + fmtNum(b.hi, unit === "r" ? 1 : 0);
  if (b.hi == null) return "≥ " + fmtNum(b.lo, unit === "r" ? 1 : 0);
  return fmtNum(b.lo, unit === "r" ? 1 : 0);
}

function renderDistribution(data) {
  const el = document.getElementById("distribution-content");
  if (!el) return;
  const w = chartWidth(el);
  const bc = data.by_currency || {}, ccys = Object.keys(bc).sort();
  if (!ccys.length) { el.innerHTML = '<div class="subtitle">aucun trade clos pour ces filtres</div>'; return; }
  el.innerHTML = ccys.map(ccy => {
    const d = (bc[ccy] || {}).distribution || {};
    const unit = d.unit || "r", bins = d.bins || [];
    const items = bins.map(b => ({ label: binLabel(b, unit), value: b.n || 0,
      tip: (b.lo == null ? "< " + fmtNum(b.hi, 2) : b.hi == null ? "≥ " + fmtNum(b.lo, 2)
        : "[" + fmtNum(b.lo, 2) + ", " + fmtNum(b.hi, 2) + ")") + (unit === "r" ? " R" : " " + ccy) +
        " · " + nTrades(b.n) }));
    return currencyBlock(ccy, barChart(items, w, 180, { plain: true, labelEvery: 2 }) +
      '<div class="subtitle">unité ' + esc(unit === "r" ? "R" : ccy) +
      (d.n_without_r ? " · " + esc(d.n_without_r) + " trade(s) sans R" : "") + "</div>");
  }).join("");
}

function renderSummary(data) {
  const el = document.getElementById("summary-content");
  if (!el) return;
  const bc = data.by_currency || {}, ccys = Object.keys(bc).sort();
  if (!ccys.length) { el.innerHTML = '<div class="subtitle">aucun trade clos pour ces filtres</div>'; return; }
  el.innerHTML = ccys.map(ccy => currencyBlock(ccy, summaryBlock((bc[ccy] || {}).summary, ccy))).join("");
}

function renderKpi(data) {
  const el = document.getElementById("kpi");
  if (!el) return;
  const bc = data.by_currency || {}, ccys = Object.keys(bc).sort();
  el.innerHTML = ccys.length
    ? ccys.map(ccy => (ccys.length > 1 ? '<div class="ccy-title">' + esc(ccy) + "</div>" : "") +
        '<div class="tiles">' + kpiTiles((bc[ccy] || {}).kpi, ccy, false) + "</div>").join("")
    : '<div class="tiles">' + kpiTiles({}, "", false) + "</div>";
}

function renderAnalytics(data) {
  AN.charts = {};
  renderHeader(data);
  const fb = document.getElementById("filters");
  if (fb) {
    refreshFilterOptions(fb, (data.filters || {}).options || {});
    fb.classList.remove("busy");
  }
  renderKpi(data);
  renderPerformance(data);
  renderHeatmap(data);
  renderInstances(data);
  renderStrategies(data);
  renderWeekdayHour(data);
  renderDistribution(data);
  renderSummary(data);
  renderOpenPositions(data);
  renderWarnings(data);
  AN.animate = false;
}

/* Section « positions ouvertes » (AN-30) : rendue à part — `age_h` vit
 * (heures depuis l'ouverture, 2 décimales) et ne doit pas déclencher le
 * re-rendu complet de la page à chaque tick. */
function renderOpenPositions(data) {
  const op = document.getElementById("open-positions-content");
  if (op) op.innerHTML = openPositions(data.open_positions);
}

/* Tick de la page : un fetch, re-rendu seulement si le JSON diffère (AN-3),
 * puis le journal. force = changement de filtres. */
async function refreshAnalytics(force) {
  const qs = filtersQuery(AN.filters);
  const seq = ++AN.reqSeq;
  const res = await fetchJSON("/api/analytics?" + qs);
  if (!res || seq !== AN.reqSeq) return;   /* réponse périmée : un fetch plus récent est parti */
  if (res.status !== 200) {
    const el = document.getElementById("warnings-content");
    if (el) el.innerHTML = '<div class="err-line">' + esc((res.body && res.body.error) || ("réponse " + res.status)) + "</div>";
    const fb = document.getElementById("filters");
    if (fb) fb.classList.remove("busy");
    return;
  }
  setStamp(res.body);
  const txt = payloadText(res.body);
  if (force || txt !== AN.lastText) {
    AN.lastText = txt;
    AN.data = res.body;
    renderAnalytics(res.body);
  } else if (AN.data) {
    AN.data.open_positions = res.body.open_positions;   /* âges à jour, rien d'autre ne bouge */
    renderOpenPositions(AN.data);
  }
  await refreshJournal();
}

/* Texte de comparaison d'un payload (AN-3 / D-AN-14) : `generated` change à
 * chaque requête (horodatage UTC à la seconde) — il est retiré avant
 * JSON.stringify, sinon le garde « re-rendu seulement si le JSON diffère »
 * ne bloque jamais rien et le DOM est reconstruit toutes les 10 s. */
function payloadText(body) {
  const rest = Object.assign({}, body);
  delete rest.generated;
  if (Array.isArray(rest.open_positions)) {
    /* age_h avance à chaque tick : comparé sans lui (section rendue à part) */
    rest.open_positions = rest.open_positions.map(p => Object.assign({}, p, { age_h: undefined }));
  }
  return JSON.stringify(rest);
}

function debounce(fn, ms) {
  let t = null;
  return () => { clearTimeout(t); t = setTimeout(fn, ms); };
}

function bootAnalytics() {
  AN.filters = filtersFromUrl();
  pushFiltersToUrl();
  filterBar(document.getElementById("filters"));
  installTooltips();
  installJournalControls();
  ["show-balance", "show-drawdown"].forEach(id => {
    const cb = document.getElementById(id);
    if (cb) cb.addEventListener("change", () => { if (AN.data) renderPerformance(AN.data); });
  });
  window.addEventListener("resize", debounce(() => { if (AN.data) renderAnalytics(AN.data); }, 250));
  /* AN-27 : un panneau d'options ouvert ne doit pas rester au-dessus des
   * tuiles — clic hors du <details> = fermeture. */
  document.addEventListener("click", e => {
    document.querySelectorAll(".filters .fsel[open]").forEach(d => {
      if (!d.contains(e.target)) d.removeAttribute("open");
    });
  });
  poll(() => refreshAnalytics(false), 10000);   /* 10 s (AN-3) */
}

/* ── bandeau KPI de la vue d'ensemble (AN-31) ── */
let indexKpiText = null;

async function refreshIndexKpi() {
  const el = document.getElementById("kpi-band");
  if (!el) return;
  let body = null;
  try {
    const r = await fetch("/api/analytics/kpi");
    if (r.ok) body = await r.json();
  } catch (e) {
    body = null;          /* le bandeau est un bonus : /api/state porte déjà l'état */
  }
  if (!body) { el.innerHTML = ""; indexKpiText = null; return; }
  const txt = payloadText(body);
  if (txt === indexKpiText) return;
  indexKpiText = txt;
  let html = "";
  ["LIVE", "PAPER"].forEach(mode => {
    const byCcy = body[mode] || {};
    Object.keys(byCcy).sort().forEach(ccy => {
      const k = byCcy[ccy] || {};
      if (!k.total_trades) return;
      html += '<section class="panel kpi-band ' + (mode === "LIVE" ? "live" : "") + '"><h2>' +
        esc(mode) + " · " + esc(ccy) + ' <a href="/analytics?mode=' + esc(mode) + '">analyse</a></h2>' +
        '<div class="kpi-tiles"><div class="tiles">' + kpiTiles(k, ccy, true) + "</div></div></section>";
    });
  });
  el.innerHTML = html;
}

/* ── boot ─────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "index") {
    poll(refreshIndex, 5000);          /* UI-8: 5 s */
    poll(refreshIndexKpi, 10000);      /* AN-31: bandeau KPI, 10 s */
  }
  else if (page === "strategy") poll(refreshStrategy, 5000);
  else if (page === "services") poll(refreshServices, 10000); /* 10 s */
  else if (page === "analytics") bootAnalytics();             /* 10 s (AN-3) */
});
