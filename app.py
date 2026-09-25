import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from playwright.async_api import async_playwright

app = FastAPI()

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verificación de Cobertura - CAPS</title>
  <style>
    * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: #f4f6f9; margin: 0; padding: 20px; display: flex; justify-content: center; }
    .container { background: #fff; width: 100%; max-width: 600px; padding: 24px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-top: 20px; }
    h1 { font-size: 1.3rem; color: #1e293b; margin-top: 0; }
    p.sub { font-size: 0.85rem; color: #64748b; margin-bottom: 20px; }
    .input-group { display: flex; gap: 8px; margin-bottom: 16px; }
    input { flex: 1; padding: 12px; font-size: 1.1rem; border: 1.5px solid #cbd5e1; border-radius: 8px; outline: none; }
    input:focus { border-color: #0284c7; }
    button { background: #0284c7; color: white; border: none; border-radius: 8px; padding: 0 20px; font-size: 1rem; font-weight: 600; cursor: pointer; }
    button:disabled { background: #94a3b8; }
    .card-res { display: none; margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 16px; }
    .item { margin-bottom: 12px; }
    .item-label { font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 600; }
    .item-val { font-size: 1.05rem; color: #0f172a; font-weight: 600; margin-top: 2px; }
    .cobertura-card { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
    .cobertura-nombre { font-size: 1rem; font-weight: bold; color: #166534; }
    .cobertura-detalle { font-size: 0.85rem; color: #374151; margin-top: 2px; }
    .badge-publico { display: inline-block; padding: 8px 12px; border-radius: 6px; font-size: 0.95rem; font-weight: bold; background: #fef3c7; color: #92400e; }
    .alert-error { background: #fef2f2; color: #991b1b; padding: 12px; border-radius: 8px; border: 1px solid #fecaca; margin-top: 15px; font-size: 0.9rem; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Consulta de Cobertura</h1>
    <p class="sub">Padrón Único Consolidado Operativo (PUCO)</p>
    
    <div class="input-group">
      <input type="number" id="dni" placeholder="Ingrese DNI..." autofocus onkeydown="if(event.key==='Enter') consultar()">
      <button id="btn" onclick="consultar()">Consultar</button>
    </div>

    <div id="error-box" class="alert-error" style="display: none;"></div>

    <div id="resultado" class="card-res">
      <div class="item">
        <div class="item-label">Paciente</div>
        <div id="res-nombre" class="item-val">-</div>
      </div>
      <div class="item">
        <div class="item-label">Coberturas Detectadas</div>
        <div id="res-coberturas"></div>
      </div>
    </div>
  </div>

  <script>
    async function consultar() {
      const dni = document.getElementById('dni').value.trim();
      const btn = document.getElementById('btn');
      const box = document.getElementById('resultado');
      const errBox = document.getElementById('error-box');

      if (!dni) return;
      btn.disabled = true;
      btn.innerText = 'Buscando...';
      box.style.display = 'none';
      errBox.style.display = 'none';

      try {
        const resp = await fetch(`/api/puco/${dni}`);
        const data = await resp.json();

        if (data.error) {
          errBox.innerText = data.error;
          errBox.style.display = 'block';
          return;
        }

        document.getElementById('res-nombre').innerText = data.nombre || 'No informado';
        const cobContainer = document.getElementById('res-coberturas');
        cobContainer.innerHTML = '';

        if (data.coberturas && data.coberturas.length > 0) {
          data.coberturas.forEach(c => {
            cobContainer.innerHTML += `
              <div class="cobertura-card">
                <div class="cobertura-nombre">${c.cobertura}</div>
                <div class="cobertura-detalle">Doc: ${c.tipodoc} ${c.nrodoc}</div>
              </div>
            `;
          });
        } else {
          cobContainer.innerHTML = `<span class="badge-publico">Sin obra social registrada (Atención Pública / SUMAR+)</span>`;
        }

        box.style.display = 'block';
      } catch (e) {
        errBox.innerText = 'Error al conectar con el servidor.';
        errBox.style.display = 'block';
      } finally {
        btn.disabled = false;
        btn.innerText = 'Consultar';
      }
    }
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_CONTENT

@app.get("/api/puco/{dni}")
async def get_puco(dni: str):
    dni_limpio = "".join(filter(str.isdigit, dni))
    if not dni_limpio:
        return {"error": "DNI inválido"}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            # 1. Cargar la página esperando que el DOM básico esté listo
            await page.goto("https://sisa.msal.gov.ar/sisa/#sisa", wait_until="domcontentloaded", timeout=60000)

            # 2. Si todavía no está en la pantalla del padrón, buscar y hacer clic en PUCO
            # Intentamos detectar si ya está visible el buscador o si hay que clickear la tarjeta
            input_existente = page.locator('input[placeholder*="valor"]')
            if await input_existente.count() == 0:
                # Buscamos cualquier botón o tarjeta que mencione PUCO
                tarjeta_puco = page.locator('div:has-text("PUCO"), span:has-text("PUCO"), a:has-text("PUCO")').last
                try:
                    await tarjeta_puco.wait_for(timeout=25000)
                    await tarjeta_puco.click()
                except Exception:
                    # Si no encuentra por texto, forzamos navegación directa por hash
                    await page.evaluate("window.location.hash = '#puco'")

            # 3. Esperar que el input de búsqueda del padrón esté visible
            # Filtramos específicamente el input que tiene 'valor' o que no es el de usuario/login
            input_dni = page.locator('input[placeholder*="valor"], input:not([placeholder*="suario"]):not([type="password"]):visible').first
            await input_dni.wait_for(timeout=25000)
            
            # Limpiar y escribir el DNI
            await input_dni.click()
            await input_dni.fill(dni_limpio)

            # 4. Clic en Buscar
            btn_buscar = page.locator('button:has-text("Buscar"), div[role="button"]:has-text("Buscar"), .btn:has-text("Buscar")').first
            await btn_buscar.click()

            # 5. Esperar a que responda el grid de resultados
            await page.wait_for_timeout(4000)

            # 6. Extraer resultados
            filas_datos = []
            nombre_encontrado = None

            rows = page.locator("table tr")
            count = await rows.count()

            for i in range(count):
                row = rows.nth(i)
                text = await row.inner_text()
                
                if dni_limpio in text:
                    cols = [c.strip() for c in text.split("\t") if c.strip()]
                    if len(cols) >= 5:
                        tipodoc = cols[0]
                        nrodoc = cols[1]
                        cobertura = cols[3]
                        denominacion = cols[4]

                        if not nombre_encontrado:
                            nombre_encontrado = denominacion

                        filas_datos.append({
                            "tipodoc": tipodoc,
                            "nrodoc": nrodoc,
                            "cobertura": cobertura
                        })
                    elif len(cols) >= 4:
                        cobertura = cols[2]
                        denominacion = cols[3]
                        if not nombre_encontrado:
                            nombre_encontrado = denominacion
                        filas_datos.append({
                            "tipodoc": "DNI",
                            "nrodoc": dni_limpio,
                            "cobertura": cobertura
                        })

            await browser.close()

            return {
                "nombre": nombre_encontrado,
                "coberturas": filas_datos
            }

    except Exception as e:
        return {"error": f"Error al ejecutar automatización: {str(e)}"}
