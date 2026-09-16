import os
import sys
import ast
import json
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.error


COUNTER_FILE = "counter.txt"
SARI_SISTEM_FILE = "sari_sistem.py"
TEST_FILE = "test_sari.py"

MAX_GENERATIONS = 50
MAX_CODE_LINES = 35


# ============================================================
# 1. NESİL
# ============================================================

count = 0

if os.path.exists(COUNTER_FILE):
    with open(
        COUNTER_FILE,
        "r",
        encoding="utf-8"
    ) as f:
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
print("=" * 55)
print(
    f"MAVİ-KIRMIZI DENEYİ "
    f"{generation}/{MAX_GENERATIONS}"
)
print("=" * 55)


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
# 3. SARI SİSTEMİ OKU
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
    f"Sarı Sistem okundu: "
    f"{len(mevcut_kod.splitlines())} satır."
)


# ============================================================
# 4. MAVİ SİSTEM
# ============================================================

prompt = f"""
Sen Mavi Sistem'sin.

Mevcut Sarı Sistem aşağıdadır:

-------------------------
{mevcut_kod}
-------------------------

Görevin sisteme TEK bir yeni özellik eklemektir.

ÇOK ÖNEMLİ KURALLAR:

1. Yalnızca Python kodu döndür.
2. Markdown kullanma.
3. Açıklama yazma.
4. En fazla {MAX_CODE_LINES} satır üret.
5. Tam olarak BİR yeni metot üret.
6. İlk parametre kesinlikle self olmalı.
7. Yeni metodun self dışında PARAMETRESİ OLMAMALI.
8. Metot Oyuncu sınıfının içine eklenebilir olmalı.
9. Harici import kullanma.
10. Mevcut özellikleri bozmamalı.
11. Metot çağrıldığında hata vermemeli.
12. Metot gerçek ve anlamlı bir oyun özelliği sağlamalı.
13. self.seviye, self.xp, self.envanter veya self.isim
    gibi mevcut oyuncu durumlarından yararlanabilirsin.
14. Metot yalnızca gösterişli bir print fonksiyonu olmamalı.
15. Mümkünse oyuncunun durumunu değiştirmeli veya
    anlamlı bir değer döndürmeli.
16. Daha önce var olan bir metodun adını kullanma.

Sadece metodun kendisini döndür.

Örnek:

def can_durumu(self):
    return max(0, self.xp // 10)

Yalnızca Python kodunu döndür.
"""


# ============================================================
# 5. OPENAI
# ============================================================

url = "https://api.openai.com/v1/responses"

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
        "Authorization": f"Bearer {api_key}"
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
    print(f"HTTP kodu: {e.code}")

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
# 6. OPENAI METNİNİ BUL
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

    print(
        "HATA: OpenAI kod üretmedi."
    )

    sys.exit(1)


generated_code = generated_code.strip()

generated_code = (
    generated_code
    .replace("```python", "")
    .replace("```", "")
    .strip()
)


print()
print("MAVİ'NİN ÖNERİSİ")
print("-" * 55)
print(generated_code)
print("-" * 55)


# ============================================================
# 7. KIRMIZI - KOD SINIRLARI
# ============================================================

line_count = len(
    generated_code.splitlines()
)

if line_count == 0:

    print(
        "🔴 RED: Kod boş."
    )

    sys.exit(1)


if line_count > MAX_CODE_LINES:

    print(
        f"🔴 RED: {line_count} satır "
        f"> {MAX_CODE_LINES}."
    )

    sys.exit(1)


# ============================================================
# 8. KIRMIZI - AST
# ============================================================

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
        "🔴 RED: Tam olarak bir "
        "fonksiyon gerekli."
    )

    sys.exit(1)


new_method = functions[0]


# ============================================================
# 9. SELF KONTROLÜ
# ============================================================

if not new_method.args.args:

    print(
        "🔴 RED: self parametresi yok."
    )

    sys.exit(1)


if new_method.args.args[0].arg != "self":

    print(
        "🔴 RED: İlk parametre self olmalı."
    )

    sys.exit(1)


if len(new_method.args.args) != 1:

    print(
        "🔴 RED: self dışında "
        "parametre kullanılamaz."
    )

    sys.exit(1)


# ============================================================
# 10. IMPORT KONTROLÜ
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
            "🔴 RED: Yeni metot import "
            "kullanamaz."
        )

        sys.exit(1)


# ============================================================
# 11. SARI AST'SİNİ OKU
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
        f"🔴 RED: Sarı Sistem okunamadı: {e}"
    )

    sys.exit(1)


# ============================================================
# 12. OYUNCU SINIFI
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
        "🔴 RED: Oyuncu sınıfı bulunamadı."
    )

    sys.exit(1)


# ============================================================
# 13. METOT ADI
# ============================================================

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
# 14. ADAY SİSTEMİ OLUŞTUR
# ============================================================

player_class.body.append(
    new_method
)

candidate_source = ast.unparse(
    module
)


# ============================================================
# 15. GEÇİCİ DİZİN
# ============================================================

temp_dir = tempfile.mkdtemp(
    prefix="mavi_kirmizi_"
)

candidate_file = os.path.join(
    temp_dir,
    SARI_SISTEM_FILE
)


try:

    with open(
        candidate_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(candidate_source)


    # ========================================================
    # 16. SYNTAX TESTİ
    # ========================================================

    print()
    print(
        "🔴 Syntax testi çalıştırılıyor..."
    )

    syntax_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            candidate_file
        ],
        capture_output=True,
        text=True
    )


    if syntax_result.returncode != 0:

        print(
            "🔴 RED: Aday sistem "
            "syntax testini geçemedi."
        )

        print(syntax_result.stderr)

        sys.exit(1)


    print(
        "✅ Syntax testi başarılı."
    )


    # ========================================================
    # 17. TEMEL ÇALIŞMA TESTİ
    # ========================================================

    print(
        "🔴 Temel çalışma testi..."
    )

    smoke_code = """
import sys

sys.path.insert(0, sys.argv[1])

from sari_sistem import Oyuncu

oyuncu = Oyuncu()

assert oyuncu.isim
assert oyuncu.seviye >= 1
assert oyuncu.xp >= 0
assert isinstance(oyuncu.envanter, list)

oyuncu.xp_kazan(10)

assert oyuncu.xp >= 10

print("SMOKE_TEST_OK")
"""


    smoke_file = os.path.join(
        temp_dir,
        "smoke_test.py"
    )

    with open(
        smoke_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(smoke_code)


    smoke_result = subprocess.run(
        [
            sys.executable,
            smoke_file,
            temp_dir
        ],
        capture_output=True,
        text=True,
        cwd=temp_dir
    )


    if smoke_result.returncode != 0:

        print(
            "🔴 RED: Temel çalışma "
            "testi başarısız."
        )

        print(
            smoke_result.stderr
        )

        sys.exit(1)


    print(
        "✅ Temel çalışma testi başarılı."
    )


    # ========================================================
    # 18. TEST DOSYASI VARSA ÇALIŞTIR
    # ========================================================

    if os.path.exists(TEST_FILE):

        print(
            "🔴 Mevcut regresyon testleri "
            "çalıştırılıyor..."
        )

        candidate_test_file = os.path.join(
            temp_dir,
            TEST_FILE
        )

        shutil.copy2(
            TEST_FILE,
            candidate_test_file
        )


        test_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                candidate_test_file
            ],
            capture_output=True,
            text=True,
            cwd=temp_dir
        )


        if test_result.returncode != 0:

            print(
                "🔴 RED: Regresyon "
                "testleri başarısız."
            )

            print(
                test_result.stdout
            )

            print(
                test_result.stderr
            )

            sys.exit(1)


        print(
            "✅ Regresyon testleri başarılı."
        )


    # ========================================================
    # 19. YENİ METOT TESTİ
    # ========================================================

    print(
        f"🔴 Yeni metot test ediliyor: "
        f"{new_method.name}"
    )


    new_method_test_code = f"""
import sys

sys.path.insert(0, sys.argv[1])

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
"""


    new_method_test_file = os.path.join(
        temp_dir,
        "new_method_test.py"
    )

    with open(
        new_method_test_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            new_method_test_code
        )


    new_test_result = subprocess.run(
        [
            sys.executable,
            new_method_test_file,
            temp_dir
        ],
        capture_output=True,
        text=True,
        cwd=temp_dir
    )


    if new_test_result.returncode != 0:

        print(
            "🔴 RED: Yeni metot çalışmadı."
        )

        print(
            new_test_result.stderr
        )

        sys.exit(1)


    print(
        "✅ Yeni metot çalışıyor."
    )


    # ========================================================
    # 20. BAŞARILIYSA SARI'YA AKTAR
    # ========================================================

    with open(
        SARI_SISTEM_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(candidate_source)


    with open(
        COUNTER_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            str(generation)
        )


    # ========================================================
    # 21. BAŞARILI
    # ========================================================

    print()
    print("=" * 55)
    print("🟢 DENEY BAŞARILI")
    print("=" * 55)

    print(
        f"Nesil: {generation}/{MAX_GENERATIONS}"
    )

    print(
        f"Yeni metot: {new_method.name}"
    )

    print(
        "Kırmızı bütün testleri geçti."
    )

    print(
        "Değişiklik Sarı Sisteme aktarıldı."
    )

    print("=" * 55)


finally:

    shutil.rmtree(
        temp_dir,
        ignore_errors=True
)
