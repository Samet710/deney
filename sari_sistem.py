from sari_sistem import Oyuncu


def test_oyuncu_olusturma():

    oyuncu = Oyuncu()

    assert oyuncu.isim == "AllStar"
    assert oyuncu.seviye == 1
    assert oyuncu.xp == 0
    assert oyuncu.envanter == []


def test_xp_kazanma():

    oyuncu = Oyuncu()

    oyuncu.xp_kazan(50)

    assert oyuncu.xp == 50


def test_envanter():

    oyuncu = Oyuncu()

    assert isinstance(
        oyuncu.envanter,
        list
    )


def test_seviye_atlama():

    oyuncu = Oyuncu()

    oyuncu.xp_kazan(120)

    assert oyuncu.seviye >= 2
