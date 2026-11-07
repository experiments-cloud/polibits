import os
from openai import OpenAI

# Initialize the client (assumes OPENAI_API_KEY environment variable is configured)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Exact model snapshot to reproduce (e.g. "gpt-3.5-turbo-0125", "gpt-4o-2024-08-06", "gpt-5.4").
MODEL = os.environ.get("MODEL", "gpt-5.4")
# GPT-5.x reasoning models only accept the default temperature (1); the
# parameter is sent only to models that support it.
SUPPORTS_TEMPERATURE = not MODEL.startswith(("gpt-5", "o1", "o3", "o4"))

def reproducir_experimento_p2():
    # 1. Read the source code of the base monolith (Baseline)
    archivo_entrada = "p1_control.py"
    try:
        with open(archivo_entrada, "r", encoding="utf-8") as file:
            codigo_base = file.read()
            print(f"[OK] File '{archivo_entrada}' read correctly.")
    except FileNotFoundError:
        print(f"[ERROR] File '{archivo_entrada}' not found. Make sure it is in the same directory.")
        return

    # 2. Define the Methodologically Neutral Prompt (No bias)
    prompt_instruccion = """Act as a senior Software Architect specialized in Python. Below, I will provide you with the source code of a monolithic system with high technical debt.

Your task is to exclusively refactor the document processing logic and the discount logic by applying the 'Factory Method' creational design pattern.

Strictly follow these generation rules:
1. Before writing the source code, use your Chain of Thought to analyze the current coupling and explain your design proposal.
2. The resulting code must be fully functional and include static typing (Type Hints).
3. The system must be ready to run on Python 3.12 without the need to install external libraries.
4. Apply your professional judgment to decide on the data structure and internal algorithms of the Factory that you consider most appropriate to ensure the scalability of the system.

[INPUT CODE]:
"""
    # Concatenate the instruction with the code
    prompt_completo = f"{prompt_instruccion}\n{codigo_base}"

    print("[INFO] Sending request to GPT...")
    print(f"[INFO] Model: {MODEL} | temperature: {'0.0' if SUPPORTS_TEMPERATURE else 'default (not supported)'}")

    # 3. API call with the experiment parameters
    try:
        response = client.chat.completions.create(
            **({"temperature": 0.0} if SUPPORTS_TEMPERATURE else {}),
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an expert assistant in software engineering, systems architecture, and refactoring in Python."},
                {"role": "user", "content": prompt_completo}
            ],
        )

        resultado = response.choices[0].message.content

        # 4. Save the result for later analysis with Radon and Timeit
        archivo_salida = f"p2_ia_refactored_{MODEL}_{response.created}.py"  # keeps every run
        print(f"[INFO] Model snapshot returned by the API: {response.model}")
        with open(archivo_salida, "w", encoding="utf-8") as out_file:
            out_file.write(resultado)
        
        print(f"[SUCCESS] Experiment completed. The raw result from the IA has been saved in '{archivo_salida}'.")

    except Exception as e:
        print(f"[ERROR] A failure occurred during the API call: {e}")

if __name__ == "__main__":
    reproducir_experimento_p2()