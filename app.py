import re
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

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
                <div class="cobertura-nombre">${c}</div>
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
def get_puco(dni: str):
    dni_limpio = "".join(filter(str.isdigit, dni))
    if not dni_limpio:
        return {"error": "DNI inválido"}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://sisa.msal.gov.ar",
        "Referer": "https://sisa.msal.gov.ar/sisa/",
        "Accept": "*/*",
        "Accept-Language": "es-419,es;q=0.9",
        "X-GWT-Module-Base": "https://sisa.msal.gov.ar/sisa/sisa/",
        "X-GWT-Permutation": "93043F93A2BBFCE894385D3E4952CA2D",
        "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
    })

    try:
        # 1. Obtener cookie de sesión anónima
        session.get("https://sisa.msal.gov.ar/sisa/", timeout=10)

        # 2. Armar el payload GWT-RPC inyectando el DNI en la posición de búsqueda
        payload = (
            f"7|0|14|https://sisa.msal.gov.ar/sisa/sisa/|5CFBDB55F3DE4A47FE42E765E5AA02D3|"
            f"ar.gob.msal.sisa.client.commons.components.lista.service.ListService|getPage|"
            f"java.lang.Integer/3438268394|java.util.List|Z|"
            f"ar.gob.msal.sisa.shared.model.list.ComplexFilter/30068811|java.util.ArrayList/4159755760|"
            f"ar.gob.msal.sisa.client.commons.components.lista.simple.SearchFilter/1978531670|97390|"
            f"ar.gob.msal.sisa.client.entitys.list.Filter$OPERATION/3408968308|"
            f"ar.gob.msal.sisa.client.entitys.list.Filter$OPERATOR/860546718|{dni_limpio}|"
            f"1|2|3|4|10|5|5|5|6|6|5|7|5|6|8|5|790|5|1|-2|9|0|9|1|10|11|12|0|13|0|0|14|0|0|1|5|25|0|0|"
        )

        # 3. Consultar servicio interno
        res = session.post(
            "https://sisa.msal.gov.ar/sisa/sisa/service/list",
            data=payload,
            timeout=15
        )

        raw_text = res.text

        # GWT responde con prefijo '//OK' cuando la llamada es exitosa
        if not raw_text.startswith("//OK"):
            return {"error": f"SISA no respondió correctamente: {raw_text[:120]}"}

        # 4. Extraer strings del payload serializado de GWT
        # El formato GWT devuelve una lista serializada: //OK[...,["str1","str2",...],...]
        matches = re.findall(r'"([^"]*)"', raw_text)

        coberturas = []
        nombre = None

        # Expresión para descartar clases internas de Java/GWT y metadatos
        ignorar = re.compile(r'^(ar\.gob|java\.|DNI|M|F|X|[0-9]+)$', re.IGNORECASE)

        for s in matches:
            s_clean = s.strip()
            if not s_clean or ignorar.match(s_clean):
                continue
            
            # Si parece nombre y apellido (contiene coma o apellidos típicos)
            if ("," in s_clean or s_clean.isupper()) and not any(p in s_clean for p in ["O.S.", "SWISS", "MEDIC", "OBRA SOCIAL", "IOMA", "OSDE", "PAMI", "S.A."]):
                if not nombre:
                    nombre = s_clean
            # Si parece obra social o prepaga
            elif any(p in s_clean for p in ["O.S.", "OS", "IOMA", "SWISS", "MEDIC", "S.A.", "OBRA SOCIAL", "PAMI", "OSDE", "SALUD", "UNION", "ASOCIACION"]):
                if s_clean not in coberturas:
                    coberturas.append(s_clean)

        return {
            "nombre": nombre or "Paciente identificado",
            "coberturas": coberturas
        }

    except Exception as e:
        return {"error": f"Excepción en la consulta: {str(e)}"}
