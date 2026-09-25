import os
import requests
import xml.etree.ElementTree as ET
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

SISA_USER = os.getenv("SISA_USER", "")
SISA_PASS = os.getenv("SISA_PASS", "")

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
    .cobertura-rnos { font-size: 0.8rem; color: #15803d; margin-top: 4px; }
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
          errBox.innerText = `SISA: ${data.error}`;
          errBox.style.display = 'block';
          return;
        }

        document.getElementById('res-nombre').innerText = data.nombre || 'No registrado';
        const cobContainer = document.getElementById('res-coberturas');
        cobContainer.innerHTML = '';

        if (data.coberturas && data.coberturas.length > 0) {
          data.coberturas.forEach(c => {
            cobContainer.innerHTML += `
              <div class="cobertura-card">
                <div class="cobertura-nombre">${c.coberturaSocial}</div>
                <div class="cobertura-rnos">RNOS: ${c.rnos || 'S/D'}</div>
              </div>
            `;
          });
        } else {
          cobContainer.innerHTML = `<span class="badge-publico">Sin obra social registrada (Atención Pública / SUMAR+)</span>`;
        }

        box.style.display = 'block';
      } catch (e) {
        errBox.innerText = 'Error al conectar con el servidor. Intente nuevamente.';
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
def get_puco(dni: str):
    dni_limpio = "".join(filter(str.isdigit, dni))
    
    if not SISA_USER or not SISA_PASS:
        return {"error": "Faltan configurar las variables SISA_USER y SISA_PASS en Render"}

    try:
        url = f"https://sisa.msal.gov.ar/sisa/services/rest/puco/{dni_limpio}"
        res = requests.post(
            url, 
            json={"usuario": SISA_USER, "clave": SISA_PASS}, 
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        # En caso de error HTTP de red o endpoint
        if res.status_code != 200:
            return {"error": f"HTTP {res.status_code}: {res.text[:100]}"}

        # Parsear XML retornado por SISA
        root = ET.fromstring(res.text)
        
        # SISA puede devolver <puco> con hijos directos o múltiples nodos
        resultado = root.findtext("resultado") or ""

        # Manejo de errores de credenciales o cuota
        if resultado in ["ERROR_AUTENTICACION", "NO_TIENE_QUOTA_DISPONIBLE", "ERROR_DATOS", "ERROR_INESPERADO"]:
            return {"error": f"{resultado} (Revise usuario/clave o cuota asignada en SISA)"}

        # Extraer registros: buscar si vienen en elementos anidados o en la raíz
        registros = []
        pucos = root.findall(".//puco") or root.findall(".//return")
        
        if pucos:
            for item in pucos:
                cob = item.findtext("coberturaSocial")
                if cob:
                    registros.append({
                        "coberturaSocial": cob,
                        "rnos": item.findtext("rnos") or "",
                        "denominacion": item.findtext("denominacion") or ""
                    })
        else:
            # Caso de resultado único en la raíz
            cob = root.findtext("coberturaSocial")
            if cob:
                registros.append({
                    "coberturaSocial": cob,
                    "rnos": root.findtext("rnos") or "",
                    "denominacion": root.findtext("denominacion") or ""
                })

        nombre = registros[0]["denominacion"] if registros else (root.findtext("denominacion") or "-")

        return {
            "nombre": nombre,
            "coberturas": registros,
            "resultado_sisa": resultado or "OK"
        }

    except ET.ParseError:
        return {"error": f"Respuesta no válida de SISA: {res.text[:120]}"}
    except Exception as e:
        return {"error": f"Excepción interna: {str(e)}"}
