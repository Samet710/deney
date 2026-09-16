# Sarı Sistem - Çekirdek Oyun ve İlerleme Motoru

class Oyuncu:
    def __init__(self, isim="AllStar"):
        self.isim = isim
        self.seviye = 1
        self.xp = 0
        self.envanter = []

    def xp_kazan(self, miktar):
        self.xp += miktar
        print(f"{self.isim} {miktar} XP kazandı! Toplam XP: {self.xp}")
        if self.xp >= self.seviye * 100:
            self.seviye += 1
            print(f"TEBRİKLER! Seviye Atlandı! Yeni Seviye: {self.seviye}")

    def durum_raporu(self):
        print(f"\n--- {self.isim} Durum Raporu ---")
        print(f"Seviye: {self.seviye} | XP: {self.xp}")
        print(f"Envanter: {self.envanter}\n")

if __name__ == "__main__":
    hero = Oyuncu()
    hero.durum_raporu()
    hero.xp_kazan(120)
    hero.durum_raporu()
  
