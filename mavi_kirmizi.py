import os
import sys
import ast
import json
import urllib.request
import urllib.error

COUNTER_FILE = "counter.txt"
SARI_SISTEM_FILE = "sari_sistem.py"

MAX_GENERATIONS = 50
MAX_CODE_LINES = 35

count = 0

if os.path.exists(COUNTER_FILE):
    with open(COUNTER_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if content.isdigit():
            count = int(content)

if count >= MAX_GENERATIONS:
    print(f"Deney {MAX_GENERATIONS} nesil sınırına ulaştı.")
    sys.exit(0)

print(f"--- Deney Adımı {count + 1}/{MAX_GENERATIONS} Başlatılıyor ---")

api_key = os.getenv("OPENAI_API_KEY", "").strip()

if not api_key:
    print("Hata: OPENAI_API_KEY bulunamadı.")
    sys.exit(1)


with open(SARI_SISTEM_FILE, "r", encoding="utf-8") as f:
    mevcut_kod = f.read()


prompt = f"""
Sen Mavi Sistem'sin.

Aşağıdaki Python oyun motorunu incele.

--- SARI SİSTEM ---
{mevcut_kod}
--- SARI SİSTEM SONU ---

Bu sistem için küçük ama gerçek bir geliştirme yap.

Kurallar:
1. Sadece Python kodu döndür.
2. Markdown kullanma.
3. Açıklama yazma.
4. En fazla {MAX_CODE_LINES} satır kod üret.
5. Yeni kod mevcut Oyuncu sınıfına eklenebilecek bir metot olmalı.
6. Mevcut özellikleri bozmamalı.
7. Kod çalışabilir olmalı.

Yalnızca yeni metodu döndür.
"""


url = "https://api.openai.com/v1/responses"

payload = {
    "model": "gpt-5.6-luna",
    "input": prompt
}

data = json.dumps(payload).encode("utf-8")

request = urllib.request.Request(
    url,
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    },
    method="POST"
)


try:
    with urllib.request.urlopen(request, timeout=60) as response:
        response_data = json.loads(
            response.read().decode("utf-8")
        )

except urllib.error.HTTPError as e:
    error_body = e.read().decode("utf-8", errors="replace")

    print("OpenAI API Hatası!")
    print(f"HTTP Kod: {e.code}")
    print(f"Sunucu cevabı: {error_body}")

    sys.exit(1)

except Exception as e:
    print(f"Mavi Sistem Hata Aldı: {e}")
    sys.exit(1)


try:
    generated_code = response_data["output"][0]["content"][0]["text"]

except (KeyError, IndexError, TypeError):
    print("OpenAI cevabı beklenen formatta değil.")
    print(
        json.dumps(
            response_data,
            indent=2,
            ensure_ascii=False
        )
    )
    sys.exit(1)


generated_code = generated_code.strip()

generated_code = (
    generated_code
    .replace("```python", "")
    .replace("```", "")
    .strip()
)


line_count = len(generated_code.splitlines())

print(
    f"Mavi Sistem kod üretti: "
    f"{line_count} satır."
)


if line_count > MAX_CODE_LINES:
    print(
        f"Kırmızı Sistem reddetti: "
        f"{line_count} > {MAX_CODE_LINES} satır."
    )
    sys.exit(1)


try:
    tree = ast.parse(generated_code)

except SyntaxError as e:
    print(
        f"Kırmızı Sistem reddetti: "
        f"Syntax hatası -> {e}"
    )
    sys.exit(1)


functions = [
    node
    for node in tree.body
    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef)
    )
]


if len(functions) != 1:
    print(
        "Kırmızı Sistem reddetti: "
        "Tam olarak bir fonksiyon bekleniyordu."
    )
    sys.exit(1)


new_function = functions[0]

if not new_function.args.args:
    print(
        "Kırmızı Sistem reddetti: "
        "self parametresi yok."
    )
    sys.exit(1)


print("Kırmızı Sistem: Temel denetimler başarılı.")


with open(SARI_SISTEM_FILE, "a", encoding="utf-8") as f:
    f.write(
        "\n\n"
        f"# --- Geliştirme Adımı {count + 1} ---\n"
        "# Mavi tarafından üretildi, Kırmızı tarafından onaylandı.\n"
        + generated_code
        + "\n"
    )


with open(COUNTER_FILE, "w", encoding="utf-8") as f:
    f.write(str(count + 1))


print(
    f"Sarı Sistem güncellendi. "
    f"Nesil: {count + 1}/{MAX_GENERATIONS}"
)
