import os
import sys
import ast
import json
import tempfile
import shutil
import subprocess
import urllib.request
import urllib.error


COUNTER_FILE = "counter.txt"
SARI_SISTEM_FILE = "sari_sistem.py"

MAX_GENERATIONS = 50
MAX_CODE_LINES = 35


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def oku_sayi(dosya):
    if not os.path.exists(dosya):
        return 0

    with open(
        dosya,
        "r",
        encoding="utf-8"
    ) as f:
        veri = f.read().strip()

    return int(veri) if veri.isdigit() else 0


def yaz_sayi(dosya, sayi):
    with open(
        dosya,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(str(sayi))


def cevap_metnini_bul(response_data):
    for item in response_data.get("output", []):

        if item.get("type") != "message":
            continue

        for content in item.get("content", []):

            if content.get("type") == "output_text":
                return content.get("text", "")

    return ""


def oyuncu_sinifini_bul(tree):
    """
    AST'nin tamamında Oyuncu sınıfını arar.
    """

    for node in ast.walk(tree):

        if (
            isinstance(node, ast.ClassDef)
            and node.name == "Oyuncu"
        ):
            return node

    return None


def mevcut_metotlari_bul(oyuncu):
    return {
        node.name
        for node in oyuncu.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        )
    }


# ============================================================
# NESİL
# ============================================================

generation = oku_sayi(
    COUNTER_FILE
)

if generation >= MAX_GENERATIONS:

    print(
        f"Deney {MAX_GENERATIONS} başarılı nesile ulaştı."
    )

    sys.exit(0)


print()
print("=" * 60)
print("OTONOM MAVİ-KIRMIZI DENEYİ")
print("=" * 60)

print(
    f"Mevcut başarılı nesil: "
    f"{generation}/{MAX_GENERATIONS}"
)

print(
    f"Sıradaki nesil: "
    f"{generation + 1}/{MAX_GENERATIONS}"
)

print("=" * 60)


# ============================================================
# OPENAI API KEY
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
# SARI DOSYASI
# ============================================================

if not os.path.exists(
    SARI_SISTEM_FILE
):

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
    f"Sarı Sistem: "
    f"{len(mevcut_kod.splitlines())} satır"
)


# ============================================================
# SARİYI PARSE ET
# ============================================================

try:

    sari_tree = ast.parse(
        mevcut_kod
    )

except SyntaxError as e:

    print(
        f"🔴 RED: Sarı Sistem syntax hatası: {e}"
    )

    sys.exit(1)


oyuncu = oyuncu_sinifini_bul(
    sari_tree
)


if oyuncu is None:

    print()
    print(
        "🔴 RED: Sarı Sistem içinde "
        "'Oyuncu' sınıfı bulunamadı."
    )

    print()
    print(
        "Sarı dosyasındaki sınıflar:"
    )

    bulunan_siniflar = [
        node.name
        for node in ast.walk(sari_tree)
        if isinstance(node, ast.ClassDef)
    ]

    if bulunan_siniflar:

        for isim in bulunan_siniflar:
            print(
                f"  - {isim}"
            )

    else:

        print(
            "  Hiç sınıf bulunamadı."
        )

    sys.exit(1)


print(
    "🔴 Kırmızı: Oyuncu sınıfı bulundu."
)


mevcut_metotlar = (
    mevcut_metotlari_bul(oyuncu)
)


print(
    "Mevcut metotlar:"
)

for isim in sorted(
    mevcut_metotlar
):
    print(
        f"  - {isim}"
    )


# ============================================================
# MAVİ PROMPT
# ============================================================

prompt = f"""
Sen Mavi Sistem'sin.

Aşağıdaki Python oyun motorunu geliştir:

--- SARI SİSTEM ---

{mevcut_kod}

--- SARI SİSTEM SONU ---

Görevin Oyuncu sınıfına TEK bir yeni özellik eklemek.

Kurallar:

1. Yalnızca bir Python metodu üret.
2. Markdown kullanma.
3. Açıklama yazma.
4. En fazla {MAX_CODE_LINES} satır üret.
5. İlk parametre self olmalı.
6. self dışında hiçbir parametre kullanma.
7. Harici import kullanma.
8. Mevcut metotların isimlerini kullanma.
9. Mevcut sistemi bozmama.
10. Metot kendi başına çalışabilmeli.
11. Metot oyuncunun mevcut verilerinden
    yararlanmalı.
12. Sadece print yapan bir metot üretme.
13. Mümkünse oyuncunun durumunu değiştirmeli
    veya anlamlı bir değer döndürmeli.

Mevcut metot isimleri:

{", ".join(sorted(mevcut_metotlar))}

Yalnızca yeni metodu döndür.
"""


# ============================================================
# OPENAI
# ============================================================

url = (
    "https://api.openai.com/v1/responses"
)


payload = {
    "model": "gpt-5.6-luna",
    "input": prompt
}


data = json.dumps(
    payload
).encode("utf-8")


request = urllib.request.Request(
    url,
    data=data,
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

    print(
        "OpenAI API Hatası!"
    )

    print(
        f"HTTP kodu: {e.code}"
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
# OPENAI CEVABI
# ============================================================

generated_code = cevap_metnini_bul(
    response_data
).strip()


if not generated_code:

    print(
        "HATA: OpenAI kod üretmedi."
    )

    sys.exit(1)


generated_code = (
    generated_code
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
# ADAY SYNTAX
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
        f"> {MAX_CODE_LINES}"
    )

    sys.exit(1)


try:

    aday_tree = ast.parse(
        generated_code
    )

except SyntaxError as e:

    print(
        f"🔴 RED: Aday syntax hatası: {e}"
    )

    sys.exit(1)


# ============================================================
# TAM OLARAK BİR FONKSİYON
# ============================================================

functions = [
    node
    for node in aday_tree.body
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
        "🔴 RED: Tam olarak bir metot gerekli."
    )

    sys.exit(1)


new_method = functions[0]


# ============================================================
# PARAMETRE KONTROLÜ
# ============================================================

if not new_method.args.args:

    print(
        "🔴 RED: self parametresi yok."
    )

    sys.exit(1)


if (
    new_method.args.args[0].arg
    != "self"
):

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
# IMPORT KONTROLÜ
# ============================================================

for node in ast.walk(
    aday_tree
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
# İSİM KONTROLÜ
# ============================================================

if new_method.name in mevcut_metotlar:

    print(
        f"🔴 RED: '{new_method.name}' "
        "zaten mevcut."
    )

    sys.exit(1)


# ============================================================
# ADAYI OYUNCU SINIFINA EKLE
# ============================================================

oyuncu.body.append(
    new_method
)

ast.fix_missing_locations(
    sari_tree
)


# ============================================================
# BİRLEŞİK KOD
# ============================================================

try:

    aday_kod = ast.unparse(
        sari_tree
    )

except Exception as e:

    print(
        f"🔴 RED: Kod yeniden oluşturulamadı: {e}"
    )

    sys.exit(1)


# ============================================================
# SON SYNTAX TESTİ
# ============================================================

try:

    compile(
        aday_kod,
        SARI_SISTEM_FILE,
        "exec"
    )

except SyntaxError as e:

    print(
        f"🔴 RED: Birleşik sistem syntax hatası: {e}"
    )

    sys.exit(1)


print(
    "🔴 Kırmızı: Entegrasyon syntax testi ✅"
)


# ============================================================
# GEÇİCİ ORTAM
# ============================================================

temp_dir = tempfile.mkdtemp(
    prefix="mavi_kirmizi_"
)


try:

    candidate_file = os.path.join(
        temp_dir,
        SARI_SISTEM_FILE
    )


    with open(
        candidate_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(aday_kod)


    # ========================================================
    # YENİ METODU ÇALIŞTIR
    # ========================================================

    test_code = f"""
from sari_sistem import Oyuncu

oyuncu = Oyuncu()

sonuc = oyuncu.{new_method.name}()

print("NEW_METHOD_OK")
print("SONUC:", sonuc)
"""


    test_file = os.path.join(
        temp_dir,
        "test_new_method.py"
    )


    with open(
        test_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(test_code)


    print(
        "🔴 Kırmızı: Yeni metot çalıştırılıyor..."
    )


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

        print(
            "🔴 RED: Yeni metot çalışmadı."
        )

        print(
            result.stderr
        )

        sys.exit(1)


    print(
        "🔴 Kırmızı: Yeni metot çalışıyor ✅"
    )


    # ========================================================
    # TEMEL SARI TESTLERİ
    # ========================================================

    testler = [
        (
            "oyuncu_olusturma",
            """
from sari_sistem import Oyuncu

oyuncu = Oyuncu()

assert oyuncu.isim == "AllStar"
assert oyuncu.seviye == 1
assert oyuncu.xp == 0
assert oyuncu.envanter == []

print("OK")
"""
        ),
        (
            "xp",
            """
from sari_sistem import Oyuncu

oyuncu = Oyuncu()

oyuncu.xp_kazan(50)

assert oyuncu.xp == 50

print("OK")
"""
        ),
        (
            "envanter",
            """
from sari_sistem import Oyuncu

oyuncu = Oyuncu()

assert isinstance(
    oyuncu.envanter,
    list
)

print("OK")
"""
        ),
        (
            "seviye",
            """
from sari_sistem import Oyuncu

oyuncu = Oyuncu()

oyuncu.xp_kazan(120)

assert oyuncu.seviye >= 2

print("OK")
"""
        )
    ]


    print(
        "🔴 Kırmızı: Mevcut özellikler test ediliyor..."
    )


    for test_name, test_source in testler:

        path = os.path.join(
            temp_dir,
            f"test_{test_name}.py"
        )


        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(test_source)


        result = subprocess.run(
            [
                sys.executable,
                path
            ],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=15
        )


        if result.returncode != 0:

            print(
                f"🔴 RED: {test_name} testi başarısız."
            )

            print(
                result.stderr
            )

            sys.exit(1)


        print(
            f"   ✅ {test_name}"
        )


    print(
        "🔴 Kırmızı: Tüm temel testler başarılı."
    )


finally:

    shutil.rmtree(
        temp_dir,
        ignore_errors=True
    )


# ============================================================
# SARI'YA AKTAR
# ============================================================

with open(
    SARI_SISTEM_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(aday_kod)
    f.write("\n")


new_generation = generation + 1

yaz_sayi(
    COUNTER_FILE,
    new_generation
)


# ============================================================
# BAŞARI
# ============================================================

print()
print("=" * 60)
print("🟢 DENEY BAŞARILI")
print("=" * 60)

print(
    f"Eski nesil: {generation}"
)

print(
    f"Yeni nesil: "
    f"{new_generation}/{MAX_GENERATIONS}"
)

print(
    f"Eklenen metot: "
    f"{new_method.name}"
)

print(
    "Kırmızı bütün testleri geçti."
)

print(
    "Sarı Sistem güncellendi."
)

print("=" * 60)
