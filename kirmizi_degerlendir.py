import ast
import os
import subprocess
import sys
import tempfile
import shutil


def _metotlari_bul(kod):
    tree = ast.parse(kod)

    return [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
    ]


def _metot_kalitesi(method):
    """
    Metoda 0-100 arası deterministik kalite puanı verir.
    Bu bir 'zeka puanı' değildir.
    Sadece deney için ölçülebilir sinyaller kullanır.
    """

    score = 0

    source_line_count = (
        method.end_lineno - method.lineno + 1
        if method.end_lineno
        else 1
    )

    # 1. Gerçek bir değer döndürüyor mu?
    has_return = any(
        isinstance(node, ast.Return)
        for node in ast.walk(method)
    )

    if has_return:
        score += 25

    # 2. Oyuncunun durumuna dokunuyor mu?
    touches_state = False

    for node in ast.walk(method):

        if isinstance(node, ast.Attribute):

            if isinstance(node.value, ast.Name):
                if node.value.id == "self":
                    touches_state = True

    if touches_state:
        score += 25

    # 3. Sadece print yapan boş bir metot mu?
    meaningful_statement = False

    for node in method.body:

        if isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
                ast.Return,
                ast.Try
            )
        ):
            meaningful_statement = True

    if meaningful_statement:
        score += 15

    # 4. Kısa ve anlaşılır kod
    if source_line_count <= 12:
        score += 15
    elif source_line_count <= 20:
        score += 8

    # 5. Çok karmaşık olmaması
    branch_count = 0

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
            branch_count += 1

    if branch_count <= 3:
        score += 10
    elif branch_count <= 5:
        score += 5

    # 6. Mevcut oyuncu özelliklerinden yararlanıyor mu?
    known_attributes = {
        "isim",
        "seviye",
        "xp",
        "envanter"
    }

    uses_known_attribute = False

    for node in ast.walk(method):

        if isinstance(node, ast.Attribute):

            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and node.attr in known_attributes
            ):
                uses_known_attribute = True
                break

    if uses_known_attribute:
        score += 10

    return min(score, 100)


def _kalite_ortalamasi(kod):
    methods = _metotlari_bul(kod)

    # __main__ dışındaki sınıf metotlarını tercih et
    methods = [
        method
        for method in methods
        if method.name != "<module>"
    ]

    if not methods:
        return 0.0

    scores = [
        _metot_kalitesi(method)
        for method in methods
    ]

    return sum(scores) / len(scores)


def _pytest_calistir(system_source, test_file):
    """
    Verilen sistem kodunu geçici dizine koyar
    ve mevcut regresyon testlerini çalıştırır.
    """

    temp_dir = tempfile.mkdtemp(
        prefix="kirmizi_eval_"
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
            test_file,
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
            timeout=30
        )

        return {
            "passed": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
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


def degerlendir(system_source, test_file):
    """
    Bir Sarı Sistem sürümünün ölçümlerini üretir.
    """

    try:
        ast.parse(system_source)
    except SyntaxError as e:
        return {
            "valid": False,
            "score": 0,
            "quality": 0,
            "tests_passed": False,
            "reason": f"Syntax hatası: {e}"
        }

    test_result = _pytest_calistir(
        system_source,
        test_file
    )

    quality = _kalite_ortalamasi(
        system_source
    )

    # Testler zorunlu. Geçmeyen sistem gerçek
    # puan alamaz.
    if not test_result["passed"]:
        final_score = 0
    else:
        final_score = 50 + (
            quality * 0.5
        )

    return {
        "valid": True,
        "score": round(final_score, 2),
        "quality": round(quality, 2),
        "tests_passed": test_result["passed"],
        "reason": (
            "OK"
            if test_result["passed"]
            else "Regresyon testleri başarısız"
        )
  }
