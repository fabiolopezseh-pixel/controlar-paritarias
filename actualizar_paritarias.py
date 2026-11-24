import os
import json
import datetime
from google import genai
from google.genai import types

ARCHIVO_JSON = "paritarias_ar.json"

def cargar_actual():
    with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_actualizado(data):
    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Falta la variable de entorno GEMINI_API_KEY")

    data_actual = cargar_actual()
    hoy = datetime.datetime.now()
    mes_anio_actual = hoy.strftime("%Y-%m")

    client = genai.Client(api_key=api_key)

    prompt = f"""
Eres un especialista en liquidación de sueldos y Convenios Colectivos de Trabajo (CCT) de Argentina.
Fecha actual de consulta: {hoy.strftime("%Y-%m-%d")} ({mes_anio_actual}).

Tu tarea es verificar en fuentes oficiales y portales laborales argentinos actualizados (FATSA, FAECYS, UPSRA, UOCRA, UOM, Camioneros, Ignacio Online, Sueldos y Jornales) si existen escalas salariales básicas vigentes más recientes para los convenios incluidos en el siguiente JSON:

{json.dumps(data_actual, ensure_ascii=False, indent=2)}

REGLAS ESTRICTAS:
1. Mantén EXACTAMENTE la misma estructura de claves JSON, nombres de rubros, nombres de convenios, iconos y nombres de categorías del JSON original. No agregues ni elimines claves.
2. Actualiza los montos numéricos (como string sin puntos ni signos, ej: "1950000") de cada categoría ÚNICAMENTE si encuentras un acuerdo paritario oficial vigente para {mes_anio_actual} o posterior que supere los valores actuales.
3. Si para algún convenio no hay un acuerdo nuevo confirmado o el monto vigente es igual al actual, conserva el valor exacto que ya tenía el JSON.
4. Si al menos un salario básico cambió respecto al JSON original, actualiza el campo "version" al formato "{hoy.strftime("%Y.%m")}.{hoy.strftime("%d")}". Si no hubo cambios en ningún monto, mantén la misma "version".
5. Devuelve ÚNICAMENTE el objeto JSON válido, sin bloques markdown (```json), sin explicaciones ni texto adicional.
"""

    print("Consultando acuerdos paritarios vigentes con Gemini + Google Search...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0.1,
        ),
    )

    texto_limpio = response.text.strip()
    if texto_limpio.startswith("```"):
        lineas = texto_limpio.splitlines()
        lineas = [l for l in lineas if not l.strip().startswith("```")]
        texto_limpio = "\n".join(lineas).strip()

    try:
        nueva_data = json.loads(texto_limpio)
    except json.JSONDecodeError as e:
        print("Error al parsear respuesta JSON:", texto_limpio)
        raise e

    # Validación de integridad estructural antes de sobrescribir
    if "actividades" not in nueva_data or len(nueva_data["actividades"]) != len(data_actual["actividades"]):
        raise ValueError("La respuesta no conserva la estructura completa de actividades. Se aborta el guardado.")

    if json.dumps(nueva_data["actividades"], sort_keys=True) == json.dumps(data_actual["actividades"], sort_keys=True):
        print("Sin cambios salariales detectados. El archivo paritarias_ar.json ya está al día.")
        return

    guardar_actualizado(nueva_data)
    print(f"¡Actualización completada! Nueva versión: {nueva_data.get('version')}")

if __name__ == "__main__":
    main()
