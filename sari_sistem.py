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

    def gelisim_uygulamasi(self):
        envanter_etkisi = len(self.envanter) * 10
        temel_odul = self.seviye * 15
        kazanilan_xp = temel_odul + envanter_etkisi
        eski_seviye = self.seviye
        self.xp += kazanilan_xp
        while self.xp >= self.seviye * 100:
            self.seviye += 1
        return {'oyuncu': self.isim, 'kazanilan_xp': kazanilan_xp, 'toplam_xp': self.xp, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'seviye_atlama_sayisi': self.seviye - eski_seviye, 'envanter_etkisi': envanter_etkisi}

    def ilerleme_ritueli(self):
        envanter_sayisi = len(self.envanter)
        eski_seviye = self.seviye
        taban_odul = self.seviye * 12
        envanter_bonusu = envanter_sayisi * 8
        kazanilan_xp = taban_odul + envanter_bonusu
        self.xp += kazanilan_xp
        while self.xp >= self.seviye * 100:
            self.seviye += 1
        odul = {'ad': f'Gelişim Mührü {self.seviye}', 'seviye': self.seviye, 'xp': kazanilan_xp}
        self.envanter.append(odul)
        return {'oyuncu': self.isim, 'kazanilan_xp': kazanilan_xp, 'toplam_xp': self.xp, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'seviye_atlama': self.seviye - eski_seviye, 'eklenen_odul': odul, 'envanter_sayisi': len(self.envanter)}

    def yildiz_uyumu(self):
        eski_seviye = self.seviye
        envanter_sayisi = len(self.envanter)
        temel_xp = self.seviye * 10
        envanter_bonusu = envanter_sayisi * 5
        kazanilan_xp = temel_xp + envanter_bonusu
        self.xp += kazanilan_xp
        while self.xp >= self.seviye * 100:
            self.seviye += 1
        nesne = {'ad': f'Yıldız Parçası {self.seviye}', 'seviye': self.seviye, 'deger': kazanilan_xp}
        self.envanter.append(nesne)
        return {'oyuncu': self.isim, 'kazanilan_xp': kazanilan_xp, 'toplam_xp': self.xp, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'seviye_atlama_sayisi': self.seviye - eski_seviye, 'eklenen_esya': nesne, 'envanter_sayisi': len(self.envanter)}

    def esya_birlestir(self):
        if len(self.envanter) < 2:
            return {'oyuncu': self.isim, 'basarili': False, 'neden': 'Birleştirme için en az iki eşya gerekli.', 'envanter_sayisi': len(self.envanter)}
        ilk_esya = self.envanter.pop(0)
        ikinci_esya = self.envanter.pop(0)
        eski_seviye = self.seviye
        kazanilan_xp = self.seviye * 20 + 10
        self.xp += kazanilan_xp
        while self.xp >= self.seviye * 100:
            self.seviye += 1
        birlesik_esya = {'ad': f'Birleşmiş Eser {self.seviye}', 'kaynaklar': [ilk_esya, ikinci_esya], 'seviye': self.seviye, 'deger': kazanilan_xp * 2}
        self.envanter.append(birlesik_esya)
        return {'oyuncu': self.isim, 'basarili': True, 'birlesen_esyalar': [ilk_esya, ikinci_esya], 'olusan_esya': birlesik_esya, 'kazanilan_xp': kazanilan_xp, 'toplam_xp': self.xp, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'seviye_atlama_sayisi': self.seviye - eski_seviye, 'envanter_sayisi': len(self.envanter)}

    def esya_satisi(self):
        if not self.envanter:
            return {'oyuncu': self.isim, 'basarili': False, 'neden': 'Satılacak eşya bulunmuyor.', 'altin': getattr(self, 'altin', 0), 'envanter_sayisi': 0}
        esya = self.envanter.pop(0)
        temel_fiyat = self.seviye * 10
        kaynak_degeri = 0
        if isinstance(esya, dict):
            kaynak_degeri = esya.get('deger', esya.get('değer', 0))
            if not isinstance(kaynak_degeri, (int, float)) or kaynak_degeri < 0:
                kaynak_degeri = 0
        satis_fiyati = max(temel_fiyat, int(kaynak_degeri))
        eski_altin = getattr(self, 'altin', 0)
        self.altin = eski_altin + satis_fiyati
        return {'oyuncu': self.isim, 'basarili': True, 'satilan_esya': esya, 'kazanilan_altin': satis_fiyati, 'toplam_altin': self.altin, 'envanter_sayisi': len(self.envanter)}
if __name__ == '__main__':
    hero = Oyuncu()
    hero.durum_raporu()
    hero.xp_kazan(120)
    hero.durum_raporu()
