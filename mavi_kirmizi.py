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


COUNTER_FILE = "counter.txt"
SARI_SISTEM_FILE = "sari_sistem.py"
TEST_FILE = "test_sari.py"
PAGES_DATA_FILE = os.path.join("docs", "data.json")

MAX_GENERATIONS = 50
MAX_CODE_LINES = 35

OPENAI_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = "gpt-5.6-luna"


# ============================================================
# DOSYA YARDIMCILARI
# ============================================================

def oku_sayi(dosya):
    if not os.path.exists(dosya):
        return 0

    try:
        with open(
            dosya,
            "r",
            encoding="utf-8"
        ) as f:
            veri = f.read().strip()

        if veri.isdigit():
            return int(veri)

    except Exception:
        pass

    return 0


def yaz_sayi(dosya, sayi):
    with open(
        dosya,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(str(sayi))


def simdi():
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


# ============================================================
# AST YARDIMCILARI
# ============================================================

def oyuncu_sinifini_bul(tree):

    for node in ast.walk(tree):

        if (
            isinstance(node, ast.ClassDef)
            and node.name == "Oyuncu"
        ):
            return node

    return None


def metotlari_bul(tree):

    return [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        )
    ]


def public_metotlari_bul(tree):

    methods = []

    for method in metotlari_bul(tree):

        if method.name.startswith("_"):
            continue

        methods.append(method)

    return methods


def cevap_metnini_bul(response_data):

    direct_text = response_data.get(
        "output_text"
    )

    if (
        isinstance(direct_text, str)
        and direct_text.strip()
    ):
        return direct_text.strip()


    for item in response_data.get(
        "output",
        []
    ):

        if item.get("type") != "message":
            continue


        for content in item.get(
            "content",
            []
        ):

            if (
                content.get("type")
                == "output_text"
            ):

                text = content.get(
                    "text",
                    ""
                )

                if text:
                    return text.strip()


    return ""


# ============================================================
# GITHUB PAGES VERİSİ
# ============================================================

def pages_verisi_yaz(
    sari_kod,
    generation,
    latest_method=None,
    latest_code=None,
    decision="Hazırlanıyor",
    baseline_score=None,
    candidate_score=None,
    score_difference=None
):

    if not os.path.exists("docs"):
        os.makedirs("docs")


    try:

        tree = ast.parse(
            sari_kod
        )

    except Exception:

        tree = None


    methods = []


    if tree is not None:

        player = oyuncu_sinifini_bul(
            tree
        )


        if player is not None:

            for node in player.body:

                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef
                    )
                ):

                    if node.name.startswith("_"):
                        continue


                    methods.append(
                        {
                            "name": node.name
                        }
                    )


    data = {
        "generation": generation,
        "max_generations": MAX_GENERATIONS,
        "latest_method": latest_method,
        "latest_generation": (
            generation
            if latest_method
            else None
        ),
        "latest_code": latest_code,
        "line_count": len(
            sari_kod.splitlines()
        ),
        "updated_at": simdi(),
        "experiment_status": decision,
        "baseline_score": baseline_score,
        "candidate_score": candidate_score,
        "score_difference": score_difference,
        "player": {
            "level": 1,
            "xp": 0,
            "inventory": 0
        },
        "methods": methods
    }


    with open(
        PAGES_DATA_FILE,
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


    has_return = any(
        isinstance(
            node,
            ast.Return
        )
        for node in ast.walk(method)
    )


    if has_return:
        score += 20


    touches_self = False


    for node in ast.walk(method):

        if isinstance(
            node,
            ast.Attribute
        ):

            if (
                isinstance(
                    node.value,
                    ast.Name
                )
                and node.value.id == "self"
            ):

                touches_self = True
                break


    if touches_self:
        score += 25


    meaningful = False


    meaningful_nodes = (
        ast.If,
        ast.For,
        ast.While,
        ast.Assign,
        ast.AnnAssign,
        ast.AugAssign,
        ast.Return,
        ast.Try
    )


    for node in method.body:

        if isinstance(
            node,
            meaningful_nodes
        ):

            meaningful = True
            break


    if meaningful:
        score += 20


    if method.end_lineno:

        line_count = (
            method.end_lineno
            - method.lineno
            + 1
        )

    else:

        line_count = 1


    if line_count <= 8:
        score += 20

    elif line_count <= 15:
        score += 12

    elif line_count <= 25:
        score += 5


    branches = 0


    for node in ast.walk(method):

        if isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.Try
            )
        ):

            branches += 1


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

def sistem_metrikleri(kod):

    try:

        tree = ast.parse(
            kod
        )

    except SyntaxError:

        return {
            "valid": False,
            "method_count": 0,
            "quality": 0,
            "score": 0
        }


    player = oyuncu_sinifini_bul(
        tree
    )


    if player is None:

        return {
            "valid": False,
            "method_count": 0,
            "quality": 0,
            "score": 0
        }


    methods = [
        node
        for node in player.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        )
        and not node.name.startswith("_")
    ]


    if methods:

        qualities = [
            metot_kalitesi(method)
            for method in methods
        ]

        average_quality = (
            sum(qualities)
            / len(qualities)
        )

    else:

        average_quality = 0


    method_points = min(
        len(methods) * 3,
        20
    )


    quality_points = (
        average_quality * 0.40
    )


    score = (
        method_points
        + quality_points
    )


    return {
        "valid": True,
        "method_count": len(methods),
        "quality": round(
            average_quality,
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
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint"
}


def guvenlik_kontrolu(tree):

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Name
        ):

            if node.id in BANNED_NAMES:

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
        "Güvenlik kontrolü başarılı."
    )


# ============================================================
# ADAY SİSTEM OLUŞTUR
# ============================================================

def aday_sistemi_olustur(
    mevcut_kod,
    generated_code
):

    try:

        mevcut_tree = ast.parse(
            mevcut_kod
        )

    except SyntaxError as e:

        return (
            False,
            f"Mevcut Sarı syntax hatası: {e}",
            None,
            None
        )


    try:

        aday_tree = ast.parse(
            generated_code
        )

    except SyntaxError as e:

        return (
            False,
            f"Aday syntax hatası: {e}",
            None,
            None
        )


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

        return (
            False,
            "Aday tam olarak bir metot içermeli.",
            None,
            None
        )


    new_method = functions[0]


    if not new_method.args.args:

        return (
            False,
            "self parametresi yok.",
            None,
            None
        )


    if (
        new_method.args.args[0].arg
        != "self"
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


    safe, message = (
        guvenlik_kontrolu(
            aday_tree
        )
    )


    if not safe:

        return (
            False,
            message,
            None,
            None
        )


    oyuncu = oyuncu_sinifini_bul(
        mevcut_tree
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
        for node in oyuncu.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
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
        mevcut_tree
    )


    try:

        candidate_source = ast.unparse(
            mevcut_tree
        )

    except Exception as e:

        return (
            False,
            f"Aday kod oluşturulamadı: {e}",
            None,
            None
        )


    try:

        compile(
            candidate_source,
            SARI_SISTEM_FILE,
            "exec"
        )

    except SyntaxError as e:

        return (
            False,
            f"Birleşik syntax hatası: {e}",
            None,
            None
        )


    return (
        True,
        "Aday sistem oluşturuldu.",
        candidate_source,
        new_method
    )


# ============================================================
# BURADAN SONRA PARÇA 2
# ============================================================
def pytest_testi(
    system_source,
    timeout=30
):

    temp_dir = tempfile.mkdtemp(
        prefix="red_test_"
    )

    try:

        system_path = os.path.join(
            temp_dir,
            "sari_sistem.py"
        )

        test_path = os.path.join(
            temp_dir,
            "test_sari.py"
        )


        with open(
            system_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(system_source)


        shutil.copy2(
            TEST_FILE,
            test_path
        )


        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q"
            ],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )


        return {
            "passed": (
                result.returncode == 0
            ),
            "stdout": result.stdout,
            "stderr": result.stderr
        }


    except subprocess.TimeoutExpired:

        return {
            "passed": False,
            "stdout": "",
            "stderr": "Test zaman aşımına uğradı."
        }


    except Exception as e:

        return {
            "passed": False,
            "stdout": "",
            "stderr": str(e)
        }


    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


def yeni_metot_testi(
    system_source,
    method_name,
    timeout=15
):

    temp_dir = tempfile.mkdtemp(
        prefix="new_method_"
    )

    try:

        system_path = os.path.join(
            temp_dir,
            "sari_sistem.py"
        )

        test_path = os.path.join(
            temp_dir,
            "run_new_method.py"
        )


        with open(
            system_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                system_source
            )


        test_code = f"""
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


        with open(
            test_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                test_code
            )


        result = subprocess.run(
            [
                sys.executable,
                test_path
            ],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )


        return {
            "passed": (
                result.returncode == 0
            ),
            "stdout": result.stdout,
            "stderr": result.stderr
        }


    except subprocess.TimeoutExpired:

        return {
            "passed": False,
            "stdout": "",
            "stderr": "Yeni metot zaman aşımına uğradı."
        }


    except Exception as e:

        return {
            "passed": False,
            "stdout": "",
            "stderr": str(e)
        }


    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


def adayi_reddet(
    mevcut_kod,
    generation,
    generated_code,
    reason,
    baseline_score=None,
    candidate_score=None
):

    difference = None


    if (
        baseline_score is not None
        and candidate_score is not None
    ):

        difference = round(
            candidate_score
            - baseline_score,
            2
        )


    pages_verisi_yaz(
        sari_kod=mevcut_kod,
        generation=generation,
        latest_method=None,
        latest_code=generated_code,
        decision=(
            f"🔴 RED: {reason}"
        ),
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        score_difference=difference
    )


    print()
    print("=" * 60)
    print("🔴 ADAY REDDEDİLDİ")
    print("=" * 60)
    print(reason)
    print("Sarı Sistem değiştirilmedi.")
    print("=" * 60)


    sys.exit(0)


# ============================================================
# ANA PROGRAM
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
    SARI_SISTEM_FILE
):

    print(
        f"HATA: {SARI_SISTEM_FILE} bulunamadı."
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
    SARI_SISTEM_FILE,
    "r",
    encoding="utf-8"
) as f:

    mevcut_kod = f.read()


print()
print("=" * 60)
print("OTONOM MAVİ-KIRMIZI DENEYİ")
print("=" * 60)

print(
    f"Mevcut nesil: "
    f"{generation}/{MAX_GENERATIONS}"
)

print(
    f"Aday nesil: "
    f"{generation + 1}/{MAX_GENERATIONS}"
)

print("=" * 60)


# ============================================================
# MEVCUT SARI SİSTEM
# ============================================================

try:

    sari_tree = ast.parse(
        mevcut_kod
    )

except SyntaxError as e:

    print(
        f"🔴 Sarı Sistem syntax hatası: {e}"
    )

    sys.exit(1)


oyuncu = oyuncu_sinifini_bul(
    sari_tree
)


if oyuncu is None:

    print(
        "🔴 Sarı Sistem içinde "
        "Oyuncu sınıfı bulunamadı."
    )

    sys.exit(1)


mevcut_metotlar = sorted(
    {
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
)


print(
    "Mevcut metotlar:"
)


for isim in mevcut_metotlar:

    print(
        f"  - {isim}"
    )


# ============================================================
# MAVİ PROMPT
# ============================================================

prompt = f"""
Sen MAVİ SİSTEM'sin.

Görevin mevcut Python oyun motorunu
tek bir küçük ama gerçek özellik ile geliştirmek.

MEVCUT SARI SİSTEM:

-------------------------
{mevcut_kod}
-------------------------

MEVCUT METOTLAR:

{", ".join(mevcut_metotlar)}

KURALLAR:

1. Yalnızca bir Python metodu üret.
2. Markdown kullanma.
3. Açıklama yazma.
4. En fazla {MAX_CODE_LINES} satır üret.
5. İlk parametre kesinlikle self olmalı.
6. self dışında hiçbir parametre kullanma.
7. Import kullanma.
8. Yasaklı Python özelliklerini kullanma.
9. Mevcut metot isimlerini tekrar kullanma.
10. Yeni metot Oyuncu sınıfına eklenebilir olmalı.
11. Mevcut özellikleri bozmamalı.
12. Sonsuz döngü oluşturmamalı.
13. Sadece print yapan metot üretme.
14. Gerçek bir oyun işlevi sağlamalı.
15. self.seviye, self.xp,
    self.envanter veya self.isim
    özelliklerinden yararlanabilirsin.
16. Mümkünse anlamlı bir değer döndür
    veya oyuncunun durumunu değiştir.

Yalnızca yeni metodun kendisini döndür.
"""


# ============================================================
# OPENAI
# ============================================================

payload = {
    "model": OPENAI_MODEL,
    "input": prompt
}


request_data = json.dumps(
    payload
).encode("utf-8")


request = urllib.request.Request(
    OPENAI_URL,
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
# OPENAI ÇIKTISI
# ============================================================

generated_code = cevap_metnini_bul(
    response_data
)


if not generated_code:

    print(
        "HATA: OpenAI kod üretmedi."
    )

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


print()
print("🔵 MAVİ'NİN ADAYI")
print("-" * 60)
print(generated_code)
print("-" * 60)


# ============================================================
# SATIR KONTROLÜ
# ============================================================

line_count = len(
    generated_code.splitlines()
)


print(
    f"Mavi kod uzunluğu: "
    f"{line_count} satır"
)


if line_count == 0:

    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        "Kod boş."
    )


if line_count > MAX_CODE_LINES:

    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        (
            f"Kod {MAX_CODE_LINES} "
            "satır sınırını aştı."
        )
    )


# ============================================================
# ADAYI OLUŞTUR
# ============================================================

print()
print(
    "🔴 KIRMIZI DENETİM BAŞLADI"
)


ok, message, aday_kod, new_method = (
    aday_sistemi_olustur(
        mevcut_kod,
        generated_code
    )
)


if not ok:

    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        message
    )


print(
    "🔴 Kırmızı: "
    "Aday sınıfa entegre edildi ✅"
)


# ============================================================
# YENİ METOT TESTİ
# ============================================================

print(
    "🔴 Kırmızı: "
    "Yeni metot çalıştırılıyor..."
)


new_method_result = yeni_metot_testi(
    aday_kod,
    new_method.name
)


if not new_method_result["passed"]:

    print(
        "🔴 Yeni metot başarısız."
    )

    print(
        new_method_result["stderr"]
    )

    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        "Yeni metot çalışma testini geçemedi."
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
    "Mevcut özellikler test ediliyor..."
)


baseline_tests = pytest_testi(
    mevcut_kod
)


if not baseline_tests["passed"]:

    print(
        "🔴 Mevcut Sarı testleri başarısız."
    )

    print(
        baseline_tests["stderr"]
    )

    sys.exit(1)


print(
    "   ✅ Mevcut Sarı testleri"
)


candidate_tests = pytest_testi(
    aday_kod
)


if not candidate_tests["passed"]:

    print(
        "   ❌ Aday regresyon testi"
    )

    print(
        candidate_tests["stderr"]
    )

    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        "Aday mevcut özellikleri koruyamadı."
    )


print(
    "   ✅ Aday regresyon testleri"
)


# ============================================================
# SKORLAR
# ============================================================

baseline_metrics = sistem_metrikleri(
    mevcut_kod
)


candidate_metrics = sistem_metrikleri(
    aday_kod
)


baseline_score = baseline_metrics[
    "score"
]


candidate_score = candidate_metrics[
    "score"
]


new_method_quality = metot_kalitesi(
    new_method
)


print()
print("🔴 KIRMIZI ÖLÇÜM")
print("-" * 60)

print(
    f"Mevcut metot sayısı: "
    f"{baseline_metrics['method_count']}"
)

print(
    f"Aday metot sayısı: "
    f"{candidate_metrics['method_count']}"
)

print(
    f"Mevcut kalite: "
    f"{baseline_metrics['quality']}"
)

print(
    f"Aday kalite: "
    f"{candidate_metrics['quality']}"
)

print(
    f"Yeni metot kalite: "
    f"{new_method_quality}"
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
    "Skor farkı: "
    f"{round(candidate_score - baseline_score, 2)}"
)

print("-" * 60)


# ============================================================
# YENİ METOT KALİTESİ
# ============================================================

if new_method_quality < 60:

    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        (
            "Yeni metodun kalite puanı "
            f"{new_method_quality}. "
            "Minimum 60 gerekli."
        ),
        baseline_score,
        candidate_score
    )


# ============================================================
# GERÇEK SEÇİLİM
# ============================================================

if candidate_score <= baseline_score:

    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        (
            "Aday sistem mevcut sistemden "
            "daha iyi skor üretmedi."
        ),
        baseline_score,
        candidate_score
    )


# ============================================================
# SARI SİSTEME KABUL
# ============================================================

new_generation = (
    generation + 1
)


with open(
    SARI_SISTEM_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        aday_kod
    )

    f.write(
        "\n"
    )


yaz_sayi(
    COUNTER_FILE,
    new_generation
)


# ============================================================
# PAGES VERİSİ
# ============================================================

pages_verisi_yaz(
    sari_kod=aday_kod,
    generation=new_generation,
    latest_method=new_method.name,
    latest_code=generated_code,
    decision="🟢 KABUL: Geliştirme başarılı",
    baseline_score=baseline_score,
    candidate_score=candidate_score,
    score_difference=round(
        candidate_score
        - baseline_score,
        2
    )
)


# ============================================================
# SONUÇ
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
    f"Yeni metot kalite: "
    f"{new_method_quality}"
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
    f"+{round(candidate_score - baseline_score, 2)}"
)

print(
    "Kırmızı bütün kontrolleri geçti."
)

print(
    "🟡 Sarı Sistem güncellendi."
)

print(
    "🌐 GitHub Pages verisi güncellendi."
)

print("=" * 60)
