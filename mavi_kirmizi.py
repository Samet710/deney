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

SARI_SISTEM_FILE = "sari_sistem.py"
TEST_FILE = "test_sari.py"

PAGES_DATA_FILE = os.path.join(
    "docs",
    "data.json"
)

MAX_GENERATIONS = 50

# Mavi tek seferde en fazla 1000 satır yazabilir.
MAX_CODE_LINES = 1000

# Mavi'ye son kaç deney gösterilecek?
MAX_HISTORY_FOR_PROMPT = 10

OPENAI_URL = (
    "https://api.openai.com/v1/responses"
)

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


def yaz_sayi(
    dosya,
    sayi
):

    with open(
        dosya,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            str(sayi)
        )


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

    if not os.path.exists(
        HISTORY_FILE
    ):

        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            veri = json.load(f)

        if isinstance(
            veri,
            list
        ):

            return veri

    except Exception:
        pass

    return []


def gecmise_ekle(
    kayit
):

    gecmis = gecmisi_oku()

    gecmis.append(
        kayit
    )

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            gecmis,
            f,
            ensure_ascii=False,
            indent=2
        )


def gecmis_ozeti():

    gecmis = gecmisi_oku()

    if not gecmis:

        return (
            "Henüz geçmiş deney bulunmuyor."
        )


    son_kayitlar = (
        gecmis[
            -MAX_HISTORY_FOR_PROMPT:
        ]
    )


    satirlar = []


    for kayit in son_kayitlar:

        sonuc = kayit.get(
            "result",
            "unknown"
        )

        metod = kayit.get(
            "method",
            "bilinmiyor"
        )

        reason = kayit.get(
            "reason",
            ""
        )

        baseline = kayit.get(
            "baseline_score"
        )

        candidate = kayit.get(
            "candidate_score"
        )

        difference = kayit.get(
            "score_difference"
        )


        satirlar.append(
            (
                f"- {sonuc.upper()} | "
                f"metot={metod} | "
                f"mevcut={baseline} | "
                f"aday={candidate} | "
                f"fark={difference} | "
                f"neden={reason}"
            )
        )


    return "\n".join(
        satirlar
    )


# ============================================================
# AST
# ============================================================

def oyuncu_sinifini_bul(
    tree
):

    for node in ast.walk(tree):

        if (
            isinstance(
                node,
                ast.ClassDef
            )
            and node.name == "Oyuncu"
        ):

            return node

    return None


def oyuncu_metotlarini_bul(
    player
):

    return [
        node
        for node in player.body

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        )
    ]


def cevap_metnini_bul(
    response_data
):

    direct_text = response_data.get(
        "output_text"
    )


    if (
        isinstance(
            direct_text,
            str
        )
        and direct_text.strip()
    ):

        return direct_text.strip()


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

            if (
                content.get(
                    "type"
                )
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
# PAGES
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

    os.makedirs(
        "docs",
        exist_ok=True
    )


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


    gecmis = gecmisi_oku()


    data = {
        "generation": generation,

        "max_generations": (
            MAX_GENERATIONS
        ),

        "latest_method": (
            latest_method
        ),

        "latest_generation": (
            generation
            if latest_method
            else None
        ),

        "latest_code": (
            latest_code
        ),

        "line_count": len(
            sari_kod.splitlines()
        ),

        "updated_at": simdi(),

        "experiment_status": (
            decision
        ),

        "baseline_score": (
            baseline_score
        ),

        "candidate_score": (
            candidate_score
        ),

        "score_difference": (
            score_difference
        ),

        "history_count": len(
            gecmis
        ),

        "recent_history": (
            gecmis[
                -MAX_HISTORY_FOR_PROMPT:
            ]
        ),

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

def metot_kalitesi(
    method
):

    score = 0


    # Return var mı?
    has_return = any(
        isinstance(
            node,
            ast.Return
        )
        for node in ast.walk(
            method
        )
    )


    if has_return:
        score += 20


    # self kullanıyor mu?
    touches_self = False


    for node in ast.walk(
        method
    ):

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


    # Anlamlı yapı var mı?
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


    meaningful = any(
        isinstance(
            node,
            meaningful_nodes
        )
        for node in method.body
    )


    if meaningful:
        score += 20


    # Uzunluk
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

    elif line_count <= 30:

        score += 5


    # Karmaşıklık
    branches = 0


    for node in ast.walk(
        method
    ):

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

def sistem_metrikleri(
    kod
):

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
            metot_kalitesi(
                method
            )
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

        "method_count": len(
            methods
        ),

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


def guvenlik_kontrolu(
    tree
):

    for node in ast.walk(
        tree
    ):

        # Yasak isimler
        if isinstance(
            node,
            ast.Name
        ):

            if (
                node.id
                in BANNED_NAMES
            ):

                return (
                    False,
                    f"Yasaklı isim: "
                    f"{node.id}"
                )


        # Yasak attribute'lar
        if isinstance(
            node,
            ast.Attribute
        ):

            if (
                node.attr
                in BANNED_NAMES
            ):

                return (
                    False,
                    f"Yasaklı özellik: "
                    f"{node.attr}"
                )


            # Dunder introspection yasak
            if node.attr.startswith(
                "__"
            ):

                return (
                    False,
                    (
                        "Dunder özellikleri "
                        "kullanılamaz."
                    )
                )


        # Import tamamen yasak
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
            (
                "Mevcut Sarı syntax "
                f"hatası: {e}"
            ),
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
            (
                "Aday syntax hatası: "
                f"{e}"
            ),
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
            (
                "Aday tam olarak "
                "bir metot içermeli."
            ),
            None,
            None
        )


    new_method = functions[0]


    # self zorunlu
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


    # self dışında positional argüman yok
    if len(
        new_method.args.args
    ) != 1:

        return (
            False,
            (
                "self dışında "
                "parametre kullanılamaz."
            ),
            None,
            None
        )


    # *args yasak
    if new_method.args.vararg:

        return (
            False,
            "*args kullanılamaz.",
            None,
            None
        )


    # **kwargs yasak
    if new_method.args.kwarg:

        return (
            False,
            "**kwargs kullanılamaz.",
            None,
            None
        )


    # keyword-only argüman yasak
    if new_method.args.kwonlyargs:

        return (
            False,
            "Keyword-only parametre kullanılamaz.",
            None,
            None
        )


    # Güvenlik
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


    # Oyuncu
    oyuncu = oyuncu_sinifini_bul(
        mevcut_tree
    )


    if oyuncu is None:

        return (
            False,
            (
                "Sarı Sistem içinde "
                "Oyuncu sınıfı bulunamadı."
            ),
            None,
            None
        )


    mevcut_isimler = {
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


    if new_method.name in (
        mevcut_isimler
    ):

        return (
            False,
            (
                f"{new_method.name} "
                "zaten mevcut."
            ),
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

        candidate_source = (
            ast.unparse(
                mevcut_tree
            )
        )

    except Exception as e:

        return (
            False,
            (
                "Aday kod oluşturulamadı: "
                f"{e}"
            ),
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
            (
                "Birleşik syntax hatası: "
                f"{e}"
            ),
            None,
            None
        )


    return (
        True,
        "Aday sistem oluşturuldu.",
        candidate_source,
        new_method
        )
    def temiz_env():

    env = os.environ.copy()

    # AI tarafından üretilen kodun
    # API anahtarına ulaşmasını engelle.
    env.pop(
        "OPENAI_API_KEY",
        None
    )

    env.pop(
        "GEMINI_API_KEY",
        None
    )

    return env


# ============================================================
# PYTEST
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

            f.write(
                system_source
            )


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

            timeout=timeout,

            env=temiz_env()
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
            "stderr": (
                "Test zaman aşımına uğradı."
            )
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


# ============================================================
# YENİ METOT TESTİ
# ============================================================

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

            timeout=timeout,

            env=temiz_env()
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
            "stderr": (
                "Yeni metot zaman aşımına uğradı."
            )
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


# ============================================================
# ADAYI REDDET
# ============================================================

def adayi_reddet(
    mevcut_kod,
    generation,
    generated_code,
    reason,
    method_name=None,
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


    kayit = {
        "time": simdi(),

        "attempt": (
            len(
                gecmisi_oku()
            ) + 1
        ),

        "generation": generation,

        "method": method_name,

        "result": "rejected",

        "reason": reason,

        "baseline_score": (
            baseline_score
        ),

        "candidate_score": (
            candidate_score
        ),

        "score_difference": (
            difference
        ),

        "code": generated_code
    }


    gecmise_ekle(
        kayit
    )


    pages_verisi_yaz(
        sari_kod=mevcut_kod,

        generation=generation,

        latest_method=method_name,

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

    print(
        f"Metot: {method_name}"
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

    print("=" * 60)


    # Reddedilen aday sistem hatası değildir.
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
# GEÇMİŞ
# ============================================================

gecmis = gecmisi_oku()

gecmis_metni = (
    gecmis_ozeti()
)


print()
print("=" * 60)
print("OTONOM MAVİ-KIRMIZI DENEYİ")
print("=" * 60)

print(
    f"Mevcut nesil: "
    f"{generation}/{MAX_GENERATIONS}"
)

print(
    f"Geçmiş deney: "
    f"{len(gecmis)}"
)

print(
    f"Aday nesil: "
    f"{generation + 1}/{MAX_GENERATIONS}"
)

print(
    f"Maksimum Mavi kodu: "
    f"{MAX_CODE_LINES} satır"
)

print("=" * 60)


# ============================================================
# SARI SİSTEM ANALİZİ
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

Sen deneylerden öğrenen bir
yazılım geliştirme ajanısın.

Görevin mevcut Sarı Sisteme
TEK bir yeni ve anlamlı özellik eklemek.

==================================================
MEVCUT SARI SİSTEM
==================================================

{mevcut_kod}


==================================================
MEVCUT METOTLAR
==================================================

{", ".join(mevcut_metotlar)}


==================================================
SON DENEYLER
==================================================

{gecmis_metni}


==================================================
GEÇMİŞTEN ÖĞREN
==================================================

Önceki deney sonuçlarını dikkate al.

- Reddedilen yaklaşımları aynen tekrarlama.
- Negatif skor farklarını incele.
- Başarılı değişikliklerden yararlan.
- Aynı metot fikrini tekrar üretme.
- Sisteme gerçekten yeni bir yetenek eklemeye çalış.


==================================================
KOD KURALLARI
==================================================

1. Yalnızca BİR Python metodu üret.

2. En fazla {MAX_CODE_LINES} satır üretebilirsin.

3. Markdown kullanma.

4. Açıklama yazma.

5. İlk parametre kesinlikle self olmalı.

6. self dışında hiçbir parametre kullanma.

7. *args kullanma.

8. **kwargs kullanma.

9. Import kullanma.

10. Harici kütüphane kullanma.

11. Mevcut metot isimlerini tekrar kullanma.

12. Sonsuz döngü oluşturma.

13. Sadece print yapan metot üretme.

14. Gerçek bir oyun özelliği üret.

15. Mevcut Sarı Sistem özelliklerini bozma.

16. Oyuncunun mevcut durumundan
    anlamlı şekilde yararlan.

17. Mümkünse durum değiştir
    veya anlamlı bir değer döndür.

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
).encode(
    "utf-8"
)


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

generated_code = (
    cevap_metnini_bul(
        response_data
    )
)


if not generated_code:

    print(
        "HATA: OpenAI kod üretmedi."
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
    f"{line_count}/{MAX_CODE_LINES}"
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
            f"Kod sınırı aşıldı: "
            f"{line_count} > "
            f"{MAX_CODE_LINES}"
        )
    )


# ============================================================
# KIRMIZI
# ============================================================

print()
print("🔴 KIRMIZI DENETİM BAŞLADI")


ok, message, aday_kod, new_method = (
    aday_sistemi_olustur(
        mevcut_kod,
        generated_code
    )
)


method_name = (
    new_method.name
    if new_method
    else None
)


if not ok:

    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        message,
        method_name=method_name
    )


print(
    "🔴 Kırmızı: "
    "Aday sınıfa entegre edildi ✅"
)


# ============================================================
# YENİ METOT ÇALIŞMA TESTİ
# ============================================================

print(
    "🔴 Kırmızı: "
    "Yeni metot çalıştırılıyor..."
)


new_method_result = yeni_metot_testi(
    aday_kod,
    method_name
)


if not new_method_result[
    "passed"
]:

    print(
        new_method_result["stderr"]
    )


    adayi_reddet(
        mevcut_kod,
        generation,
        generated_code,
        (
            "Yeni metot çalışma "
            "testini geçemedi."
        ),
        method_name=method_name
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


baseline_tests = pytest_testi(
    mevcut_kod
)


if not baseline_tests[
    "passed"
]:

    print(
        baseline_tests["stderr"]
    )

    sys.exit(1)


print(
    "   ✅ Mevcut Sarı testleri"
)


# ============================================================
# ADAY TESTLERİ
# ============================================================

candidate_tests = pytest_testi(
    aday_kod
)


if not candidate_tests[
    "passed"
]:

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
        (
            "Aday mevcut özellikleri "
            "koruyamadı."
        ),
        method_name=method_name
    )


print(
    "   ✅ Aday regresyon testleri"
)


# ============================================================
# SKORLAR
# ============================================================

baseline_metrics = (
    sistem_metrikleri(
        mevcut_kod
    )
)


candidate_metrics = (
    sistem_metrikleri(
        aday_kod
    )
)


baseline_score = (
    baseline_metrics[
        "score"
    ]
)


candidate_score = (
    candidate_metrics[
        "score"
    ]
)


new_method_quality = (
    metot_kalitesi(
        new_method
    )
)


score_difference = round(
    candidate_score
    - baseline_score,
    2
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
    f"Skor farkı: "
    f"{score_difference}"
)

print("-" * 60)


# ============================================================
# KALİTE EŞİĞİ
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
        method_name=method_name,
        baseline_score=baseline_score,
        candidate_score=candidate_score
    )


# ============================================================
# SEÇİLİM
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
        method_name=method_name,
        baseline_score=baseline_score,
        candidate_score=candidate_score
    )


# ============================================================
# KABUL
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
# BAŞARILI DENEYİ HAFIZAYA YAZ
# ============================================================

kayit = {
    "time": simdi(),

    "attempt": (
        len(
            gecmisi_oku()
        ) + 1
    ),

    "generation": new_generation,

    "previous_generation": generation,

    "method": method_name,

    "result": "accepted",

    "reason": (
        "Aday sistem mevcut sistemden "
        "daha iyi skor üretti."
    ),

    "baseline_score": baseline_score,

    "candidate_score": candidate_score,

    "score_difference": score_difference,

    "method_quality": new_method_quality,

    "code": generated_code
}


gecmise_ekle(
    kayit
)


# ============================================================
# PAGES
# ============================================================

pages_verisi_yaz(
    sari_kod=aday_kod,

    generation=new_generation,

    latest_method=method_name,

    latest_code=generated_code,

    decision=(
        "🟢 KABUL: "
        "Geliştirme başarılı"
    ),

    baseline_score=baseline_score,

    candidate_score=candidate_score,

    score_difference=score_difference
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
    f"{method_name}"
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
    f"+{score_difference}"
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

print("=" * 60)
