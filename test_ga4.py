import os
import sys
from pathlib import Path

# Configurar credenciales
base_dir = Path(__file__).resolve().parent
credentials_path = base_dir / "credentials.json"

if not credentials_path.exists():
    print(f"Error: No se encontró el archivo de credenciales en {credentials_path}")
    sys.exit(1)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

PROPERTY_ID = "291106508"

def main():
    print(f"--- Conectando a Google Analytics 4 (Propiedad: {PROPERTY_ID}) ---")
    try:
        client = BetaAnalyticsDataClient()
        request = RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            dimensions=[Dimension(name="country")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
            ],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        )

        response = client.run_report(request)

        print("\n✅ Conexión exitosa!")
        print(f"Filas obtenidas: {len(response.rows)}\n")
        print(f"{'País':<25} {'Usuarios Activos':<18} {'Sesiones':<12} {'Vistas de Página'}")
        print("-" * 70)

        if not response.rows:
            print("No se encontraron datos para los últimos 30 días.")
        else:
            for row in response.rows[:10]:
                country = row.dimension_values[0].value
                users = row.metric_values[0].value
                sessions = row.metric_values[1].value
                views = row.metric_values[2].value
                print(f"{country:<25} {users:<18} {sessions:<12} {views}")

    except Exception as e:
        print(f"\n❌ Error al consultar GA4: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
