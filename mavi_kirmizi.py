import os
import sys
import ast
import json
import tempfile
import urllib.request
import urllib.error

from kirmizi_degerlendir import degerlendir


COUNTER_FILE = "counter.txt"
ATTEMPTS_FILE = "attempts.txt"
SARI_SISTEM_FILE = "sari_sistem.py"
TEST_FILE = "test_sari.py"

MAX_GENERATIONS = 50
MAX_CODE_LINES = 35


# ============================================================
# 1. NESİL SAYACI
# ============================================================

def sayi_oku(dosya):
    if not os.path.exists(dosya):
        return 0

    with open(
        dosya,
        "r",
        encoding="utf-8"
    ) as f:
        content = f.read().strip()

    return int(content) if content.isdigit() else 0


def sayi_yaz(dosya, sayi):
    with open(
        dosya,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(str(sayi))


generation = sayi_oku(
    COUNTER_FILE
)

attempt = sayi_oku(
    ATTEMPTS_FILE
) + 1


if generation >= MAX_GENERATIONS:
    print(
        f"Deney {MAX_GENERATIONS} "
        "başarılı nesle ulaştı."
    )
    sys.exit(0)


print()
print("=" * 60)
print("OTONOM MAVİ-KIRMIZI DENEYİ")
print("=" * 60)

print(
    f"Başarılı nesil: "
    f"{generation}/{MAX_GENERATIONS}"
)

print(
    f"Deneme numarası: {attempt}"
)

print("=" * 60)


# ============================================================
# 2. API ANAHTARI
# ============================================================

api_key = os.getenv(
    "OPENAI_API_KEY",
    ""
).strip()


if not api_key:
    print(
        "HATA: OPENAI_API_KEY bulunamadı."
    )
    sys.exit(1)


# ============================================================
# 3. DOSYALARI KONTROL ET
# ============================================================

if not os.path.exists(
    SARI_SISTEM_FILE
):
    print(
        f"HATA: {SARI_SISTEM_FILE} yok."
    )
    sys.exit(1)


if not os.path.exists(
    TEST_FILE
):
    print(
        f"HATA: {TEST_FILE} yok."
    )
    sys.exit(1)


# ============================================================
# 4. MEVCUT SARI SİSTEM
# ============================================================

with open(
    SARI_SISTEM_FILE,
    "r",
    encoding="utf-8"
) as f:
    mevcut_kod = f.read()


print(
    f"Sarı Sistem: "
    f"{len(mevcut_kod.splitlines())} satır"
)


# ============================================================
# 5. MAVİ PROMPT
# ============================================================

prompt = f"""
Sen Mavi Sistem'sin.

Aşağıdaki Python oyun motorunu geliştir.

--- MEVCUT SARI SİSTEM ---

{mevcut_kod}

--- SON ---

Görevin mevcut sisteme tek bir anlamlı
oyuncu özelliği eklemek.

Kurallar:

1. Yalnızca Python kodu üret.
2. Markdown kullanma.
3. Açıklama yazma.
4. En fazla {MAX_CODE_LINES} satır.
5. Tam olarak BİR yeni metot üret.
6. İlk parametre self olmalı.
7. self dışında parametre kullanma.
8. Harici import kullanma.
9. Daha önce mevcut olan bir metot adını kullanma.
10. Metot Oyuncu sınıfına eklenebilir olmalı.
11. Mevcut özellikleri bozmamalı.
12. Metot çağrıldığında hata vermemeli.
13. Mümkünse oyuncunun durumunu değiştirmeli
    veya anlamlı bir değer döndürmeli.
14. Sadece print yapan bir metot üretme.

Yalnızca yeni metodu döndür.
"""


# ============================================================
# 6. OPENAI
# ============================================================

url = (
    "https://api.openai.com/v1/responses"
)

payload = {
    "model": "gpt-5.6-luna",
    "input": prompt
}

request_data = json.dumps(
    payload
).encode("utf-8")


request = urllib.request.Request(
    url,
    data=request_data,
    headers={
        "Content-Type": "application/json",
        "Authorization": (
            f"Bearer {api_key}"
        )
    },
    method="POST"
)


try:

    with urllib.request.urlopen(
        request,
        timeout=120
    ) as response:

        response_data = json.loads(
            response.read().decode("utf-8")
        )

except urllib.error.HTTPError as e:

    print("OPENAI API HATASI")
    print(
        f"HTTP: {e.code}"
    )

    print(
        e.read().decode(
            "utf-8",
            errors="replace"
        )
    )

    sys.exit(1)

except Exception as e:

    print(
        f"OpenAI bağlantı hatası: {e}"
    )

    sys.exit(1)


# ============================================================
# 7. OPENAI METNİNİ BUL
# ============================================================

generated_code = None

for output_item in response_data.get(
    "output",
    []
):

    if output_item.get(
        "type"
    ) != "message":
        continue

    for content_item in output_item.get(
        "content",
        []
    ):

        if content_item.get(
            "type"
        ) == "output_text":

            generated_code = (
                content_item.get("text")
            )

            break

    if generated_code:
        break


if not generated_code:
    print(
        "HATA: OpenAI kod üretmedi."
    )
    sys.exit(1)


generated_code = (
    generated_code
    .strip()
    .replace("```python", "")
    .replace("```", "")
    .strip()
)


print()
print("🔵 MAVİ'NİN ADAYI")
print("-" * 60)
print(generated_code)
print("-" * 60)


# ============================================================
# 8. ADAYIN TEMEL KONTROLLERİ
# ============================================================

line_count = len(
    generated_code.splitlines()
)


if line_count == 0:
    print("🔴 RED: Kod boş.")
    sys.exit(1)


if line_count > MAX_CODE_LINES:
    print(
        f"🔴 RED: {line_count} > "
        f"{MAX_CODE_LINES} satır."
    )
    sys.exit(1)


try:

    method_tree = ast.parse(
        generated_code
    )

except SyntaxError as e:

    print(
        f"🔴 RED: Syntax hatası: {e}"
    )

    sys.exit(1)


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
        "🔴 RED: Tam olarak "
        "bir metot gerekli."
    )

    sys.exit(1)


new_method = functions[0]


if not new_method.args.args:

    print(
        "🔴 RED: self yok."
    )

    sys.exit(1)


if new_method.args.args[0].arg != "self":

    print(
        "🔴 RED: İlk parametre "
        "self olmalı."
    )

    sys.exit(1)


if len(new_method.args.args) != 1:

    print(
        "🔴 RED: self dışında "
        "parametre kullanılamaz."
    )

    sys.exit(1)


for node in ast.walk(
    new_method
):

    if isinstance(
        node,
        (
            ast.Import,
            ast.ImportFrom
        )
    ):

        print(
            "🔴 RED: Import kullanılamaz."
        )

        sys.exit(1)


# ============================================================
# 9. SARI SINIFINI BUL
# ============================================================

module = ast.parse(
    mevcut_kod
)

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
        "🔴 RED: Oyuncu sınıfı bulunamadı."
    )

    sys.exit(1)


existing_methods = {
    node.name
    for node in player_class.body
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef
        )
    )
}


if new_method.name in existing_methods:

    print(
        f"🔴 RED: {new_method.name} "
        "zaten mevcut."
    )

    sys.exit(1)


# ============================================================
# 10. ADAY SÜRÜMÜ OLUŞTUR
# ============================================================

player_class.body.append(
    new_method
)

candidate_source = ast.unparse(
    module
)


# ============================================================
# 11. ADAY SYNTAX
# ============================================================

try:

    ast.parse(
        candidate_source
    )

except SyntaxError as e:

    print(
        f"🔴 RED: Entegrasyon syntax "
        f"hatası: {e}"
    )

    sys.exit(1)


print(
    "🔴 Entegrasyon syntax testi: ✅"
)


# ============================================================
# 12. YENİ METODUN ÇALIŞMA TESTİ
# ============================================================

temp_dir = tempfile.mkdtemp(
    prefix="aday_"
)

try:

    candidate_file = os.path.join(
        temp_dir,
        SARI_SISTEM_FILE
    )

    test_file = os.path.join(
        temp_dir,
        "yeni_metot_test.py"
    )


    with open(
        candidate_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(candidate_source)


    test_code = f'''
from sari_sistem import Oyuncu

oyuncu = Oyuncu()

metot = getattr(
    oyuncu,
    "{new_method.name}"
)

assert callable(metot)

sonuc = metot()

print("NEW_METHOD_OK")
print(type(sonuc).__name__)
'''


    with open(
        test_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(test_code)


    result = subprocess.run(
        [
            sys.executable,
            test_file
        ],
        cwd=temp_dir,
        capture_output=True,
        text=True,
        timeout=15
    )


    if result.returncode != 0:

        print()
        print(
            "🔴 RED: Yeni metot "
            "çalışma testini geçemedi."
        )

        print(result.stderr)

        sys.exit(1)


    print(
        "🔴 Yeni metot çalışma testi: ✅"
    )


finally:

    import shutil

    shutil.rmtree(
        temp_dir,
        ignore_errors=True
    )


# ============================================================
# 13. BASELINE ÖLÇ
# ============================================================

print()
print("🔴 Mevcut Sarı Sistem ölçülüyor...")

baseline = degerlendir(
    mevcut_kod,
    TEST_FILE
)


print(
    f"   Testler: "
    f"{'✅' if baseline['tests_passed'] else '❌'}"
)

print(
    f"   Kalite: "
    f"{baseline['quality']}"
)

print(
    f"   Skor: "
    f"{baseline['score']}"
)


if not baseline["tests_passed"]:

    print(
        "🔴 Mevcut Sarı Sistem "
        "zaten testleri geçemiyor."
    )

    sys.exit(1)


# ============================================================
# 14. ADAYI ÖLÇ
# ============================================================

print()
print("🔴 Aday Sarı Sistem ölçülüyor...")

candidate = degerlendir(
    candidate_source,
    TEST_FILE
)


print(
    f"   Testler: "
    f"{'✅' if candidate['tests_passed'] else '❌'}"
)

print(
    f"   Kalite: "
    f"{candidate['quality']}"
)

print(
    f"   Skor: "
    f"{candidate['score']}"
)


# ============================================================
# 15. KARAR
# ============================================================

if not candidate["tests_passed"]:

    print()
    print(
        "🔴 RED: Aday regresyon "
        "testlerini geçemedi."
    )

    sys.exit(1)


if candidate["score"] <= baseline["score"]:

    print()
    print(
        "🔴 RED: Aday sistem mevcut "
        "sistemden daha iyi değil."
    )

    print(
        f"Mevcut: {baseline['score']}"
    )

    print(
        f"Aday:   {candidate['score']}"
    )

    sys.exit(1)


# ============================================================
# 16. SARI'YA KABUL
# ============================================================

with open(
    SARI_SISTEM_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        candidate_source
    )


generation += 1

sayi_yaz(
    COUNTER_FILE,
    generation
)

sayi_yaz(
    ATTEMPTS_FILE,
    attempt
)


# ============================================================
# 17. BAŞARILI
# ============================================================

print()
print("=" * 60)
print("🟢 DENEY BAŞARILI")
print("=" * 60)

print(
    f"Yeni nesil: "
    f"{generation}/{MAX_GENERATIONS}"
)

print(
    f"Eklenen metot: "
    f"{new_method.name}"
)

print(
    f"Eski skor: "
    f"{baseline['score']}"
)

print(
    f"Yeni skor: "
    f"{candidate['score']}"
)

print(
    f"Fark: "
    f"+{round(candidate['score'] - baseline['score'], 2)}"
)

print(
    "Sarı Sistem güncellendi."
)

print("=" * 60)
