# Automatización de Reportes Semanales GA4 + Google Ads + Dashboard Web (GitHub Pages) + Google Chat

Este proyecto genera automáticamente todos los viernes a las 09:00 AM ART (12:00 UTC):
1. **Un Dashboard Web Estadístico Interactivo (`docs/index.html`)** con gráficos (Chart.js), selector de ventanas (7, 30 y 90 días), variaciones semana contra semana (`WoW %`) y tablas detalladas de **GA4 (Propiedad `291106508`)** y **Google Ads (`368-683-2552 - DHARTEC S.A.S.`)**.
2. **Una Tarjeta Ejecutiva Compacta en Google Chat (`Cards v2`)** que muestra únicamente los **Insights Estratégicos y Planes de Mejora de Gemini AI**, el **Seguimiento de la Memoria de Acciones (`actions_memory.json`)** y el **botón de acceso directo al Dashboard Web**.

---

## 🌐 Cómo Activar GitHub Pages (Gratis y Acceso con Link)

1. Sube este proyecto a tu repositorio de GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: dashboard web estadístico GA4/Ads + tarjeta ejecutiva Google Chat"
   git branch -M main
   git remote add origin https://github.com/TU-USUARIO/TU-REPOSITORIO.git
   git push -u origin main
   ```
2. En tu repositorio de GitHub, ve a **Settings** $\rightarrow$ **Pages**.
3. En **Build and deployment** $\rightarrow$ **Source**, elige **Deploy from a branch**.
4. En **Branch**, selecciona `main` y la carpeta **`/docs`**, y haz clic en **Save**.
5. ¡Listo! El link de tu web será `https://TU-USUARIO.github.io/TU-REPOSITORIO/` (el workflow de GitHub Actions detecta automáticamente `github.repository` y coloca ese link exacto en el botón de Google Chat).

---

## 🛠️ Comandos Locales

```bash
# Generar el Dashboard Web (docs/index.html) y enviar la tarjeta ejecutiva a Google Chat
python report_generator.py

# Ver todas las acciones registradas en memoria
python report_generator.py --list-actions

# Marcar una acción como completada para que Gemini evalúe su impacto antes vs. después
python report_generator.py --mark-completed ACT-001 --notes "Se implementó cambio en campaña/landing"
```
