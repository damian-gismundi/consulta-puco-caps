import os
import requests
import xml.etree.ElementTree as ET
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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
    .container { background: #fff; width: 100%; max-width: 480px; padding: 24px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-top: 20px; }
    h1 { font-size: 1.25rem; color: #1e293b; margin-top: 0; }
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
    .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; }
    .badge-os { background: #e0f2fe; color: #0369a1; }
    .badge-publico { background: #fef3c7; color: #92400e; }
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

    <div id="resultado" class="card-res">
      <div class="item">
        <div class="item-label">Paciente</div>
        <div id="res-nombre" class="item-val">-</div>
      </div>
      <div class="item">
        <div class="item-label">Cobertura</div>
        <div id="res-cobertura" class="item-val">-</div>
      </div>
      <div class="item">
        <div class="item-label">Código RNOS</div>
        <div id="res-rnos" class="item-val">-</div>
      </div>
    </div>
  </div>

  <script>
    async function consultar() {
      const dni = document.getElementById('dni').value.trim();
      const btn = document.getElementById('btn');
      const box = document.getElementById('resultado');

      if (!dni) return;
      btn.disabled = true;
      btn.innerText = 'Buscando...';
      box.style.display = 'none';

      try {
        const resp = await fetch(`/api/puco/${dni}`);
        const data = await resp.json();
        
        document.getElementById('res-nombre').innerText = data.nombre || 'No informado';
        document.getElementById('res-cobertura').innerHTML = data.tiene_cobertura 
          ? `<span class="badge badge-os">${data.cobertura}</span>`
          : `<span class="badge badge-publico">Sin obra social (Atención Pública / SUMAR+)</span>`;
        document.getElementById('res-rnos').innerText = data.rnos || '-';
        box.style.display = 'block';
      } catch (e) {
        alert('Error al consultar. Verifique la conexión o el DNI.');
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
    
    # 1. Si tenés credenciales configuradas en las variables de entorno de Render:
    if SISA_USER and SISA_PASS:
        try:
            url = f"https://sisa.msal.gov.ar/sisa/services/rest/puco/{dni_limpio}"
            res = requests.post(url, json={"usuario": SISA_USER, "clave": SISA_PASS}, timeout=8)
            root = ET.fromstring(res.text)
            resultado = root.findtext("resultado")
            
            if resultado == "OK":
                return {
                    "tiene_cobertura": True,
                    "nombre": root.findtext("denominacion"),
                    "cobertura": root.findtext("coberturaSocial"),
                    "rnos": root.findtext("rnos")
                }
            else:
                return {
                    "tiene_cobertura": False,
                    "nombre": "-",
                    "cobertura": "Sin cobertura formal registrada",
                    "rnos": "-"
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # 2. Si todavía no cargaste credenciales (aviso):
    return {
        "tiene_cobertura": False,
        "nombre": "Configuración requerida",
        "cobertura": "Falta configurar SISA_USER y SISA_PASS en el servidor",
        "rnos": "-"
    }
