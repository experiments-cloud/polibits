import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Exact model snapshot to reproduce (e.g. "gpt-3.5-turbo-0125", "gpt-4o-2024-08-06", "gpt-5.4").
MODEL = os.environ.get("MODEL", "gpt-5.4")
# GPT-5.x reasoning models only accept the default temperature (1); the
# parameter is sent only to models that support it.
SUPPORTS_TEMPERATURE = not MODEL.startswith(("gpt-5", "o1", "o3", "o4"))

def reproducir_experimento_p4():
    archivo_entrada = "p1_control.py"
    try:
        with open(archivo_entrada, "r", encoding="utf-8") as file:
            codigo_base = file.read()
            print(f"[OK] File '{archivo_entrada}' read correctly.")
    except FileNotFoundError:
        print(f"[ERROR] File '{archivo_entrada}' not found.")
        return

    prompt_instruccion = """Act as a senior Software Architect specialized in Python. Based on the discount logic of the attached monolithic system, your task is to refactor the payment engine applying the 'Strategy' behavioral design pattern.

Strictly follow these generation rules:
1. Use your Chain of Thought to explain how you will separate the business rules from the execution context.
2. The code must be functional, include static typing (Type Hints), and apply abstract classes (ABC).
3. Design a Context class (e.g., ShoppingCartContext) that includes a method to dynamically assign the strategy based on a text string (e.g., 'BLACK_FRIDAY', 'REGULAR'). 
4. Apply your professional judgment to decide on the data structure and internal algorithms of this Context that you consider most appropriate for processing the strategy selection.

[INPUT CODE]:
"""
    prompt_completo = f"{prompt_instruccion}\n{codigo_base}"

    print(f"[INFO] Sending request to {MODEL} for the Strategy pattern...")
    print(f"[INFO] Model: {MODEL} | temperature: {'0.0' if SUPPORTS_TEMPERATURE else 'default (not supported)'}")

    try:
        response = client.chat.completions.create(
            **({"temperature": 0.0} if SUPPORTS_TEMPERATURE else {}),
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an expert assistant in system architecture in Python."},
                {"role": "user", "content": prompt_completo}
            ],
        )

        resultado = response.choices[0].message.content

        archivo_salida = f"p4_ia_refactored_{MODEL}_{response.created}.py"  # keeps every run
        print(f"[INFO] Model snapshot returned by the API: {response.model}")
        with open(archivo_salida, "w", encoding="utf-8") as out_file:
            out_file.write(resultado)
        
        print(f"[SUCCESS] P4 experiment completed. Result saved in '{archivo_salida}'.")

    except Exception as e:
        print(f"[ERROR] API failure: {e}")

if __name__ == "__main__":
    reproducir_experimento_p4()