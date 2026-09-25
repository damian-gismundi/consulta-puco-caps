@app.get("/api/puco/{dni}")
def get_puco(dni: str):
    dni_limpio = "".join(filter(str.isdigit, dni))
    if not dni_limpio:
        return {"error": "DNI inválido"}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "es-419,es;q=0.9",
        "Origin": "https://sisa.msal.gov.ar",
        "Referer": "https://sisa.msal.gov.ar/sisa/",
    })

    try:
        # 1. Cargar la landing inicial para cookies base
        session.get("https://sisa.msal.gov.ar/sisa/", timeout=10)

        # 2. Inicializar el contexto del módulo GWT
        session.get("https://sisa.msal.gov.ar/sisa/sisa/sisa.nocache.js", timeout=10)

        # 3. Payload GWT con headers de RPC
        headers_rpc = {
            "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
            "X-GWT-Module-Base": "https://sisa.msal.gov.ar/sisa/sisa/",
            "X-GWT-Permutation": "93043F93A2BBFCE894385D3E4952CA2D",
        }

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

        res = session.post(
            "https://sisa.msal.gov.ar/sisa/sisa/service/list",
            data=payload,
            headers=headers_rpc,
            timeout=15
        )

        raw_text = res.text

        if "SessionTimeOutException" in raw_text:
            return {"error": "SISA exige sesión activa iniciada en el navegador. Conviene habilitar la cuota del usuario oficial para evitar bloqueos de sesión."}

        if not raw_text.startswith("//OK"):
            return {"error": f"SISA respondió: {raw_text[:120]}"}

        # Extraer strings devueltos
        matches = re.findall(r'"([^"]*)"', raw_text)

        coberturas = []
        nombre = None
        ignorar = re.compile(r'^(ar\.gob|java\.|DNI|M|F|X|[0-9]+)$', re.IGNORECASE)

        for s in matches:
            s_clean = s.strip()
            if not s_clean or ignorar.match(s_clean):
                continue
            
            if ("," in s_clean or " " in s_clean) and not any(p in s_clean for p in ["O.S.", "SWISS", "MEDIC", "OBRA SOCIAL", "IOMA", "OSDE", "PAMI", "S.A."]):
                if not nombre and len(s_clean) > 4:
                    nombre = s_clean
            elif any(p in s_clean for p in ["O.S.", "OS", "IOMA", "SWISS", "MEDIC", "S.A.", "OBRA SOCIAL", "PAMI", "OSDE", "SALUD"]):
                if s_clean not in coberturas:
                    coberturas.append(s_clean)

        return {
            "nombre": nombre or "Paciente identificado",
            "coberturas": coberturas
        }

    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}
