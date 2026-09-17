import os
import sys
import ast
import json
import tempfile
import shutil
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ============================================================
# AYARLAR
# ============================================================

COUNTER_FILE = "counter.txt"
HISTORY_FILE = "history.json"

SARI_FILE = "sari_sistem.py"
TEST_FILE = "test_sari.py"
PAGES_FILE = os.path.join("docs", "data.json")

MAX_GENERATIONS = 50
MAX_CODE_LINES = 1000
MAX_HISTORY = 10

OPENAI_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = "gpt-5.6-luna"


# Testlerde API anahtarını vermiyoruz.
TEST_ENV = os.environ.copy()
TEST_ENV.pop("OPENAI_API_KEY", None)
TEST_ENV.pop("GEMINI_API_KEY", None)


# ============================================================
# DOSYA YARDIMCILARI
# ============================================================

def oku_sayi(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            value = f.read().strip()

        return int(value) if value.isdigit() else 0

    except Exception:
        return 0


def yaz_sayi(path, value):
    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(str(value))


def simdi():
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


# ============================================================
# GEÇMİŞ
# ============================================================

def gecmisi_oku():
    try:
        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        return data if isinstance(
            data,
            list
        ) else []

    except Exception:
        return []


def gecmise_ekle(record):
    history = gecmisi_oku()
    history.append(record)

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )


def gecmis_ozeti():
    history = gecmisi_oku()

    if not history:
        return "Henüz geçmiş deney yok."

    lines = []

    for item in history[-MAX_HISTORY:]:
        lines.append(
            f"- {item.get('result')} | "
            f"{item.get('method')} | "
            f"fark={item.get('score_difference')} | "
            f"neden={item.get('reason')}"
        )

    return "\n".join(lines)


# ============================================================
# AST
# ============================================================

def oyuncu_sinifini_bul(tree):
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "Oyuncu"
        ):
            return node

    return None


def metotlari_bul(oyuncu):
    return [
        node
        for node in oyuncu.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        )
    ]


def openai_metin(response_data):
    text = response_data.get(
        "output_text"
    )

    if isinstance(
        text,
        str
    ) and text.strip():
        return text.strip()

    for item in response_data.get(
        "output",
        []
    ):
        if item.get(
            "type"
        ) != "message":
            continue

        for content in item.get(
            "content",
            []
        ):
            if content.get(
                "type"
            ) == "output_text":

                text = content.get(
                    "text",
                    ""
                )

                if text:
                    return text.strip()

    return ""


# ============================================================
# PAGES VERİSİ
# ============================================================

def pages_verisi_yaz(
    source,
    generation,
    decision,
    method=None,
    code=None,
    baseline=None,
    candidate=None,
    difference=None
):

    os.makedirs(
        "docs",
        exist_ok=True
    )

    try:
        tree = ast.parse(source)
        oyuncu = oyuncu_sinifini_bul(tree)

    except Exception:
        oyuncu = None

    methods = []

    if oyuncu is not None:
        for node in metotlari_bul(oyuncu):
            if not node.name.startswith("_"):
                methods.append(
                    {
                        "name": node.name
                    }
                )

    history = gecmisi_oku()

    data = {
        "generation": generation,
        "max_generations": MAX_GENERATIONS,
        "latest_method": method,
        "latest_generation": (
            generation
            if method
            else None
        ),
        "latest_code": code,
        "line_count": len(
            source.splitlines()
        ),
        "updated_at": simdi(),
        "experiment_status": decision,
        "baseline_score": baseline,
        "candidate_score": candidate,
        "score_difference": difference,
        "history_count": len(history),
        "recent_history": history[
            -MAX_HISTORY:
        ],
        "player": {
            "level": 1,
            "xp": 0,
            "inventory": 0
        },
        "methods": methods
    }

    with open(
        PAGES_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# METOT KALİTESİ
# ============================================================

def metot_kalitesi(method):
    score = 0

    if any(
        isinstance(
            node,
            ast.Return
        )
        for node in ast.walk(method)
    ):
        score += 20

    if any(
        isinstance(
            node,
            ast.Attribute
        )
        and isinstance(
            node.value,
            ast.Name
        )
        and node.value.id == "self"
        for node in ast.walk(method)
    ):
        score += 25

    meaningful = (
        ast.If,
        ast.For,
        ast.While,
        ast.Assign,
        ast.AnnAssign,
        ast.AugAssign,
        ast.Return,
        ast.Try
    )

    if any(
        isinstance(
            node,
            meaningful
        )
        for node in method.body
    ):
        score += 20

    lines = (
        method.end_lineno
        - method.lineno
        + 1
        if method.end_lineno
        else 1
    )

    if lines <= 8:
        score += 20
    elif lines <= 15:
        score += 12
    elif lines <= 30:
        score += 5

    branches = sum(
        isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.Try
            )
        )
        for node in ast.walk(method)
    )

    if branches <= 2:
        score += 15
    elif branches <= 4:
        score += 8

    return min(
        score,
        100
    )


# ============================================================
# SİSTEM METRİKLERİ
# ============================================================

def sistem_metrikleri(source):
    try:
        tree = ast.parse(source)

    except SyntaxError:
        return {
            "valid": False,
            "method_count": 0,
            "quality": 0,
            "score": 0
        }

    oyuncu = oyuncu_sinifini_bul(tree)

    if oyuncu is None:
        return {
            "valid": False,
            "method_count": 0,
            "quality": 0,
            "score": 0
        }

    methods = [
        node
        for node in metotlari_bul(
            oyuncu
        )
        if not node.name.startswith("_")
    ]

    qualities = [
        metot_kalitesi(node)
        for node in methods
    ]

    quality = (
        sum(qualities) / len(qualities)
        if qualities
        else 0
    )

    method_points = min(
        len(methods) * 3,
        20
    )

    score = (
        method_points
        + quality * 0.40
    )

    return {
        "valid": True,
        "method_count": len(methods),
        "quality": round(
            quality,
            2
        ),
        "score": round(
            score,
            2
        )
    }


# ============================================================
# GÜVENLİK
# ============================================================

BANNED_NAMES = {
    "__import__",
    "__builtins__",
    "__loader__",
    "__spec__",
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "globals",
    "locals",
    "vars",
    "dir",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint",
    "help",
    "memoryview",
    "os",
    "sys",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "pathlib",
    "shutil",
    "ctypes",
    "pickle",
    "marshal"
}


def guvenlik_kontrolu(tree):
    for node in ast.walk(tree):

        if (
            isinstance(node, ast.Name)
            and node.id in BANNED_NAMES
        ):
            return (
                False,
                f"Yasaklı isim: {node.id}"
            )

        if isinstance(
            node,
            ast.Attribute
        ):

            if node.attr in BANNED_NAMES:
                return (
                    False,
                    f"Yasaklı özellik: {node.attr}"
                )

            if node.attr.startswith("__"):
                return (
                    False,
                    "Dunder özellikleri kullanılamaz."
                )

        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom
            )
        ):
            return (
                False,
                "Import kullanılamaz."
            )

    return (
        True,
        "OK"
    )


# ============================================================
# ADAYI SARI İLE BİRLEŞTİR
# ============================================================

def aday_sistemi_olustur(
    current_source,
    generated_code
):

    try:
        current_tree = ast.parse(
            current_source
        )

        generated_tree = ast.parse(
            generated_code
        )

    except SyntaxError as e:
        return (
            False,
            f"Syntax hatası: {e}",
            None,
            None
        )

    functions = [
        node
        for node in generated_tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        )
    ]

    if len(functions) != 1:
        return (
            False,
            "Aday tam olarak bir metot içermeli.",
            None,
            None
        )

    new_method = functions[0]

    if (
        not new_method.args.args
        or new_method.args.args[0].arg != "self"
    ):
        return (
            False,
            "İlk parametre self olmalı.",
            None,
            None
        )

    if len(
        new_method.args.args
    ) != 1:
        return (
            False,
            "self dışında parametre kullanılamaz.",
            None,
            None
        )

    if (
        new_method.args.vararg
        or new_method.args.kwarg
        or new_method.args.kwonlyargs
    ):
        return (
            False,
            "Ekstra parametre kullanılamaz.",
            None,
            None
        )

    safe, reason = guvenlik_kontrolu(
        generated_tree
    )

    if not safe:
        return (
            False,
            reason,
            None,
            None
        )

    oyuncu = oyuncu_sinifini_bul(
        current_tree
    )

    if oyuncu is None:
        return (
            False,
            "Sarı Sistem içinde Oyuncu sınıfı bulunamadı.",
            None,
            None
        )

    existing_names = {
        node.name
        for node in metotlari_bul(
            oyuncu
        )
    }

    if new_method.name in existing_names:
        return (
            False,
            f"{new_method.name} zaten mevcut.",
            None,
            None
        )

    oyuncu.body.append(
        new_method
    )

    ast.fix_missing_locations(
        current_tree
    )

    try:
        candidate_source = ast.unparse(
            current_tree
        )

        compile(
            candidate_source,
            SARI_FILE,
            "exec"
        )

    except Exception as e:
        return (
            False,
            f"Aday sistem derlenemedi: {e}",
            None,
            None
        )

    return (
        True,
        "Aday hazır.",
        candidate_source,
        new_method
    )
    # ============================================================
# GEÇİCİ PYTEST
# ============================================================

def run_pytest(
    source,
    timeout=30
):

    temp = tempfile.mkdtemp(
        prefix="red_pytest_"
    )

    try:

        with open(
            os.path.join(
                temp,
                SARI_FILE
            ),
            "w",
            encoding="utf-8"
        ) as f:

            f.write(source)


        shutil.copy2(
            TEST_FILE,
            os.path.join(
                temp,
                TEST_FILE
            )
        )


        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q"
            ],
            cwd=temp,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=TEST_ENV
        )


        return (
            result.returncode == 0,
            result.stdout,
            result.stderr
        )


    except subprocess.TimeoutExpired:

        return (
            False,
            "",
            "Pytest zaman aşımına uğradı."
        )


    except Exception as e:

        return (
            False,
            "",
            str(e)
        )


    finally:

        shutil.rmtree(
            temp,
            ignore_errors=True
        )


# ============================================================
# YENİ METOT TESTİ
# ============================================================

def run_new_method(
    source,
    method_name,
    timeout=15
):

    temp = tempfile.mkdtemp(
        prefix="red_method_"
    )

    try:

        with open(
            os.path.join(
                temp,
                SARI_FILE
            ),
            "w",
            encoding="utf-8"
        ) as f:

            f.write(source)


        runner = f"""
from sari_sistem import Oyuncu

oyuncu = Oyuncu()

metot = getattr(
    oyuncu,
    {method_name!r}
)

assert callable(metot)

sonuc = metot()

print("NEW_METHOD_OK")
print(type(sonuc).__name__)
"""


        runner_path = os.path.join(
            temp,
            "run_new_method.py"
        )


        with open(
            runner_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                runner
            )


        result = subprocess.run(
            [
                sys.executable,
                runner_path
            ],
            cwd=temp,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=TEST_ENV
        )


        return (
            result.returncode == 0,
            result.stdout,
            result.stderr
        )


    except subprocess.TimeoutExpired:

        return (
            False,
            "",
            "Yeni metot zaman aşımına uğradı."
        )


    except Exception as e:

        return (
            False,
            "",
            str(e)
        )


    finally:

        shutil.rmtree(
            temp,
            ignore_errors=True
        )


# ============================================================
# RED
# ============================================================

def reddet(
    source,
    generation,
    generated_code,
    reason,
    method=None,
    baseline=None,
    candidate=None
):

    difference = None

    if (
        baseline is not None
        and candidate is not None
    ):

        difference = round(
            candidate - baseline,
            2
        )


    gecmise_ekle({
        "time": simdi(),
        "attempt": len(
            gecmisi_oku()
        ) + 1,
        "generation": generation,
        "method": method,
        "result": "rejected",
        "reason": reason,
        "baseline_score": baseline,
        "candidate_score": candidate,
        "score_difference": difference,
        "code": generated_code
    })


    pages_verisi_yaz(
        source,
        generation,
        f"🔴 RED: {reason}",
        method,
        generated_code,
        baseline,
        candidate,
        difference
    )


    print()
    print("=" * 55)
    print("🔴 ADAY REDDEDİLDİ")
    print("=" * 55)
    print(
        f"Metot: {method}"
    )
    print(
        f"Neden: {reason}"
    )

    if difference is not None:
        print(
            f"Skor farkı: {difference}"
        )

    print(
        "📚 history.json güncellendi."
    )

    print(
        "🟡 Sarı Sistem değiştirilmedi."
    )

    print("=" * 55)

    sys.exit(0)


# ============================================================
# BAŞLANGIÇ
# ============================================================

generation = oku_sayi(
    COUNTER_FILE
)


if generation >= MAX_GENERATIONS:

    print(
        f"Deney {MAX_GENERATIONS} "
        "başarılı nesile ulaştı."
    )

    sys.exit(0)


api_key = os.getenv(
    "OPENAI_API_KEY",
    ""
).strip()


if not api_key:

    print(
        "HATA: OPENAI_API_KEY bulunamadı."
    )

    sys.exit(1)


if not os.path.exists(
    SARI_FILE
):

    print(
        f"HATA: {SARI_FILE} bulunamadı."
    )

    sys.exit(1)


if not os.path.exists(
    TEST_FILE
):

    print(
        f"HATA: {TEST_FILE} bulunamadı."
    )

    sys.exit(1)


with open(
    SARI_FILE,
    "r",
    encoding="utf-8"
) as f:

    current_source = f.read()


history = gecmisi_oku()


print()
print("=" * 55)
print("OTONOM MAVİ-KIRMIZI DENEYİ")
print("=" * 55)

print(
    f"Mevcut nesil: "
    f"{generation}/{MAX_GENERATIONS}"
)

print(
    f"Aday nesil: "
    f"{generation + 1}/{MAX_GENERATIONS}"
)

print(
    f"Geçmiş deney: "
    f"{len(history)}"
)

print(
    f"Mavi maksimum kod: "
    f"{MAX_CODE_LINES} satır"
)

print("=" * 55)


# ============================================================
# SARIYI ANALİZ ET
# ============================================================

try:

    tree = ast.parse(
        current_source
    )

except SyntaxError as e:

    print(
        f"🔴 Sarı Sistem syntax hatası: {e}"
    )

    sys.exit(1)


player = oyuncu_sinifini_bul(
    tree
)


if player is None:

    print(
        "🔴 Sarı Sistem içinde "
        "Oyuncu sınıfı bulunamadı."
    )

    sys.exit(1)


current_methods = sorted(
    node.name
    for node in metotlari_bul(
        player
    )
)


print(
    "Mevcut metotlar:"
)


for name in current_methods:

    print(
        f"  - {name}"
    )


# ============================================================
# MAVİ PROMPT
# ============================================================

prompt = f"""
Sen MAVİ SİSTEM'sin.

Geçmiş deney sonuçlarından yararlanan
bir yazılım geliştirme ajanısın.

MEVCUT SARI SİSTEM:

{current_source}

MEVCUT METOTLAR:

{", ".join(current_methods)}

SON DENEYLER:

{gecmis_ozeti()}

Amaç:
Oyuncu sınıfına tek bir yeni,
anlamlı oyun özelliği eklemek.

Kurallar:

1. Yalnızca BİR Python metodu döndür.
2. En fazla {MAX_CODE_LINES} satır kullanabilirsin.
3. İlk parametre self olmalı.
4. self dışında parametre kullanma.
5. *args ve **kwargs kullanma.
6. Import kullanma.
7. Mevcut metot isimlerini kullanma.
8. Sonsuz döngü oluşturma.
9. Sadece print yapan metot üretme.
10. Mevcut özellikleri bozma.
11. Gerçek bir oyun işlevi ekle.
12. Geçmişte reddedilen yaklaşımı aynen tekrarlama.

Sadece Python kodu döndür.
"""


# ============================================================
# OPENAI
# ============================================================

request = urllib.request.Request(
    OPENAI_URL,
    data=json.dumps({
        "model": OPENAI_MODEL,
        "input": prompt
    }).encode("utf-8"),
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
            response.read().decode(
                "utf-8"
            )
        )


except urllib.error.HTTPError as e:

    print(
        "OPENAI API HATASI"
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
# MAVİ ÇIKTISI
# ============================================================

generated = openai_metin(
    response_data
)


if not generated:

    print(
        "HATA: OpenAI kod üretmedi."
    )

    sys.exit(1)


generated = (
    generated
    .replace(
        "```python",
        ""
    )
    .replace(
        "```",
        ""
    )
    .strip()
)


line_count = len(
    generated.splitlines()
)


print()
print("🔵 MAVİ'NİN ADAYI")
print("-" * 55)
print(generated)
print("-" * 55)

print(
    f"Mavi kod uzunluğu: "
    f"{line_count}/{MAX_CODE_LINES}"
)


if line_count == 0:

    reddet(
        current_source,
        generation,
        generated,
        "Kod boş."
    )


if line_count > MAX_CODE_LINES:

    reddet(
        current_source,
        generation,
        generated,
        (
            f"Kod sınırı aşıldı: "
            f"{line_count} > "
            f"{MAX_CODE_LINES}"
        )
    )


# ============================================================
# ADAYI OLUŞTUR
# ============================================================

print()
print(
    "🔴 KIRMIZI DENETİM BAŞLADI"
)


ok, reason, candidate_source, method = (
    aday_sistemi_olustur(
        current_source,
        generated
    )
)


method_name = (
    method.name
    if method
    else None
)


if not ok:

    reddet(
        current_source,
        generation,
        generated,
        reason,
        method_name
    )


print(
    "🔴 Kırmızı: "
    "Aday sınıfa entegre edildi ✅"
)


# ============================================================
# YENİ METOT
# ============================================================

print(
    "🔴 Kırmızı: "
    "Yeni metot çalıştırılıyor..."
)


method_ok, _, method_error = (
    run_new_method(
        candidate_source,
        method_name
    )
)


if not method_ok:

    print(
        method_error
    )

    reddet(
        current_source,
        generation,
        generated,
        "Yeni metot çalışma testini geçemedi.",
        method_name
    )


print(
    "🔴 Kırmızı: "
    "Yeni metot çalışıyor ✅"
)


# ============================================================
# MEVCUT SİSTEM TESTLERİ
# ============================================================

print(
    "🔴 Kırmızı: "
    "Mevcut Sarı testleri..."
)


base_ok, _, base_error = run_pytest(
    current_source
)


if not base_ok:

    print(
        base_error
    )

    print(
        "🔴 Mevcut Sarı Sistem "
        "zaten testleri geçemiyor."
    )

    sys.exit(1)


print(
    "   ✅ Mevcut Sarı testleri"
)


# ============================================================
# ADAY TESTLERİ
# ============================================================

candidate_ok, _, candidate_error = (
    run_pytest(
        candidate_source
    )
)


if not candidate_ok:

    print(
        candidate_error
    )

    reddet(
        current_source,
        generation,
        generated,
        "Aday mevcut özellikleri koruyamadı.",
        method_name
    )


print(
    "   ✅ Aday regresyon testleri"
)


# ============================================================
# ÖLÇÜM
# ============================================================

base_metrics = (
    sistem_metrikleri(
        current_source
    )
)


candidate_metrics = (
    sistem_metrikleri(
        candidate_source
    )
)


baseline_score = (
    base_metrics["score"]
)


candidate_score = (
    candidate_metrics["score"]
)


quality = metot_kalitesi(
    method
)


difference = round(
    candidate_score
    - baseline_score,
    2
)


print()
print(
    "🔴 KIRMIZI ÖLÇÜM"
)
print("-" * 55)

print(
    f"Mevcut metot sayısı: "
    f"{base_metrics['method_count']}"
)

print(
    f"Aday metot sayısı: "
    f"{candidate_metrics['method_count']}"
)

print(
    f"Mevcut kalite: "
    f"{base_metrics['quality']}"
)

print(
    f"Aday kalite: "
    f"{candidate_metrics['quality']}"
)

print(
    f"Yeni metot kalite: "
    f"{quality}"
)

print(
    f"Mevcut sistem skoru: "
    f"{baseline_score}"
)

print(
    f"Aday sistem skoru: "
    f"{candidate_score}"
)

print(
    f"Skor farkı: "
    f"{difference}"
)

print("-" * 55)


# ============================================================
# KALİTE EŞİĞİ
# ============================================================

if quality < 60:

    reddet(
        current_source,
        generation,
        generated,
        (
            f"Yeni metodun kalite puanı "
            f"{quality}; minimum 60."
        ),
        method_name,
        baseline_score,
        candidate_score
    )


# ============================================================
# SEÇİLİM
# ============================================================

if candidate_score <= baseline_score:

    reddet(
        current_source,
        generation,
        generated,
        (
            "Aday sistem mevcut "
            "sistemden daha iyi skor üretmedi."
        ),
        method_name,
        baseline_score,
        candidate_score
    )


# ============================================================
# KABUL
# ============================================================

new_generation = (
    generation + 1
)


with open(
    SARI_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        candidate_source
    )

    f.write(
        "\n"
    )


yaz_sayi(
    COUNTER_FILE,
    new_generation
)


gecmise_ekle({
    "time": simdi(),

    "attempt": len(
        gecmisi_oku()
    ) + 1,

    "generation": new_generation,

    "previous_generation": generation,

    "method": method_name,

    "result": "accepted",

    "reason": (
        "Aday sistem daha yüksek skor aldı."
    ),

    "baseline_score": baseline_score,

    "candidate_score": candidate_score,

    "score_difference": difference,

    "method_quality": quality,

    "code": generated
})


pages_verisi_yaz(
    candidate_source,
    new_generation,
    "🟢 KABUL: Geliştirme başarılı",
    method_name,
    generated,
    baseline_score,
    candidate_score,
    difference
)


print()
print("=" * 55)
print("🟢 DENEY BAŞARILI")
print("=" * 55)

print(
    f"Eski nesil: {generation}"
)

print(
    f"Yeni nesil: "
    f"{new_generation}/{MAX_GENERATIONS}"
)

print(
    f"Eklenen metot: "
    f"{method_name}"
)

print(
    f"Yeni metot kalite: "
    f"{quality}"
)

print(
    f"Eski skor: "
    f"{baseline_score}"
)

print(
    f"Yeni skor: "
    f"{candidate_score}"
)

print(
    f"Fark: "
    f"+{difference}"
)

print(
    "📚 history.json güncellendi."
)

print(
    "🟡 Sarı Sistem güncellendi."
)

print(
    "🌐 GitHub Pages verisi güncellendi."
)

print("=" * 55)
