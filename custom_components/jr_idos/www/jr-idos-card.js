const CARD_VERSION = "1.0.1";
const BASE_URL = "/jr_idos";
const T_CACHE = {};

const WARN_MIN = 15, ALERT_MIN = 8;

const TYPE_COLOR = {
  bus: "#2e9e4f",
  vlak: "#2f6fd0",
  tram: "#d2554d",
  trol: "#d4a017",
  metro: "#8e44ad",
};
const DEFAULT_COLOR = "#2f6fd0";

const DEFAULTS = {
  line: "Line",
  departure: "Depart",
  minutes: "{min} min",
  departure_in: "Departs in",
  no_connections: "No connections.",
  unavailable: "Entity unavailable.",
  entity_label: "Main route entity",
};

const TYPE_ICON = {
  bus: "mdi:bus",
  vlak: "mdi:train",
  tram: "mdi:tram",
  trol: "mdi:bus-electric",
  metro: "mdi:subway-variant",
};
const DEFAULT_ICON = "mdi:bus-clock";

async function loadTexts(lang) {
  const code = (lang || "en").split("-")[0];
  if (!T_CACHE[code]) {
    T_CACHE[code] = fetch(`${BASE_URL}/translations/${code}.json?v=${CARD_VERSION}`)
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);
  }
  const texts = await T_CACHE[code];
  return texts || (code !== "en" ? loadTexts("en") : {});
}

function tr(texts, key, vars = {}) {
  let s = texts?.[key] ?? DEFAULTS[key] ?? key;
  for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, v);
  return s;
}

function hashColor(str) {
  let h = 0;
  for (const c of str || "") h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return 30 + (h % 300);
}

const minsTo = (ts, now) => Math.max(0, Math.ceil((ts * 1000 - now) / 60000));

const userLang = (hass) => hass?.locale?.language || hass?.language;

const vehicleColor = (name) => TYPE_COLOR[(name || "").toLowerCase()] ?? DEFAULT_COLOR;

const vehicleIcon = (v) => {
  const key = Object.keys(TYPE_ICON).find((k) => (v || "").toLowerCase().startsWith(k));
  return TYPE_ICON[key] || DEFAULT_ICON;
};

class OdjezdyCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("jr-idos-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find(
      (e) => e.startsWith("sensor.") && Array.isArray(hass.states[e].attributes.spoje)
    );
    return { entity: entity || "" };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._timer = null;
    this._hass = null;
    this._config = null;
    this._t = {};
    this._lang = null;
  }

  setConfig(config) {
    if (!config || !config.entity) throw new Error("Chybí 'entity'.");
    this._config = { mode: "board", ...config };
    this._render();
  }

  set hass(hass) {
    const old = this._hass?.states[this._config?.entity];
    this._hass = hass;
    if (old !== hass.states[this._config?.entity]) this._render();
    this._loadLang();
  }

  async _loadLang() {
    const lang = userLang(this._hass);
    if (!lang || lang === this._lang) return;
    this._lang = lang;
    this._t = await loadTexts(lang);
    this._render();
  }

  getCardSize() {
    const n = this._entity()?.attributes.spoje?.length ?? 3;
    return 3 + n;
  }

  connectedCallback() {
    const tick = () => {
      this._render();
      this._timer = setTimeout(tick, 60000 - (Date.now() % 60000) + 500);
    };
    tick();
  }

  disconnectedCallback() {
    clearTimeout(this._timer);
    this._timer = null;
  }

  _entity() {
    return this._hass?.states[this._config?.entity];
  }

  // gradient podle pořadí: první spoj nejsytější, další blednou
  _color(i, n, vehicle) {
    const mix = n > 1 ? (i / (n - 1)) * 25 : 0; // 0 % až 25 % bílé
    return `color-mix(in srgb, ${vehicleColor(vehicle)}, white ${mix}%)`;
  }

  _hue() {
    return hashColor(this._config.entity);
  }

  _render() {
    if (!this._config || !this._hass) return;
    const st = this._entity();
    const root = this.shadowRoot;

    if (!st || st.state === "unavailable") {
      const name = st?.attributes?.friendly_name || this._config.entity;
      root.innerHTML = `<ha-card><div class="empty"><b>${name}</b><br>${tr(this._t, "unavailable")}</div></ha-card>${STYLE}`;
      return;
    }

    const a = st.attributes;
    const now = Date.now();
    const offset = Number(a.offset) || 0;
    const spoje = (a.spoje || []).filter((s) => s.odjezd_ts * 1000 > now - 60000);
    const n = spoje.length;

    // pruh se plní od (WARN_MIN + offset) do (offset) minut před odjezdem
    let progress = "";
    const first = spoje[0];
    if (first) {
      const mins = minsTo(first.odjezd_ts, now);
      const remaining = mins - offset;
      const p = Math.min(100, Math.max(0, ((WARN_MIN - remaining) / WARN_MIN) * 100));
      const cls = mins < ALERT_MIN + offset ? "red" : mins < WARN_MIN + offset ? "orange" : "";
      progress = `<div class="bar"><div class="${cls}" style="width:${p}%"></div></div>`;
    }
    const headIcon = first ? vehicleIcon(first.prostredek) : DEFAULT_ICON;

    const rows = spoje
      .map((s, i) => {
        const mins = minsTo(s.odjezd_ts, now);

        let cls = "";
        if (i === 0) {
          if (mins < ALERT_MIN + offset) cls = "red";
          else if (mins < WARN_MIN + offset) cls = "orange";
        }

        const text =
          mins >= 60
            ? `${Math.floor(mins / 60)}:${String(mins % 60).padStart(2, "0")} h`
            : tr(this._t, "minutes", { min: mins });
        const eta = `<span class="pill ${cls}">${text}</span>`;

        return `
          <tr class="row">
            <td class="vehicle">${s.prostredek || ""}</td>
            <td class="line"><span class="badge" title="${s.linka || ""}" style="background:${this._color(i, n, s.prostredek)}">${s.linka || ""}</span></td>
            <td class="time">${s.odjezd}</td>
            <td class="eta">${eta}</td>
          </tr>`;
      })
      .join("");

    const strip = this._config.color_strip
      ? `style="--route-color:hsl(${this._hue()},50%,65%)"`
      : "";

    root.innerHTML = `
      <ha-card class="${this._config.color_strip ? "striped" : ""}" ${strip}>
        <div class="head">
          <div class="title">
            <ha-icon class="vi" icon="${headIcon}"></ha-icon>
            <span class="ttext">${a.vychozi || ""} → ${a.cilova || ""}</span>
          </div>
        </div>
        <table>
          <tr class="cols">
            <th></th><th></th>
            <th class="time">${tr(this._t, "departure")}</th>
            <th class="eta">${tr(this._t, "departure_in")}</th>
          </tr>
          ${progress ? `<tr class="barrow"><td colspan="4">${progress}</td></tr>` : ""}
          ${rows || `<tr><td colspan="4" class="empty">${tr(this._t, "no_connections")}</td></tr>`}
        </table>
      </ha-card>${STYLE}`;
  }
}

const STYLE = `<style>
  .head { padding: 12px 16px 4px; font-weight: 500; color: var(--primary-text-color); display: flex; align-items: center; gap: 6px; }
  .head .vi { --mdc-icon-size: 20px; flex: none; color: var(--secondary-text-color); }
  .head .ttext { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .title { display: flex; align-items: center; gap: 6px; }
  .vi { --mdc-icon-size: 20px; flex: none; color: var(--secondary-text-color); }

  table { width: 100%; border-collapse: collapse; }
  td, th { padding: 8px 6px; white-space: nowrap; font-weight: inherit; text-align: left; vertical-align: middle; }
  tr > :first-child { padding-left: 16px; }
  tr > :last-child { padding-right: 16px; }

  .cols th { padding-top: 0; padding-bottom: 4px; font-size: 0.8em; font-weight: 400;
             color: var(--secondary-text-color); }
  .cols th.time, .cols th.eta { text-align: right; }
  .cols th.eta { padding-right: 26px; }

  .row { border-top: 1px solid var(--divider-color); color: var(--primary-text-color); }
  .barrow td { padding: 0; }
  .barrow + .row { border-top: none; }

  .vehicle { color: var(--secondary-text-color); padding-right: 0; }
  .line { width: 100%; max-width: 0; }
  .badge { display: inline-block; min-width: 36px; max-width: 100%; box-sizing: border-box;
           text-align: center; padding: 2px 8px; border-radius: 6px; color: #fff; vertical-align: middle;
           font-weight: 700; overflow: hidden; text-overflow: ellipsis; }
  .time { text-align: right; color: var(--secondary-text-color); }
  .eta { text-align: right; font-weight: 500; }

  .pill { display: inline-block; padding: 2px 10px; border-radius: 6px; font-weight: 700; }
  .pill.orange { background: var(--warning-color, #ff9800); color: #fff; }
  .pill.red { background: var(--error-color, #db4437); color: #fff; }

  .bar { height: 4px; background: var(--divider-color); overflow: hidden; }
  .bar div { height: 100%; background: var(--primary-color); transition: width 1s linear; }
  .bar div.orange { background: var(--warning-color, #ff9800); }
  .bar div.red { background: var(--error-color, #db4437); }

  .empty { padding: 16px; color: var(--secondary-text-color); }
  .empty b { color: var(--primary-text-color); }
  ha-card.striped { border-left: 8px solid var(--route-color); }
</style>`;

class OdjezdyCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._t) {
      this._t = {};
      loadTexts(userLang(hass)).then((t) => {
        this._t = t;
        if (this._form) this._form.computeLabel = () => tr(this._t, "entity_label");
        this._render();
      });
    }
    if (this._form) this._form.hass = hass;
    else this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      const ids = Object.keys(this._hass.states).filter((id) => id.startsWith("sensor.") && Array.isArray(this._hass.states[id].attributes?.spoje));
      this._form.schema = [
        {
          name: "entity",
          required: true,
          selector: { entity: { domain: "sensor", integration: "jr_idos", include_entities: ids } },
        },
        { name: "color_strip", selector: { boolean: {} } },
      ];
      this._form.computeLabel = (schema) => tr(this._t, schema.name === "color_strip" ? "color_strip" : "entity_label");
      this._form.addEventListener("value-changed", (e) =>
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: e.detail.value },
            bubbles: true,
            composed: true,
          })
        )
      );
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
  }
}

customElements.define("jr-idos-card", OdjezdyCard);
customElements.define("jr-idos-card-editor", OdjezdyCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "jr-idos-card",
  name: "Odjezdy spojů IDOS",
  description: "Odjezdy z integrace jr_idos s odpočtem.",
  preview: false,
});
console.info(
  `%c JR-IDOS-CARD %c ${CARD_VERSION}`,
  "background:#0000FF;color:#fff",
  ""
);