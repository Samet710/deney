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


# ============================================================
# 1. NESİL SAYACINI OKU
# ============================================================

count = 0

if os.path.exists(COUNTER_FILE):
    with open(COUNTER_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

        if content.isdigit():
            count = int(content)


if count >= MAX_GENERATIONS:
    print(
        f"Deney {MAX_GENERATIONS} nesile ulaştı."
    )
    sys.exit(0)


generation = count + 1

print()
print("=" * 50)
print(
    f"MAVİ-KIRMIZI DENEYİ "
    f"{generation}/{MAX_GENERATIONS}"
)
print("=" * 50)


# ============================================================
# 2. OPENAI API ANAHTARINI AL
# ============================================================

api_key = os.getenv("OPENAI_API_KEY", "").strip()

if not api_key:
    print("HATA: OPENAI_API_KEY bulunamadı.")
    sys.exit(1)


# ============================================================
# 3. SARI SİSTEMİN MEVCUT KODUNU OKU
# ============================================================

if not os.path.exists(SARI_SISTEM_FILE):
    print(
        f"HATA: {SARI_SISTEM_FILE} bulunamadı."
    )
    sys.exit(1)


with open(
    SARI_SISTEM_FILE,
    "r",
    encoding="utf-8"
) as f:
    mevcut_kod = f.read()


print(
    f"Sarı Sistem okundu. "
    f"{len(mevcut_kod.splitlines())} satır."
)


# ============================================================
# 4. MAVİ SİSTEM - GELİŞTİRME İSTEĞİ
# ============================================================

prompt = f"""
Sen Mavi Sistem'sin.

Görevin, mevcut Sarı Sistemi küçük ama gerçek
bir geliştirmeyle iyileştirmektir.

MEVCUT SARI SİSTEM:

-------------------------
{mevcut_kod}
-------------------------

KURALLAR:

1. Yalnızca Python kodu üret.
2. Markdown kullanma.
3. Açıklama yazma.
4. En fazla {MAX_CODE_LINES} satır kod üret.
5. Tam olarak BİR yeni metot üret.
6. Metot Oyuncu sınıfının içine eklenebilir olmalı.
7. İlk parametresi kesinlikle self olmalı.
8. Yeni metot mevcut Oyuncu özellikleriyle uyumlu olmalı.
9. Mevcut özellikleri bozmamalı.
10. Metot anlamlı ve kullanılabilir bir özellik eklemeli.
11. Harici kütüphane kullanma.
12. Yalnızca metodun kendisini döndür.

ÖRNEK:

def esya_ekle(self, esya):
    if esya is None:
        raise ValueError("Eşya boş olamaz.")

    self.envanter.append(esya)

Sadece Python kodunu döndür.
"""


# ============================================================
# 5. OPENAI RESPONSES API
# ============================================================

url = "https://api.openai.com/v1/responses"

payload = {
    "model": "gpt-5.6-luna",
    "input": prompt
}

request_data = json.dumps(payload).encode("utf-8")

request = urllib.request.Request(
    url,
    data=request_data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    },
    method="POST"
)


# ============================================================
# 6. API ÇAĞRISINI GERÇEKLEŞTİR
# ============================================================

try:

    with urllib.request.urlopen(
        request,
        timeout=120
    ) as response:

        response_data = json.loads(
            response.read().decode("utf-8")
        )

except urllib.error.HTTPError as e:

    error_body = e.read().decode(
        "utf-8",
        errors="replace"
    )

    print()
    print("OPENAI API HATASI")
    print("-" * 40)
    print(f"HTTP kodu: {e.code}")
    print(f"Sunucu cevabı: {error_body}")
    print("-" * 40)

    sys.exit(1)

except urllib.error.URLError as e:

    print()
    print("AĞ HATASI")
    print(f"OpenAI'ye bağlanılamadı: {e}")
    sys.exit(1)

except Exception as e:

    print()
    print("BEKLENMEYEN API HATASI")
    print(str(e))

    sys.exit(1)


# ============================================================
# 7. OPENAI CEVABINI KONTROL ET
# ============================================================

if not isinstance(response_data, dict):

    print(
        "HATA: OpenAI cevabı sözlük formatında değil."
    )

    sys.exit(1)


if response_data.get("status") != "completed":

    print(
        "HATA: OpenAI cevabı tamamlanmamış."
    )

    print(
        f"Durum: {response_data.get('status')}"
    )

    sys.exit(1)


# ============================================================
# 8. output_text BUL
# ============================================================

generated_code = None

for output_item in response_data.get(
    "output",
    []
):

    if output_item.get("type") != "message":
        continue

    for content_item in output_item.get(
        "content",
        []
    ):

        if content_item.get(
            "type"
        ) == "output_text":

            generated_code = content_item.get(
                "text"
            )

            break

    if generated_code:
        break


if not generated_code:

    print()
    print(
        "HATA: OpenAI cevabında "
        "üretim kodu bulunamadı."
    )

    print()
    print("OpenAI cevabı:")

    print(
        json.dumps(
            response_data,
            indent=2,
            ensure_ascii=False
        )
    )

    sys.exit(1)


# ============================================================
# 9. ÜRETİLEN KODU TEMİZLE
# ============================================================

generated_code = generated_code.strip()

generated_code = (
    generated_code
    .replace("```python", "")
    .replace("```", "")
    .strip()
)


print()
print("MAVİ SİSTEM KOD ÜRETTİ")
print("-" * 40)
print(generated_code)
print("-" * 40)


# ============================================================
# 10. KIRMIZI - SATIR SAYISI KONTROLÜ
# ============================================================

line_count = len(
    generated_code.splitlines()
)

print(
    f"Kırmızı Sistem: "
    f"{line_count} satır."
)


if line_count == 0:

    print(
        "Kırmızı Sistem REDDETTİ: "
        "Kod boş."
    )

    sys.exit(1)


if line_count > MAX_CODE_LINES:

    print(
        "Kırmızı Sistem REDDETTİ: "
        f"{line_count} satır > "
        f"{MAX_CODE_LINES} satır."
    )

    sys.exit(1)


# ============================================================
# 11. KIRMIZI - PYTHON SYNTAX KONTROLÜ
# ============================================================

try:

    method_tree = ast.parse(
        generated_code
    )

except SyntaxError as e:

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        f"Syntax hatası: {e}"
    )

    sys.exit(1)


# ============================================================
# 12. KIRMIZI - TAM OLARAK BİR FONKSİYON
# ============================================================

functions = [
    node
    for node in method_tree.body
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef
        )
    )
]


if len(functions) != 1:

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        "Tam olarak bir fonksiyon "
        "bekleniyordu."
    )

    sys.exit(1)


new_method = functions[0]


# ============================================================
# 13. KIRMIZI - SELF KONTROLÜ
# ============================================================

if not new_method.args.args:

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        "Metodun parametreleri yok."
    )

    sys.exit(1)


first_argument = (
    new_method.args.args[0].arg
)


if first_argument != "self":

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        "İlk parametre self olmalı."
    )

    sys.exit(1)


# ============================================================
# 14. KIRMIZI - SADECE İZİN VERİLEN ŞEYLER
# ============================================================

for node in ast.walk(new_method):

    if isinstance(
        node,
        (
            ast.Import,
            ast.ImportFrom
        )
    ):

        print(
            "Kırmızı Sistem REDDETTİ:"
        )

        print(
            "Yeni metot harici "
            "kütüphane import edemez."
        )

        sys.exit(1)


print(
    "Kırmızı Sistem: "
    "Temel kontroller başarılı."
)


# ============================================================
# 15. SARI SİSTEMİN AST'SİNİ OKU
# ============================================================

try:

    with open(
        SARI_SISTEM_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        source = f.read()

    module = ast.parse(source)

except Exception as e:

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        f"Sarı Sistem okunamadı: {e}"
    )

    sys.exit(1)


# ============================================================
# 16. OYUNCU SINIFINI BUL
# ============================================================

player_class = None

for node in module.body:

    if (
        isinstance(node, ast.ClassDef)
        and node.name == "Oyuncu"
    ):

        player_class = node
        break


if player_class is None:

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        "Oyuncu sınıfı bulunamadı."
    )

    sys.exit(1)


# ============================================================
# 17. AYNI METOT VAR MI?
# ============================================================

existing_method_names = []

for node in player_class.body:

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef
        )
    ):

        existing_method_names.append(
            node.name
        )


if new_method.name in existing_method_names:

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        f"'{new_method.name}' adlı "
        "metot zaten mevcut."
    )

    sys.exit(1)


# ============================================================
# 18. YENİ METODU OYUNCU SINIFINA EKLE
# ============================================================

player_class.body.append(
    new_method
)


# ============================================================
# 19. DÜZENLENMİŞ KODU AST'DEN GERİ ÜRET
# ============================================================

try:

    import astunparse

except ImportError:

    print(
        "HATA: astunparse kurulu değil."
    )

    sys.exit(1)


new_source = astunparse.unparse(
    module
)


# ============================================================
# 20. KIRMIZI - SON HALİN SYNTAX TESTİ
# ============================================================

try:

    ast.parse(new_source)

except SyntaxError as e:

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        "Entegre edilmiş Sarı Sistem "
        "syntax testini geçemedi."
    )

    print(e)

    sys.exit(1)


print(
    "Kırmızı Sistem: "
    "Entegrasyon syntax testi başarılı."
)


# ============================================================
# 21. SARI SİSTEMİ KAYDET
# ============================================================

with open(
    SARI_SISTEM_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(new_source)


# ============================================================
# 22. NESİL SAYACINI ARTIR
# ============================================================

with open(
    COUNTER_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        str(generation)
    )


# ============================================================
# 23. SONUÇ
# ============================================================

print()
print("=" * 50)
print("DENEY BAŞARILI")
print("=" * 50)

print(
    f"Yeni nesil: "
    f"{generation}/{MAX_GENERATIONS}"
)

print(
    f"Eklenen metot: "
    f"{new_method.name}"
)

print(
    "Sarı Sistem güncellendi."
)

print("=" * 50)
