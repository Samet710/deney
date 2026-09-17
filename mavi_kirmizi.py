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
HISTORY_FILE = "history.json"

SARI_FILE = "sari_sistem.py"
TEST_FILE = "test_sari.py"
PAGES_FILE = os.path.join("docs", "data.json")

MAX_GENERATIONS = 50
MAX_CODE_LINES = 1000
MAX_HISTORY = 10

OPENAI_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = "gpt-5.6-luna"


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


# ============================================================
# TEMEL YARDIMCILAR
# ============================================================

def now():
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def read_int(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            value = f.read().strip()

        return (
            int(value)
            if value.isdigit()
            else 0
        )

    except Exception:
        return 0


def write_int(path, value):
    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            str(value)
        )


# ============================================================
# GEÇMİŞ
# ============================================================

def read_history():

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)


        if isinstance(
            data,
            list
        ):

            return data


    except Exception:
        pass


    return []


def add_history(record):

    history = read_history()

    history.append(
        record
    )


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


def history_summary():

    history = read_history()


    if not history:

        return (
            "Henüz geçmiş deney yok."
        )


    rows = []


    for item in history[
        -MAX_HISTORY:
    ]:

        rows.append(
            f"- {item.get('result')} | "
            f"metot={item.get('method')} | "
            f"fark={item.get('score_difference')} | "
            f"neden={item.get('reason')}"
        )


    return "\n".join(
        rows
    )


# ============================================================
# AST
# ============================================================

def find_player(tree):

    for node in ast.walk(
        tree
    ):

        if (
            isinstance(
                node,
                ast.ClassDef
            )
            and node.name == "Oyuncu"
        ):

            return node


    return None


def player_methods(player):

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


def response_text(data):

    text = data.get(
        "output_text"
    )


    if (
        isinstance(
            text,
            str
        )
        and text.strip()
    ):

        return text.strip()


    for item in data.get(
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
# GITHUB PAGES
# ============================================================

def write_pages(
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

        tree = ast.parse(
            source
        )

        player = find_player(
            tree
        )

    except Exception:

        player = None


    methods = []


    if player is not None:

        for node in player_methods(
            player
        ):

            if node.name.startswith(
                "_"
            ):

                continue


            methods.append(
                {
                    "name": node.name
                }
            )


    history = read_history()


    data = {

        "generation": generation,

        "max_generations":
            MAX_GENERATIONS,

        "latest_method": method,

        "latest_generation": (
            generation
            if method
            else None
        ),

        "latest_code": code,

        "line_count":
            len(source.splitlines()),

        "updated_at": now(),

        "experiment_status": decision,

        "baseline_score": baseline,

        "candidate_score": candidate,

        "score_difference": difference,

        "history_count":
            len(history),

        "recent_history":
            history[-MAX_HISTORY:],

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

def method_quality(method):

    score = 0


    # Değer döndürüyor mu?
    if any(
        isinstance(
            node,
            ast.Return
        )
        for node in ast.walk(
            method
        )
    ):

        score += 20


    # self kullanıyor mu?
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
        for node in ast.walk(
            method
        )
    ):

        score += 25


    # Gerçek mantık içeriyor mu?
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


    # Çok gereksiz uzun değil mi?
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


    # Aşırı dallanma var mı?
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

        for node in ast.walk(
            method
        )
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
# SİSTEM SKORU
# ============================================================

def system_metrics(source):

    try:

        tree = ast.parse(
            source
        )

    except SyntaxError:

        return {
            "valid": False,
            "method_count": 0,
            "quality": 0,
            "score": 0
        }


    player = find_player(
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

        for node in player_methods(
            player
        )

        if not node.name.startswith(
            "_"
        )
    ]


    qualities = [

        method_quality(
            node
        )

        for node in methods
    ]


    quality = (

        sum(qualities)
        / len(qualities)

        if qualities

        else 0
    )


    score = min(

        100,

        round(

            40
            + min(
                len(methods) * 2,
                20
            )
            + quality * 0.40,

            2
        )
    )


    return {

        "valid": True,

        "method_count":
            len(methods),

        "quality":
            round(
                quality,
                2
            ),

        "score": score
    }


# ============================================================
# GÜVENLİK KONTROLÜ
# ============================================================

def security_check(tree):

    for node in ast.walk(
        tree
    ):

        # Yasak isimler
        if isinstance(
            node,
            ast.Name
        ):

            if node.id in BANNED_NAMES:

                return (
                    False,
                    f"Yasaklı isim: {node.id}"
                )


        # Yasak attribute'lar
        if isinstance(
            node,
            ast.Attribute
        ):

            if node.attr in BANNED_NAMES:

                return (
                    False,
                    f"Yasaklı özellik: {node.attr}"
                )


            # __class__, __dict__ vb.
            if node.attr.startswith(
                "__"
            ):

                return (
                    False,
                    "Dunder özellikleri kullanılamaz."
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


        # getattr / hasattr özel kontrol
        if isinstance(
            node,
            ast.Call
        ):

            if isinstance(
                node.func,
                ast.Name
            ):

                function_name = (
                    node.func.id
                )


                if function_name in {
                    "getattr",
                    "hasattr"
                }:

                    # Hedef nesne self olmalı
                    if not node.args:

                        return (
                            False,
                            (
                                f"{function_name} "
                                "hedef olmadan kullanılamaz."
                            )
                        )


                    target = node.args[0]


                    if not (
                        isinstance(
                            target,
                            ast.Name
                        )
                        and target.id == "self"
                    ):

                        return (
                            False,
                            (
                                f"{function_name} "
                                "yalnızca self "
                                "üzerinde kullanılabilir."
                            )
                        )


                    # Alan adı sabitse dunder kontrolü
                    if len(
                        node.args
                    ) >= 2:

                        attr_arg = node.args[1]


                        if isinstance(
                            attr_arg,
                            ast.Constant
                        ):

                            if (
                                isinstance(
                                    attr_arg.value,
                                    str
                                )
                                and attr_arg.value.startswith(
                                    "__"
                                )
                            ):

                                return (
                                    False,
                                    "Dunder alanına erişilemez."
                                )


    return (
        True,
        "Güvenlik kontrolü başarılı."
    )


# ============================================================
# ADAYI OLUŞTUR
# ============================================================

def build_candidate(
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
            (
                "Aday tam olarak "
                "bir metot içermeli."
            ),
            None,
            None
        )


    method = functions[0]


    # self
    if (
        not method.args.args
        or method.args.args[0].arg != "self"
    ):

        return (
            False,
            "İlk parametre self olmalı.",
            None,
            None
        )


    # self dışındaki normal parametreleri reddet
    if len(
        method.args.args
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


    # *args / **kwargs / keyword-only
    if (
        method.args.vararg
        or method.args.kwarg
        or method.args.kwonlyargs
    ):

        return (
            False,
            "Ekstra parametre kullanılamaz.",
            None,
            None
        )


    safe, reason = security_check(
        generated_tree
    )


    if not safe:

        return (
            False,
            reason,
            None,
            None
        )


    player = find_player(
        current_tree
    )


    if player is None:

        return (
            False,
            (
                "Sarı Sistem içinde "
                "Oyuncu sınıfı bulunamadı."
            ),
            None,
            None
        )


    existing = {
        node.name
        for node in player_methods(
            player
        )
    }


    if method.name in existing:

        return (
            False,
            (
                f"{method.name} "
                "zaten mevcut."
            ),
            None,
            None
        )


    # Metodu geçici olarak ekle
    player.body.append(
        method
    )


    ast.fix_missing_locations(
        current_tree
    )


    try:

        merged = ast.unparse(
            current_tree
        )

        compile(
            merged,
            SARI_FILE,
            "exec"
        )

    except Exception as e:

        return (
            False,
            (
                "Aday sistem "
                f"derlenemedi: {e}"
            ),
            None,
            None
        )


    return (
        True,
        "Aday hazır.",
        merged,
        method
    )
    # ============================================================
# PYTHON TESTİ
# ============================================================

def run_python_test(
    source,
    script_name,
    script_source,
    timeout
):

    temp = tempfile.mkdtemp(
        prefix="red_test_"
    )


    try:

        system_path = os.path.join(
            temp,
            SARI_FILE
        )


        script_path = os.path.join(
            temp,
            script_name
        )


        with open(
            system_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                source
            )


        with open(
            script_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                script_source
            )


        env = {
            key: value

            for key, value
            in os.environ.items()

            if key not in {
                "OPENAI_API_KEY",
                "GEMINI_API_KEY"
            }
        }


        result = subprocess.run(
            [
                sys.executable,
                script_path
            ],

            cwd=temp,

            capture_output=True,

            text=True,

            timeout=timeout,

            env=env
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
            "Test zaman aşımına uğradı."
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
# PYTEST
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

            f.write(
                source
            )


        shutil.copy2(
            TEST_FILE,
            os.path.join(
                temp,
                TEST_FILE
            )
        )


        env = {
            key: value

            for key, value
            in os.environ.items()

            if key not in {
                "OPENAI_API_KEY",
                "GEMINI_API_KEY"
            }
        }


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

            env=env
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
    method_name
):

    script = f"""
from sari_sistem import Oyuncu

oyuncu = Oyuncu()

metot = getattr(
    oyuncu,
    {method_name!r}
)

assert callable(metot)

try:
    sonuc = metot()
except Exception as exc:
    print("NEW_METHOD_ERROR")
    print(type(exc).__name__)
    print(str(exc))
    raise

print("NEW_METHOD_OK")
print(type(sonuc).__name__)
"""


    return run_python_test(
        source,
        "run_new_method.py",
        script,
        15
    )


# ============================================================
# REDDET
# ============================================================

def reject(
    source,
    generation,
    code,
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


    history = read_history()


    add_history({
        "time": now(),

        "attempt":
            len(history) + 1,

        "generation":
            generation,

        "method":
            method,

        "result":
            "rejected",

        "reason":
            reason,

        "baseline_score":
            baseline,

        "candidate_score":
            candidate,

        "score_difference":
            difference,

        "code":
            code
    })


    write_pages(
        source=source,
        generation=generation,
        decision=(
            f"🔴 RED: {reason}"
        ),
        method=method,
        code=code,
        baseline=baseline,
        candidate=candidate,
        difference=difference
    )


    print()
    print("=" * 60)
    print("🔴 ADAY REDDEDİLDİ")
    print("=" * 60)
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

    print("=" * 60)


    # Adayın reddedilmesi sistem hatası değil.
    sys.exit(0)


# ============================================================
# ANA PROGRAM
# ============================================================

def main():

    generation = read_int(
        COUNTER_FILE
    )


    if generation >= MAX_GENERATIONS:

        print(
            f"Deney {MAX_GENERATIONS} "
            "başarılı nesile ulaştı."
        )

        return


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


    history = read_history()


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


    print(
        f"Geçmiş deney: "
        f"{len(history)}"
    )


    print(
        f"Mavi maksimum: "
        f"{MAX_CODE_LINES} satır"
    )


    print("=" * 60)


    # --------------------------------------------------------
    # SARI ANALİZİ
    # --------------------------------------------------------

    try:

        tree = ast.parse(
            current_source
        )

    except SyntaxError as e:

        print(
            f"🔴 Sarı Sistem syntax hatası: {e}"
        )

        sys.exit(1)


    player = find_player(
        tree
    )


    if player is None:

        print(
            "🔴 Oyuncu sınıfı bulunamadı."
        )

        sys.exit(1)


    current_methods = sorted(
        node.name
        for node in player_methods(
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


    # --------------------------------------------------------
    # MAVİ PROMPT
    # --------------------------------------------------------

    prompt = f"""
Sen MAVİ SİSTEM'sin.

Görevin mevcut Python oyun motoruna
tek bir yeni, anlamlı ve çalışabilir
özellik eklemek.

MEVCUT SARI SİSTEM:

{current_source}

MEVCUT METOTLAR:

{", ".join(current_methods)}

SON DENEYLER:

{history_summary()}

GEÇMİŞTEN ÖĞREN:

- Reddedilmiş yaklaşımları aynen tekrarlama.
- Negatif sonuçları dikkate al.
- Kabul edilmiş fikirlerden yararlan.
- Aynı metot adını kullanma.
- Gerçek bir oyun yeteneği düşün.

KOD KURALLARI:

1. Yalnızca BİR Python metodu üret.

2. En fazla {MAX_CODE_LINES}
   satır kullanabilirsin.

3. İlk parametre self olmalı.

4. self dışında normal parametre
   kullanma.

5. *args ve **kwargs kullanma.

6. Import kullanma.

7. Dış sistemlere erişme.

8. Sonsuz döngü oluşturma.

9. Sadece print yapan metot üretme.

10. Mevcut özellikleri bozma.

11. Gerçek bir oyun işlevi ekle.

12. getattr veya hasattr kullanabilirsin.
    Ancak yalnızca self üzerinde kullan.

13. Dunder alanlarına erişme.

Yalnızca yeni metodun Python kodunu döndür.
"""


    # --------------------------------------------------------
    # OPENAI
    # --------------------------------------------------------

    request = urllib.request.Request(
        OPENAI_URL,

        data=json.dumps({
            "model": OPENAI_MODEL,
            "input": prompt
        }).encode("utf-8"),

        headers={
            "Content-Type":
                "application/json",

            "Authorization":
                f"Bearer {api_key}"
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


    # --------------------------------------------------------
    # MAVİ ÇIKTISI
    # --------------------------------------------------------

    generated = response_text(
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
    print("-" * 60)
    print(generated)
    print("-" * 60)


    print(
        f"Mavi kod uzunluğu: "
        f"{line_count}/{MAX_CODE_LINES}"
    )


    if line_count == 0:

        reject(
            current_source,
            generation,
            generated,
            "Kod boş."
        )


    if line_count > MAX_CODE_LINES:

        reject(
            current_source,
            generation,
            generated,
            (
                f"Kod sınırı aşıldı: "
                f"{line_count} > "
                f"{MAX_CODE_LINES}"
            )
        )


    # --------------------------------------------------------
    # KIRMIZI - ENTEGRASYON
    # --------------------------------------------------------

    print()
    print(
        "🔴 KIRMIZI DENETİM BAŞLADI"
    )


    ok, reason, candidate_source, method = (
        build_candidate(
            current_source,
            generated
        )
    )


    method_name = (
        method.name
        if method is not None
        else None
    )


    if not ok:

        reject(
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


    # --------------------------------------------------------
    # YENİ METOT TESTİ
    # --------------------------------------------------------

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


        reject(
            current_source,
            generation,
            generated,
            (
                "Yeni metot çalışma "
                "testini geçemedi."
            ),
            method_name
        )


    print(
        "🔴 Kırmızı: "
        "Yeni metot çalışıyor ✅"
    )


    # --------------------------------------------------------
    # MEVCUT TESTLER
    # --------------------------------------------------------

    print(
        "🔴 Kırmızı: "
        "Mevcut Sarı testleri..."
    )


    base_ok, _, base_error = (
        run_pytest(
            current_source
        )
    )


    if not base_ok:

        print(
            base_error
        )

        print(
            "🔴 Mevcut Sarı Sistem "
            "testleri geçmiyor."
        )

        sys.exit(1)


    print(
        "   ✅ Mevcut Sarı testleri"
    )


    # --------------------------------------------------------
    # ADAY REGRESYON
    # --------------------------------------------------------

    candidate_ok, _, candidate_error = (
        run_pytest(
            candidate_source
        )
    )


    if not candidate_ok:

        print(
            candidate_error
        )


        reject(
            current_source,
            generation,
            generated,
            (
                "Aday mevcut özellikleri "
                "koruyamadı."
            ),
            method_name
        )


    print(
        "   ✅ Aday regresyon testleri"
    )


    # --------------------------------------------------------
    # ÖLÇÜM
    # --------------------------------------------------------

    baseline = system_metrics(
        current_source
    )


    candidate_metrics = (
        system_metrics(
            candidate_source
        )
    )


    baseline_score = baseline[
        "score"
    ]


    candidate_average_quality = (
        candidate_metrics[
            "quality"
        ]
    )


    new_feature_quality = (
        method_quality(
            method
        )
    )


    # BURASI EN ÖNEMLİ DEĞİŞİKLİK:
    #
    # Artık adayın ortalama kalitesi,
    # mevcut sistemin ortalama kalitesi
    # ile kıyaslanıp doğrudan RED nedeni
    # yapılmıyor.
    #
    # Yeni metodun kendi kalite değeri
    # ayrı ölçülüyor.

    feature_bonus = round(
        new_feature_quality * 0.10,
        2
    )


    candidate_score = round(
        baseline_score
        + feature_bonus,
        2
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

    print("-" * 60)


    print(
        f"Mevcut metot sayısı: "
        f"{baseline['method_count']}"
    )


    print(
        f"Aday metot sayısı: "
        f"{candidate_metrics['method_count']}"
    )


    print(
        f"Mevcut ortalama kalite: "
        f"{baseline['quality']}"
    )


    print(
        f"Aday ortalama kalite: "
        f"{candidate_average_quality}"
    )


    print(
        f"Yeni metot kalite: "
        f"{new_feature_quality}"
    )


    print(
        f"Yeni özellik katkısı: "
        f"+{feature_bonus}"
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


    print("-" * 60)


    # --------------------------------------------------------
    # ASGARİ YENİ ÖZELLİK KALİTESİ
    # --------------------------------------------------------

    if new_feature_quality < 60:

        reject(
            current_source,
            generation,
            generated,
            (
                "Yeni metot kalite puanı "
                f"{new_feature_quality}; "
                "minimum 60."
            ),
            method_name,
            baseline_score,
            candidate_score
        )


    # --------------------------------------------------------
    # KABUL
    # --------------------------------------------------------

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


    write_int(
        COUNTER_FILE,
        new_generation
    )


    add_history({

        "time":
            now(),

        "attempt":
            len(read_history()) + 1,

        "generation":
            new_generation,

        "previous_generation":
            generation,

        "method":
            method_name,

        "result":
            "accepted",

        "reason":
            (
                "Aday testleri geçti ve "
                "yeni özellik minimum "
                "kalite eşiğini geçti."
            ),

        "baseline_score":
            baseline_score,

        "candidate_score":
            candidate_score,

        "score_difference":
            difference,

        "method_quality":
            new_feature_quality,

        "code":
            generated
    })


    write_pages(
        source=candidate_source,
        generation=new_generation,
        decision=(
            "🟢 KABUL: "
            "Geliştirme başarılı"
        ),
        method=method_name,
        code=generated,
        baseline=baseline_score,
        candidate=candidate_score,
        difference=difference
    )


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
        f"{new_feature_quality}"
    )


    print(
        f"Yeni özellik katkısı: "
        f"+{feature_bonus}"
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


    print("=" * 60)


if __name__ == "__main__":
    main()
