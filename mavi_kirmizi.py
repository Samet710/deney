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
# NESİL SAYACI
# ============================================================

count = 0

if os.path.exists(COUNTER_FILE):
    with open(COUNTER_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

        if content.isdigit():
            count = int(content)


if count >= MAX_GENERATIONS:
    print(
        f"Deney {MAX_GENERATIONS} nesil sınırına ulaştı."
    )
    sys.exit(0)


generation = count + 1

print(
    f"--- Deney Adımı "
    f"{generation}/{MAX_GENERATIONS} Başlatılıyor ---"
)


# ============================================================
# API ANAHTARI
# ============================================================

api_key = os.getenv("OPENAI_API_KEY", "").strip()

if not api_key:
    print("Hata: OPENAI_API_KEY bulunamadı.")
    sys.exit(1)


# ============================================================
# SARI SİSTEMİ OKU
# ============================================================

with open(
    SARI_SISTEM_FILE,
    "r",
    encoding="utf-8"
) as f:
    mevcut_kod = f.read()


# ============================================================
# MAVİ SİSTEM - GELİŞTİRME İSTEĞİ
# ============================================================

prompt = f"""
Sen Mavi Sistem'sin.

Aşağıdaki Python oyun motorunu incele.

--- SARI SİSTEM BAŞLANGICI ---

{mevcut_kod}

--- SARI SİSTEM SONU ---

Görevin:
Sisteme küçük fakat gerçek bir geliştirme eklemek.

Kurallar:

1. Yalnızca Python kodu üret.
2. Markdown kullanma.
3. Açıklama yazma.
4. En fazla {MAX_CODE_LINES} satır kod üret.
5. Tam olarak BİR yeni metot üret.
6. Metot Oyuncu sınıfının içine eklenebilir olmalı.
7. İlk parametre kesinlikle self olmalı.
8. Mevcut özellikleri bozmamalı.
9. Metot kendi başına anlamlı bir özellik sağlamalı.
10. Yalnızca metodun kendisini döndür.

Örnek:

def esya_ekle(self, esya):
    if esya is None:
        raise ValueError("Eşya boş olamaz.")

    self.envanter.append(esya)

Yalnızca kod döndür.
"""


# ============================================================
# OPENAI RESPONSES API
# ============================================================

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

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        response_data = json.loads(
            response.read().decode("utf-8")
        )

except urllib.error.HTTPError as e:

    error_body = e.read().decode(
        "utf-8",
        errors="replace"
    )

    print("OpenAI API Hatası!")
    print(f"HTTP Kod: {e.code}")
    print(f"Sunucu cevabı: {error_body}")

    sys.exit(1)

except Exception as e:

    print(
        f"Mavi Sistem bağlantı hatası: {e}"
    )

    sys.exit(1)


# ============================================================
# OPENAI CEVABINDAN METNİ AL
# ============================================================

generated_code = response_data.get(
    "output_text"
)


if not generated_code:

    print(
        "OpenAI cevabında output_text bulunamadı."
    )

    print(
        json.dumps(
            response_data,
            indent=2,
            ensure_ascii=False
        )
    )

    sys.exit(1)


generated_code = generated_code.strip()


# Markdown temizliği
generated_code = (
    generated_code
    .replace("```python", "")
    .replace("```", "")
    .strip()
)


print("Mavi Sistem: Kod üretildi.")
print(generated_code)


# ============================================================
# KIRMIZI SİSTEM - SATIR KONTROLÜ
# ============================================================

line_count = len(
    generated_code.splitlines()
)

print(
    f"Kırmızı Sistem: "
    f"{line_count} satır."
)


if line_count > MAX_CODE_LINES:

    print(
        "Kırmızı Sistem REDDETTİ: "
        f"{line_count} > {MAX_CODE_LINES}"
    )

    sys.exit(1)


# ============================================================
# KIRMIZI SİSTEM - SYNTAX KONTROLÜ
# ============================================================

try:

    tree = ast.parse(
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
# KIRMIZI SİSTEM - SADECE 1 FONKSİYON
# ============================================================

functions = [
    node
    for node in tree.body
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


new_function = functions[0]


# ============================================================
# KIRMIZI SİSTEM - SELF KONTROLÜ
# ============================================================

if not new_function.args.args:

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        "Fonksiyon self parametresi içermiyor."
    )

    sys.exit(1)


first_argument = (
    new_function.args.args[0].arg
)


if first_argument != "self":

    print(
        "Kırmızı Sistem REDDETTİ:"
    )

    print(
        "İlk parametre self olmalı."
    )

    sys.exit(1)


print(
    "Kırmızı Sistem: "
    "Temel kontroller başarılı."
)


# ============================================================
# MAVİ'NİN ÜRETTİĞİ METODU AL
# ============================================================

method_source = generated_code.rstrip()


# ============================================================
# SARI SİSTEMİ AST İLE GÜNCELLE
# ============================================================

with open(
    SARI_SISTEM_FILE,
    "r",
    encoding="utf-8"
) as f:

    source = f.read()


module = ast.parse(source)


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


# Metot gövdesini parse et
method_tree = ast.parse(
    method_source
)

new_method_node = method_tree.body[0]


# Aynı isimli metot varsa değiştir.
# Yoksa yeni metot ekle.

new_methods = []

replaced = False

for node in player_class.body:

    if (
        isinstance(node, ast.FunctionDef)
        and node.name == new_method_node.name
    ):

        new_methods.append(
            new_method_node
        )

        replaced = True

    else:

        new_methods.append(node)


if not replaced:

    new_methods.append(
        new_method_node
    )


player_class.body = new_methods


# Python kodunu tekrar oluştur
try:

    import astunparse

except ImportError:

    print(
        "astunparse paketi gerekli."
    )

    sys.exit(1)


new_source = astunparse.unparse(
    module
)


# ============================================================
# SARI SİSTEMİ KAYDET
# ============================================================

with open(
    SARI_SISTEM_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(new_source)


# ============================================================
# NESİLİ KAYDET
# ============================================================

with open(
    COUNTER_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        str(generation)
    )


print(
    "Sarı Sistem başarıyla güncellendi."
)

print(
    f"Mevcut nesil: "
    f"{generation}/{MAX_GENERATIONS}"
)
