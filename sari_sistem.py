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

    def zindan_baskini(self):
        if not hasattr(self, 'altin'):
            self.altin = 0
        if not hasattr(self, 'zindan_baskini_sayisi'):
            self.zindan_baskini_sayisi = 0
        ekipman_gucu = 0
        for esya in self.envanter:
            if isinstance(esya, dict):
                deger = esya.get('deger', esya.get('değer', 0))
                if isinstance(deger, (int, float)) and deger > 0:
                    ekipman_gucu += int(deger)
        eski_seviye = self.seviye
        eski_altin = self.altin
        baskin_numarasi = self.zindan_baskini_sayisi + 1
        taban_xp = self.seviye * 25
        ekipman_bonusu = min(ekipman_gucu, self.seviye * 40)
        kazanilan_xp = taban_xp + ekipman_bonusu
        kazanilan_altin = self.seviye * 15 + len(self.envanter) * 5
        self.xp += kazanilan_xp
        self.altin += kazanilan_altin
        self.zindan_baskini_sayisi = baskin_numarasi
        while self.xp >= self.seviye * 100:
            self.seviye += 1
        ganimet = {'ad': f'Zindan Ganimeti {baskin_numarasi}', 'seviye': self.seviye, 'deger': max(10, kazanilan_altin // 2)}
        self.envanter.append(ganimet)
        return {'oyuncu': self.isim, 'basarili': True, 'baskin_numarasi': baskin_numarasi, 'kazanilan_xp': kazanilan_xp, 'toplam_xp': self.xp, 'kazanilan_altin': kazanilan_altin, 'toplam_altin': self.altin, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'seviye_atlama_sayisi': self.seviye - eski_seviye, 'ekipman_gucu': ekipman_gucu, 'ganimet': ganimet, 'envanter_sayisi': len(self.envanter), 'onceki_altin': eski_altin}

    def boss_savasi(self):
        if not hasattr(self, 'altin'):
            self.altin = 0
        if not hasattr(self, 'boss_savasi_sayisi'):
            self.boss_savasi_sayisi = 0
        self.boss_savasi_sayisi += 1
        savas_no = self.boss_savasi_sayisi
        eski_seviye = self.seviye
        eski_xp = self.xp
        eski_altin = self.altin
        ekipman_gucu = 0
        for esya in self.envanter:
            if isinstance(esya, dict):
                deger = esya.get('deger', esya.get('değer', 0))
                if isinstance(deger, (int, float)) and deger > 0:
                    ekipman_gucu += int(deger)
        oyuncu_gucu = self.seviye * 30 + ekipman_gucu + len(self.envanter) * 5
        boss_gucu = self.seviye * 25 + savas_no * 8
        basarili = oyuncu_gucu >= boss_gucu
        if basarili:
            kazanilan_xp = self.seviye * 35 + ekipman_gucu // 2
            kazanilan_altin = self.seviye * 20 + len(self.envanter) * 7
            self.xp += kazanilan_xp
            self.altin += kazanilan_altin
            while self.xp >= self.seviye * 100:
                self.seviye += 1
            ganimet = {'ad': f'Boss Ganimeti {savas_no}', 'seviye': self.seviye, 'deger': max(20, kazanilan_altin // 2)}
            self.envanter.append(ganimet)
            return {'oyuncu': self.isim, 'basarili': True, 'savas_numarasi': savas_no, 'oyuncu_gucu': oyuncu_gucu, 'boss_gucu': boss_gucu, 'kazanilan_xp': kazanilan_xp, 'toplam_xp': self.xp, 'kazanilan_altin': kazanilan_altin, 'toplam_altin': self.altin, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'seviye_atlama_sayisi': self.seviye - eski_seviye, 'ganimet': ganimet, 'envanter_sayisi': len(self.envanter)}
        kaybedilen_xp = min(self.xp, self.seviye * 10)
        self.xp -= kaybedilen_xp
        ceza_altini = min(self.altin, self.seviye * 5)
        self.altin -= ceza_altini
        return {'oyuncu': self.isim, 'basarili': False, 'savas_numarasi': savas_no, 'oyuncu_gucu': oyuncu_gucu, 'boss_gucu': boss_gucu, 'kaybedilen_xp': kaybedilen_xp, 'toplam_xp': self.xp, 'kaybedilen_altin': ceza_altini, 'toplam_altin': self.altin, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'envanter_sayisi': len(self.envanter)}

    def ekipman_buyule(self):
        if not hasattr(self, 'altin'):
            self.altin = 0
        hedef_esya = None
        hedef_index = -1
        for index, esya in enumerate(self.envanter):
            if isinstance(esya, dict):
                hedef_esya = esya
                hedef_index = index
                break
        if hedef_esya is None:
            return {'oyuncu': self.isim, 'basarili': False, 'neden': 'Büyülenecek uygun bir ekipman bulunmuyor.', 'toplam_altin': self.altin, 'envanter_sayisi': len(self.envanter)}
        mevcut_deger = hedef_esya.get('deger', hedef_esya.get('değer', 0))
        if not isinstance(mevcut_deger, (int, float)) or mevcut_deger < 0:
            mevcut_deger = 0
        buyu_sayisi = hedef_esya.get('buyu_sayisi', 0)
        if not isinstance(buyu_sayisi, int) or buyu_sayisi < 0:
            buyu_sayisi = 0
        maliyet = self.seviye * 12 + int(mevcut_deger * 0.25) + buyu_sayisi * 10
        maliyet = max(15, maliyet)
        if self.altin < maliyet:
            return {'oyuncu': self.isim, 'basarili': False, 'neden': 'Büyüleme için yeterli altın bulunmuyor.', 'gereken_altin': maliyet, 'toplam_altin': self.altin, 'eksik_altin': maliyet - self.altin, 'esya': hedef_esya, 'envanter_sayisi': len(self.envanter)}
        eski_seviye = self.seviye
        eski_altin = self.altin
        eski_deger = mevcut_deger
        deger_artisi = max(10, self.seviye * 8 + buyu_sayisi * 4)
        kazanilan_xp = self.seviye * 10 + deger_artisi // 2
        self.altin -= maliyet
        self.xp += kazanilan_xp
        hedef_esya['deger'] = int(eski_deger + deger_artisi)
        hedef_esya['buyu_sayisi'] = buyu_sayisi + 1
        hedef_esya['buyulu'] = True
        hedef_esya['buyu_adi'] = f'Kademe {buyu_sayisi + 1} Büyüsü'
        while self.xp >= self.seviye * 100:
            self.seviye += 1
        return {'oyuncu': self.isim, 'basarili': True, 'esya_indexi': hedef_index, 'buyulenen_esya': hedef_esya, 'harcanan_altin': maliyet, 'onceki_altin': eski_altin, 'toplam_altin': self.altin, 'deger_artisi': deger_artisi, 'eski_deger': eski_deger, 'yeni_deger': hedef_esya['deger'], 'kazanilan_xp': kazanilan_xp, 'toplam_xp': self.xp, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'seviye_atlama_sayisi': self.seviye - eski_seviye, 'envanter_sayisi': len(self.envanter)}

    def gizli_gecit_kesfi(self):
        if not hasattr(self, 'altin'):
            self.altin = 0
        if not hasattr(self, 'gecit_kesfi_sayisi'):
            self.gecit_kesfi_sayisi = 0
        if not self.envanter:
            return {'oyuncu': self.isim, 'basarili': False, 'neden': 'Gizli geçidi açmak için en az bir eşya gerekli.', 'toplam_altin': self.altin, 'envanter_sayisi': 0}
        deneme_no = self.gecit_kesfi_sayisi + 1
        anahtar_esya = self.envanter[0]
        anahtar_degeri = 0
        if isinstance(anahtar_esya, dict):
            anahtar_degeri = anahtar_esya.get('deger', anahtar_esya.get('değer', 0))
            if not isinstance(anahtar_degeri, (int, float)) or anahtar_degeri < 0:
                anahtar_degeri = 0
        diger_esya_gucu = 0
        for esya in self.envanter[1:]:
            if isinstance(esya, dict):
                deger = esya.get('deger', esya.get('değer', 0))
                if isinstance(deger, (int, float)) and deger > 0:
                    diger_esya_gucu += int(deger)
        kesif_gucu = self.seviye * 35 + int(anahtar_degeri) + min(diger_esya_gucu, self.seviye * 30)
        gecit_zorlugu = self.seviye * 30 + deneme_no * 12
        basarili = kesif_gucu >= gecit_zorlugu
        eski_seviye = self.seviye
        eski_xp = self.xp
        eski_altin = self.altin
        self.gecit_kesfi_sayisi = deneme_no
        if not basarili:
            kaybedilen_xp = min(self.xp, self.seviye * 8)
            kaybedilen_altin = min(self.altin, self.seviye * 6)
            self.xp -= kaybedilen_xp
            self.altin -= kaybedilen_altin
            return {'oyuncu': self.isim, 'basarili': False, 'kesif_numarasi': deneme_no, 'kesif_gucu': kesif_gucu, 'gecit_zorlugu': gecit_zorlugu, 'kaybedilen_xp': kaybedilen_xp, 'toplam_xp': self.xp, 'kaybedilen_altin': kaybedilen_altin, 'toplam_altin': self.altin, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'kullanilan_esya': anahtar_esya, 'envanter_sayisi': len(self.envanter)}
        kullanilan_esya = self.envanter.pop(0)
        kazanilan_xp = self.seviye * 30 + int(anahtar_degeri) // 2
        kazanilan_altin = self.seviye * 25 + int(anahtar_degeri) // 3
        self.xp += kazanilan_xp
        self.altin += kazanilan_altin
        while self.xp >= self.seviye * 100:
            self.seviye += 1
        bulunan_eser = {'ad': f'Gizli Geçit Eseri {deneme_no}', 'seviye': self.seviye, 'deger': max(25, kazanilan_altin + self.seviye * 5), 'kaynak_esya': kullanilan_esya}
        self.envanter.append(bulunan_eser)
        return {'oyuncu': self.isim, 'basarili': True, 'kesif_numarasi': deneme_no, 'kesif_gucu': kesif_gucu, 'gecit_zorlugu': gecit_zorlugu, 'kullanilan_esya': kullanilan_esya, 'bulunan_eser': bulunan_eser, 'kazanilan_xp': kazanilan_xp, 'toplam_xp': self.xp, 'kazanilan_altin': kazanilan_altin, 'toplam_altin': self.altin, 'eski_seviye': eski_seviye, 'yeni_seviye': self.seviye, 'seviye_atlama_sayisi': self.seviye - eski_seviye, 'envanter_sayisi': len(self.envanter)}
if __name__ == '__main__':
    hero = Oyuncu()
    hero.durum_raporu()
    hero.xp_kazan(120)
    hero.durum_raporu()
