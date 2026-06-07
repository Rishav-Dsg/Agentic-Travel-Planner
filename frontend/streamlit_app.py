"""
Agentic AI Travel Planner — Streamlit frontend.

Run with:
    streamlit run frontend.py
"""

import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000/api/plan-trip"

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Voyage — AI Travel Planner",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400&family=Outfit:wght@300;400;500&display=swap');

/* ── Root variables ── */
:root {
    --ink:       #0d0d0d;
    --paper:     #faf8f3;
    --gold:      #c9a84c;
    --gold-dim:  #8a6f32;
    --sand:      #e8e0d0;
    --mist:      #f0ece4;
    --smoke:     #6b6560;
    --red:       #c0392b;
    --green:     #2e7d5e;
    --radius:    2px;
}

/* ── Global reset ── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--ink) !important;
    color: var(--paper) !important;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse at 20% 0%, #1a1208 0%, transparent 60%),
        radial-gradient(ellipse at 80% 100%, #0f1a14 0%, transparent 60%),
        var(--ink) !important;
    min-height: 100vh;
}

[data-testid="stHeader"],
[data-testid="stToolbar"],
footer { display: none !important; }

/* ── Typography ── */
h1, h2, h3 { font-family: 'Cormorant Garamond', serif !important; }
p, li, span, label, div { font-family: 'Outfit', sans-serif !important; }
code, pre { font-family: 'DM Mono', monospace !important; }

/* ── Masthead ── */
.masthead {
    text-align: center;
    padding: 4rem 2rem 2rem;
    border-bottom: 1px solid #2a2520;
    margin-bottom: 3rem;
    position: relative;
}
.masthead::before {
    content: '';
    position: absolute;
    top: 0; left: 50%; transform: translateX(-50%);
    width: 1px; height: 3rem;
    background: linear-gradient(to bottom, transparent, var(--gold));
}
.masthead-tag {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 1rem;
}
.masthead-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: clamp(3.5rem, 8vw, 6rem);
    font-weight: 300;
    line-height: 0.95;
    letter-spacing: -0.02em;
    color: var(--paper);
    margin: 0 0 0.5rem;
}
.masthead-title em {
    font-style: italic;
    color: var(--gold);
}
.masthead-sub {
    font-family: 'Outfit', sans-serif;
    font-weight: 300;
    font-size: 0.85rem;
    color: var(--smoke);
    letter-spacing: 0.05em;
}

/* ── Form panel ── */
.form-panel {
    background: #111009;
    border: 1px solid #2a2520;
    border-radius: var(--radius);
    padding: 2.5rem;
    margin-bottom: 2rem;
}
.form-section-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: var(--gold-dim);
    margin-bottom: 1.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #2a2520;
}

/* ── Streamlit widget overrides ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: #0d0c09 !important;
    border: 1px solid #2a2520 !important;
    border-radius: var(--radius) !important;
    color: var(--paper) !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 1rem !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 1px var(--gold-dim) !important;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stMultiSelect"] label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    color: var(--smoke) !important;
}

/* Multiselect */
[data-testid="stMultiSelect"] > div > div {
    background: #0d0c09 !important;
    border: 1px solid #2a2520 !important;
    border-radius: var(--radius) !important;
}
[data-baseweb="tag"] {
    background: #1e1a10 !important;
    border: 1px solid var(--gold-dim) !important;
    border-radius: 1px !important;
}
[data-baseweb="tag"] span {
    color: var(--gold) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
}

/* ── Generate button ── */
[data-testid="stButton"] button {
    background: transparent !important;
    border: 1px solid var(--gold) !important;
    color: var(--gold) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.25em !important;
    text-transform: uppercase !important;
    padding: 0.85rem 3rem !important;
    border-radius: var(--radius) !important;
    width: 100% !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
}
[data-testid="stButton"] button:hover {
    background: var(--gold) !important;
    color: var(--ink) !important;
}

/* ── Result sections ── */
.section-rule {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 3rem 0 1.5rem;
}
.section-rule-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: var(--gold);
    white-space: nowrap;
}
.section-rule-line {
    flex: 1;
    height: 1px;
    background: #2a2520;
}

/* ── Summary block ── */
.summary-block {
    background: #111009;
    border-left: 3px solid var(--gold);
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
}
.summary-text {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.35rem;
    font-weight: 300;
    line-height: 1.7;
    color: var(--paper);
    font-style: italic;
}

/* ── Metric pills ── */
.metrics-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
}
.metric-pill {
    background: #111009;
    border: 1px solid #2a2520;
    padding: 1rem 1.5rem;
    flex: 1;
    min-width: 140px;
}
.metric-pill-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.55rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--smoke);
    margin-bottom: 0.4rem;
}
.metric-pill-value {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.6rem;
    font-weight: 600;
    color: var(--paper);
}
.metric-pill-value.gold { color: var(--gold); }
.metric-pill-value.green { color: #4caf82; }
.metric-pill-value.red { color: #e05c4b; }

/* ── Budget grid ── */
.budget-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1px;
    background: #2a2520;
    border: 1px solid #2a2520;
    margin-bottom: 2rem;
}
.budget-cell {
    background: #0d0c09;
    padding: 1.25rem 1.5rem;
    text-align: center;
}
.budget-cell-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.55rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--smoke);
    margin-bottom: 0.5rem;
}
.budget-cell-icon { font-size: 1.1rem; margin-bottom: 0.3rem; }
.budget-cell-amount {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.4rem;
    font-weight: 600;
    color: var(--gold);
}
.budget-cell-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    color: var(--smoke);
    margin-top: 0.2rem;
}

/* ── Real-time cost banner ── */
.realtime-banner {
    background: #0d1410;
    border: 1px solid #1e3d2a;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.realtime-dot {
    width: 8px; height: 8px;
    background: #4caf82;
    border-radius: 50%;
    animation: pulse 2s infinite;
    flex-shrink: 0;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}
.realtime-text {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    color: #4caf82;
}

/* ── Day cards ── */
.day-card {
    background: #111009;
    border: 1px solid #2a2520;
    margin-bottom: 1rem;
    overflow: hidden;
}
.day-card-header {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #2a2520;
    cursor: pointer;
}
.day-number {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.5rem;
    font-weight: 300;
    color: var(--gold-dim);
    line-height: 1;
    min-width: 3rem;
}
.day-location {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.2rem;
    font-weight: 400;
    color: var(--paper);
}
.day-activity-count {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    color: var(--smoke);
    margin-left: auto;
}

.activity-item {
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #1a1712;
    display: flex;
    gap: 1rem;
}
.activity-item:last-child { border-bottom: none; }
.activity-marker {
    width: 6px; height: 6px;
    border: 1px solid var(--gold-dim);
    border-radius: 50%;
    margin-top: 0.4rem;
    flex-shrink: 0;
}
.activity-name {
    font-family: 'Outfit', sans-serif;
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--paper);
    margin-bottom: 0.3rem;
}
.activity-desc {
    font-family: 'Outfit', sans-serif;
    font-size: 0.8rem;
    font-weight: 300;
    color: var(--smoke);
    line-height: 1.6;
}

/* ── Budget insufficient ── */
.insufficient-hero {
    background: #1a0a08;
    border: 1px solid #5a2520;
    padding: 2.5rem;
    margin-bottom: 2rem;
    text-align: center;
}
.insufficient-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}
.insufficient-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2rem;
    font-weight: 300;
    color: #e05c4b;
    margin-bottom: 0.5rem;
}
.insufficient-sub {
    font-family: 'Outfit', sans-serif;
    font-size: 0.9rem;
    color: var(--smoke);
}
.cost-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #2a2520;
}
.cost-row:last-child { border-bottom: none; }
.cost-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    color: var(--smoke);
}
.cost-amount {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.1rem;
    color: var(--paper);
}
.suggestion-item {
    background: #0f150d;
    border-left: 2px solid #2e7d5e;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-family: 'Outfit', sans-serif;
    font-size: 0.83rem;
    color: var(--smoke);
    line-height: 1.5;
}

/* ── Spinner override ── */
[data-testid="stSpinner"] { color: var(--gold) !important; }

/* ── Error ── */
[data-testid="stAlert"] {
    background: #1a0a08 !important;
    border: 1px solid #5a2520 !important;
    border-radius: var(--radius) !important;
    color: #e05c4b !important;
    font-family: 'Outfit', sans-serif !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--ink); }
::-webkit-scrollbar-thumb { background: #2a2520; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ── Masthead ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="masthead">
    <div class="masthead-tag">Agentic AI · LangGraph · CrewAI · MCP</div>
    <div class="masthead-title">Voy<em>age</em></div>
    <div class="masthead-sub">Intelligent travel planning powered by autonomous AI agents</div>
</div>
""", unsafe_allow_html=True)


# ── Form ───────────────────────────────────────────────────────────────────────

st.markdown('<div class="form-panel">', unsafe_allow_html=True)
st.markdown('<div class="form-section-label">Plan your journey</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    destination = st.text_input("Destination", value="Tokyo", placeholder="City or country")
    origin = st.text_input("Flying from", value="Delhi", placeholder="Departure city")

with col2:
    budget = st.number_input("Budget (₹)", min_value=1000, max_value=10000000, value=80000, step=1000)
    days = st.number_input("Days", min_value=1, max_value=30, value=5)

with col3:
    interests = st.multiselect(
        "Interests",
        ["anime", "food", "temples", "shopping", "nightlife", "history",
         "nature", "technology", "museums", "adventure", "beaches",
         "art", "architecture", "street food", "hiking", "photography"],
        default=["food", "temples"],
    )

st.markdown("</div>", unsafe_allow_html=True)

generate = st.button("✦  Generate Trip Plan  ✦")


# ── Helpers ────────────────────────────────────────────────────────────────────

def section_rule(label: str):
    st.markdown(f"""
    <div class="section-rule">
        <span class="section-rule-label">{label}</span>
        <span class="section-rule-line"></span>
    </div>
    """, unsafe_allow_html=True)


def metric_pill(label: str, value: str, cls: str = ""):
    return f"""
    <div class="metric-pill">
        <div class="metric-pill-label">{label}</div>
        <div class="metric-pill-value {cls}">{value}</div>
    </div>"""


BUDGET_ICONS = {
    "flight": ("✈", "Round-trip flight"),
    "hotel": ("🏨", "Accommodation"),
    "food": ("🍜", "Food & dining"),
    "transport": ("🚇", "Local transport"),
    "misc": ("🎒", "Miscellaneous"),
}


def render_travel_plan(result: dict):
    """Renders a successful TravelPlan response."""

    # ── Summary ────────────────────────────────────────────────────────────────
    section_rule("Trip Overview")
    st.markdown(f"""
    <div class="summary-block">
        <div class="summary-text">{result.get('trip_summary', '')}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metrics row ────────────────────────────────────────────────────────────
    weather = result.get("weather_condition", "—")
    score   = result.get("evaluation_score")
    reason  = result.get("evaluation_reason", "")

    score_cls = "green" if score and score >= 7 else ("red" if score and score < 5 else "gold")
    score_str = f"{score}/10" if score else "—"
    weather_icon = {"Sunny": "☀", "Rainy": "🌧", "Hot": "🌡", "Cold": "❄"}.get(weather, "🌤")

    pills_html = '<div class="metrics-row">'
    pills_html += metric_pill("Weather", f"{weather_icon}  {weather}")
    pills_html += metric_pill("AI Score", score_str, score_cls)
    pills_html += metric_pill("Duration", f"{result.get('days', len(result.get('itinerary', [])))}&nbsp;days")
    rtc = result.get("real_time_costs")
    if rtc and rtc.get("total_estimated_cost"):
        pills_html += metric_pill("Est. Total", f"₹{rtc['total_estimated_cost']:,}")
    pills_html += '</div>'
    st.markdown(pills_html, unsafe_allow_html=True)

    if reason:
        st.markdown(f"""
        <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#6b6560;
                    padding:0.75rem 1rem;border-left:2px solid #2a2520;margin-bottom:2rem;
                    letter-spacing:0.05em;">
            {reason}
        </div>
        """, unsafe_allow_html=True)

    # ── Real-time cost banner ──────────────────────────────────────────────────
    if rtc:
        flight_src = rtc.get("flight_source", "estimated")
        hotel_src  = rtc.get("hotel_source",  "estimated")
        is_live = "live" in flight_src.lower() or "live" in hotel_src.lower()
        dot_cls = "realtime-dot" if is_live else "realtime-dot"
        src_label = "Live pricing from Google Flights & Hotels" if is_live else "Estimated pricing (add API keys for live data)"
        st.markdown(f"""
        <div class="realtime-banner">
            <div class="{dot_cls}" style="{'background:#4caf82' if is_live else 'background:#c9a84c'}"></div>
            <span class="realtime-text" style="{'color:#4caf82' if is_live else 'color:#c9a84c'}">
                {src_label} &nbsp;·&nbsp; Flight: ₹{rtc.get('flight_cost',0):,} &nbsp;·&nbsp;
                Hotel: ₹{rtc.get('hotel_cost_per_night',0):,}/night
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Flight + Hotel recommendations ─────────────────────────────────────
        cheapest_flight = rtc.get("cheapest_flight_option")
        cheapest_hotel  = rtc.get("cheapest_hotel_option")

        if cheapest_flight or cheapest_hotel:
            section_rule("Recommended Options")
            rec_col1, rec_col2 = st.columns(2)

            with rec_col1:
                if cheapest_flight:
                    airline  = cheapest_flight.get("airline", "—")
                    price    = cheapest_flight.get("price_inr", 0)
                    stops    = cheapest_flight.get("stops", 0)
                    duration = cheapest_flight.get("duration", 0)
                    stop_str = "Direct" if stops == 0 else f"{stops} stop(s)"
                    dur_str  = f"{duration // 60}h {duration % 60}m" if duration else "—"
                    st.markdown(f"""
                    <div class="metric-pill" style="border-color:#2a2520;">
                        <div class="metric-pill-label">✈  Cheapest Flight · {stop_str}</div>
                        <div class="metric-pill-value gold">₹{price:,}</div>
                        <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#6b6560;margin-top:0.3rem;">
                            {airline} &nbsp;·&nbsp; {dur_str}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with rec_col2:
                if cheapest_hotel:
                    hname    = cheapest_hotel.get("name", "—")
                    hprice   = cheapest_hotel.get("per_night_inr", 0)
                    hrating  = cheapest_hotel.get("rating")
                    hdesc    = cheapest_hotel.get("description", "")[:80]
                    hamen    = cheapest_hotel.get("amenities", [])[:3]
                    rat_str  = f"⭐ {hrating}" if hrating else ""
                    amen_str = "  ·  ".join(hamen) if hamen else ""
                    st.markdown(f"""
                    <div class="metric-pill" style="border-color:#2a2520;">
                        <div class="metric-pill-label">🏨  Cheapest Hotel &nbsp; {rat_str}</div>
                        <div class="metric-pill-value" style="font-size:1rem;line-height:1.3;">{hname}</div>
                        <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#4caf82;margin-top:0.3rem;">
                            ₹{hprice:,}/night
                        </div>
                        <div style="font-family:'Outfit',sans-serif;font-size:0.75rem;color:#6b6560;margin-top:0.3rem;">
                            {hdesc}
                        </div>
                        <div style="font-family:'DM Mono',monospace;font-size:0.6rem;color:#2a6040;margin-top:0.3rem;">
                            {amen_str}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # ── Budget breakdown ───────────────────────────────────────────────────────
    section_rule("Budget Breakdown")
    bd = result.get("budget_breakdown", {})
    total = sum(bd.values())

    cells = ""
    for key, (icon, label) in BUDGET_ICONS.items():
        amount = bd.get(key, 0)
        pct    = int((amount / total) * 100) if total else 0
        cells += f"""
        <div class="budget-cell">
            <div class="budget-cell-icon">{icon}</div>
            <div class="budget-cell-label">{label}</div>
            <div class="budget-cell-amount">₹{amount:,}</div>
            <div class="budget-cell-sub">{pct}% of budget</div>
        </div>"""

    st.markdown(f'<div class="budget-grid">{cells}</div>', unsafe_allow_html=True)

    # ── Itinerary ──────────────────────────────────────────────────────────────
    section_rule("Itinerary")

    for day in result.get("itinerary", []):
        activities = day.get("activities", [])
        acts_html  = ""
        for act in activities:
            acts_html += f"""
            <div class="activity-item">
                <div class="activity-marker"></div>
                <div>
                    <div class="activity-name">{act.get('activity','')}</div>
                    <div class="activity-desc">{act.get('description','')}</div>
                </div>
            </div>"""

        with st.expander(f"", expanded=(day.get("day", 1) == 1)):
            st.markdown(f"""
            <div class="day-card">
                <div class="day-card-header">
                    <div class="day-number">{day.get('day','')}</div>
                    <div>
                        <div class="day-location">{day.get('location','')}</div>
                    </div>
                    <div class="day-activity-count">{len(activities)} stops</div>
                </div>
                {acts_html}
            </div>
            """, unsafe_allow_html=True)


def render_budget_insufficient(result: dict):
    """Renders a BudgetInsufficientResponse with detailed breakdown and suggestions."""

    your_budget  = result.get("your_budget", 0)
    min_required = result.get("minimum_required", 0)
    shortfall    = result.get("shortfall", 0)
    destination  = result.get("destination", "")
    days         = result.get("days", 0)
    pct_covered  = int((your_budget / min_required) * 100) if min_required else 0

    st.markdown(f"""
    <div class="insufficient-hero">
        <div class="insufficient-icon">⚠</div>
        <div class="insufficient-title">Budget Insufficient</div>
        <div class="insufficient-sub">
            Your budget covers {pct_covered}% of the estimated cost for
            {days} days in {destination}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        section_rule("Cost vs Budget")

        bd = result.get("breakdown", {})
        rows = [
            ("✈  Flight",       bd.get("flight",    {}).get("cost", 0)),
            ("🏨  Hotel",        bd.get("hotel",     {}).get("cost", 0)),
            ("🍜  Food",         bd.get("food",      {}).get("cost", 0)),
            ("🚇  Transport",    bd.get("transport", {}).get("cost", 0)),
            ("🎒  Misc",         bd.get("misc",      {}).get("cost", 0)),
            ("🛡  Safety buffer", bd.get("safety_buffer", {}).get("cost", 0)),
        ]

        rows_html = ""
        for label, amount in rows:
            rows_html += f"""
            <div class="cost-row">
                <span class="cost-label">{label}</span>
                <span class="cost-amount">₹{amount:,}</span>
            </div>"""

        rows_html += f"""
        <div class="cost-row" style="margin-top:0.5rem;border-top:1px solid var(--gold-dim);padding-top:1rem;">
            <span class="cost-label" style="color:var(--paper)">Total required</span>
            <span class="cost-amount" style="color:#e05c4b;font-size:1.4rem;">₹{min_required:,}</span>
        </div>
        <div class="cost-row">
            <span class="cost-label" style="color:var(--paper)">Your budget</span>
            <span class="cost-amount" style="color:#4caf82;font-size:1.4rem;">₹{your_budget:,}</span>
        </div>
        <div class="cost-row">
            <span class="cost-label" style="color:var(--paper)">Shortfall</span>
            <span class="cost-amount" style="color:#e05c4b;font-size:1.6rem;">₹{shortfall:,}</span>
        </div>"""

        st.markdown(f'<div style="background:#111009;border:1px solid #2a2520;padding:1.5rem;">{rows_html}</div>', unsafe_allow_html=True)

        # Cheapest options found
        flight_opt = result.get("cheapest_flight")
        hotel_opt  = result.get("cheapest_hotel")

        if flight_opt or hotel_opt:
            section_rule("Cheapest Options Found")
            if flight_opt:
                airline  = flight_opt.get("airline", "Estimated")
                price    = flight_opt.get("price_inr", 0)
                stops    = flight_opt.get("stops", 0)
                stop_str = "Direct" if stops == 0 else f"{stops} stop(s)"
                st.markdown(f"""
                <div class="cost-row">
                    <span class="cost-label">✈  Cheapest flight · {stop_str} · {airline}</span>
                    <span class="cost-amount">₹{price:,}</span>
                </div>""", unsafe_allow_html=True)
            if hotel_opt:
                hname  = hotel_opt.get("name", "Budget hotel")
                hprice = hotel_opt.get("per_night_inr", 0)
                hrat   = hotel_opt.get("rating")
                rat_str = f" · ⭐ {hrat}" if hrat else ""
                st.markdown(f"""
                <div class="cost-row">
                    <span class="cost-label">🏨  {hname}{rat_str}</span>
                    <span class="cost-amount">₹{hprice:,}/night</span>
                </div>""", unsafe_allow_html=True)

    with col_b:
        section_rule("Suggestions")
        for s in result.get("suggestions", []):
            st.markdown(f'<div class="suggestion-item">→ &nbsp;{s}</div>', unsafe_allow_html=True)

        # Quick fix calculator
        section_rule("Quick Fix")
        needed = min_required - your_budget
        if needed > 0:
            st.markdown(f"""
            <div style="background:#111009;border:1px solid #2a2520;padding:1.5rem;text-align:center;">
                <div style="font-family:'DM Mono',monospace;font-size:0.6rem;letter-spacing:0.2em;
                            text-transform:uppercase;color:var(--smoke);margin-bottom:0.5rem;">
                    Additional budget needed
                </div>
                <div style="font-family:'Cormorant Garamond',serif;font-size:3rem;font-weight:300;color:#e05c4b;">
                    ₹{needed:,}
                </div>
                <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:var(--smoke);margin-top:0.5rem;">
                    Increase budget to ₹{min_required:,} to proceed
                </div>
            </div>
            """, unsafe_allow_html=True)


# ── Main action ────────────────────────────────────────────────────────────────

if generate:
    if not destination.strip():
        st.error("Please enter a destination.")
        st.stop()

    if not interests:
        st.error("Please select at least one interest.")
        st.stop()

    payload = {
        "destination": destination.strip(),
        "budget":      int(budget),
        "days":        int(days),
        "interests":   interests,
        "origin":      origin.strip() or "Delhi",
    }

    with st.spinner("Agents are working — fetching live prices, planning your itinerary…"):
        try:
            response = requests.post(API_URL, json=payload, timeout=900)
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the API. Make sure the backend is running: `python -m uvicorn backend.main:app --reload`")
            st.stop()
        except requests.exceptions.Timeout:
            st.error("Request timed out. The LLM is taking too long — try a shorter trip or a faster model.")
            st.stop()

    if response.status_code == 422:
        detail = response.json().get("detail", response.text)
        st.error(f"Invalid input: {detail}")
        st.stop()

    if response.status_code != 200:
        st.error(f"API error {response.status_code}: {response.text[:300]}")
        st.stop()

    result = response.json()

    # Route to the correct renderer
    if not result.get("budget_sufficient", True):
        render_budget_insufficient(result)
    else:
        render_travel_plan(result)