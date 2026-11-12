import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import requests
import google.auth.transport.requests
from pydantic import BaseModel, Field
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account
from google import genai
from google.genai import types

from dashboard_builder import generate_web_dashboard

# --- CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "actions_memory.json"
DOCS_DIR = BASE_DIR / "docs"
# --- CARGA DE .ENV LOCAL SI EXISTE ---
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "291106508")
GOOGLE_ADS_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "3686832552")
GOOGLE_ADS_DEVELOPER_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
WEBHOOK_URL = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def resolve_dashboard_url() -> str:
    """Resuelve la URL pública de GitHub Pages para el botón de Google Chat."""
    explicit_url = os.environ.get("DASHBOARD_URL", "").strip()
    if explicit_url:
        return explicit_url
    gh_repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if gh_repo and "/" in gh_repo:
        owner, repo = gh_repo.split("/", 1)
        return f"https://{owner}.github.io/{repo}/"
    return "https://mauro1986ok.github.io/ga4-analytics/"


SEGMENT_ORDER = [
    "Google Ads",
    "Meta Ads (IG/FB/AN)",
    "Google Orgánico",
    "Directo",
    "IA & Otros",
]


# --- ESQUEMA ESTRUCTURED PARA GEMINI ---
class SuggestedAction(BaseModel):
    topic: str = Field(description="Área simple en español claro (ej. ' Textos de la Web', 'Anuncios en Google', 'Formulario de Contacto')")
    title: str = Field(description="Título práctico y directo de la mejora a realizar, sin tecnicismos")
    description: str = Field(description="Explicación sencilla con datos reales de qué está pasando y qué hacer paso a paso")
    target_metric: str = Field(description="Resultado concreto que buscamos lograr en lenguaje simple")


class GeminiReportOutput(BaseModel):
    memory_evaluation_html: str = Field(
        description="Resumen claro y sin tecnicismos en HTML simple (<b>, <br>, <i>) de las tareas completadas y las tareas pendientes."
    )
    insights_html: str = Field(
        description="3 hallazgos prácticos en HTML simple (<b>, <br>, <i>, sin **), explicados en lenguaje cotidiano y directo para un dueño de negocio, usando los números reales para explicar exactamente qué está sucediendo y qué hacer."
    )
    new_actions: list[SuggestedAction] = Field(
        description="Lista de nuevas acciones (o lista vacía [] si las tareas pendientes actuales ya cubren los puntos principales)."
    )


def load_memory():
    """Carga el historial de acciones y sugerencias."""
    if not MEMORY_FILE.exists():
        return {"actions": []}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando actions_memory.json: {e}")
        return {"actions": []}


def save_memory(memory_data):
    """Guarda el historial de acciones."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, indent=2, ensure_ascii=False)


def mark_action_status(action_id, status, notes=""):
    """Permite marcar una acción como 'completed' o 'pending'."""
    mem = load_memory()
    found = False
    for a in mem.get("actions", []):
        if a["id"].upper() == action_id.upper():
            a["status"] = status
            a["updated_at"] = datetime.now().strftime("%Y-%m-%d")
            if notes:
                a["resolution_notes"] = notes
            found = True
            print(f"✅ Acción {action_id} actualizada a estado: {status}")
            break
    if not found:
        print(f"❌ No se encontró la acción con ID {action_id}")
    else:
        save_memory(mem)


def list_actions():
    """Muestra la lista de acciones en consola."""
    mem = load_memory()
    actions = mem.get("actions", [])
    print(f"\n--- HISTORIAL DE ACCIONES ({len(actions)} registradas) ---")
    for a in actions:
        status_icon = "✅" if a.get("status") == "completed" else "⏳"
        print(f"{status_icon} [{a['id']}] ({a.get('status', 'pending')}) - {a.get('title')}")
        print(f"   Creada: {a.get('created_at')} | Tema: {a.get('topic')}")
        print(f"   Detalle: {a.get('description')}")
        if a.get("target_metric"):
            print(f"   Métrica Objetivo: {a.get('target_metric')}")
        if a.get("resolution_notes"):
            print(f"   Notas de resolución: {a.get('resolution_notes')}")
        print("-" * 60)


def get_service_account_credentials(scopes=None):
    """Obtiene credenciales de Service Account desde variable de entorno o archivo local."""
    credentials_json_env = os.environ.get("GA4_CREDENTIALS_JSON")
    if credentials_json_env:
        info = json.loads(credentials_json_env)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)

    local_creds = BASE_DIR / "credentials.json"
    if local_creds.exists():
        return service_account.Credentials.from_service_account_file(str(local_creds), scopes=scopes)

    raise FileNotFoundError("No se encontraron credenciales (credentials.json o GA4_CREDENTIALS_JSON).")


def get_ga4_client():
    """Inicializa el cliente de GA4 soportando archivo local o variable de entorno."""
    creds = get_service_account_credentials()
    return BetaAnalyticsDataClient(credentials=creds)


def fetch_native_google_ads_v23(customer_id: str):
    """
    Consulta directamente la API nativa de Google Ads v23 (con nivel Explorer activo)
    para obtener:
    1) Cuota de Impresiones (Search Impression Share, Lost IS Budget, Lost IS Rank) y Presupuesto Diario.
    2) Nivel de Calidad (Quality Score 1-10) y desglose (Creatividad, CTR esperado, Experiencia en Landing Post-Clic).
    3) Copys reales de Anuncios RSA (Headlines, Descriptions, Ad Strength, URL final).
    """
    try:
        creds = get_service_account_credentials(scopes=["https://www.googleapis.com/auth/adwords"])
        creds.refresh(google.auth.transport.requests.Request())
        headers = {"Authorization": f"Bearer {creds.token}"}
        if GOOGLE_ADS_DEVELOPER_TOKEN:
            headers["developer-token"] = GOOGLE_ADS_DEVELOPER_TOKEN

        url = f"https://googleads.googleapis.com/v23/customers/{customer_id}/googleAds:search"

        def run_gaql(query_str):
            r = requests.post(url, headers=headers, json={"query": query_str}, timeout=15)
            if r.status_code != 200:
                raise RuntimeError(r.text[:300])
            return r.json().get("results", [])

        # 1. Campaign Impression Share & Budgets (Last 30 Days)
        q_campaigns = """
            SELECT
              campaign.name,
              campaign.status,
              campaign_budget.amount_micros,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.search_impression_share,
              metrics.search_budget_lost_impression_share,
              metrics.search_rank_lost_impression_share
            FROM campaign
            WHERE segments.date DURING LAST_30_DAYS AND metrics.impressions > 0
        """
        campaign_is = []
        for row in run_gaql(q_campaigns):
            c = row.get("campaign", {})
            m = row.get("metrics", {})
            b = row.get("campaignBudget", {})
            budget_daily = int(b.get("amountMicros", 0)) / 1_000_000
            cost_30d = int(m.get("costMicros", 0)) / 1_000_000
            sis = float(m.get("searchImpressionShare", 0)) * 100
            lost_budget = float(m.get("searchBudgetLostImpressionShare", 0)) * 100
            lost_rank = float(m.get("searchRankLostImpressionShare", 0)) * 100
            campaign_is.append({
                "campaign": c.get("name", ""),
                "status": c.get("status", ""),
                "daily_budget": round(budget_daily, 2),
                "impressions_30d": int(m.get("impressions", 0)),
                "clicks_30d": int(m.get("clicks", 0)),
                "cost_30d": round(cost_30d, 2),
                "search_impression_share_pct": round(sis, 1),
                "lost_is_budget_pct": round(lost_budget, 1),
                "lost_is_rank_pct": round(lost_rank, 1),
            })

        # 2. Keywords Quality Score & Match Type (Last 30 Days)
        q_keywords = """
            SELECT
              campaign.name,
              ad_group.name,
              ad_group_criterion.keyword.text,
              ad_group_criterion.keyword.match_type,
              ad_group_criterion.quality_info.quality_score,
              ad_group_criterion.quality_info.creative_quality_score,
              ad_group_criterion.quality_info.post_click_quality_score,
              ad_group_criterion.quality_info.search_predicted_ctr,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros
            FROM keyword_view
            WHERE segments.date DURING LAST_30_DAYS AND metrics.impressions > 0
            ORDER BY metrics.impressions DESC
            LIMIT 40
        """
        keywords_qs = []
        for row in run_gaql(q_keywords):
            ag = row.get("adGroup", {})
            crit = row.get("adGroupCriterion", {})
            kw = crit.get("keyword", {})
            qi = crit.get("qualityInfo", {})
            m = row.get("metrics", {})
            keywords_qs.append({
                "ad_group": ag.get("name", ""),
                "keyword": kw.get("text", ""),
                "match_type": kw.get("matchType", ""),
                "quality_score": qi.get("qualityScore", None),
                "creative_quality": qi.get("creativeQualityScore", "N/A"),
                "landing_experience": qi.get("postClickQualityScore", "N/A"),
                "expected_ctr": qi.get("searchPredictedCtr", "N/A"),
                "impressions_30d": int(m.get("impressions", 0)),
                "clicks_30d": int(m.get("clicks", 0)),
                "cost_30d": round(int(m.get("costMicros", 0)) / 1_000_000, 2),
            })

        # Calcular métricas globales de Quality Score
        scored_kws = [k for k in keywords_qs if k["quality_score"] is not None]
        total_scored_imp = sum(k["impressions_30d"] for k in scored_kws)
        weighted_avg_qs = (
            sum(k["quality_score"] * k["impressions_30d"] for k in scored_kws) / total_scored_imp
            if total_scored_imp > 0
            else 0.0
        )
        critical_count = sum(1 for k in scored_kws if k["quality_score"] <= 3)
        below_avg_landing_count = sum(1 for k in scored_kws if k["landing_experience"] == "BELOW_AVERAGE")
        total_scored_cost = sum(k["cost_30d"] for k in scored_kws)

        # 3. RSA Ads Headlines, Descriptions & Ad Strength (Last 30 Days)
        q_ads = """
            SELECT
              campaign.name,
              ad_group.name,
              ad_group_ad.ad.id,
              ad_group_ad.ad_strength,
              ad_group_ad.ad.final_urls,
              ad_group_ad.ad.responsive_search_ad.headlines,
              ad_group_ad.ad.responsive_search_ad.descriptions,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros
            FROM ad_group_ad
            WHERE segments.date DURING LAST_30_DAYS AND metrics.impressions > 0
            ORDER BY metrics.impressions DESC
            LIMIT 15
        """
        rsa_ads = []
        for row in run_gaql(q_ads):
            ag = row.get("adGroup", {})
            aga = row.get("adGroupAd", {})
            ad = aga.get("ad", {})
            rsa = ad.get("responsiveSearchAd", {})
            m = row.get("metrics", {})
            headlines = [h.get("text", "") for h in rsa.get("headlines", []) if h.get("text")]
            descriptions = [d.get("text", "") for d in rsa.get("descriptions", []) if d.get("text")]
            imp = int(m.get("impressions", 0))
            clicks = int(m.get("clicks", 0))
            rsa_ads.append({
                "ad_id": str(ad.get("id", "")),
                "ad_group": ag.get("name", ""),
                "ad_strength": aga.get("adStrength", ""),
                "final_url": (ad.get("finalUrls") or [""])[0],
                "headlines": headlines[:6],
                "descriptions": descriptions[:3],
                "impressions_30d": imp,
                "clicks_30d": clicks,
                "ctr_30d": round((clicks / imp * 100), 2) if imp > 0 else 0.0,
                "cost_30d": round(int(m.get("costMicros", 0)) / 1_000_000, 2),
            })

        return {
            "status": "ok",
            "campaign_impression_share": campaign_is,
            "keywords_quality_score": keywords_qs,
            "quality_score_summary": {
                "weighted_avg_qs": round(weighted_avg_qs, 2),
                "total_scored_keywords": len(scored_kws),
                "critical_keywords_count": critical_count,
                "below_avg_landing_count": below_avg_landing_count,
                "total_cost_30d": round(total_scored_cost, 2),
            },
            "rsa_ads": rsa_ads,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "campaign_impression_share": [],
            "keywords_quality_score": [],
            "quality_score_summary": {
                "weighted_avg_qs": 0.0,
                "total_scored_keywords": 0,
                "critical_keywords_count": 0,
                "below_avg_landing_count": 0,
                "total_cost_30d": 0.0,
            },
            "rsa_ads": [],
        }


def format_duration(seconds):
    """Convierte segundos a formato 'Xm Ys'."""
    sec = int(round(seconds))
    minutes = sec // 60
    remaining_seconds = sec % 60
    if minutes > 0:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def format_delta(curr, prev):
    """Calcula la variación porcentual WoW y devuelve un string con signo."""
    if prev is None or prev == 0:
        if curr > 0:
            return "+nuevo"
        return "0%"
    diff_pct = ((curr - prev) / prev) * 100.0
    sign = "+" if diff_pct > 0 else ""
    return f"{sign}{diff_pct:.0f}%"


def classify_segment(channel_group, source_medium):
    """Clasifica el tráfico en los 5 segmentos estratégicos acordados."""
    ch = channel_group.lower()
    sm = source_medium.lower()

    if "google / cpc" in sm or "adwords" in sm or ch in ["paid search", "cross-network", "paid shopping"]:
        return "Google Ads"
    if (
        any(tag in sm for tag in ["ig / paid", "fb / paid", "an / paid", "th / paid", "facebook", "instagram", "meta"])
        or ch in ["paid social", "paid other"]
    ):
        return "Meta Ads (IG/FB/AN)"
    if "google / organic" in sm or (ch == "organic search" and "google" in sm):
        return "Google Orgánico"
    if "(direct)" in sm or ch == "direct":
        return "Directo"
    return "IA & Otros"


def fetch_channel_data(client, property_id, start_days_ago, end_days_ago=1, label=""):
    """Consulta métricas de canales y las agrupa en los 5 segmentos."""
    end_str = "yesterday" if end_days_ago == 1 else f"{end_days_ago}daysAgo"
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionDefaultChannelGroup"),
            Dimension(name="sessionSourceMedium"),
        ],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="screenPageViewsPerSession"),
            Metric(name="keyEvents"),
        ],
        date_ranges=[DateRange(start_date=f"{start_days_ago}daysAgo", end_date=end_str)],
    )

    response = client.run_report(request)
    segments = {
        seg: {
            "users": 0,
            "sessions": 0,
            "engaged_sessions": 0.0,
            "total_duration": 0.0,
            "total_views": 0.0,
            "key_events": 0,
            "sub_sources": {},
        }
        for seg in SEGMENT_ORDER
    }

    for row in response.rows:
        ch = row.dimension_values[0].value
        sm = row.dimension_values[1].value
        seg = classify_segment(ch, sm)

        users = int(row.metric_values[0].value)
        sessions = int(row.metric_values[1].value)
        eng_rate = float(row.metric_values[2].value)
        avg_dur = float(row.metric_values[3].value)
        pages_per_sess = float(row.metric_values[4].value)
        events = int(float(row.metric_values[5].value))

        s = segments[seg]
        s["users"] += users
        s["sessions"] += sessions
        s["engaged_sessions"] += eng_rate * sessions
        s["total_duration"] += avg_dur * sessions
        s["total_views"] += pages_per_sess * sessions
        s["key_events"] += events

        if sm not in s["sub_sources"]:
            s["sub_sources"][sm] = {"sessions": 0, "total_dur": 0.0, "engaged": 0.0, "key_events": 0}
        s["sub_sources"][sm]["sessions"] += sessions
        s["sub_sources"][sm]["total_dur"] += avg_dur * sessions
        s["sub_sources"][sm]["engaged"] += eng_rate * sessions
        s["sub_sources"][sm]["key_events"] += events

    result = {"label": label, "segments": {}}
    for seg_name in SEGMENT_ORDER:
        s = segments[seg_name]
        sess = s["sessions"]
        breakdown = {}
        for sm_key, sm_val in sorted(s["sub_sources"].items(), key=lambda x: x[1]["sessions"], reverse=True)[:4]:
            sm_sess = sm_val["sessions"]
            breakdown[sm_key] = {
                "sessions": sm_sess,
                "avg_duration": (sm_val["total_dur"] / sm_sess) if sm_sess > 0 else 0.0,
                "engagement_rate": (sm_val["engaged"] / sm_sess * 100) if sm_sess > 0 else 0.0,
                "key_events": sm_val["key_events"],
            }

        result["segments"][seg_name] = {
            "users": s["users"],
            "sessions": sess,
            "engagement_rate": (s["engaged_sessions"] / sess * 100) if sess > 0 else 0.0,
            "avg_duration": (s["total_duration"] / sess) if sess > 0 else 0.0,
            "pages_per_session": (s["total_views"] / sess) if sess > 0 else 0.0,
            "key_events": s["key_events"],
            "top_sources": breakdown,
        }
    return result


def compute_wow_deltas(data_7d, data_prev_7d):
    """Calcula variaciones WoW (%) comparando los últimos 7 días contra los 7 días anteriores."""
    deltas = {}
    for seg_name in SEGMENT_ORDER:
        curr = data_7d["segments"][seg_name]
        prev = data_prev_7d["segments"][seg_name]
        deltas[seg_name] = {
            "sessions_delta": format_delta(curr["sessions"], prev["sessions"]),
            "duration_delta": format_delta(curr["avg_duration"], prev["avg_duration"]),
            "engagement_delta": format_delta(curr["engagement_rate"], prev["engagement_rate"]),
            "prev_sessions": prev["sessions"],
        }
    return deltas


def fetch_google_ads_financials(client, property_id):
    """Cruza Campaña + Grupo de Anuncios + Impresiones + Gasto + Clics vs Sesiones + Costo por Sesión Interactiva."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionGoogleAdsCampaignName"),
            Dimension(name="sessionGoogleAdsAdGroupName"),
        ],
        metrics=[
            Metric(name="advertiserAdImpressions"),
            Metric(name="advertiserAdClicks"),
            Metric(name="advertiserAdCost"),
            Metric(name="sessions"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="keyEvents"),
        ],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
        limit=25,
    )
    response = client.run_report(request)
    campaigns = []
    for row in response.rows:
        camp = row.dimension_values[0].value
        adgroup = row.dimension_values[1].value
        if camp == "(not set)" and adgroup == "(not set)":
            continue
        impressions = int(float(row.metric_values[0].value))
        clicks = int(float(row.metric_values[1].value))
        cost = float(row.metric_values[2].value)
        sessions = int(row.metric_values[3].value)
        eng_rate = float(row.metric_values[4].value)
        avg_dur = float(row.metric_values[5].value)
        key_events = int(float(row.metric_values[6].value))

        ctr = (clicks / impressions * 100.0) if impressions > 0 else 0.0
        engaged_sessions = sessions * eng_rate
        cost_per_engaged = (cost / engaged_sessions) if engaged_sessions > 0 else 0.0
        click_to_session_rate = (sessions / clicks * 100.0) if clicks > 0 else 0.0

        campaigns.append({
            "campaign": camp,
            "ad_group": adgroup,
            "impressions": impressions,
            "clicks": clicks,
            "ctr_pct": round(ctr, 2),
            "sessions": sessions,
            "click_retention_pct": round(click_to_session_rate, 1),
            "cost": round(cost, 2),
            "cpc": round(cost / clicks, 2) if clicks > 0 else 0.0,
            "cost_per_engaged_session": round(cost_per_engaged, 2),
            "engagement_rate": round(eng_rate * 100, 1),
            "avg_duration": avg_dur,
            "key_events": key_events,
        })
    campaigns.sort(key=lambda x: x["cost"], reverse=True)
    return campaigns


def fetch_google_ads_bidded_keywords(client, property_id):
    """Extrae las Keywords compradas en Google Ads con Impresiones, CTR %, CPC, Gasto y Permanencia."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionGoogleAdsAdGroupName"),
            Dimension(name="sessionGoogleAdsKeyword"),
        ],
        metrics=[
            Metric(name="advertiserAdImpressions"),
            Metric(name="advertiserAdClicks"),
            Metric(name="advertiserAdCost"),
            Metric(name="sessions"),
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
        ],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
        limit=30,
    )
    response = client.run_report(request)
    bidded = []
    for row in response.rows:
        adgroup = row.dimension_values[0].value
        kw = row.dimension_values[1].value
        if kw == "(not set)" or not kw:
            continue
        imp = int(float(row.metric_values[0].value))
        clicks = int(float(row.metric_values[1].value))
        cost = float(row.metric_values[2].value)
        sess = int(row.metric_values[3].value)
        dur = float(row.metric_values[4].value)
        eng = float(row.metric_values[5].value) * 100.0
        ctr = (clicks / imp * 100.0) if imp > 0 else 0.0
        cpc = (cost / clicks) if clicks > 0 else 0.0

        bidded.append({
            "ad_group": adgroup,
            "keyword": kw,
            "impressions": imp,
            "clicks": clicks,
            "ctr_pct": round(ctr, 2),
            "cost": round(cost, 2),
            "cpc": round(cpc, 2),
            "sessions": sess,
            "avg_duration": round(dur, 1),
            "engagement_rate": round(eng, 1),
        })
    bidded.sort(key=lambda x: x["impressions"], reverse=True)
    return bidded


def fetch_google_ads_creatives_and_network(client, property_id):
    """Extrae el rendimiento por Anuncio (Creative ID) y Red (Google Search vs Search Partners)."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionGoogleAdsAdGroupName"),
            Dimension(name="sessionGoogleAdsCreativeId"),
            Dimension(name="sessionGoogleAdsAdNetworkType"),
        ],
        metrics=[
            Metric(name="advertiserAdImpressions"),
            Metric(name="advertiserAdClicks"),
            Metric(name="advertiserAdCost"),
            Metric(name="sessions"),
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
        ],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
        limit=25,
    )
    response = client.run_report(request)
    creatives = []
    for row in response.rows:
        adgroup = row.dimension_values[0].value
        creative_id = row.dimension_values[1].value
        network = row.dimension_values[2].value
        if creative_id == "(not set)" or not creative_id:
            continue
        imp = int(float(row.metric_values[0].value))
        clicks = int(float(row.metric_values[1].value))
        cost = float(row.metric_values[2].value)
        sess = int(row.metric_values[3].value)
        dur = float(row.metric_values[4].value)
        eng = float(row.metric_values[5].value) * 100.0
        ctr = (clicks / imp * 100.0) if imp > 0 else 0.0

        creatives.append({
            "ad_group": adgroup,
            "creative_id": creative_id,
            "network": network,
            "impressions": imp,
            "clicks": clicks,
            "ctr_pct": round(ctr, 2),
            "cost": round(cost, 2),
            "sessions": sess,
            "avg_duration": round(dur, 1),
            "engagement_rate": round(eng, 1),
        })
    creatives.sort(key=lambda x: x["cost"], reverse=True)
    return creatives


def fetch_google_ads_keywords(client, property_id):
    """Cruza Google Ads Search Queries reales con la Landing Page y tiempo de retención."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="landingPage"),
            Dimension(name="sessionGoogleAdsQuery"),
        ],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
            Metric(name="keyEvents"),
        ],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
        limit=50,
    )
    response = client.run_report(request)
    keywords_data = []
    for row in response.rows:
        landing = row.dimension_values[0].value
        query = row.dimension_values[1].value
        if query == "(not set)" or not query:
            continue
        keywords_data.append({
            "landing": landing,
            "query": query,
            "users": int(row.metric_values[0].value),
            "sessions": int(row.metric_values[1].value),
            "avg_duration": float(row.metric_values[2].value),
            "engagement_rate": float(row.metric_values[3].value) * 100,
            "key_events": int(float(row.metric_values[4].value)),
        })
    keywords_data.sort(key=lambda x: x["avg_duration"], reverse=True)
    return keywords_data


def fetch_device_x_channel(client, property_id):
    """Cruza Dispositivo (Desktop vs Mobile) en canales pagos y orgánicos (últimos 90 días)."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="deviceCategory"),
            Dimension(name="sessionDefaultChannelGroup"),
            Dimension(name="sessionSourceMedium"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="keyEvents"),
        ],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
        limit=50,
    )
    response = client.run_report(request)
    matrix = {}
    for seg in ["Google Ads", "Meta Ads (IG/FB/AN)", "Google Orgánico", "Directo"]:
        matrix[seg] = {
            "desktop": {"sessions": 0, "engaged": 0.0, "dur": 0.0, "conv": 0},
            "mobile": {"sessions": 0, "engaged": 0.0, "dur": 0.0, "conv": 0},
        }

    for row in response.rows:
        dev = row.dimension_values[0].value.lower()
        if dev not in ["desktop", "mobile"]:
            continue
        ch = row.dimension_values[1].value
        sm = row.dimension_values[2].value
        seg = classify_segment(ch, sm)
        if seg not in matrix:
            continue

        sess = int(row.metric_values[0].value)
        eng = float(row.metric_values[1].value)
        dur = float(row.metric_values[2].value)
        conv = int(float(row.metric_values[3].value))

        cell = matrix[seg][dev]
        cell["sessions"] += sess
        cell["engaged"] += eng * sess
        cell["dur"] += dur * sess
        cell["conv"] += conv

    summary = {}
    for seg, devs in matrix.items():
        summary[seg] = {}
        for dev, d in devs.items():
            s = d["sessions"]
            summary[seg][dev] = {
                "sessions": s,
                "engagement_rate": round((d["engaged"] / s * 100), 1) if s > 0 else 0.0,
                "avg_duration": round((d["dur"] / s), 1) if s > 0 else 0.0,
                "key_events": d["conv"],
                "conv_rate": round((d["conv"] / s * 100), 2) if s > 0 else 0.0,
            }
    return summary


def fetch_hablemos_funnel_audit(client, property_id):
    """Audita el embudo hacia /hablemos/, paridad page_view = conversión y pérdida de atribución a Directo."""
    req_events = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="pagePath"), Dimension(name="eventName")],
        metrics=[Metric(name="eventCount"), Metric(name="totalUsers")],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
        limit=50,
    )
    resp_events = client.run_report(req_events)
    hablemos_events = {}
    for row in resp_events.rows:
        path = row.dimension_values[0].value
        ev = row.dimension_values[1].value
        if "hablemos" in path:
            hablemos_events[ev] = hablemos_events.get(ev, 0) + int(row.metric_values[0].value)

    req_attr = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="firstUserSourceMedium"),
            Dimension(name="sessionSourceMedium"),
            Dimension(name="pageReferrer"),
        ],
        metrics=[Metric(name="sessions"), Metric(name="keyEvents"), Metric(name="averageSessionDuration")],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
        limit=40,
    )
    resp_attr = client.run_report(req_attr)
    attribution_rows = []
    for row in resp_attr.rows:
        ke = int(float(row.metric_values[1].value))
        if ke > 0:
            attribution_rows.append({
                "first_user_source_medium": row.dimension_values[0].value,
                "session_source_medium": row.dimension_values[1].value,
                "page_referrer": row.dimension_values[2].value or "(sin referrer)",
                "sessions": int(row.metric_values[0].value),
                "key_events": ke,
                "avg_duration": round(float(row.metric_values[2].value), 1),
            })
    attribution_rows.sort(key=lambda x: x["key_events"], reverse=True)

    page_views = hablemos_events.get("page_view", 0)
    conversions = hablemos_events.get("ads_conversion_Solicitar_cotizaci_n_1", 0)
    session_starts = hablemos_events.get("session_start", 0)

    return {
        "hablemos_page_views_90d": page_views,
        "hablemos_conversions_90d": conversions,
        "hablemos_session_starts_90d": session_starts,
        "is_1to1_pageview_trigger": (page_views > 0 and page_views == conversions),
        "direct_session_reset_pct": round((session_starts / page_views * 100), 1) if page_views > 0 else 0.0,
        "conversion_attribution_breakdown": attribution_rows[:10],
    }


def fetch_geo_x_channel(client, property_id):
    """Cruza Top Provincias de Argentina con Canal y métricas de calidad (últimos 90 días)."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="country"),
            Dimension(name="region"),
            Dimension(name="sessionDefaultChannelGroup"),
            Dimension(name="sessionSourceMedium"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="keyEvents"),
        ],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
        limit=60,
    )
    response = client.run_report(request)
    provinces = {}
    for row in response.rows:
        country = row.dimension_values[0].value
        region = row.dimension_values[1].value
        if country != "Argentina" or region in ["(not set)", ""]:
            continue
        ch = row.dimension_values[2].value
        sm = row.dimension_values[3].value
        seg = classify_segment(ch, sm)

        sess = int(row.metric_values[0].value)
        eng = float(row.metric_values[1].value)
        dur = float(row.metric_values[2].value)
        conv = int(float(row.metric_values[3].value))

        if region not in provinces:
            provinces[region] = {
                "sessions": 0,
                "engaged": 0.0,
                "dur": 0.0,
                "conv": 0,
                "by_segment": {},
            }
        p = provinces[region]
        p["sessions"] += sess
        p["engaged"] += eng * sess
        p["dur"] += dur * sess
        p["conv"] += conv

        if seg not in p["by_segment"]:
            p["by_segment"][seg] = {"sessions": 0, "dur": 0.0, "engaged": 0.0, "conv": 0}
        ps = p["by_segment"][seg]
        ps["sessions"] += sess
        ps["dur"] += dur * sess
        ps["engaged"] += eng * sess
        ps["conv"] += conv

    sorted_provs = sorted(provinces.items(), key=lambda x: x[1]["sessions"], reverse=True)[:6]
    geo_summary = []
    for prov_name, p in sorted_provs:
        s = p["sessions"]
        seg_details = []
        for seg_name, ps in sorted(p["by_segment"].items(), key=lambda x: x[1]["sessions"], reverse=True)[:3]:
            ss = ps["sessions"]
            seg_details.append(
                f"{seg_name}: {ss} ses ({format_duration(ps['dur']/ss if ss else 0)}, {ps['engaged']/ss*100 if ss else 0:.0f}% eng)"
            )
        geo_summary.append({
            "province": prov_name.replace(" Province", ""),
            "sessions": s,
            "avg_duration": round(p["dur"] / s, 1) if s > 0 else 0.0,
            "engagement_rate": round(p["engaged"] / s * 100, 1) if s > 0 else 0.0,
            "key_events": p["conv"],
            "top_segments": seg_details,
        })
    return geo_summary


def fetch_target_landings(client, property_id):
    """Consulta específicamente las 3 landings clave: Habilitaciones, Huella de Carbono, Sustentabilidad."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="landingPage")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
            Metric(name="keyEvents"),
        ],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="yesterday")],
        limit=50,
    )
    response = client.run_report(request)
    landings_result = {
        "Habilitaciones y Permisos": {"users": 0, "sessions": 0, "total_dur": 0.0, "engaged": 0.0, "events": 0, "paths": []},
        "Huella de Carbono": {"users": 0, "sessions": 0, "total_dur": 0.0, "engaged": 0.0, "events": 0, "paths": []},
        "Sustentabilidad": {"users": 0, "sessions": 0, "total_dur": 0.0, "engaged": 0.0, "events": 0, "paths": []},
    }

    for row in response.rows:
        lp = row.dimension_values[0].value
        users = int(row.metric_values[0].value)
        sessions = int(row.metric_values[1].value)
        dur = float(row.metric_values[2].value)
        eng = float(row.metric_values[3].value)
        events = int(float(row.metric_values[4].value))

        cat = None
        if "habilitaciones" in lp:
            cat = "Habilitaciones y Permisos"
        elif "huella" in lp:
            cat = "Huella de Carbono"
        elif "sustentab" in lp:
            cat = "Sustentabilidad"

        if cat:
            g = landings_result[cat]
            g["users"] += users
            g["sessions"] += sessions
            g["total_dur"] += dur * sessions
            g["engaged"] += eng * sessions
            g["events"] += events
            g["paths"].append(f"{lp} ({users} u, {format_duration(dur)})")

    summary = {}
    for cat, g in landings_result.items():
        s = g["sessions"]
        summary[cat] = {
            "users": g["users"],
            "sessions": s,
            "avg_duration": (g["total_dur"] / s) if s > 0 else 0.0,
            "engagement_rate": (g["engaged"] / s * 100) if s > 0 else 0.0,
            "key_events": g["events"],
            "paths": g["paths"][:3],
        }
    return summary


def fetch_content_data(client, property_id):
    """Consulta páginas principales y desempeño de artículos."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="pagePath"), Dimension(name="pageTitle")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="averageSessionDuration"),
            Metric(name="screenPageViews"),
            Metric(name="engagementRate"),
        ],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="yesterday")],
        limit=25,
    )
    response = client.run_report(request)
    pages = []
    for row in response.rows:
        pages.append({
            "path": row.dimension_values[0].value,
            "title": row.dimension_values[1].value,
            "users": int(row.metric_values[0].value),
            "sessions": int(row.metric_values[1].value),
            "avg_duration": float(row.metric_values[2].value),
            "views": int(row.metric_values[3].value),
            "engagement_rate": float(row.metric_values[4].value) * 100,
        })
    return pages


def build_metrics_snapshot(data_30d, target_landings, hablemos_audit, ads_financials, native_ads_v23=None):
    """Construye una foto resumida de las métricas actuales para guardar en actions_memory.json."""
    total_ads_cost = sum(c["cost"] for c in ads_financials)
    qs_summary = (native_ads_v23 or {}).get("quality_score_summary", {})
    return {
        "captured_at": datetime.now().strftime("%Y-%m-%d"),
        "quality_score_weighted_avg": qs_summary.get("weighted_avg_qs", 0.0),
        "quality_score_critical_count": qs_summary.get("critical_keywords_count", 0),
        "google_ads_30d_sessions": data_30d["segments"]["Google Ads"]["sessions"],
        "google_ads_30d_eng_rate": round(data_30d["segments"]["Google Ads"]["engagement_rate"], 1),
        "meta_ads_30d_sessions": data_30d["segments"]["Meta Ads (IG/FB/AN)"]["sessions"],
        "meta_ads_30d_eng_rate": round(data_30d["segments"]["Meta Ads (IG/FB/AN)"]["engagement_rate"], 1),
        "organic_30d_sessions": data_30d["segments"]["Google Orgánico"]["sessions"],
        "ads_cost_90d": round(total_ads_cost, 2),
        "hablemos_views_90d": hablemos_audit["hablemos_page_views_90d"],
        "hablemos_conversions_90d": hablemos_audit["hablemos_conversions_90d"],
        "hablemos_direct_reset_pct": hablemos_audit["direct_session_reset_pct"],
        "landings_30d": {
            k: {"sessions": v["sessions"], "avg_duration_sec": round(v["avg_duration"], 1), "eng_rate": round(v["engagement_rate"], 1)}
            for k, v in target_landings.items()
        },
    }


def update_memory_with_new_actions(memory_data, new_actions, current_snapshot):
    """Guarda automáticamente las nuevas acciones sugeridas por Gemini con su snapshot base."""
    actions = memory_data.get("actions", [])

    for a in actions:
        if "baseline_snapshot" not in a:
            a["baseline_snapshot"] = current_snapshot

    existing_titles = {a.get("title", "").strip().lower() for a in actions}
    next_num = len(actions) + 1

    added_ids = []
    for na in new_actions:
        if na.title.strip().lower() in existing_titles:
            continue
        new_id = f"ACT-{next_num:03d}"
        next_num += 1
        actions.append({
            "id": new_id,
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "topic": na.topic,
            "title": na.title,
            "description": na.description,
            "target_metric": na.target_metric,
            "status": "pending",
            "resolution_notes": "",
            "baseline_snapshot": current_snapshot,
        })
        added_ids.append(new_id)

    memory_data["actions"] = actions
    memory_data["last_run_snapshot"] = current_snapshot
    save_memory(memory_data)
    if added_ids:
        print(f"💾 Se auto-registraron nuevas acciones en actions_memory.json: {', '.join(added_ids)}")
    return added_ids


def generate_insights_with_gemini(
    data_7d,
    wow_deltas,
    data_30d,
    data_90d,
    ads_financials,
    ads_bidded_keywords,
    ads_creatives,
    ads_keywords,
    native_ads_v23,
    device_matrix,
    hablemos_audit,
    geo_summary,
    target_landings,
    content_data,
    memory_data,
    current_snapshot,
):
    """Usa Gemini con salida estructurada JSON para evaluar memoria, generar insights y auto-registrar acciones."""
    print("🤖 Consultando a Gemini API con Google Ads API v23 nativa + GA4...")

    client = genai.Client(api_key=GEMINI_API_KEY)

    past_actions = memory_data.get("actions", [])
    pending_actions = [a for a in past_actions if a.get("status") == "pending"]
    completed_actions = [a for a in past_actions if a.get("status") == "completed"]

    summary_payload = {
        "completed_actions": completed_actions,
        "pending_actions": [
            {"id": a["id"], "title": a["title"], "topic": a["topic"], "description": a["description"]}
            for a in pending_actions
        ],
        "current_snapshot": current_snapshot,
        "channels_7d": data_7d["segments"],
        "wow_deltas_7d_vs_prev7d": wow_deltas,
        "channels_30d": data_30d["segments"],
        "channels_90d": data_90d["segments"],
        "native_google_ads_api_v23": native_ads_v23,
        "google_ads_financials_90d": ads_financials,
        "google_ads_bidded_keywords_90d": ads_bidded_keywords[:15],
        "google_ads_creatives_and_network_90d": ads_creatives[:12],
        "google_ads_top_search_queries_90d": ads_keywords[:12],
        "device_x_channel_90d": device_matrix,
        "hablemos_funnel_audit_90d": hablemos_audit,
        "geo_provinces_90d": geo_summary,
        "target_landings_30d": target_landings,
        "top_pages_30d": content_data[:10],
    }

    prompt = """
Eres el Asesor Senior de Negocios y Marketing de Dhartec (https://www.dhartec.com - Consultora de Ingeniería Ambiental en Argentina).
Tu lector es el dueño o director de la empresa. NO uses jerga técnica publicitaria incomprensible (evita tecnicismos vacíos como 'concordancia de frase', 'fuga técnica', 'attribution reset', 'postClickQualityScore').
Explica con MANZANAS qué está pasando con la plata, las visitas y las consultas reales, usando los números del JSON para dar INDICACIONES EXACTAS Y PRÁCTICAS.

REGLAS ESTRICTAS DE REDACCIÓN:
1. Usa ÚNICAMENTE etiquetas HTML simples (<b>, <i>, <br>). PROHIBIDO usar Markdown (**, ###, *).
2. Estructura exactamente estos 3 bloques en `insights_html`:

   • <b>💰 1. Publicidad en Google: Por qué no aparecemos más y dónde se va la plata</b>
     Explica con números reales:
     - En Habilitaciones ('CAMPAÑA-UNI-HAB.AR') tenemos presupuesto de sobra (solo perdemos 0.8% de apariciones por plata), pero en 6 de cada 10 búsquedas (66.7%) NO aparecemos porque Google califica a nuestra página web con notas muy bajas (1 a 3 sobre 10 en 'gestión ambiental' e 'informe de impacto'). Qué hacer exactamente: poner esas frases exactas en los títulos de /habilitaciones-permisos/ para duplicar apariciones sin gastar un peso más.
     - Dónde sí funciona y dónde se pierde plata: las búsquedas de 'gestoría medioambiental' y 'consultor ambiental' retienen entre 6 y 8 minutos de lectura, mientras que frases amplias como 'reducir la huella de carbono' apenas retienen 58 segundos. Además, en 'Partners de búsqueda' (sitios secundarios fuera de Google) la gente se va en 6 segundos.
     - Indicación clara: destildar 'Partners de búsqueda' en la configuración de Google Ads y subirle el presupuesto a las búsquedas de consultoría/gestoría.

   • <b>🚨 2. Formulario de Contacto, Celulares vs. Computadoras e Instagram</b>
     Explica con números reales:
     - Qué pasa en la página de contacto (/hablemos/): hoy el sistema cuenta que hubo 143 consultas porque está mal configurado y cuenta como consulta a cualquiera que solo abrió la página sin mandar nada. Además, el 55% de los que entran ahí pierden el origen de qué anuncio los trajo. Indicación: pedirle al programador web que la consulta se cuente recién cuando la persona hace clic en 'Enviar formulario'.
     - Celulares vs. Computadoras: en Google Ads, quienes entran desde una computadora leen más de 3 minutos y generan las consultas, pero se gasta el doble de plata en celulares donde solo están 1m 17s y nadie consulta. Y en Instagram entraron 3.381 visitas que duraron 2 segundos (toques accidentales en la pantalla).
     - Indicación clara: bajar la oferta de costo en celulares para que los anuncios salgan más en computadoras de oficina, y pausar o revisar los anuncios en Instagram.

   • <b>🗺️ 3. Provincias y Servicios que más rinden</b>
     Explica con números reales:
     - Dónde están los clientes más interesados: Buenos Aires y CABA concentran las búsquedas inmediatas de habilitaciones, pero en provincias industriales como Mendoza (casi 3 minutos de lectura promedio y hasta 5m 45s) y Santa Fe (más de 2 minutos) hay mucho tiempo de lectura.
     - Indicación clara: asegurarse de que en la página de habilitaciones se aclare que se trabaja con normativas provinciales de PBA, CABA, Santa Fe y Mendoza, y sumar botones de consulta dentro de los artículos de residuos y sustentabilidad.

3. En `memory_evaluation_html`:
   - Escribe un resumen ultra claro y amigable en 3-4 renglones explicando qué tareas se implementaron y cuáles siguen pendientes (indicando qué beneficio traerá hacerlas).

4. En `new_actions`:
   - Si las 7 acciones pendientes ya cubren los puntos principales, devuelve una lista vacía `[]`. Solo genera una acción si encuentras algo nuevo y muy concreto, redactado en lenguaje 100% cotidiano.
"""

    for model_name in ["gemini-3.8-flash", "gemini-2.5-flash"]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt + "\n\nDATOS JSON:\n" + json.dumps(summary_payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiReportOutput,
                    temperature=0.2,
                ),
            )
            parsed = GeminiReportOutput.model_validate_json(response.text)
            added_ids = update_memory_with_new_actions(memory_data, parsed.new_actions, current_snapshot)
            return parsed, added_ids
        except Exception as e:
            print(f"Aviso con modelo {model_name}: {e}")

    fallback = GeminiReportOutput(
        memory_evaluation_html="⏳ Acciones pendientes en seguimiento.",
        insights_html="⚠️ No se pudieron generar insights automáticos en esta ejecución.",
        new_actions=[],
    )
    return fallback, []


def build_google_chat_card(
    data_7d,
    ads_financials,
    hablemos_audit,
    gemini_output,
    added_ids,
    dashboard_url: str,
    native_ads_v23=None,
):
    """
    Construye el mensaje ejecutivo compacto de Google Chat Card v2:
    Contiene únicamente la Memoria de Acciones, los Insights y Mejoras de Gemini,
    y el botón de acceso directo al Dashboard Web Estadístico.
    """
    total_sess_7d = sum(s["sessions"] for s in data_7d["segments"].values())
    total_ads_cost_90d = sum(c["cost"] for c in ads_financials)
    total_conv_90d = hablemos_audit.get("hablemos_conversions_90d", 0)
    qs_summary = (native_ads_v23 or {}).get("quality_score_summary", {})
    avg_qs = qs_summary.get("weighted_avg_qs", 0.0)
    crit_qs = qs_summary.get("critical_keywords_count", 0)

    new_act_banner = ""
    if added_ids:
        new_act_banner = f"<br><br>💾 <b>Nuevas acciones auto-registradas hoy en memoria:</b> {', '.join(added_ids)}"

    card_payload = {
        "cardsV2": [
            {
                "cardId": "weekly_ga4_executive_summary",
                "card": {
                    "header": {
                        "title": "📊 Inteligencia Ejecutiva GA4 & Ads API v23 - Dhartec",
                        "subtitle": f"Insights, Quality Score, Mejoras & Link al Dashboard Web | {datetime.now().strftime('%d/%m/%Y')}",
                        "imageUrl": "https://www.gstatic.com/images/branding/product/2x/analytics_48dp.png",
                        "imageType": "SQUARE",
                    },
                    "sections": [
                        {
                            "header": "💡 Insights Estratégicos y Mejoras de la Semana (Gemini AI)",
                            "collapsible": False,
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": f"{gemini_output.insights_html}{new_act_banner}"
                                    }
                                }
                            ],
                        },
                        {
                            "header": "🧠 Estado de Memoria de Acciones",
                            "collapsible": True,
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": gemini_output.memory_evaluation_html
                                    }
                                }
                            ],
                        },
                        {
                            "header": "🌐 Tablero Estadístico Web Completo",
                            "collapsible": False,
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": (
                                            f"<b>Resumen Rápido:</b> {total_sess_7d} sesiones (últimos 7d) | "
                                            f"Inversión Ads (90d): <b>${total_ads_cost_90d:.2f}</b> | "
                                            f"<b>Quality Score Promedio:</b> <b>{avg_qs:.1f}/10</b> <i>({crit_qs} keywords en alerta crítica 1-3)</i>.<br>"
                                            f"<i>Todos los gráficos interactivos, diagnóstico de Quality Score (1-10), Cuota de Impresiones, Copys RSA y Tareas Pendientes están en la web:</i>"
                                        )
                                    }
                                },
                                {
                                    "buttonList": {
                                        "buttons": [
                                            {
                                                "text": "📊 Abrir Dashboard Estadístico Web",
                                                "onClick": {
                                                    "openLink": {
                                                        "url": dashboard_url
                                                    }
                                                },
                                            }
                                        ]
                                    }
                                },
                            ],
                        },
                    ],
                },
            }
        ]
    }
    return card_payload


def send_to_google_chat(payload, webhook_url):
    """Envía la tarjeta a Google Chat vía webhook."""
    print("📤 Enviando tarjeta ejecutiva compacta a Google Chat...")
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    resp = requests.post(webhook_url, json=payload, headers=headers)
    if resp.status_code == 200:
        print("✅ Reporte enviado exitosamente a Google Chat!")
        return True
    else:
        print(f"❌ Error al enviar a Google Chat: {resp.status_code} - {resp.text}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Reporte Semanal GA4 + Google Ads + Gemini AI + Dashboard Web")
    parser.add_argument("--mark-completed", help="Marca un ID de acción como completado (ej. ACT-001)")
    parser.add_argument("--notes", help="Notas opcionales para la acción completada", default="")
    parser.add_argument("--list-actions", action="store_true", help="Lista las acciones registradas en memoria")
    args = parser.parse_args()

    if args.list_actions:
        list_actions()
        return

    if args.mark_completed:
        mark_action_status(args.mark_completed, "completed", args.notes)
        return

    print("=== INICIANDO GENERACIÓN DE DASHBOARD WEB + REPORTE EJECUTIVO ===")
    memory_data = load_memory()
    client = get_ga4_client()

    print("1/8 Obteniendo métricas de los 5 segmentos (7d, 7d previos WoW, 30d y 90d)...")
    data_7d = fetch_channel_data(client, PROPERTY_ID, start_days_ago=7, end_days_ago=1, label="Últimos 7 Días")
    data_prev_7d = fetch_channel_data(client, PROPERTY_ID, start_days_ago=14, end_days_ago=8, label="7 Días Previos")
    wow_deltas = compute_wow_deltas(data_7d, data_prev_7d)
    data_30d = fetch_channel_data(client, PROPERTY_ID, start_days_ago=30, end_days_ago=1, label="Últimos 30 Días")
    data_90d = fetch_channel_data(client, PROPERTY_ID, start_days_ago=90, end_days_ago=1, label="Últimos 90 Días")

    print("2/8 Consultando Google Ads API v23 nativa (Explorer Access) + datos vinculados GA4...")
    ads_financials = fetch_google_ads_financials(client, PROPERTY_ID)
    ads_bidded_keywords = fetch_google_ads_bidded_keywords(client, PROPERTY_ID)
    ads_creatives = fetch_google_ads_creatives_and_network(client, PROPERTY_ID)
    ads_keywords = fetch_google_ads_keywords(client, PROPERTY_ID)
    native_ads_v23 = fetch_native_google_ads_v23(GOOGLE_ADS_CUSTOMER_ID)

    print("3/8 Obteniendo cruce de Dispositivo (Desktop vs Mobile) por Canal...")
    device_matrix = fetch_device_x_channel(client, PROPERTY_ID)

    print("4/8 Auditando embudo /hablemos/ y origen real de conversiones (firstUserSourceMedium)...")
    hablemos_audit = fetch_hablemos_funnel_audit(client, PROPERTY_ID)

    print("5/8 Obteniendo cruce geográfico por Provincia y Landings clave...")
    geo_summary = fetch_geo_x_channel(client, PROPERTY_ID)
    target_landings = fetch_target_landings(client, PROPERTY_ID)
    content_data = fetch_content_data(client, PROPERTY_ID)

    current_snapshot = build_metrics_snapshot(data_30d, target_landings, hablemos_audit, ads_financials, native_ads_v23)

    print("6/8 Evaluando memoria, generando insights con Gemini y auto-registrando nuevas acciones...")
    gemini_output, added_ids = generate_insights_with_gemini(
        data_7d,
        wow_deltas,
        data_30d,
        data_90d,
        ads_financials,
        ads_bidded_keywords,
        ads_creatives,
        ads_keywords,
        native_ads_v23,
        device_matrix,
        hablemos_audit,
        geo_summary,
        target_landings,
        content_data,
        memory_data,
        current_snapshot,
    )

    print("7/8 Generando Dashboard Web Estadístico en docs/index.html...")
    report_bundle = {
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "property_id": PROPERTY_ID,
        "google_ads_customer_id": GOOGLE_ADS_CUSTOMER_ID,
        "data_7d": data_7d,
        "wow_deltas": wow_deltas,
        "data_30d": data_30d,
        "data_90d": data_90d,
        "ads_financials": ads_financials,
        "ads_bidded_keywords": ads_bidded_keywords,
        "ads_creatives": ads_creatives,
        "ads_keywords": ads_keywords,
        "native_google_ads_v23": native_ads_v23,
        "device_matrix": device_matrix,
        "hablemos_audit": hablemos_audit,
        "geo_summary": geo_summary,
        "target_landings": target_landings,
        "content_data": content_data,
        "gemini_insights_html": gemini_output.insights_html,
        "gemini_memory_html": gemini_output.memory_evaluation_html,
        "memory_actions": memory_data.get("actions", []),
    }
    index_path = generate_web_dashboard(DOCS_DIR, report_bundle)
    dashboard_url = resolve_dashboard_url()
    print(f"🌐 Dashboard Web generado en: {index_path} (URL configurada: {dashboard_url})")

    print("8/8 Construyendo y enviando tarjeta ejecutiva con link a Google Chat...")
    payload = build_google_chat_card(
        data_7d,
        ads_financials,
        hablemos_audit,
        gemini_output,
        added_ids,
        dashboard_url,
        native_ads_v23,
    )
    success = send_to_google_chat(payload, WEBHOOK_URL)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
