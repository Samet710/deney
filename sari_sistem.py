class Oyuncu:

    def __init__(self, isim='AllStar'):
        self.isim = isim
        self.seviye = 1
        self.xp = 0
        self.envanter = []

    def xp_kazan(self, miktar):
        self.xp += miktar
        print(f'{self.isim} {miktar} XP kazandı! Toplam XP: {self.xp}')
        if self.xp >= self.seviye * 100:
            self.seviye += 1
            print(f'TEBRİKLER! Seviye Atlandı! Yeni Seviye: {self.seviye}')

    def durum_raporu(self):
        print(f'\n--- {self.isim} Durum Raporu ---')
        print(f'Seviye: {self.seviye} | XP: {self.xp}')
        print(f'Envanter: {self.envanter}\n')

    def seviye_senkronize_et(self):
        seviye_atlandi = 0
        while self.xp >= self.seviye * 100:
            self.seviye += 1
            seviye_atlandi += 1
        return seviye_atlandi

    def ilerleme_ozeti(self):
        hedef_xp = self.seviye * 100
        return {'isim': self.isim, 'seviye': self.seviye, 'xp': self.xp, 'sonraki_seviye_xp': hedef_xp, 'kalan_xp': max(0, hedef_xp - self.xp), 'envanter_sayisi': len(self.envanter)}

    def gelisim_degeri(self):
        seviye_puani = self.seviye * 100
        envanter_puani = len(self.envanter) * 25
        toplam_puan = self.xp + seviye_puani + envanter_puani
        return {'oyuncu': self.isim, 'gelisim_puani': toplam_puan, 'seviye_katkisi': seviye_puani, 'xp_katkisi': self.xp, 'envanter_katkisi': envanter_puani}
if __name__ == '__main__':
    hero = Oyuncu()
    hero.durum_raporu()
    hero.xp_kazan(120)
    hero.durum_raporu()
