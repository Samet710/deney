import os
import sys
import ast
import json
import urllib.request

COUNTER_FILE = "counter.txt"
SARI_SISTEM_FILE = "sari_sistem.py"
MAX_SATIR_SINIRI = 50

count = 0
if os.path.exists(COUNTER_FILE):
    with open(COUNTER_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        count = int(content) if content.isdigit() else 0

if count >= 50:
    print("Mavi-Kırmızı Deneyi hedeflenen 50 geliştirme sınırına ulaştı ve durduruldu.")
    sys.exit(0)

print(f"--- Deney Adımı {count + 1}/50 Başlatılıyor ---")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Hata: GEMINI_API_KEY çevre değişkeni bulunamadı.")
    sys.exit(1)

# MAVI SISTEM: Sıkı kısıtlamalı prompt ile istek atar
prompt = (
    f"Sen Mavi Sistem'sin. 'sari_sistem.py' içindeki Oyuncu sınıfı veya oyun motoru için {count + 1}. adımda eklenmek üzere "
    f"KISA ve BAĞIMSIZ bir Python fonksiyonu veya metodu yaz. "
    f"KURAL 1: Yazdığın kod kesinlikle en fazla 35 satır olmalı. "
    f"KURAL 2: Sadece çalışabilir Python kodu döndür. Açıklama veya markdown tırnakları (```) asla kullanma."
)

url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){api_key}"
payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        generated_code = res_data["candidates"][0]["content"]["parts"][0]["text"]
        generated_code = generated_code.replace("```python", "").replace("```", "").strip()
        print("Mavi Sistem: Kod parçası üretildi.")
except Exception as e:
    print(f"Mavi Sistem Hata Aldı: {e}")
    sys.exit(1)

# KIRMIZI SISTEM: Satır sayısı ve Sözdizimi denetimi
satir_sayisi = len(generated_code.splitlines())
print(f"Kırmızı Sistem Denetimi: Gelen kod {satir_sayisi} satır.")

if satir_sayisi > MAX_SATIR_SINIRI:
    print(f"Kırmızı Sistem Reddetti: Kod sınır olan {MAX_SATIR_SINIRI} satırı aştı ({satir_sayisi} satır).")
    sys.exit(1)

try:
    ast.parse(generated_code)
    print("Kırmızı Sistem: Sözdizimi testi başarılı, onaylandı.")
except SyntaxError as e:
    print(f"Kırmızı Sistem Reddetti: Sözdizimi hatası var -> {e}")
    sys.exit(1)

# SARI SISTEM: Onaylanan kodu entegre etme
with open(SARI_SISTEM_FILE, "a", encoding="utf-8") as f:
    f.write(f"\n\n# --- Geliştirme Adımı {count + 1} ---\n" + generated_code)

with open(COUNTER_FILE, "w", encoding="utf-8") as f:
    f.write(str(count + 1))

print(f"Sarı Sistem Başarıyla Güncellendi! Mevcut Seviye: {count + 1}/50")
      
