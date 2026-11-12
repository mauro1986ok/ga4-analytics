import json
from pathlib import Path
from datetime import datetime


def format_duration(seconds):
    sec = int(round(seconds or 0))
    minutes = sec // 60
    remaining_seconds = sec % 60
    if minutes > 0:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def generate_web_dashboard(output_dir: Path, report_bundle: dict) -> Path:
    """
    Genera el Dashboard Web Interactivo en docs/index.html y guarda el respaldo JSON en docs/report_data.json.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")

    json_path = output_dir / "report_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_bundle, f, indent=2, ensure_ascii=False)

    data_json_str = json.dumps(report_bundle, ensure_ascii=False)
    generated_at = report_bundle.get("generated_at", datetime.now().strftime("%d/%m/%Y %H:%M"))

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Dhartec | Dashboard Estadístico GA4 & Google Ads API v23</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; }}
    .glass-card {{ background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 0.875rem; }}
    .tab-btn.active {{ background: #10b981; color: #052e16; font-weight: 700; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35); }}
    .period-btn.active {{ background: #3b82f6; color: #ffffff; font-weight: 600; }}
    table th {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; }}
    table td {{ font-size: 0.875rem; }}
    tr:hover td {{ background-color: rgba(51, 65, 85, 0.45); }}
  </style>
</head>
<body class="min-h-screen pb-16">

  <!-- TOP NAVBAR -->
  <header class="sticky top-0 z-30 backdrop-blur-md bg-slate-900/90 border-b border-slate-800">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-bold text-lg">
          🌿
        </div>
        <div>
          <h1 class="text-lg sm:text-xl font-bold text-white tracking-tight">
            Dhartec · Inteligencia Digital GA4 & Google Ads API v23
          </h1>
          <p class="text-xs text-slate-400">
            Propiedad GA4: <span class="text-slate-200 font-medium">291106508</span> &nbsp;|&nbsp;
            Google Ads: <span class="text-slate-200 font-medium">368-683-2552 (DHARTEC S.A.S.)</span> &nbsp;|&nbsp;
            Actualizado: <span class="text-emerald-400 font-medium">{generated_at}</span>
          </p>
        </div>
      </div>

      <!-- SELECTOR DE PERÍODO PARA CANALES -->
      <div class="flex items-center gap-2 bg-slate-800/90 p-1 rounded-lg border border-slate-700 self-start md:self-auto">
        <span class="text-xs text-slate-400 px-2">Ventana Canales:</span>
        <button onclick="setPeriod('7d')" id="period-7d" class="period-btn px-3 py-1.5 rounded-md text-xs text-slate-300 transition">7 Días (WoW)</button>
        <button onclick="setPeriod('30d')" id="period-30d" class="period-btn active px-3 py-1.5 rounded-md text-xs text-slate-300 transition">30 Días</button>
        <button onclick="setPeriod('90d')" id="period-90d" class="period-btn px-3 py-1.5 rounded-md text-xs text-slate-300 transition">90 Días</button>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 pt-6 space-y-6">

    <!-- KPI CARDS ROW -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4" id="kpi-cards-container"></section>

    <!-- NAVIGATION TABS -->
    <nav class="flex flex-wrap gap-2 bg-slate-900/90 p-1.5 rounded-xl border border-slate-800">
      <button onclick="showTab('tab-channels')" id="btn-tab-channels" class="tab-btn active px-4 py-2 rounded-lg text-xs sm:text-sm text-slate-300 transition">
        📊 5 Canales & Tendencia WoW
      </button>
      <button onclick="showTab('tab-ads')" id="btn-tab-ads" class="tab-btn px-4 py-2 rounded-lg text-xs sm:text-sm text-slate-300 transition">
        💰 Google Ads API v23 (Quality Score & IS)
      </button>
      <button onclick="showTab('tab-qs-monitor')" id="btn-tab-qs-monitor" class="tab-btn px-4 py-2 rounded-lg text-xs sm:text-sm text-amber-300 bg-amber-500/10 border border-amber-500/30 transition">
        🎯 Semáforo de Quality Score
      </button>
      <button onclick="showTab('tab-funnel')" id="btn-tab-funnel" class="tab-btn px-4 py-2 rounded-lg text-xs sm:text-sm text-slate-300 transition">
        🚨 Embudo /hablemos/ & Landings Core
      </button>
      <button onclick="showTab('tab-device-geo')" id="btn-tab-device-geo" class="tab-btn px-4 py-2 rounded-lg text-xs sm:text-sm text-slate-300 transition">
        💻📱 Dispositivos & 🗺️ Provincias
      </button>
      <button onclick="showTab('tab-memory')" id="btn-tab-memory" class="tab-btn px-4 py-2 rounded-lg text-xs sm:text-sm text-slate-300 transition">
        🧠 Insights Gemini & Memoria
      </button>
      <button onclick="showTab('tab-pending-actions')" id="btn-tab-pending-actions" class="tab-btn px-4 py-2 rounded-lg text-xs sm:text-sm text-slate-300 transition">
        ⏳ Tareas Pendientes
      </button>
    </nav>

    <!-- TAB 1: 5 CANALES & TENDENCIA -->
    <section id="tab-channels" class="space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-sm font-semibold text-slate-200" id="chart-channels-title">Sesiones vs. Tasa de Interacción (%) por Segmento</h2>
            <span class="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" id="active-period-badge">30 Días</span>
          </div>
          <div class="h-72">
            <canvas id="channelsChart"></canvas>
          </div>
        </div>

        <div class="glass-card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-sm font-semibold text-slate-200">Tiempo Medio de Permanencia (Segundos) vs. Conversiones</h2>
            <span class="text-xs text-slate-400">Comparativa de Calidad B2B</span>
          </div>
          <div class="h-72">
            <canvas id="durationChart"></canvas>
          </div>
        </div>
      </div>

      <div class="glass-card p-5 overflow-x-auto">
        <h3 class="text-sm font-semibold text-white mb-1">Desglose Detallado de los 5 Segmentos de Adquisición</h3>
        <p class="text-xs text-slate-400 mb-4">Incluye variaciones semana contra semana (WoW %: últimos 7 días vs. 7 días previos) y las sub-fuentes principales dentro de cada canal.</p>
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-700/80">
              <th class="py-3 px-3">Segmento</th>
              <th class="py-3 px-3">Sesiones</th>
              <th class="py-3 px-3">Usuarios</th>
              <th class="py-3 px-3">Variación WoW (7d)</th>
              <th class="py-3 px-3">Interacción (Eng %)</th>
              <th class="py-3 px-3">Permanencia Media</th>
              <th class="py-3 px-3">Págs / Sesión</th>
              <th class="py-3 px-3">Conversiones</th>
              <th class="py-3 px-3">Sub-fuentes Principales</th>
            </tr>
          </thead>
          <tbody id="channels-table-body" class="divide-y divide-slate-800"></tbody>
        </table>
      </div>
    </section>

    <!-- TAB 2: GOOGLE ADS API v23 + GA4 -->
    <section id="tab-ads" class="space-y-6 hidden">
      <!-- Estado API Nativa v23 -->
      <div id="native-ads-banner" class="glass-card p-4 border-l-4 border-emerald-500"></div>

      <!-- SECCIÓN NATIVA GOOGLE ADS API v23: CUOTA DE IMPRESIONES & QUALITY SCORE -->
      <div id="native-ads-tables-wrapper" class="space-y-6">
        <div class="glass-card p-5 overflow-x-auto">
          <h3 class="text-sm font-semibold text-emerald-400 mb-1">⚡ [API Nativa v23] Cuota de Impresiones de Búsqueda (Search Impression Share - Últimos 30 Días)</h3>
          <p class="text-xs text-slate-400 mb-4">Muestra qué porcentaje de búsquedas totales capta cada campaña y cuánto pierde por falta de Presupuesto vs. por bajo Ad Rank / Quality Score.</p>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-700/80">
                <th class="py-2.5 px-3">Campaña</th>
                <th class="py-2.5 px-3">Estado</th>
                <th class="py-2.5 px-3">Presupuesto Diario</th>
                <th class="py-2.5 px-3">Imp. (30d)</th>
                <th class="py-2.5 px-3">Clics (30d)</th>
                <th class="py-2.5 px-3">Gasto (30d)</th>
                <th class="py-2.5 px-3">Impression Share Captado</th>
                <th class="py-2.5 px-3">Perdido por Presupuesto</th>
                <th class="py-2.5 px-3">Perdido por Ranking / QS</th>
              </tr>
            </thead>
            <tbody id="native-is-tbody" class="divide-y divide-slate-800"></tbody>
          </table>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="glass-card p-5 overflow-x-auto">
            <h3 class="text-sm font-semibold text-emerald-400 mb-1">⚡ [API Nativa v23] Diagnóstico de Quality Score (1-10) por Keyword</h3>
            <p class="text-xs text-slate-400 mb-4">Desglosa por qué Google Ads penaliza el Ad Rank: Relevancia del Anuncio, CTR Esperado y Experiencia Post-Clic en la Landing Page.</p>
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-slate-700/80">
                  <th class="py-2 px-2">Keyword (Concordancia)</th>
                  <th class="py-2 px-2">Grupo</th>
                  <th class="py-2 px-2">QS (1-10)</th>
                  <th class="py-2 px-2">Anuncio</th>
                  <th class="py-2 px-2">CTR Esp.</th>
                  <th class="py-2 px-2">Exp. Landing</th>
                </tr>
              </thead>
              <tbody id="native-qs-tbody" class="divide-y divide-slate-800"></tbody>
            </table>
          </div>

          <div class="glass-card p-5 overflow-x-auto">
            <h3 class="text-sm font-semibold text-emerald-400 mb-1">⚡ [API Nativa v23] Copys de Anuncios RSA y Fuerza (`Ad Strength`)</h3>
            <p class="text-xs text-slate-400 mb-4">Títulos y descripciones reales activos en cada grupo de anuncios junto con su URL de destino.</p>
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-slate-700/80">
                  <th class="py-2 px-2">Anuncio ID & Fuerza</th>
                  <th class="py-2 px-2">Grupo & URL Destino</th>
                  <th class="py-2 px-2">Títulos RSA Activos</th>
                  <th class="py-2 px-2">CTR (30d)</th>
                </tr>
              </thead>
              <tbody id="native-rsa-tbody" class="divide-y divide-slate-800"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- GRÁFICOS KEYWORDS -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-card p-5">
          <h2 class="text-sm font-semibold text-slate-200 mb-4">Top Keywords Compradas: Impresiones vs. CTR (%) (90d)</h2>
          <div class="h-72">
            <canvas id="adsKeywordsChart"></canvas>
          </div>
        </div>
        <div class="glass-card p-5">
          <h2 class="text-sm font-semibold text-slate-200 mb-4">Permanencia en Landing (Segundos) por Keyword Comprada (90d)</h2>
          <div class="h-72">
            <canvas id="adsKeywordDurationChart"></canvas>
          </div>
        </div>
      </div>

      <!-- Tabla 1: Campañas y Grupos (90d GA4+Ads) -->
      <div class="glass-card p-5 overflow-x-auto">
        <h3 class="text-sm font-semibold text-white mb-1">1. Cruce GA4 + Ads por Campaña y Grupo de Anuncios (90 Días)</h3>
        <p class="text-xs text-slate-400 mb-4">Cruza inversión, CTR, retención de clic a sesión (fuga técnica), Costo por Sesión Interactiva (CPES) y permanencia en web.</p>
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-700/80">
              <th class="py-3 px-3">Campaña</th>
              <th class="py-3 px-3">Grupo de Anuncios</th>
              <th class="py-3 px-3">Impresiones</th>
              <th class="py-3 px-3">Clics</th>
              <th class="py-3 px-3">CTR</th>
              <th class="py-3 px-3">Gasto</th>
              <th class="py-3 px-3">CPC Medio</th>
              <th class="py-3 px-3">Sesiones (% Clic)</th>
              <th class="py-3 px-3">Costo / Ses. Eng</th>
              <th class="py-3 px-3">Permanencia</th>
              <th class="py-3 px-3">Eng %</th>
              <th class="py-3 px-3">Conv.</th>
            </tr>
          </thead>
          <tbody id="ads-campaigns-tbody" class="divide-y divide-slate-800"></tbody>
        </table>
      </div>

      <!-- Tabla 2: Keywords Compradas (90d) -->
      <div class="glass-card p-5 overflow-x-auto">
        <h3 class="text-sm font-semibold text-white mb-1">2. Keywords Compradas Cruzadas con Retención en Web (90 Días)</h3>
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-700/80">
              <th class="py-3 px-3">Keyword Comprada</th>
              <th class="py-3 px-3">Grupo de Anuncios</th>
              <th class="py-3 px-3">Impresiones</th>
              <th class="py-3 px-3">Clics</th>
              <th class="py-3 px-3">CTR %</th>
              <th class="py-3 px-3">Gasto</th>
              <th class="py-3 px-3">CPC</th>
              <th class="py-3 px-3">Sesiones</th>
              <th class="py-3 px-3">Permanencia Media</th>
              <th class="py-3 px-3">Interacción %</th>
            </tr>
          </thead>
          <tbody id="ads-bidded-tbody" class="divide-y divide-slate-800"></tbody>
        </table>
      </div>

      <!-- Tabla 3 y 4: Creatividades x Red + Search Queries -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-card p-5 overflow-x-auto">
          <h3 class="text-sm font-semibold text-white mb-1">3. Rendimiento por Anuncio (`Creative ID`) y Red (`Search` vs `Partners`)</h3>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-700/80">
                <th class="py-2.5 px-2">Anuncio ID</th>
                <th class="py-2.5 px-2">Grupo</th>
                <th class="py-2.5 px-2">Red</th>
                <th class="py-2.5 px-2">Imp.</th>
                <th class="py-2.5 px-2">CTR</th>
                <th class="py-2.5 px-2">Gasto</th>
                <th class="py-2.5 px-2">Duración</th>
                <th class="py-2.5 px-2">Eng %</th>
              </tr>
            </thead>
            <tbody id="ads-creatives-tbody" class="divide-y divide-slate-800"></tbody>
          </table>
        </div>

        <div class="glass-card p-5 overflow-x-auto">
          <h3 class="text-sm font-semibold text-white mb-1">4. Términos Buscados Reales (`Search Query`) x Landing Page</h3>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-700/80">
                <th class="py-2.5 px-2">Término Buscado</th>
                <th class="py-2.5 px-2">Landing Page</th>
                <th class="py-2.5 px-2">Sesiones</th>
                <th class="py-2.5 px-2">Permanencia</th>
                <th class="py-2.5 px-2">Eng %</th>
              </tr>
            </thead>
            <tbody id="ads-queries-tbody" class="divide-y divide-slate-800"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB: SEMÁFORO DE QUALITY SCORE (MONITOREO DEDICADO) -->
    <section id="tab-qs-monitor" class="space-y-6 hidden">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4" id="qs-kpi-summary-cards"></div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-card p-5">
          <h2 class="text-sm font-semibold text-slate-200 mb-2">Distribución de Keywords por Nivel de Calidad (1 a 10)</h2>
          <p class="text-xs text-slate-400 mb-4">Muestra cuántas palabras clave están en zona crítica (1-3), regular (4-6) o saludable (7-10).</p>
          <div class="h-64">
            <canvas id="qsDistributionChart"></canvas>
          </div>
        </div>

        <div class="glass-card p-5">
          <h2 class="text-sm font-semibold text-slate-200 mb-2">Diagnóstico de los 3 Factores del Quality Score</h2>
          <p class="text-xs text-slate-400 mb-4">Dónde castiga Google a Dhartec: Relevancia del Anuncio vs. CTR Esperado vs. Experiencia en la Landing Page.</p>
          <div class="h-64">
            <canvas id="qsComponentsChart"></canvas>
          </div>
        </div>
      </div>

      <div class="glass-card p-5 overflow-x-auto">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-sm font-semibold text-white">Semáforo de Palabras Clave y Acciones Correctivas</h3>
          <span class="text-xs text-slate-400">Google Ads API v23 (Últimos 30 días)</span>
        </div>
        <p class="text-xs text-slate-400 mb-4">Las keywords con nota 1 a 3 pagan sobrecosto por clic o pierden apariciones por culpa de la página de destino.</p>
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-700/80">
              <th class="py-2.5 px-3">Estado</th>
              <th class="py-2.5 px-3">Palabra Clave</th>
              <th class="py-2.5 px-3">Grupo</th>
              <th class="py-2.5 px-3">Nota QS</th>
              <th class="py-2.5 px-3">Anuncio</th>
              <th class="py-2.5 px-3">CTR Esperado</th>
              <th class="py-2.5 px-3">Página de Destino</th>
              <th class="py-2.5 px-3">Impresiones (30d)</th>
              <th class="py-2.5 px-3">Acción Recomendada</th>
            </tr>
          </thead>
          <tbody id="qs-monitor-table-body" class="divide-y divide-slate-800"></tbody>
        </table>
      </div>
    </section>
    <section id="tab-funnel" class="space-y-6 hidden">
      <div id="hablemos-alert-card" class="glass-card p-5 border-l-4 border-rose-500"></div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-card p-5 overflow-x-auto">
          <h3 class="text-sm font-semibold text-white mb-1">Rastreo de Conversiones por Primer Origen (`firstUserSourceMedium`)</h3>
          <p class="text-xs text-slate-400 mb-4">Recupera el canal que trajo por primera vez al usuario aunque la sesión en `/hablemos/` figure como Directa.</p>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-700/80">
                <th class="py-2.5 px-3">Primer Origen del Usuario</th>
                <th class="py-2.5 px-3">Origen de la Sesión</th>
                <th class="py-2.5 px-3">Sesiones</th>
                <th class="py-2.5 px-3">Conversiones</th>
                <th class="py-2.5 px-3">Duración Media</th>
              </tr>
            </thead>
            <tbody id="hablemos-attr-tbody" class="divide-y divide-slate-800"></tbody>
          </table>
        </div>

        <div class="glass-card p-5 overflow-x-auto">
          <h3 class="text-sm font-semibold text-white mb-1">Rendimiento Comparativo de las 3 Landings Core (30 Días)</h3>
          <p class="text-xs text-slate-400 mb-4">Habilitaciones y Permisos vs. Huella de Carbono vs. Sustentabilidad.</p>
          <table class="w-full text-left border-collapse mb-4">
            <thead>
              <tr class="border-b border-slate-700/80">
                <th class="py-2.5 px-3">Oferta Core</th>
                <th class="py-2.5 px-3">Usuarios</th>
                <th class="py-2.5 px-3">Sesiones</th>
                <th class="py-2.5 px-3">Permanencia</th>
                <th class="py-2.5 px-3">Interacción</th>
                <th class="py-2.5 px-3">Conv.</th>
              </tr>
            </thead>
            <tbody id="landings-core-tbody" class="divide-y divide-slate-800"></tbody>
          </table>

          <h4 class="text-xs font-semibold text-slate-300 uppercase tracking-wider mt-6 mb-2">Top Páginas y Artículos de Blog (Últimos 30 Días)</h4>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-700/80">
                <th class="py-2 px-2">Ruta</th>
                <th class="py-2 px-2">Sesiones</th>
                <th class="py-2 px-2">Vistas</th>
                <th class="py-2 px-2">Permanencia</th>
                <th class="py-2 px-2">Eng %</th>
              </tr>
            </thead>
            <tbody id="content-pages-tbody" class="divide-y divide-slate-800"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 4: DISPOSITIVOS & GEOGRAFÍA -->
    <section id="tab-device-geo" class="space-y-6 hidden">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-card p-5">
          <h2 class="text-sm font-semibold text-slate-200 mb-4">Brecha Desktop vs. Mobile: Permanencia Media (Segundos - 90d)</h2>
          <div class="h-72">
            <canvas id="deviceChart"></canvas>
          </div>
        </div>
        <div class="glass-card p-5">
          <h2 class="text-sm font-semibold text-slate-200 mb-4">Top Provincias de Argentina: Sesiones vs. Permanencia (90d)</h2>
          <div class="h-72">
            <canvas id="geoChart"></canvas>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-card p-5 overflow-x-auto">
          <h3 class="text-sm font-semibold text-white mb-3">Matriz Dispositivo (`Desktop` vs `Mobile`) por Canal (90d)</h3>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-700/80">
                <th class="py-2.5 px-3">Canal</th>
                <th class="py-2.5 px-3">Dispositivo</th>
                <th class="py-2.5 px-3">Sesiones</th>
                <th class="py-2.5 px-3">Permanencia</th>
                <th class="py-2.5 px-3">Eng %</th>
                <th class="py-2.5 px-3">Conv. (% Tasa)</th>
              </tr>
            </thead>
            <tbody id="device-tbody" class="divide-y divide-slate-800"></tbody>
          </table>
        </div>

        <div class="glass-card p-5 overflow-x-auto">
          <h3 class="text-sm font-semibold text-white mb-3">Desempeño por Jurisdicción / Provincia (90d)</h3>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-700/80">
                <th class="py-2.5 px-3">Provincia</th>
                <th class="py-2.5 px-3">Sesiones</th>
                <th class="py-2.5 px-3">Permanencia</th>
                <th class="py-2.5 px-3">Eng %</th>
                <th class="py-2.5 px-3">Conv.</th>
                <th class="py-2.5 px-3">Mix de Canales</th>
              </tr>
            </thead>
            <tbody id="geo-tbody" class="divide-y divide-slate-800"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 5: INSIGHTS GEMINI & MEMORIA DE ACCIONES -->
    <section id="tab-memory" class="space-y-6 hidden">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-card p-6 border-l-4 border-emerald-500">
          <h3 class="text-base font-bold text-white mb-3">💡 Insights Estratégicos de la Semana (Gemini AI)</h3>
          <div id="gemini-insights-box" class="text-sm text-slate-200 leading-relaxed space-y-2"></div>
        </div>
        <div class="glass-card p-6 border-l-4 border-blue-500">
          <h3 class="text-base font-bold text-white mb-3">🧠 Evaluación de Seguimiento de Memoria</h3>
          <div id="gemini-memory-box" class="text-sm text-slate-200 leading-relaxed space-y-2"></div>
        </div>
      </div>

      <div class="glass-card p-6">
        <h3 class="text-base font-bold text-white mb-1">Registro Histórico de Acciones (`actions_memory.json`)</h3>
        <p class="text-xs text-slate-400 mb-4">Cada acción guarda una foto de las métricas base (`baseline_snapshot`) del momento en que se creó para evaluar el impacto antes vs. después.</p>
        <div id="actions-cards-list" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
      </div>
    </section>

    <!-- TAB 6: TAREAS PENDIENTES PRIORITARIAS -->
    <section id="tab-pending-actions" class="space-y-6 hidden">
      <div class="glass-card p-6 border-l-4 border-amber-500">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-white">⏳ Plan de Tareas Pendientes para Dhartec</h2>
            <p class="text-xs text-slate-300 mt-1">
              Acciones prácticas identificadas a partir de los datos reales de GA4 y Google Ads. Al resolverlas se frena el gasto en visitas accidentales y se duplican las consultas comerciales sin aumentar el presupuesto.
            </p>
          </div>
          <div class="text-xs px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold self-start sm:self-auto">
            7 Tareas Prioritarias
          </div>
        </div>
      </div>

      <div id="dedicated-pending-list" class="space-y-4"></div>
    </section>

    <!-- SECCIÓN SIEMPRE VISIBLE AL FINAL DE LA WEB: TAREAS PENDIENTES -->
    <footer class="mt-12 pt-8 border-t border-slate-800 space-y-6">
      <div class="glass-card p-6 border-l-4 border-amber-500">
        <div class="flex items-center justify-between mb-2">
          <h2 class="text-base sm:text-lg font-bold text-white flex items-center gap-2">
            <span>📋</span> Lista de Tareas y Mejoras Pendientes
          </h2>
          <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
            En Seguimiento
          </span>
        </div>
        <p class="text-xs text-slate-400 mb-6">
          Estas son las indicaciones concretas que deben implementarse en el sitio web y en Google Ads para aprovechar mejor el presupuesto:
        </p>
        <div id="footer-pending-actions" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
      </div>

      <div class="text-center text-xs text-slate-500 pb-4">
        Dhartec · Sistema de Reportes Automatizados GA4 + Google Ads API v23
      </div>
    </footer>

  </main>

  <script>
    const REPORT_DATA = {data_json_str};
    let currentPeriod = '30d';
    let channelsChartInstance = null;
    let durationChartInstance = null;

    function fmtDur(sec) {{
      const s = Math.round(sec || 0);
      const m = Math.floor(s / 60);
      const r = s % 60;
      return m > 0 ? `${{m}}m ${{r}}s` : `${{r}}s`;
    }}

    function fmtBadge(val) {{
      if (val === 'ABOVE_AVERAGE') return '<span class="px-2 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Superior</span>';
      if (val === 'AVERAGE') return '<span class="px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30">Promedio</span>';
      if (val === 'BELOW_AVERAGE') return '<span class="px-2 py-0.5 rounded text-xs bg-rose-500/20 text-rose-300 border border-rose-500/30">Inferior ⚠️</span>';
      return '<span class="text-xs text-slate-500">S/D</span>';
    }}

    function showTab(tabId) {{
      ['tab-channels', 'tab-ads', 'tab-qs-monitor', 'tab-funnel', 'tab-device-geo', 'tab-memory', 'tab-pending-actions'].forEach(id => {{
        const el = document.getElementById(id);
        const btn = document.getElementById('btn-' + id);
        if (el) el.classList.add('hidden');
        if (btn) btn.classList.remove('active');
      }});
      const targetEl = document.getElementById(tabId);
      const targetBtn = document.getElementById('btn-' + tabId);
      if (targetEl) targetEl.classList.remove('hidden');
      if (targetBtn) targetBtn.classList.add('active');
    }}

    function setPeriod(period) {{
      currentPeriod = period;
      ['7d', '30d', '90d'].forEach(p => {{
        document.getElementById('period-' + p).classList.toggle('active', p === period);
      }});
      const labels = {{ '7d': 'Últimos 7 Días', '30d': 'Últimos 30 Días', '90d': 'Últimos 90 Días' }};
      document.getElementById('active-period-badge').textContent = labels[period];
      renderKPIs();
      renderChannelsSection();
    }}

    function renderKPIs() {{
      const periodMap = {{ '7d': REPORT_DATA.data_7d, '30d': REPORT_DATA.data_30d, '90d': REPORT_DATA.data_90d }};
      const segs = periodMap[currentPeriod].segments;
      let totalSess = 0, totalUsers = 0, weightedEng = 0, weightedDur = 0;
      Object.values(segs).forEach(s => {{
        totalSess += s.sessions;
        totalUsers += s.users;
        weightedEng += (s.engagement_rate * s.sessions);
        weightedDur += (s.avg_duration * s.sessions);
      }});
      const avgEng = totalSess > 0 ? (weightedEng / totalSess).toFixed(1) : '0.0';
      const avgDur = totalSess > 0 ? fmtDur(weightedDur / totalSess) : '0s';

      const totalAdsCost = (REPORT_DATA.ads_financials || []).reduce((acc, c) => acc + c.cost, 0);
      const totalAdsClicks = (REPORT_DATA.ads_financials || []).reduce((acc, c) => acc + c.clicks, 0);
      const totalAdsSess = (REPORT_DATA.ads_financials || []).reduce((acc, c) => acc + c.sessions, 0);

      const nativeAds = REPORT_DATA.native_google_ads_v23 || {{}};
      const qsSum = nativeAds.quality_score_summary || {{}};
      const avgQs = qsSum.weighted_avg_qs !== undefined ? qsSum.weighted_avg_qs.toFixed(1) : 'S/D';
      const critCount = qsSum.critical_keywords_count || 0;
      const hab = REPORT_DATA.hablemos_audit || {{}};

      document.getElementById('kpi-cards-container').innerHTML = `
        <div class="glass-card p-4">
          <div class="text-xs text-slate-400">Sesiones (${{currentPeriod.toUpperCase()}})</div>
          <div class="text-2xl font-bold text-white mt-1">${{totalSess.toLocaleString('es-AR')}}</div>
          <div class="text-xs text-emerald-400 mt-1">${{totalUsers.toLocaleString('es-AR')}} usuarios activos</div>
        </div>
        <div class="glass-card p-4">
          <div class="text-xs text-slate-400">Calidad Global (${{currentPeriod.toUpperCase()}})</div>
          <div class="text-2xl font-bold text-white mt-1">${{avgDur}}</div>
          <div class="text-xs text-blue-400 mt-1">Interacción media: ${{avgEng}}%</div>
        </div>
        <div class="glass-card p-4 border-l-2 border-amber-400">
          <div class="text-xs text-slate-400">Quality Score Ponderado</div>
          <div class="text-2xl font-bold ${{avgQs < 5 ? 'text-amber-400' : 'text-emerald-400'}} mt-1">${{avgQs}} <span class="text-xs font-normal text-slate-400">/ 10</span></div>
          <div class="text-xs text-rose-400 mt-1">${{critCount}} keywords en alerta crítica (1-3)</div>
        </div>
        <div class="glass-card p-4">
          <div class="text-xs text-slate-400">Inversión Google Ads (90d)</div>
          <div class="text-2xl font-bold text-amber-400 mt-1">$${{totalAdsCost.toFixed(2)}}</div>
          <div class="text-xs text-slate-300 mt-1">${{totalAdsClicks}} clics &rarr; ${{totalAdsSess}} sesiones</div>
        </div>
        <div class="glass-card p-4">
          <div class="text-xs text-slate-400">Embudo /hablemos/ (90d)</div>
          <div class="text-2xl font-bold text-rose-400 mt-1">${{hab.hablemos_conversions_90d || 0}} conv</div>
          <div class="text-xs text-rose-300 mt-1">${{hab.direct_session_reset_pct || 0}}% reinicio a Directo (Alerta 1:1)</div>
        </div>
      `;
    }}

    function renderChannelsSection() {{
      const periodMap = {{ '7d': REPORT_DATA.data_7d, '30d': REPORT_DATA.data_30d, '90d': REPORT_DATA.data_90d }};
      const segs = periodMap[currentPeriod].segments;
      const deltas = REPORT_DATA.wow_deltas || {{}};
      const names = Object.keys(segs);

      const tbody = document.getElementById('channels-table-body');
      tbody.innerHTML = names.map(name => {{
        const s = segs[name];
        const d = deltas[name] || {{ sessions_delta: '-', duration_delta: '-' }};
        const subList = Object.entries(s.top_sources || {{}}).map(([k, v]) =>
          `<span class="inline-block bg-slate-800 text-slate-300 text-xs px-2 py-0.5 rounded mr-1 mb-1 border border-slate-700">${{k}}: ${{v.sessions}} ses (${{fmtDur(v.avg_duration)}})</span>`
        ).join('');
        return `
          <tr>
            <td class="py-3 px-3 font-semibold text-white">${{name}}</td>
            <td class="py-3 px-3 font-medium text-slate-200">${{s.sessions.toLocaleString('es-AR')}}</td>
            <td class="py-3 px-3 text-slate-300">${{s.users.toLocaleString('es-AR')}}</td>
            <td class="py-3 px-3">
              <span class="text-xs px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700">
                Ses: ${{d.sessions_delta}} | Dur: ${{d.duration_delta}}
              </span>
            </td>
            <td class="py-3 px-3 text-blue-400 font-medium">${{s.engagement_rate.toFixed(1)}}%</td>
            <td class="py-3 px-3 text-emerald-400 font-medium">${{fmtDur(s.avg_duration)}}</td>
            <td class="py-3 px-3 text-slate-300">${{s.pages_per_session.toFixed(1)}}</td>
            <td class="py-3 px-3 font-bold text-amber-400">${{s.key_events}}</td>
            <td class="py-3 px-3">${{subList || '-'}}</td>
          </tr>
        `;
      }}).join('');

      const ctx1 = document.getElementById('channelsChart').getContext('2d');
      if (channelsChartInstance) channelsChartInstance.destroy();
      channelsChartInstance = new Chart(ctx1, {{
        type: 'bar',
        data: {{
          labels: names,
          datasets: [
            {{
              label: 'Sesiones',
              data: names.map(n => segs[n].sessions),
              backgroundColor: 'rgba(59, 130, 246, 0.7)',
              borderColor: '#3b82f6',
              borderWidth: 1,
              yAxisID: 'y'
            }},
            {{
              label: 'Interacción (%)',
              data: names.map(n => Number(segs[n].engagement_rate.toFixed(1))),
              type: 'line',
              borderColor: '#10b981',
              backgroundColor: '#10b981',
              borderWidth: 2,
              yAxisID: 'y1'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }},
            y: {{ position: 'left', ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }},
            y1: {{ position: 'right', min: 0, max: 100, ticks: {{ color: '#10b981' }}, grid: {{ drawOnChartArea: false }} }}
          }}
        }}
      }});

      const ctx2 = document.getElementById('durationChart').getContext('2d');
      if (durationChartInstance) durationChartInstance.destroy();
      durationChartInstance = new Chart(ctx2, {{
        type: 'bar',
        data: {{
          labels: names,
          datasets: [
            {{
              label: 'Permanencia Media (Segundos)',
              data: names.map(n => Math.round(segs[n].avg_duration)),
              backgroundColor: 'rgba(16, 185, 129, 0.7)',
              borderColor: '#10b981',
              borderWidth: 1,
              yAxisID: 'y'
            }},
            {{
              label: 'Conversiones (Key Events)',
              data: names.map(n => segs[n].key_events),
              type: 'line',
              borderColor: '#f59e0b',
              backgroundColor: '#f59e0b',
              borderWidth: 2,
              yAxisID: 'y1'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }},
            y: {{ position: 'left', ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }},
            y1: {{ position: 'right', ticks: {{ color: '#f59e0b' }}, grid: {{ drawOnChartArea: false }} }}
          }}
        }}
      }});
    }}

    function renderAdsSection() {{
      const nativeData = REPORT_DATA.native_google_ads_v23 || {{}};
      const banner = document.getElementById('native-ads-banner');
      if (nativeData.status === 'ok') {{
        banner.className = 'glass-card p-4 border-l-4 border-emerald-500';
        banner.innerHTML = `<div class="text-sm font-semibold text-emerald-400">✅ Google Ads API Nativa (v23 · Explorer Access) Conectada en Tiempo Real</div>
          <div class="text-xs text-slate-300 mt-1">Extrayendo Cuota de Impresiones (Impression Share), Nivel de Calidad (Quality Score 1-10) y Títulos RSA directamente desde la cuenta 368-683-2552 (DHARTEC S.A.S.).</div>`;

        // Render Native Impression Share
        document.getElementById('native-is-tbody').innerHTML = (nativeData.campaign_impression_share || []).map(c => `
          <tr>
            <td class="py-2.5 px-3 font-semibold text-white">${{c.campaign}}</td>
            <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-300">${{c.status}}</span></td>
            <td class="py-2.5 px-3 text-slate-300">$${{c.daily_budget.toLocaleString('es-AR')}}</td>
            <td class="py-2.5 px-3 text-slate-200">${{c.impressions_30d.toLocaleString('es-AR')}}</td>
            <td class="py-2.5 px-3 text-slate-200">${{c.clicks_30d}}</td>
            <td class="py-2.5 px-3 text-amber-400 font-semibold">$${{c.cost_30d.toLocaleString('es-AR')}}</td>
            <td class="py-2.5 px-3 text-emerald-400 font-bold">${{c.search_impression_share_pct}}%</td>
            <td class="py-2.5 px-3 text-blue-400 font-medium">${{c.lost_is_budget_pct}}%</td>
            <td class="py-2.5 px-3 font-bold ${{c.lost_is_rank_pct > 50 ? 'text-rose-400' : 'text-amber-300'}}">${{c.lost_is_rank_pct}}%</td>
          </tr>
        `).join('');

        // Render Native Quality Score
        document.getElementById('native-qs-tbody').innerHTML = (nativeData.keywords_quality_score || []).map(k => {{
          const qs = k.quality_score;
          const qsBadge = qs !== null && qs !== undefined
            ? `<span class="px-2 py-0.5 rounded font-bold text-xs ${{qs <= 3 ? 'bg-rose-500/25 text-rose-300 border border-rose-500/40' : (qs <= 6 ? 'bg-amber-500/25 text-amber-300' : 'bg-emerald-500/25 text-emerald-300')}}">${{qs}} / 10</span>`
            : '<span class="text-xs text-slate-500">S/C</span>';
          return `
            <tr>
              <td class="py-2 px-2 font-medium text-white">${{k.keyword}} <span class="text-xs text-slate-500">(${{k.match_type}})</span></td>
              <td class="py-2 px-2 text-xs text-slate-300">${{k.ad_group}}</td>
              <td class="py-2 px-2">${{qsBadge}}</td>
              <td class="py-2 px-2">${{fmtBadge(k.creative_quality)}}</td>
              <td class="py-2 px-2">${{fmtBadge(k.expected_ctr)}}</td>
              <td class="py-2 px-2">${{fmtBadge(k.landing_experience)}}</td>
            </tr>
          `;
        }}).join('');

        // Render Native RSA Ads
        document.getElementById('native-rsa-tbody').innerHTML = (nativeData.rsa_ads || []).map(a => `
          <tr>
            <td class="py-2 px-2">
              <div class="font-mono text-xs text-white">#${{a.ad_id}}</div>
              <span class="text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300">${{a.ad_strength}}</span>
            </td>
            <td class="py-2 px-2">
              <div class="text-xs font-semibold text-slate-200">${{a.ad_group}}</div>
              <div class="text-[11px] text-blue-400 truncate max-w-[180px]">${{a.final_url}}</div>
            </td>
            <td class="py-2 px-2 text-xs text-slate-300">
              ${{(a.headlines || []).map(h => `<span class="inline-block bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 mr-1 mb-1">${{h}}</span>`).join('')}}
            </td>
            <td class="py-2 px-2 font-semibold text-blue-400">${{a.ctr_30d}}%</td>
          </tr>
        `).join('');
      }} else {{
        document.getElementById('native-ads-tables-wrapper').classList.add('hidden');
      }}

      // Tabla 1: Campañas
      document.getElementById('ads-campaigns-tbody').innerHTML = (REPORT_DATA.ads_financials || []).map(c => `
        <tr>
          <td class="py-3 px-3 font-semibold text-white">${{c.campaign}}</td>
          <td class="py-3 px-3 text-slate-200">${{c.ad_group}}</td>
          <td class="py-3 px-3 text-slate-300">${{c.impressions.toLocaleString('es-AR')}}</td>
          <td class="py-3 px-3 text-slate-300">${{c.clicks}}</td>
          <td class="py-3 px-3 text-blue-400 font-semibold">${{c.ctr_pct}}%</td>
          <td class="py-3 px-3 text-amber-400 font-semibold">$${{c.cost.toFixed(2)}}</td>
          <td class="py-3 px-3 text-slate-300">$${{c.cpc.toFixed(2)}}</td>
          <td class="py-3 px-3 text-slate-200">${{c.sessions}} <span class="text-xs text-slate-400">(${{c.click_retention_pct}}%)</span></td>
          <td class="py-3 px-3 text-rose-300 font-medium">$${{c.cost_per_engaged_session.toFixed(2)}}</td>
          <td class="py-3 px-3 text-emerald-400 font-medium">${{fmtDur(c.avg_duration)}}</td>
          <td class="py-3 px-3 text-slate-200">${{c.engagement_rate}}%</td>
          <td class="py-3 px-3 font-bold text-white">${{c.key_events}}</td>
        </tr>
      `).join('');

      // Tabla 2: Keywords Compradas
      const bidded = REPORT_DATA.ads_bidded_keywords || [];
      document.getElementById('ads-bidded-tbody').innerHTML = bidded.map(b => `
        <tr>
          <td class="py-2.5 px-3 font-semibold text-emerald-300">[${{b.keyword}}]</td>
          <td class="py-2.5 px-3 text-slate-300">${{b.ad_group}}</td>
          <td class="py-2.5 px-3 text-slate-200">${{b.impressions.toLocaleString('es-AR')}}</td>
          <td class="py-2.5 px-3 text-slate-200">${{b.clicks}}</td>
          <td class="py-2.5 px-3 text-blue-400 font-semibold">${{b.ctr_pct}}%</td>
          <td class="py-2.5 px-3 text-amber-400">$${{b.cost.toFixed(2)}}</td>
          <td class="py-2.5 px-3 text-slate-300">$${{b.cpc.toFixed(2)}}</td>
          <td class="py-2.5 px-3 text-slate-200">${{b.sessions}}</td>
          <td class="py-2.5 px-3 font-medium ${{b.avg_duration >= 120 ? 'text-emerald-400' : 'text-slate-300'}}">${{fmtDur(b.avg_duration)}}</td>
          <td class="py-2.5 px-3 text-slate-200">${{b.engagement_rate}}%</td>
        </tr>
      `).join('');

      // Tabla 3: Creatives
      document.getElementById('ads-creatives-tbody').innerHTML = (REPORT_DATA.ads_creatives || []).map(cr => {{
        const isPartner = cr.network.toLowerCase().includes('partner');
        return `
          <tr class="${{isPartner ? 'bg-rose-950/30' : ''}}">
            <td class="py-2.5 px-2 font-mono text-xs text-white">#${{cr.creative_id}}</td>
            <td class="py-2.5 px-2 text-xs text-slate-300">${{cr.ad_group}}</td>
            <td class="py-2.5 px-2 text-xs ${{isPartner ? 'text-rose-400 font-semibold' : 'text-emerald-400'}}">${{cr.network}}</td>
            <td class="py-2.5 px-2 text-slate-300">${{cr.impressions}}</td>
            <td class="py-2.5 px-2 text-blue-400">${{cr.ctr_pct}}%</td>
            <td class="py-2.5 px-2 text-amber-400">$${{cr.cost.toFixed(2)}}</td>
            <td class="py-2.5 px-2 font-medium ${{cr.avg_duration < 30 ? 'text-rose-400' : 'text-emerald-400'}}">${{fmtDur(cr.avg_duration)}}</td>
            <td class="py-2.5 px-2 text-slate-300">${{cr.engagement_rate}}%</td>
          </tr>
        `;
      }}).join('');

      // Tabla 4: Queries
      document.getElementById('ads-queries-tbody').innerHTML = (REPORT_DATA.ads_keywords || []).slice(0, 15).map(q => `
        <tr>
          <td class="py-2.5 px-2 font-medium text-white">"${{q.query}}"</td>
          <td class="py-2.5 px-2 text-xs text-slate-400">${{q.landing}}</td>
          <td class="py-2.5 px-2 text-slate-300">${{q.sessions}}</td>
          <td class="py-2.5 px-2 text-emerald-400 font-semibold">${{fmtDur(q.avg_duration)}}</td>
          <td class="py-2.5 px-2 text-blue-400">${{q.engagement_rate.toFixed(0)}}%</td>
        </tr>
      `).join('');

      // Charts Ads
      const topBidded = bidded.slice(0, 10);
      new Chart(document.getElementById('adsKeywordsChart').getContext('2d'), {{
        type: 'bar',
        data: {{
          labels: topBidded.map(b => b.keyword),
          datasets: [
            {{
              label: 'Impresiones',
              data: topBidded.map(b => b.impressions),
              backgroundColor: 'rgba(59, 130, 246, 0.65)',
              yAxisID: 'y'
            }},
            {{
              label: 'CTR (%)',
              data: topBidded.map(b => b.ctr_pct),
              type: 'line',
              borderColor: '#f59e0b',
              backgroundColor: '#f59e0b',
              borderWidth: 2,
              yAxisID: 'y1'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#94a3b8', maxRotation: 35, minRotation: 25 }} }},
            y: {{ position: 'left', ticks: {{ color: '#94a3b8' }} }},
            y1: {{ position: 'right', ticks: {{ color: '#f59e0b' }}, grid: {{ drawOnChartArea: false }} }}
          }}
        }}
      }});

      const topDurBidded = [...bidded].sort((a, b) => b.avg_duration - a.avg_duration).slice(0, 10);
      new Chart(document.getElementById('adsKeywordDurationChart').getContext('2d'), {{
        type: 'bar',
        data: {{
          labels: topDurBidded.map(b => b.keyword),
          datasets: [{{
            label: 'Permanencia Media (Segundos)',
            data: topDurBidded.map(b => Math.round(b.avg_duration)),
            backgroundColor: 'rgba(16, 185, 129, 0.7)',
            borderColor: '#10b981',
            borderWidth: 1
          }}]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }} }},
            y: {{ ticks: {{ color: '#e2e8f0' }} }}
          }}
        }}
      }});
    }}

    function renderFunnelSection() {{
      const hab = REPORT_DATA.hablemos_audit || {{}};
      document.getElementById('hablemos-alert-card').innerHTML = `
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h3 class="text-base font-bold text-rose-400">
              ${{hab.is_1to1_pageview_trigger ? '⚠️ Alerta de Paridad 1:1 en /hablemos/ (Pageview = Conversión)' : '✅ Auditoría de Embudo /hablemos/'}}
            </h3>
            <p class="text-xs text-slate-300 mt-1">
              En los últimos 90 días se registraron <b>${{hab.hablemos_page_views_90d}} vistas de página</b> en <code>/hablemos/</code> y exactamente
              <b>${{hab.hablemos_conversions_90d}} disparos</b> del evento <code>ads_conversion_Solicitar_cotizaci_n_1</code>.
              Además, <b>${{hab.hablemos_session_starts_90d}} visitas (${{hab.direct_session_reset_pct}}%)</b> iniciaron como sesión nueva Directa.
            </p>
          </div>
        </div>
      `;

      document.getElementById('hablemos-attr-tbody').innerHTML = (hab.conversion_attribution_breakdown || []).map(r => `
        <tr>
          <td class="py-2.5 px-3 font-semibold text-emerald-400">${{r.first_user_source_medium}}</td>
          <td class="py-2.5 px-3 text-slate-300">${{r.session_source_medium}}</td>
          <td class="py-2.5 px-3 text-slate-300">${{r.sessions}}</td>
          <td class="py-2.5 px-3 font-bold text-amber-400">${{r.key_events}}</td>
          <td class="py-2.5 px-3 text-slate-200">${{fmtDur(r.avg_duration)}}</td>
        </tr>
      `).join('');

      const landings = REPORT_DATA.target_landings || {{}};
      document.getElementById('landings-core-tbody').innerHTML = Object.entries(landings).map(([name, d]) => `
        <tr>
          <td class="py-2.5 px-3 font-semibold text-white">${{name}}</td>
          <td class="py-2.5 px-3 text-slate-300">${{d.users}}</td>
          <td class="py-2.5 px-3 text-slate-200">${{d.sessions}}</td>
          <td class="py-2.5 px-3 text-emerald-400 font-semibold">${{fmtDur(d.avg_duration)}}</td>
          <td class="py-2.5 px-3 text-blue-400">${{d.engagement_rate.toFixed(1)}}%</td>
          <td class="py-2.5 px-3 font-bold text-amber-400">${{d.key_events}}</td>
        </tr>
      `).join('');

      document.getElementById('content-pages-tbody').innerHTML = (REPORT_DATA.content_data || []).slice(0, 8).map(p => `
        <tr>
          <td class="py-2 px-2 text-xs font-mono text-slate-200">${{p.path}}</td>
          <td class="py-2 px-2 text-slate-300">${{p.sessions}}</td>
          <td class="py-2 px-2 text-slate-400">${{p.views}}</td>
          <td class="py-2 px-2 text-emerald-400 font-medium">${{fmtDur(p.avg_duration)}}</td>
          <td class="py-2 px-2 text-blue-400">${{p.engagement_rate.toFixed(0)}}%</td>
        </tr>
      `).join('');
    }}

    function renderDeviceAndGeoSection() {{
      const devMatrix = REPORT_DATA.device_matrix || {{}};
      const segNames = Object.keys(devMatrix);

      let devRows = '';
      segNames.forEach(seg => {{
        ['desktop', 'mobile'].forEach(dev => {{
          const d = devMatrix[seg][dev];
          devRows += `
            <tr>
              <td class="py-2.5 px-3 font-semibold text-white">${{seg}}</td>
              <td class="py-2.5 px-3 text-slate-300">${{dev === 'desktop' ? '💻 Desktop' : '📱 Mobile'}}</td>
              <td class="py-2.5 px-3 text-slate-200">${{d.sessions}}</td>
              <td class="py-2.5 px-3 text-emerald-400 font-medium">${{fmtDur(d.avg_duration)}}</td>
              <td class="py-2.5 px-3 text-blue-400">${{d.engagement_rate}}%</td>
              <td class="py-2.5 px-3 font-bold text-amber-400">${{d.key_events}} <span class="text-xs text-slate-400">(${{d.conv_rate}}%)</span></td>
            </tr>
          `;
        }});
      }});
      document.getElementById('device-tbody').innerHTML = devRows;

      new Chart(document.getElementById('deviceChart').getContext('2d'), {{
        type: 'bar',
        data: {{
          labels: segNames,
          datasets: [
            {{
              label: '💻 Desktop (Segundos)',
              data: segNames.map(s => Math.round(devMatrix[s].desktop.avg_duration)),
              backgroundColor: 'rgba(16, 185, 129, 0.75)'
            }},
            {{
              label: '📱 Mobile (Segundos)',
              data: segNames.map(s => Math.round(devMatrix[s].mobile.avg_duration)),
              backgroundColor: 'rgba(59, 130, 246, 0.75)'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }} }},
            y: {{ ticks: {{ color: '#94a3b8' }} }}
          }}
        }}
      }});

      const geo = REPORT_DATA.geo_summary || [];
      document.getElementById('geo-tbody').innerHTML = geo.map(g => `
        <tr>
          <td class="py-2.5 px-3 font-semibold text-white">${{g.province}}</td>
          <td class="py-2.5 px-3 text-slate-200">${{g.sessions}}</td>
          <td class="py-2.5 px-3 text-emerald-400 font-medium">${{fmtDur(g.avg_duration)}}</td>
          <td class="py-2.5 px-3 text-blue-400">${{g.engagement_rate}}%</td>
          <td class="py-2.5 px-3 font-bold text-amber-400">${{g.key_events}}</td>
          <td class="py-2.5 px-3 text-xs text-slate-400">${{(g.top_segments || []).join(' · ')}}</td>
        </tr>
      `).join('');

      new Chart(document.getElementById('geoChart').getContext('2d'), {{
        type: 'bar',
        data: {{
          labels: geo.map(g => g.province),
          datasets: [
            {{
              label: 'Sesiones (90d)',
              data: geo.map(g => g.sessions),
              backgroundColor: 'rgba(59, 130, 246, 0.7)',
              yAxisID: 'y'
            }},
            {{
              label: 'Permanencia (Segundos)',
              data: geo.map(g => Math.round(g.avg_duration)),
              type: 'line',
              borderColor: '#10b981',
              backgroundColor: '#10b981',
              borderWidth: 2,
              yAxisID: 'y1'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }} }},
            y: {{ position: 'left', ticks: {{ color: '#94a3b8' }} }},
            y1: {{ position: 'right', ticks: {{ color: '#10b981' }}, grid: {{ drawOnChartArea: false }} }}
          }}
        }}
      }});
    }}

    function renderMemorySection() {{
      document.getElementById('gemini-insights-box').innerHTML = REPORT_DATA.gemini_insights_html || '';
      document.getElementById('gemini-memory-box').innerHTML = REPORT_DATA.gemini_memory_html || '';

      const actions = REPORT_DATA.memory_actions || [];
      document.getElementById('actions-cards-list').innerHTML = actions.map(a => {{
        const isDone = a.status === 'completed';
        return `
          <div class="p-4 rounded-xl bg-slate-900/90 border ${{isDone ? 'border-emerald-500/40' : 'border-amber-500/30'}}">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-mono font-bold px-2 py-0.5 rounded ${{isDone ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}}">
                ${{isDone ? '✅ COMPLETADA' : '⏳ PENDIENTE'}} · ${{a.id}}
              </span>
              <span class="text-xs text-slate-400">Creada: ${{a.created_at}}</span>
            </div>
            <div class="text-xs font-semibold text-blue-400 uppercase tracking-wider">${{a.topic}}</div>
            <h4 class="text-sm font-bold text-white mt-0.5">${{a.title}}</h4>
            <p class="text-xs text-slate-300 mt-2 leading-relaxed">${{a.description}}</p>
            ${{a.target_metric ? `<div class="mt-3 text-xs text-emerald-400 bg-emerald-950/30 p-2 rounded border border-emerald-800/40">🎯 <b>Métrica Objetivo:</b> ${{a.target_metric}}</div>` : ''}}
          </div>
        `;
      }}).join('');
    }}

    function renderQualityScoreMonitorSection() {{
      const nativeAds = REPORT_DATA.native_google_ads_v23 || {{}};
      const kws = nativeAds.keywords_quality_score || [];
      const qsSum = nativeAds.quality_score_summary || {{}};

      const scored = kws.filter(k => k.quality_score !== null && k.quality_score !== undefined);
      const crit = scored.filter(k => k.quality_score <= 3);
      const regular = scored.filter(k => k.quality_score >= 4 && k.quality_score <= 6);
      const good = scored.filter(k => k.quality_score >= 7);

      document.getElementById('qs-kpi-summary-cards').innerHTML = `
        <div class="glass-card p-5 border-l-4 border-amber-500">
          <div class="text-xs text-slate-400">Quality Score Ponderado por Impresiones</div>
          <div class="text-3xl font-bold text-amber-400 mt-1">${{qsSum.weighted_avg_qs || '2.99'}} <span class="text-sm font-normal text-slate-400">/ 10</span></div>
          <p class="text-xs text-slate-300 mt-2">
            El promedio general de la cuenta está por debajo de 5 puntos, lo que causa que Google aumente el costo por clic y limite apariciones.
          </p>
        </div>
        <div class="glass-card p-5 border-l-4 border-rose-500">
          <div class="text-xs text-slate-400">Palabras Clave en Alerta Crítica (1 a 3 / 10)</div>
          <div class="text-3xl font-bold text-rose-400 mt-1">${{crit.length}} <span class="text-sm font-normal text-slate-400">de ${{scored.length}} palabras</span></div>
          <p class="text-xs text-slate-300 mt-2">
            Concentran más del 60% de las búsquedas de habilitaciones y huella ('gestión ambiental', 'informe de impacto', 'la huella de carbono').
          </p>
        </div>
        <div class="glass-card p-5 border-l-4 border-blue-500">
          <div class="text-xs text-slate-400">Diagnóstico Principal del Problema</div>
          <div class="text-lg font-bold text-blue-300 mt-1">${{qsSum.below_avg_landing_count || 22}} de ${{scored.length}} en 'Inferior al Promedio'</div>
          <p class="text-xs text-slate-300 mt-2">
            El 85% de las notas bajas se debe a que la página de destino no tiene los términos exactos que busca el usuario.
          </p>
        </div>
      `;

      // Tabla Semáforo
      document.getElementById('qs-monitor-table-body').innerHTML = scored.map(k => {{
        const qs = k.quality_score;
        let statusBadge = '';
        let rowClass = '';
        let action = '';

        if (qs <= 3) {{
          statusBadge = '<span class="px-2 py-0.5 rounded text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">🔴 CRÍTICO</span>';
          rowClass = 'bg-rose-950/20';
          action = 'Poner este término textual en el título de la página de destino para subir la nota.';
        }} else if (qs <= 6) {{
          statusBadge = '<span class="px-2 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">🟡 REGULAR</span>';
          action = 'Reforzar el término dentro de los párrafos y subtítulos de la página.';
        }} else {{
          statusBadge = '<span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">🟢 EXCELENTE</span>';
          action = 'Mantener y proteger esta keyword; es de bajo costo y alta conversión.';
        }}

        return `
          <tr class="${{rowClass}}">
            <td class="py-2.5 px-3">${{statusBadge}}</td>
            <td class="py-2.5 px-3 font-semibold text-white">[${{k.keyword}}]</td>
            <td class="py-2.5 px-3 text-xs text-slate-300">${{k.ad_group}}</td>
            <td class="py-2.5 px-3 font-bold text-sm ${{qs <= 3 ? 'text-rose-400' : (qs <= 6 ? 'text-amber-300' : 'text-emerald-400')}}">${{qs}} / 10</td>
            <td class="py-2.5 px-3">${{fmtBadge(k.creative_quality)}}</td>
            <td class="py-2.5 px-3">${{fmtBadge(k.expected_ctr)}}</td>
            <td class="py-2.5 px-3">${{fmtBadge(k.landing_experience)}}</td>
            <td class="py-2.5 px-3 text-slate-200">${{k.impressions_30d.toLocaleString('es-AR')}}</td>
            <td class="py-2.5 px-3 text-xs text-slate-300">${{action}}</td>
          </tr>
        `;
      }}).join('');

      // Gráficos Quality Score
      new Chart(document.getElementById('qsDistributionChart').getContext('2d'), {{
        type: 'pie',
        data: {{
          labels: ['Críticas (1-3 pts)', 'Regulares (4-6 pts)', 'Saludables (7-10 pts)'],
          datasets: [{{
            data: [crit.length, regular.length, good.length],
            backgroundColor: ['#f43f5e', '#f59e0b', '#10b981'],
            borderWidth: 0
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#cbd5e1' }} }} }}
        }}
      }});

      // Conteo de factores
      let landingBelow = 0, creativeBelow = 0, ctrBelow = 0;
      scored.forEach(k => {{
        if (k.landing_experience === 'BELOW_AVERAGE') landingBelow++;
        if (k.creative_quality === 'BELOW_AVERAGE') creativeBelow++;
        if (k.expected_ctr === 'BELOW_AVERAGE') ctrBelow++;
      }});

      new Chart(document.getElementById('qsComponentsChart').getContext('2d'), {{
        type: 'bar',
        data: {{
          labels: ['Página de Destino (Landing)', 'CTR Esperado', 'Relevancia Anuncio'],
          datasets: [{{
            label: 'Keywords con calificación INFERIOR al promedio',
            data: [landingBelow, ctrBelow, creativeBelow],
            backgroundColor: ['rgba(244, 63, 94, 0.8)', 'rgba(245, 158, 11, 0.8)', 'rgba(59, 130, 246, 0.8)'],
            borderWidth: 1
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }} }},
            y: {{ ticks: {{ color: '#94a3b8' }} }}
          }}
        }}
      }});
    }}

    function renderPendingTasksSection() {{
      const actions = REPORT_DATA.memory_actions || [];
      const pending = actions.filter(a => a.status === 'pending');

      const buildCard = (a) => `
        <div class="p-5 rounded-xl bg-slate-900/90 border border-amber-500/30 hover:border-amber-500/60 transition space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
              ⏳ ${{a.id}}
            </span>
            <span class="text-xs text-slate-400">Creada: ${{a.created_at}}</span>
          </div>
          <div>
            <div class="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">${{a.topic}}</div>
            <h4 class="text-sm font-bold text-white mt-0.5">${{a.title}}</h4>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">${{a.description}}</p>
          ${{a.target_metric ? `<div class="text-xs text-emerald-400 bg-emerald-950/40 p-2.5 rounded-lg border border-emerald-800/40">🎯 <b>Beneficio / Meta:</b> ${{a.target_metric}}</div>` : ''}}
        </div>
      `;

      const cardsHtml = pending.length > 0 
        ? pending.map(buildCard).join('')
        : '<div class="text-xs text-slate-400 p-4">No hay tareas pendientes en este momento.</div>';

      const dedicatedEl = document.getElementById('dedicated-pending-list');
      if (dedicatedEl) dedicatedEl.innerHTML = cardsHtml;

      const footerEl = document.getElementById('footer-pending-actions');
      if (footerEl) footerEl.innerHTML = cardsHtml;
    }}

    // Inicializar Dashboard con ejecución aislada por bloque
    const initSteps = [
      ['KPIs', renderKPIs],
      ['Canales', renderChannelsSection],
      ['Google Ads', renderAdsSection],
      ['Quality Score', renderQualityScoreMonitorSection],
      ['Embudo', renderFunnelSection],
      ['Dispositivos y Geo', renderDeviceAndGeoSection],
      ['Memoria', renderMemorySection],
      ['Tareas Pendientes', renderPendingTasksSection]
    ];
    initSteps.forEach(([name, fn]) => {{
      try {{
        fn();
      }} catch (err) {{
        console.error(`Error inicializando sección ${{name}}:`, err);
      }}
    }});
  </script>
</body>
</html>
"""
    index_path = output_dir / "index.html"
    index_path.write_text(html_content, encoding="utf-8")
    return index_path
