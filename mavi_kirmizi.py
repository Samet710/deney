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


def oku_sayi():
    if not os.path.exists(COUNTER_FILE):
        return 0

    with open(COUNTER_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    return int(content) if content.isdigit() else 0


def cevap_metnini_al(response_data):
    for item in response_data.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")

    return ""


def fonksiyon_bul(tree):
    functions = [
        node
        for node in tree.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
    ]

    if len(functions) != 1:
        return None

    return functions[0]


def oyuncu_sinifini_bul(tree):
    for node in tree.body:
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "Oyuncu"
        ):
            return node

    return None


def aday_kontrol(generated_code, mevcut_kod):
    # -----------------------------------------
    # 1. Aday kodunun syntax kontrolü
    # -----------------------------------------
    try:
        candidate_tree = ast.parse(generated_code)
    except SyntaxError as e:
        return False, f"Syntax hatası -> {e}", None

    # -----------------------------------------
    # 2. Tam olarak bir fonksiyon mu?
    # -----------------------------------------
    new_function = fonksiyon_bul(candidate_tree)

    if new_function is None:
        return (
            False,
            "Tam olarak bir fonksiyon bekleniyordu.",
            None
        )

    # -----------------------------------------
    # 3. self parametresi var mı?
    # -----------------------------------------
    if not new_function.args.args:
        return (
            False,
            "self parametresi yok.",
            None
        )

    first_arg = new_function.args.args[0]

    if first_arg.arg != "self":
        return (
            False,
            "İlk parametre self olmalı.",
            None
        )

    # -----------------------------------------
    # 4. import yasak
    # -----------------------------------------
    for node in ast.walk(candidate_tree):
        if isinstance(
            node,
            (ast.Import, ast.ImportFrom)
        ):
            return (
                False,
                "Yeni metotta import kullanılamaz.",
                None
            )

    # -----------------------------------------
    # 5. Sarı Sistemi parse et
    # -----------------------------------------
    try:
        yellow_tree = ast.parse(mevcut_kod)
    except SyntaxError as e:
        return (
            False,
            f"Sarı Sistem syntax hatası -> {e}",
            None
        )

    # -----------------------------------------
    # 6. Oyuncu sınıfını Sarı Sistem'de bul
    # -----------------------------------------
    oyuncu = oyuncu_sinifini_bul(yellow_tree)

    if oyuncu is None:
        return (
            False,
            "Sarı Sistem içinde Oyuncu sınıfı bulunamadı.",
            None
        )

    # -----------------------------------------
    # 7. Aynı isimde metot var mı?
    # -----------------------------------------
    for node in oyuncu.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            if node.name == new_function.name:
                return (
                    False,
                    f"'{new_function.name}' isimli "
                    "metot zaten mevcut.",
                    None
                )

    # -----------------------------------------
    # 8. Metodu geçici olarak Oyuncu'ya ekle
    # -----------------------------------------
    oyuncu.body.append(new_function)

    ast.fix_missing_locations(yellow_tree)

    # -----------------------------------------
    # 9. Birleşmiş sistemi compile et
    # -----------------------------------------
    try:
        compile(
            yellow_tree,
            SARI_SISTEM_FILE,
            "exec"
        )
    except SyntaxError as e:
        return (
            False,
            f"Birleşik sistem syntax hatası -> {e}",
            None
        )

    # -----------------------------------------
    # 10. Güvenli sonuç
    # -----------------------------------------
    yeni_kod = ast.unparse(yellow_tree)

    return (
        True,
        "Aday başarıyla doğrulandı.",
        yeni_kod
    )


# =================================================
# ANA DÖNGÜ
# =================================================

count = oku_sayi()

if count >= MAX_GENERATIONS:
    print(
        f"Deney {MAX_GENERATIONS} nesil sınırına ulaştı."
    )
    sys.exit(0)


print("=" * 45)
print("OTONOM MAVİ-KIRMIZI DENEYİ")
print("=" * 45)
print(f"Başarılı nesil: {count}/{MAX_GENERATIONS}")
print(f"Deneme numarası: {count + 1}")
print("=" * 45)


api_key = os.getenv(
    "OPENAI_API_KEY",
    ""
).strip()

if not api_key:
    print("Hata: OPENAI_API_KEY bulunamadı.")
    sys.exit(1)


if not os.path.exists(SARI_SISTEM_FILE):
    print(
        f"Hata: {SARI_SISTEM_FILE} bulunamadı."
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


prompt = f"""
Sen Mavi Sistem'sin.

Aşağıdaki Python oyun motorunu incele.

--- SARI SİSTEM ---
{mevcut_kod}
--- SARI SİSTEM SONU ---

Oyuncu sınıfına küçük ama gerçek bir geliştirme yap.

Kurallar:

1. Sadece yeni bir Python metodu döndür.
2. Markdown kullanma.
3. Açıklama yazma.
4. En fazla {MAX_CODE_LINES} satır kod üret.
5. Metot mevcut Oyuncu sınıfına eklenebilir olmalı.
6. İlk parametre kesinlikle self olmalı.
7. Import kullanma.
8. Mevcut özellikleri bozmamalı.
9. Mevcut metot isimlerini tekrar kullanma.
10. Kod çalışabilir ve mantıklı olmalı.

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
    print(f"Mavi Sistem hata aldı: {e}")
    sys.exit(1)


generated_code = cevap_metnini_al(
    response_data
).strip()


if not generated_code:
    print("OpenAI cevabında output_text bulunamadı.")
    print(
        json.dumps(
            response_data,
            indent=2,
            ensure_ascii=False
        )
    )
    sys.exit(1)


generated_code = (
    generated_code
    .replace("```python", "")
    .replace("```", "")
    .strip()
)


line_count = len(
    generated_code.splitlines()
)


print()
print("🔵 MAVİ'NİN ADAYI")
print("-" * 45)
print(generated_code)
print("-" * 45)
print(f"Mavi kod uzunluğu: {line_count} satır")


if line_count > MAX_CODE_LINES:
    print(
        f"🔴 KIRMIZI REDDETTİ: "
        f"{line_count} > {MAX_CODE_LINES} satır."
    )
    sys.exit(1)


print()
print("🔴 KIRMIZI DENETİM BAŞLADI")


basarili, mesaj, birlesik_kod = aday_kontrol(
    generated_code,
    mevcut_kod
)


if not basarili:
    print(f"🔴 KIRMIZI REDDETTİ: {mesaj}")
    sys.exit(1)


print(f"🔴 KIRMIZI: {mesaj}")
print("🔴 KIRMIZI: Oyuncu sınıfı doğrulandı.")
print("🔴 KIRMIZI: Yeni metot sınıfa yerleştirildi.")
print("🔴 KIRMIZI: Birleşik sistem compile edildi.")
print("🔴 KIRMIZI: Aday kabul edildi.")


# =================================================
# SARı SİSTEMİ GERÇEKTEN GÜNCELLE
# =================================================

with open(
    SARI_SISTEM_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(birlesik_kod)
    f.write("\n")


with open(
    COUNTER_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(str(count + 1))


print()
print("=" * 45)
print(
    f"🟢 SARı SİSTEM GÜNCELLENDİ"
)
print(
    f"Nesil: {count + 1}/{MAX_GENERATIONS}"
)
print("=" * 45)
