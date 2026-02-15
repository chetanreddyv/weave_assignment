import streamlit as st
import pandas as pd
import json
import math
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from collections import defaultdict
from models import ImpactData, ContributorImpact

st.set_page_config(
    page_title="PostHog Impact Stories",
    page_icon="./",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Doodle-style SVG icons (hand-drawn, simple line art)
# ---------------------------------------------------------------------------
DOODLE_ICONS = {
    "trophy": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 8h16v4c0 6-3.5 12-8 14-4.5-2-8-8-8-14V8z" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M16 12H10c0 4 2.5 8 6 9" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M32 12h6c0 4-2.5 8-6 9" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M20 36h8" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M24 26v10" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M18 40h12" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
    </svg>''',
    "flame": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M24 4c0 8-10 14-10 24a10 10 0 0020 0c0-4-2-7-4-10 0 4-2 6-4 6s-4-4-2-10c-3 2-6 6-6 10" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>''',
    "handshake": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 20l8-8h6l4 4-8 8" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M42 20l-8-8h-6l-4 4 8 8" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M18 28l4 4 4-4 4 4 4-4" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M14 24l4 4" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>''',
    "code": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 14l-10 10 10 10" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M32 14l10 10-10 10" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M28 8L20 40" stroke="{color}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
    </svg>''',
    "lightbulb": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M24 4a12 12 0 00-6 22.4V32h12v-5.6A12 12 0 0024 4z" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M20 36h8M21 40h6" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M24 12v4M18 16l2 3M30 16l-2 3" stroke="{color}" stroke-width="1.8" stroke-linecap="round" opacity="0.5"/>
    </svg>''',
    "star": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M24 4l5.5 12.5H43l-11 8 4.5 13L24 29l-12.5 8.5 4.5-13-11-8h13.5z" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>''',
    "chart": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 40V8" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M6 40h36" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M12 32l8-10 6 6 10-16" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <circle cx="36" cy="12" r="2" stroke="{color}" stroke-width="2" fill="none"/>
    </svg>''',
    "git_pr": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="14" cy="12" r="4" stroke="{color}" stroke-width="2.2" fill="none"/>
        <circle cx="14" cy="36" r="4" stroke="{color}" stroke-width="2.2" fill="none"/>
        <circle cx="34" cy="36" r="4" stroke="{color}" stroke-width="2.2" fill="none"/>
        <path d="M14 16v16" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M34 32V20c0-4-3-8-8-8h-6" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>''',
    "shield": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M24 4L6 12v10c0 12 7 21 18 24 11-3 18-12 18-24V12L24 4z" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>''',
    "diamond": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M24 4L6 18l18 26L42 18 24 4z" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M6 18h36" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M13 18l11 26" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M35 18L24 44" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
    </svg>''',
    "rocket": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M24 6c0 0-4 8-4 16v8l-6 4v4h20v-4l-6-4v-8c0-8-4-16-4-16z" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M24 38v6" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M14 28c-4 4-8 4-8 4s2-8 6-12" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M34 28c4 4 8 4 8 4s-2-8-6-12" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>''',
    "robot": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="14" width="28" height="24" rx="4" stroke="{color}" stroke-width="2.2" fill="none"/>
        <path d="M16 26h4M28 26h4" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M20 34h8" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M24 4v10" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <circle cx="24" cy="4" r="2" stroke="{color}" stroke-width="2"/>
        <path d="M6 24h4M38 24h4" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
    </svg>''',
    "sprout": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M24 44V20" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M24 34c0 0 8 0 12-8s-6-12-12-4" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M24 26c0 0-8 0-12-8s6-12 12-4" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>''',
    "zap": '''<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M26 6L6 26h14l-4 16 20-20H22l4-16z" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>''',
}


def doodle(name, size=28, color="#6B5CE7"):
    """Return an inline SVG doodle icon."""
    svg = DOODLE_ICONS.get(name, "")
    return svg.format(size=size, color=color)


def get_archetype(row):
    """Determine engineer archetype based on metrics."""
    prs = row.get("prs_merged", 0)
    reviews = row.get("reviews_given", 0)
    quality = row.get("avg_quality_score", 0)
    
    if reviews > prs * 2 and reviews > 5:
        return "shield", "The Unblocker", "#818CF8", "Prioritizes helping others over personal shipping volume."
    elif quality >= 4.5:
        return "diamond", "The Artisan", "#34D399", "Ships code of exceptional quality and substance."
    elif prs > 20 and quality >= 4.0:
        return "rocket", "10x Engineer", "#F472B6", "High volume combined with top-tier quality."
    elif prs > 30:
        return "robot", "The Machine", "#60A5FA", "Incredible velocity and shipping consistency."
    elif quality >= 4.0 and reviews > 10:
        return "star", "All-Rounder", "#FBBF24", "Balances high quality code with strong collaboration."
    else:
        return "sprout", "Core Contribution", "#9CA3AF", "Steadily building and improving the product."

def get_narrative(row, archetype_name):
    """Generate a 1-sentence narrative summary."""
    login = row["login"]
    prs = row.get("prs_merged", 0)
    reviews = row.get("reviews_given", 0)
    
    extra = ""
    if "Unblocker" in archetype_name:
        extra = f"enabling the team with {reviews} reviews."
    elif "Artisan" in archetype_name:
        extra = f"focusing on craft and deep technical impact."
    elif "10x" in archetype_name:
        extra = f"dominating the leaderboard with speed and precision."
    elif "Machine" in archetype_name:
        extra = f"shipping continuously with {prs} merged PRs."
    else:
        extra = "and consistently moving the project forward."
        
    return f"<strong>{login}</strong> is acting as <strong>{archetype_name.split(' ', 1)[1]}</strong>, {extra}"


# ---------------------------------------------------------------------------
# Custom CSS — light, modern, SaaS aesthetic
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ---- Global ---- */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, sans-serif !important;
        }
        .stApp {
            background-color: #FAFAF9;
        }
        /* Hide Streamlit chrome */
        #MainMenu, footer, header { visibility: hidden; }
        div[data-testid="stDecoration"] { display: none; }

        /* ---- Hero ---- */
        .hero-section {
            background: linear-gradient(135deg, #E8E0FF 0%, #D4E4FF 50%, #E0F4E8 100%);
            border-radius: 24px;
            padding: 56px 40px 48px;
            text-align: center;
            margin-bottom: 36px;
            position: relative;
            overflow: hidden;
        }
        .hero-section::before {
            content: '';
            position: absolute;
            top: -40%; left: -10%;
            width: 50%; height: 180%;
            background: radial-gradient(circle, rgba(107,92,231,0.08) 0%, transparent 70%);
            pointer-events: none;
        }
        .hero-section h1 {
            font-size: 2.8rem;
            font-weight: 800;
            color: #1A1A2E;
            margin: 0 0 8px;
            letter-spacing: -0.02em;
        }
        .hero-section p {
            font-size: 1.15rem;
            color: #555;
            margin: 0;
            font-weight: 400;
        }

        /* ---- Metric tiles ---- */
        .metric-row {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 32px;
            flex-wrap: wrap;
        }
        .metric-tile {
            background: white;
            border-radius: 16px;
            padding: 24px 32px;
            min-width: 200px;
            flex: 1;
            max-width: 280px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
            text-align: center;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-tile:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 20px rgba(107,92,231,0.10);
        }
        .metric-tile .icon { margin-bottom: 8px; }
        .metric-tile .value {
            font-size: 2rem;
            font-weight: 700;
            color: #1A1A2E;
            margin: 4px 0;
        }
        .metric-tile .label {
            font-size: 0.85rem;
            color: #888;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        /* ---- Section headers ---- */
        .section-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 40px 0 20px;
        }
        .section-header h2 {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1A1A2E;
            margin: 0;
        }
        .section-header .line {
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, #ddd 0%, transparent 100%);
        }

        /* ---- Engineer cards ---- */
        .eng-card {
            background: white;
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
            border: 1px solid rgba(0,0,0,0.04);
            transition: all 0.25s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        .eng-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(107,92,231,0.12);
            border-color: rgba(107,92,231,0.2);
        }
        .eng-card .rank-badge {
            position: absolute;
            top: 16px;
            right: 16px;
            background: linear-gradient(135deg, #6B5CE7, #8B7CF7);
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.85rem;
        }
        .eng-card .avatar {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            border: 2px solid #E8E0FF;
        }
        .eng-card .name {
            font-size: 1.15rem;
            font-weight: 700;
            color: #1A1A2E;
            margin: 12px 0 4px;
        }
        .eng-card .handle {
            font-size: 0.82rem;
            color: #999;
        }
        .eng-card .stats-row {
            display: flex;
            gap: 16px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
        .eng-card .stat {
            text-align: center;
            flex: 1;
            min-width: 60px;
        }
        .eng-card .stat .stat-val {
            font-size: 1.15rem;
            font-weight: 700;
            color: #1A1A2E;
        }
        .eng-card .stat .stat-label {
            font-size: 0.7rem;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-top: 2px;
        }
        .eng-card .impact-bar-bg {
            width: 100%;
            height: 6px;
            background: #F0EDFF;
            border-radius: 3px;
            margin-top: 16px;
            overflow: hidden;
        }
        .eng-card .impact-bar {
            height: 100%;
            border-radius: 3px;
            background: linear-gradient(90deg, #6B5CE7, #A78BFA);
        }
        .baseline-label { color: #6B5CE7; font-weight: 600; }
        .ai-label { color: #E67E22; font-weight: 600; }

        /* ---- Detail panel ---- */
        .detail-panel {
            background: white;
            border-radius: 20px;
            padding: 32px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
            border: 1px solid rgba(0,0,0,0.04);
            margin-top: 12px;
        }
        .pr-card {
            background: #F9F8FF;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 12px;
            border-left: 3px solid #6B5CE7;
        }
        .pr-card .pr-title {
            font-weight: 600;
            color: #1A1A2E;
            margin-bottom: 6px;
        }
        .pr-card .pr-meta {
            font-size: 0.82rem;
            color: #888;
        }
        .pr-card .pr-reasoning {
            font-size: 0.88rem;
            color: #555;
            margin-top: 8px;
            padding: 10px 14px;
            background: white;
            border-radius: 8px;
            border: 1px solid #EDE9FE;
            font-style: italic;
        }
        .quadrant-label {
            font-size: 0.9rem;
            font-weight: 600;
            color: #555;
        }

        /* ---- Tab styling ---- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 8px 20px;
            font-weight: 500;
            color: #666;
        }
        .stTabs [aria-selected="true"] {
            background: #6B5CE7 !important;
            color: white !important;
            border-radius: 10px;
        }

        /* ---- Plotly chart container ---- */
        .stPlotlyChart {
            border-radius: 16px;
            overflow: hidden;
        }

        /* ---- View Story button styling ---- */
        .view-story-btn .stButton button {
            background: linear-gradient(135deg, #6B5CE7, #8B7CF7) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            padding: 8px 16px !important;
            letter-spacing: 0.03em !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            margin-top: -8px !important;
        }
        .view-story-btn .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 15px rgba(107,92,231,0.3) !important;
        }
        .view-story-btn .stButton button:active {
            transform: translateY(0) !important;
        }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    try:
        with open("impact_data.json", "r") as f:
            data = json.load(f)
        return ImpactData(**data)
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Helper: plotly light theme
# ---------------------------------------------------------------------------
PLOTLY_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="#FAFAF9",
    font=dict(family="Inter, sans-serif", color="#1A1A2E"),
    margin=dict(l=40, r=20, t=50, b=40),
    title_font=dict(size=16, color="#1A1A2E"),
    colorway=["#6B5CE7", "#A78BFA", "#E67E22", "#3BB273", "#3B82F6", "#F472B6", "#FBBF24"],
)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------
def render_hero(data):
    total_prs = len(data.pull_requests)
    total_reviews = sum(c.reviews_given for c in data.contributor_metrics)
    active_engineers = len(data.contributor_metrics)

    st.markdown(f"""
    <div class="hero-section">
        <h1>PostHog Impact Stories</h1>
        <p>Celebrating the humans behind the code</p>
        <div class="metric-row">
            <div class="metric-tile">
                <div class="icon">{doodle("flame", 32, "#6B5CE7")}</div>
                <div class="value">{total_prs}</div>
                <div class="label">Code Contributions</div>
            </div>
            <div class="metric-tile">
                <div class="icon">{doodle("handshake", 32, "#6B5CE7")}</div>
                <div class="value">{total_reviews}</div>
                <div class="label">Teammates Unblocked</div>
            </div>
            <div class="metric-tile">
                <div class="icon">{doodle("code", 32, "#6B5CE7")}</div>
                <div class="value">{active_engineers}</div>
                <div class="label">Active Engineers</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("ℹ️ How are Impact & Quality calculations made?"):
        st.markdown("""
        ### Impact Score Formula 
        Impact is a verifiable measure of value delivered. It is **NOT** just lines of code.
        
        $$
        \\text{Impact} = (\\text{Activity Baseline}) \\times (\\text{Quality Multiplier})
        $$
        
        **1. Activity Baseline (Log-Normalized, Value-Based):**
        
        All dimensions use logarithmic scaling to prevent any single metric from dominating.
        
        | Dimension | Weight | Logic |
        |-----------|--------|-------|
        | **Shipping PRs** | 40% | `log(1 + merged_prs × type_multiplier) × 15` |
        | **Code Reviews** | 30% | `log(1 + reviews) × 30` |
        | **Code Volume** | 15% | `log10(1 + lines_changed) × 8` |
        | **Issue Resolution** | 15% | `log(1 + closed×5 + opened×1) × 10` |
        
        **PR Type Multipliers** (inferred from title):
        - `feat:` / `feature:` → 1.5× (Features drive product forward)
        - `fix:` / `bug:` → 1.3× (Fixes resolve user pain)
        - `refactor:` / `perf:` → 1.1× (Improves long-term health)
        - `chore:` / `docs:` → 0.7× (Necessary but lower impact)
        
        **2. Quality Multiplier (AI-Evaluated):**
        *   An LLM Agent evaluates the top 10 PRs per engineer on 4 dimensions.
        *   **High Quality (>4/5):** 1.2x – 1.4x Boost
        *   **Low Quality (<2/5):** 0.6x – 0.8x Penalty
        
        ---
        ### AI Quality Score 🤖
        
        An LLM Agent (acting as a VP of Engineering) evaluates the top 10 PRs per engineer on 4 dimensions (1-5 scale).
        
        **1. Substance & Complexity (Weight: High)**
        | Score | Criteria |
        |-------|----------|
        | **5** | Major architectural change, new system, or complex algorithm |
        | **3** | Standard feature or moderate logic change |
        | **1** | Typo fix, dependency bump, or trivial one-liner |
        
        **2. Product & Business Impact (Weight: High)**
        | Score | Criteria |
        |-------|----------|
        | **5** | Unlocks new revenue, critical launch, or fixes P0 issue |
        | **3** | Enhances features or improves UX |
        | **1** | Internal chore or no direct user impact |
        
        **3. Technical Excellence (Weight: Medium)**
        | Score | Criteria |
        |-------|----------|
        | **5** | Exemplary tests, docs, and clean abstractions |
        | **3** | Adequate functionality but needs polish |
        | **1** | Poor tests, unclear intent, or potential regressions |
        
        **4. Scope of Blast Radius (Weight: Medium)**
        | Score | Criteria |
        |-------|----------|
        | **5** | Touches core infra (DB, auth, shared libs) |
        | **3** | Scoped to feature but with multiple touchpoints |
        | **1** | Completely isolated change |
        """)


def render_engineer_gallery(df, data):
    """Render top-5 engineer cards and handle selection for drill-down."""
    top5 = df.head(5)
    max_impact = top5["impact_score"].max() if not top5.empty else 1

    st.markdown(f"""
    <div class="section-header">
        {doodle("trophy", 28, "#6B5CE7")}
        <h2>Top Impact Engineers</h2>
        <div class="line"></div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(5, gap="medium")
    for idx, (_, row) in enumerate(top5.iterrows()):
        rank = idx + 1
        pct = int((row["impact_score"] / max_impact) * 100)
        quality_display = f'{row["avg_quality_score"]:.1f}' if row["avg_quality_score"] > 0 else "—"
        arch_icon, archetype, arch_color, arch_desc = get_archetype(row)
        
        # Compute baseline and delta
        baseline = row.get("baseline_impact_score", 0)
        if baseline == 0:
            baseline = row["impact_score"]  # backward compat for old data
        ai_score = row["impact_score"]
        if baseline > 0 and ai_score != baseline:
            delta_pct = ((ai_score - baseline) / baseline) * 100
            delta_sign = "↑" if delta_pct > 0 else "↓"
            delta_color = "#059669" if delta_pct > 0 else "#DC2626"
            delta_html = f'<span style="font-size: 0.65rem; color: {delta_color}; font-weight: 600; margin-left: 2px;">{delta_sign}{abs(delta_pct):.0f}%</span>'
        else:
            delta_html = ""

        with cols[idx]:
            st.markdown(f"""
            <div class="eng-card">
                <div class="rank-badge">{rank}</div>
                <div style="text-align: center; margin-bottom: 8px;">
                     <div style="display: inline-flex; align-items: center; gap: 6px; background: {arch_color}15; color: {arch_color}; padding: 4px 10px; border-radius: 12px; border: 1px solid {arch_color}30;">
                        <span>{doodle(arch_icon, 16, arch_color)}</span>
                        <span style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em;">{archetype}</span>
                    </div>
                </div>
                <img class="avatar" src="{row['avatar_url']}" alt="{row['login']}"/>
                <div class="name">{row['login']}</div>
                <div class="handle"><a href="{row['html_url']}" target="_blank" style="color: #999; text-decoration: none;">View Profile</a></div>
                <div class="stats-row">
                    <div class="stat">
                        <div class="stat-val">{row['prs_merged']}</div>
                        <div class="stat-label">PRs</div>
                    </div>
                    <div class="stat">
                        <div class="stat-val">{row['reviews_given']}</div>
                        <div class="stat-label">Reviews</div>
                    </div>
                    <div class="stat">
                        <div class="stat-val ai-label" title="Rated 1-5 by LLM on Substance &amp; Tech Quality">{quality_display}</div>
                        <div class="stat-label">Quality</div>
                    </div>
                </div>
                <div class="stats-row" style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #F3F4F6;">
                    <div class="stat">
                        <div class="stat-val baseline-label" title="Activity-based score before AI adjustment">{baseline:.0f}</div>
                        <div class="stat-label">Baseline</div>
                    </div>
                    <div class="stat">
                        <div class="stat-val ai-label" title="After AI quality multiplier">{ai_score:.0f}{delta_html}</div>
                        <div class="stat-label">AI Score</div>
                    </div>
                </div>
                <div class="impact-bar-bg"><div class="impact-bar" style="width: {pct}%"></div></div>
            </div>
            """, unsafe_allow_html=True)

            # Simple, visible button — replaces the broken ghost-button overlay
            is_selected = st.session_state.get("selected_engineer") == row["login"]
            label = f"{'✦ Viewing' if is_selected else 'View Story →'}"  
            st.markdown('<div class="view-story-btn">', unsafe_allow_html=True)
            if st.button(label, key=f"btn_{row['login']}", use_container_width=True):
                st.session_state["selected_engineer"] = row["login"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    return top5


def render_radar_chart(engineer_row, avg_row, top5_max_row):
    """Radar chart overlaying this engineer vs the top-5 average — baseline + AI dimensions."""
    categories = ["PR Volume", "Reviews", "Lines Changed", "Quality", "Issues"]

    def safe_norm(val, max_val):
        return min(val / max_val, 1.0) * 100 if max_val > 0 else 0

    # Use global top-5 max for consistent normalization across all engineers
    max_vals = {
        "prs_merged": max(top5_max_row.get("prs_merged", 1), 1),
        "reviews_given": max(top5_max_row.get("reviews_given", 1), 1),
        "lines": max(top5_max_row.get("lines", 1), 1),
        "avg_quality_score": 5,
        "issues": max(top5_max_row.get("issue_interactions", 1), 1),
    }

    eng_vals = [
        safe_norm(engineer_row["prs_merged"], max_vals["prs_merged"]),
        safe_norm(engineer_row["reviews_given"], max_vals["reviews_given"]),
        safe_norm(engineer_row.get("additions", 0) + engineer_row.get("deletions", 0), max_vals["lines"]),
        safe_norm(engineer_row.get("avg_quality_score", 0), max_vals["avg_quality_score"]),
        safe_norm(engineer_row.get("issue_interactions", 0), max_vals["issues"]),
    ]

    avg_vals = [
        safe_norm(avg_row.get("prs_merged", 0), max_vals["prs_merged"]),
        safe_norm(avg_row.get("reviews_given", 0), max_vals["reviews_given"]),
        safe_norm(avg_row.get("lines", 0), max_vals["lines"]),
        safe_norm(avg_row.get("avg_quality_score", 0), max_vals["avg_quality_score"]),
        safe_norm(avg_row.get("issue_interactions", 0), max_vals["issues"]),
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=eng_vals + [eng_vals[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name=engineer_row['login'],
        line_color='#6B5CE7',
        fillcolor='rgba(107,92,231,0.15)',
    ))
    fig.add_trace(go.Scatterpolar(
        r=avg_vals + [avg_vals[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name='Top 5 Average',
        line_color='#E67E22',
        fillcolor='rgba(230,126,34,0.08)',
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="#EDE9FE"),
            bgcolor="white",
            angularaxis=dict(gridcolor="#F0EDFF"),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        title=f"Profile: {engineer_row['login']} vs Top 5 Average",
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k != 'plot_bgcolor'},
        height=400,
    )
    return fig


def render_impact_breakdown(engineer_row):
    """Visual impact score breakdown as a horizontal stacked bar with labeled segments."""
    prs = engineer_row.get("prs_merged", 0)
    reviews = engineer_row.get("reviews_given", 0)
    lines = engineer_row.get("additions", 0) + engineer_row.get("deletions", 0)
    quality = engineer_row.get("avg_quality_score", 0)
    total_impact = engineer_row.get("impact_score", 0)
    baseline = engineer_row.get("baseline_impact_score", 0)
    if baseline == 0:
        baseline = total_impact  # backward compat for old data

    # Compute multiplier and delta
    if baseline > 0 and total_impact != baseline:
        multiplier_val = total_impact / baseline
        delta_pct = ((total_impact - baseline) / baseline) * 100
        delta_sign = "+" if delta_pct > 0 else ""
        delta_color = "#059669" if delta_pct > 0 else "#DC2626"
        multiplier_badge = (
            f'<div style="display: inline-flex; align-items: center; gap: 6px; background: {delta_color}10; '
            f'border: 1px solid {delta_color}30; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; color: {delta_color}; font-weight: 600;">'
            f'{doodle("robot", 14, delta_color)} {multiplier_val:.2f}x ({delta_sign}{delta_pct:.0f}%)</div>'
        )
    else:
        multiplier_badge = '<span style="font-size: 0.8rem; color: #999;">No AI adjustment</span>'

    # Decompose using the actual formula from main.py (log-normalized value-based model)
    # These mirror calculate_baseline_metrics() exactly
    issues_closed = engineer_row.get("issues_closed", 0)
    issue_interactions = engineer_row.get("issue_interactions", 0)
    
    # Shipping: log(1 + type_weighted_pr_value) * 15 — approximate with average multiplier
    shipping_pts = math.log(1 + prs * 10) * 15 if prs > 0 else 0
    # Reviews: log(1 + reviews) * 30
    review_pts = math.log(1 + reviews) * 30 if reviews > 0 else 0
    # Code Volume: log10(1 + lines) * 8
    volume_pts = math.log10(1 + lines) * 8 if lines > 0 else 0
    # Issues: log(1 + closed*5 + opened*1) * 10
    raw_issue = (issues_closed * 5) + (max(issue_interactions - issues_closed, 0) * 1)
    issue_pts = math.log(1 + raw_issue) * 10 if issue_interactions > 0 else 0

    components = [
        ("Shipping PRs", shipping_pts, "#6B5CE7"),
        ("Code Reviews", review_pts, "#818CF8"),
        ("Code Volume", volume_pts, "#A78BFA"),
        ("Issue Resolution", issue_pts, "#34D399"),
    ]
    # Filter out zero-value items
    components = [(name, val, color) for name, val, color in components if val > 0]
    grand_total = sum(v for _, v, _ in components)

    # Build HTML segments
    segments_html = ""
    for name, val, color in components:
        pct = (val / grand_total * 100) if grand_total > 0 else 0
        segments_html += (
            f'<div style="width: {pct}%; background: {color}; height: 100%;" '
            f'title="{name}: {val:.0f} pts ({pct:.0f}%)">'
            f'</div>'
        )

    # Stat tiles below the bar
    tile_data = [
        (doodle("git_pr", 18, "#6B5CE7"), f"{prs}", "PRs Merged"),
        (doodle("handshake", 18, "#818CF8"), f"{reviews}", "Reviews Given"),
        (doodle("code", 18, "#A78BFA"), f"{lines:,}", "Lines Changed"),
        (doodle("star", 18, "#34D399"), f"{quality:.1f}/5" if quality > 0 else "N/A", "Quality"),
    ]
    tiles_html = ""
    for icon, val, label in tile_data:
        tiles_html += (
            f'<div style="text-align: center; flex: 1; padding: 12px 8px;">'
            f'<div>{icon}</div>'
            f'<div style="font-size: 1.2rem; font-weight: 700; color: #1A1A2E; margin: 4px 0;">{val}</div>'
            f'<div style="font-size: 0.72rem; color: #999; text-transform: uppercase; letter-spacing: 0.04em;">{label}</div>'
            f'</div>'
        )

    # Legend items
    legend_html = ""
    for name, val, color in components:
        pct = (val / grand_total * 100) if grand_total > 0 else 0
        legend_html += (
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 0.9rem; color: #555;">'
            f'  <div style="display: flex; align-items: center; gap: 8px;">'
            f'    <div style="width: 12px; height: 12px; background: {color}; border-radius: 3px;"></div>'
            f'    <span style="font-weight: 500;">{name}</span>'
            f'  </div>'
            f'  <div style="font-weight: 600; color: #1A1A2E;">{val:.0f} pts <span style="color: #999; font-weight: 400; font-size: 0.8em; margin-left: 4px;">({pct:.0f}%)</span></div>'
            f'</div>'
        )

    st.markdown(f"""
    <div style="background: white; border-radius: 16px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03); min-height: 450px; display: flex; flex-direction: column;">
        <div style="font-size: 0.8rem; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 16px;">Impact Score Breakdown</div>
        <div style="display: flex; justify-content: center; gap: 40px; align-items: flex-end; margin-bottom: 20px;">
            <div style="text-align: center;">
                <div style="font-size: 2.2rem; font-weight: 800; color: #6B5CE7; line-height: 1;">{baseline:.0f}</div>
                <div style="font-size: 0.78rem; color: #6B5CE7; font-weight: 600; margin-top: 4px;">Baseline</div>
            </div>
            <div style="text-align: center; padding-bottom: 4px;">
                <div style="font-size: 1.5rem; color: #999;">→</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 3rem; font-weight: 800; color: #E67E22; line-height: 1;">{total_impact:.0f}</div>
                <div style="font-size: 0.78rem; color: #E67E22; font-weight: 600; margin-top: 4px;">AI Enhanced</div>
            </div>
        </div>
        <div style="text-align: center; margin-bottom: 20px;">
            {multiplier_badge}
        </div>
        <div style="font-size: 0.75rem; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px;">Baseline Composition</div>
        <div style="display: flex; height: 16px; border-radius: 8px; overflow: hidden; margin-bottom: 20px;">
            {segments_html}
        </div>
        <div style="margin-bottom: 16px;">
            {legend_html}
        </div>
        <div style="margin-top: auto; display: flex; gap: 8px; border-top: 1px solid #F3F4F6; padding-top: 16px;">
            {tiles_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_engineer_drilldown(login, df, data):
    """Full drill-down panel for selected engineer."""
    row = df[df["login"] == login].iloc[0].to_dict()
    user_prs = [p for p in data.pull_requests if p.user_login == login]
    merged_prs = [p for p in user_prs if p.merged_at]

    # Compute top-5 averages and max for radar (consistent scale across all engineers)
    top5 = df.head(5)
    avg_row = {
        "prs_merged": top5["prs_merged"].mean(),
        "reviews_given": top5["reviews_given"].mean(),
        "lines": (top5["additions"] + top5["deletions"]).mean(),
        "avg_quality_score": top5["avg_quality_score"].mean(),
        "issue_interactions": top5["issue_interactions"].mean() if "issue_interactions" in top5.columns else 0,
    }
    top5_max_row = {
        "prs_merged": top5["prs_merged"].max(),
        "reviews_given": top5["reviews_given"].max(),
        "lines": (top5["additions"] + top5["deletions"]).max(),
        "issue_interactions": top5["issue_interactions"].max() if "issue_interactions" in top5.columns else 1,
    }

    # --- Start of grouped engineer panel ---
    st.markdown(f"""
    <div class="section-header">
        {doodle("lightbulb", 28, "#6B5CE7")}
        <h2>Engineer Profile: {login}</h2>
        <div class="line"></div>
    </div>
    """, unsafe_allow_html=True)

    # Use a Streamlit container for visual grouping instead of a custom div wrapper
    with st.container(border=True):
        
        # Narrative Block
        arch_icon, archetype, arch_color, arch_desc = get_archetype(row)
        narrative = get_narrative(row, archetype)
        
        st.markdown(f"""
        <div style="border-radius: 12px; padding: 24px; border-left: 5px solid {arch_color}; background: #FAFAF9; margin-bottom: 24px;">
            <h3 style="margin: 0 0 8px 0; color: #1A1A2E; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                {doodle(arch_icon, 24, arch_color)}
                <span>{archetype}</span>
                <span style="font-size: 0.85rem; font-weight: 400; color: #666; background: #E8E0FF; padding: 2px 10px; border-radius: 12px; margin-left: auto;">{arch_desc}</span>
            </h3>
            <p style="font-size: 1.05rem; color: #4B5563; margin: 8px 0 0 0; line-height: 1.6;">
                {narrative}
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_radar, col_breakdown = st.columns(2)
        with col_radar:
            fig_radar = render_radar_chart(row, avg_row, top5_max_row)
            st.plotly_chart(fig_radar, use_container_width=True)
        with col_breakdown:
            render_impact_breakdown(row)

        # Timeline of merged PRs (inside the same panel)
        if merged_prs:
            st.markdown(f"""
            <div style="margin-top: 28px; padding-top: 20px; border-top: 1px solid #EDE9FE;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
                    {doodle("git_pr", 22, "#6B5CE7")}
                    <span style="font-size: 1.15rem; font-weight: 700; color: #1A1A2E;">PR Timeline</span>
                    <span style="font-size: 0.8rem; color: #999; background: #F3F4F6; padding: 2px 10px; border-radius: 12px;">{len(merged_prs)} merged</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Sort PRs by merge date (most recent first)
            sorted_prs = sorted(merged_prs, key=lambda x: str(x.merged_at), reverse=True)
            
            # Display as beautiful timeline cards
            for idx, pr in enumerate(sorted_prs):
                # Parse the merged date
                try:
                    if hasattr(pr.merged_at, 'strftime'):
                        merged_date = pr.merged_at.strftime("%b %d, %Y")
                        merged_time = pr.merged_at.strftime("%I:%M %p")
                    else:
                        dt = datetime.fromisoformat(str(pr.merged_at).replace('Z', '+00:00'))
                        merged_date = dt.strftime("%b %d, %Y")
                        merged_time = dt.strftime("%I:%M %p")
                except:
                    merged_date = str(pr.merged_at)[:10] if pr.merged_at else "Unknown"
                    merged_time = ""
                
                # Quality badge
                quality_badge = ""
                if pr.llm_quality_score:
                    score = pr.llm_quality_score
                    if score >= 4.0:
                        bg_color = "#D1FAE5"
                        text_color = "#065F46"
                        label = "High Quality"
                    elif score >= 3.0:
                        bg_color = "#FEF3C7"
                        text_color = "#92400E"
                        label = "Good Quality"
                    else:
                        bg_color = "#FEE2E2"
                        text_color = "#991B1B"
                        label = "Needs Attention"
                    quality_badge = f'<span style="background: {bg_color}; color: {text_color}; padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; font-weight: 600; display: inline-block;">{doodle("star", 12, text_color)} {score:.1f} - {label}</span>'
                
                # Code change indicator
                total_changes = pr.additions + pr.deletions
                if total_changes > 500:
                    change_icon = doodle("flame", 14, "#DC2626")
                    change_label = "Major"
                elif total_changes > 100:
                    change_icon = doodle("zap", 14, "#D97706")
                    change_label = "Medium"
                else:
                    change_icon = doodle("sprout", 14, "#059669")
                    change_label = "Small"
                
                # Reasoning block - IMPORTANT: Build as single line or dedented string to prevent Markdown code block interpretation
                reasoning_block = ""
                if pr.llm_reasoning:
                    reasoning_text = pr.llm_reasoning if len(pr.llm_reasoning) <= 200 else pr.llm_reasoning[:200] + "..."
                    reasoning_text = reasoning_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    # No indentation matches the outer f-string indentation
                    reasoning_block = (
                        f'<div style="background: white; border-radius: 10px; padding: 12px 16px; margin-top: 10px; border-left: 3px solid #A78BFA; font-size: 0.88rem; color: #555;">'
                        f'<div style="font-weight: 600; color: #6B5CE7; margin-bottom: 4px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">{doodle("lightbulb", 14, "#6B5CE7")} AI Reasoning</div>'
                        f'<div style="font-style: italic;">{reasoning_text}</div>'
                        f'</div>'
                    )
                
                # Build the full card HTML
                # Use plain concatenation or dedent to avoid indentation issues
                # Build the full card HTML - remove indentation to prevent code block parsing
                card_html = f"""
<div class="pr-card" style="position: relative; padding-left: 20px; border-left: 2px solid #E8E0FF; margin-bottom: 12px;">
    <div style="position: absolute; left: -6px; top: 24px; width: 10px; height: 10px; background: #6B5CE7; border-radius: 50%; border: 2px solid white;"></div>
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
        <div>
            <div class="pr-title" style="font-size: 1rem; margin-bottom: 4px;">
                <a href="{pr.html_url}" target="_blank" style="color: #1A1A2E; text-decoration: none; font-weight: 600;">PR #{pr.number}: {pr.title}</a>
            </div>
            <div class="pr-meta" style="font-size: 0.8rem; color: #999;">
                {merged_date} {("· " + merged_time) if merged_time else ""} · {change_icon} {change_label} · +{pr.additions} / -{pr.deletions} · {pr.changed_files} files
            </div>
        </div>
        <div style="margin-left: 12px; flex-shrink: 0;">{quality_badge}</div>
    </div>
    {reasoning_block}
</div>
"""
                
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info("No merged PRs found for this engineer in the data window.")

        # All PRs (including open/closed) as detail cards
        non_merged = [p for p in user_prs if not p.merged_at]
        if non_merged:
            with st.expander(f"Other PRs ({len(non_merged)} open/closed)"):
                for pr in non_merged:
                    quality_badge = f" · AI Quality: {pr.llm_quality_score:.1f}" if pr.llm_quality_score else ""
                    st.markdown(f"**[PR #{pr.number}]({pr.html_url})**: {pr.title}  \n"
                               f"`{pr.state}` · +{pr.additions}/-{pr.deletions} · {pr.changed_files} files{quality_badge}")



def render_analytics_tabs(df, data):
    """Story-driven analytics in tabs."""
    st.markdown(f"""
    <div class="section-header">
        {doodle("chart", 28, "#6B5CE7")}
        <h2>Story Analytics</h2>
        <div class="line"></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Quality vs Velocity", "The Unsung Heroes", "Impact Landscape"])

    with tab1:
        # 1. New Quadrant Chart: Quality vs Velocity
        plot_df = df[df["avg_quality_score"] > 0].copy()
        if not plot_df.empty:
            med_prs = plot_df["prs_merged"].median()
            med_quality = plot_df["avg_quality_score"].median()
            
            # Define Quadrants
            fig = px.scatter(
                plot_df, x="prs_merged", y="avg_quality_score",
                size="impact_score", hover_name="login",
                color="impact_score",
                color_continuous_scale=["#E8E0FF", "#6B5CE7"],
                labels={"prs_merged": "Velocity (PRs Merged)", "avg_quality_score": "Quality (AI Score)"},
                title="The Engineering Matrix: Speed vs Substance",
            )
            
            # Add colored backdrop zones
            x_max = plot_df["prs_merged"].max() * 1.1
            y_max = 5.2
            
            # Top Right: Legendary (High Speed, High Quality)
            fig.add_shape(type="rect", x0=med_prs, y0=med_quality, x1=x_max, y1=y_max, 
                          fillcolor="rgba(52, 211, 153, 0.1)", layer="below", line_width=0)
            fig.add_annotation(x=x_max*0.9, y=y_max*0.95, text="LEGENDARY", showarrow=False, 
                               font=dict(color="#059669", size=14, weight="bold"))

            # Top Left: Craftsmen (Low Speed, High Quality)
            fig.add_shape(type="rect", x0=0, y0=med_quality, x1=med_prs, y1=y_max, 
                          fillcolor="rgba(96, 165, 250, 0.1)", layer="below", line_width=0)
            fig.add_annotation(x=med_prs*0.2, y=y_max*0.95, text="CRAFTSPEOPLE", showarrow=False, 
                               font=dict(color="#2563EB", size=14, weight="bold"))

            # Bottom Right: Hustlers (High Speed, Low Quality)
            fig.add_shape(type="rect", x0=med_prs, y0=1, x1=x_max, y1=med_quality, 
                          fillcolor="rgba(251, 191, 36, 0.1)", layer="below", line_width=0)
            fig.add_annotation(x=x_max*0.9, y=1.2, text="HUSTLERS", showarrow=False, 
                               font=dict(color="#D97706", size=14, weight="bold"))
                               
            fig.update_layout(**PLOTLY_LAYOUT, height=500, xaxis=dict(range=[0, x_max]), yaxis=dict(range=[1, 5.2]))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Positions are relative to the team median. The 'Legendary' zone represents the ideal balance of shipping speed and code quality.")
        else:
            st.info("No AI quality data available yet. Run the pipeline with LLM evaluation enabled.")

    with tab2:
        # 2. Unsung Heroes: Diverging Bar / Ratio
        hero_df = df[df["reviews_given"] > 0].copy()
        if not hero_df.empty:
            # Calculate Helpfulness Ratio
            hero_df["helpfulness_ratio"] = hero_df["reviews_given"] / hero_df["prs_merged"].clip(lower=1)
            hero_df = hero_df.sort_values("helpfulness_ratio", ascending=True).tail(10) # Top 10 helpful
            
            fig = go.Figure()
            
            # PRs (Left side, negative)
            fig.add_trace(go.Bar(
                y=hero_df["login"],
                x=hero_df["prs_merged"] * -1,
                name="PRs Shipped",
                orientation='h',
                marker_color="#D1D5DB",
                text=hero_df["prs_merged"],
                textposition="auto"
            ))
            
            # Reviews (Right side, positive)
            fig.add_trace(go.Bar(
                y=hero_df["login"],
                x=hero_df["reviews_given"],
                name="Reviews Given",
                orientation='h',
                marker_color="#818CF8",
                text=hero_df["reviews_given"],
                textposition="auto"
            ))
            
            fig.update_layout(
                title="The Helpers vs The Shippers (Ratio Analysis)",
                barmode='overlay', # actually relative/stack is better for diverging, but let's emulate diverging
                xaxis=dict(title="← Self-Focus (PRs) | Team-Focus (Reviews) →", zeroline=True, zerolinewidth=2, zerolinecolor="#4B5563"),
                yaxis=dict(title=""),
                **PLOTLY_LAYOUT,
                height=500,
                showlegend=True
            )
            # Fix negative labels on X
            fig.update_xaxes(tickformat="s") # plain number
            
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"""
            <div style="background: #EEF2FF; padding: 16px; border-radius: 12px; border: 1px solid #C7D2FE; color: #4338CA;">
                <strong>{doodle("lightbulb", 16, "#4338CA")} Insight:</strong> Engineers extending to the right are the team's multipliers. They spend significantly more time reviewing others' code than shipping their own.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No review data available.")

    with tab3:
        # 3. Impact Breakdown: Stacked Bar
        # Simplify: Aggregate impact of the whole team or top 10
        top_impact = df.head(10).copy()
        
        # Approximate breakdown again
        top_impact["Impact from Shipping"] = top_impact["prs_merged"] * 15
        top_impact["Impact from Helping"] = top_impact["reviews_given"] * 15
        top_impact["Quality Bonus"] = top_impact["impact_score"] - (top_impact["Impact from Shipping"] + top_impact["Impact from Helping"])
        # Clip negative bonus for viz
        top_impact["Quality Bonus"] = top_impact["Quality Bonus"].clip(lower=0)
        
        fig = px.bar(
            top_impact, 
            x=["Impact from Shipping", "Impact from Helping", "Quality Bonus"], 
            y="login",
            orientation='h',
            title="Where does the impact come from?",
            color_discrete_map={
                "Impact from Shipping": "#D1D5DB", 
                "Impact from Helping": "#818CF8", 
                "Quality Bonus": "#34D399"
            },
            labels={"value": "Impact Points", "variable": "Source"}
        )
        
        fig.update_layout(barmode='stack', **PLOTLY_LAYOUT, height=500, xaxis_title="Total Impact Score")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Green segments represent the 'Quality Boost' earned by shipping high-leverage, well-crafted code.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    inject_css()

    data = load_data()
    if not data:
        st.warning("Data not found. Please run `main.py` first to fetch and analyze data.")
        return

    # Hero
    render_hero(data)

    # DataFrame for analysis
    metrics = [c.model_dump() for c in data.contributor_metrics]
    df = pd.DataFrame(metrics)

    if df.empty:
        st.info("No contributor data available.")
        return

    df = df.sort_values(by="impact_score", ascending=False).reset_index(drop=True)

    # Engineer gallery
    top5 = render_engineer_gallery(df, data)

    # Initialize first engineer as selected by default if nothing is selected yet
    if "selected_engineer" not in st.session_state or not st.session_state.get("selected_engineer"):
        if not top5.empty:
            st.session_state["selected_engineer"] = top5.iloc[0]["login"]

    # Selected engineer drill-down
    if "selected_engineer" in st.session_state and st.session_state["selected_engineer"]:
        login = st.session_state["selected_engineer"]
        if login in df["login"].values:
            render_engineer_drilldown(login, df, data)

    # Story analytics
    render_analytics_tabs(df, data)

    # Footer
    st.markdown("---")
    st.caption(f"Data from **{data.repo_name}** · Fetched {str(data.fetched_at)[:10]} · Cutoff {str(data.cutoff_date)[:10]}")


if __name__ == "__main__":
    main()
