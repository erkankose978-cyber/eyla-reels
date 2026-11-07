# EYLA #SantimiSantimine — günlük Reels hattı

Her gün 21:30 (Europe/Istanbul) eylaicmimarlik Instagram hesabına 1 Reels.
Sıradaki konu: `topics.md` içinde `[ ]` ile işaretli ilk satır. Paylaşınca `[x]` yap ve tarihi/medya id'sini yaz.

## Kurallar (kullanıcının açık istekleri)
- **Higgsfield KULLANMA.** (ne video üretimi ne dosya barındırma)
- **Hiçbir ücretli abonelik / plan yükseltme / satın alma yapma.** Kredi biterse dur ve kullanıcıya bildir.
- Ses: ElevenLabs bağlayıcısı, model `eleven_v4`, `generations_count: 1`.
  - Hasan Yasin (bilgi/sakin): `tILIOdKERNNbBHVEXk7I`
  - Piko (enerjik): `TA7RCSTD5b2z14h1TDTX`
- Ses her zaman **1.3×** hızlandırılır (`atempo=1.3`).
- Dil: Türkçe, "siz" hitabı, sayılar yazıyla (ElevenLabs doğru okusun). Metin ~70–85 kelime → 1.3× ile ~26–30 sn.
- Yapı: Kanca (soru) → kural/formül → somut örnek → bonus ipucu → "Sizin ... kaç santim? Yorumlara yazın."
- Bilgiler doğru ve genel kabul görmüş ölçüler olmalı; uydurma müşteri hikâyesi yok.
- Bir şey ters giderse (ses gelmez, render bozuk, Windsor hata) **paylaşma**, kullanıcıya bildir.

## Adımlar
1. **Metin:** topics.md'deki konu için metni yaz (`scripts/<slug>.txt`).
2. **Ses:** ElevenLabs `creative_generate_speech` → `creative_get_flow_run_status` ile bitmesini bekle → `content_url`.
   Bulut ortamı elevenlabsusercontent.com'a ERİŞEMEZ. Bu yüzden URL'yi `jobs/<slug>.url` dosyasına yaz, commit+push et.
   GitHub Action (`.github/workflows/fetch-audio.yml`) MP3'ü indirip `audio/<slug>.mp3` olarak commit eder (~20 sn). `git pull` ile al.
   "Free generations are busy" hatası gelirse aynı turda tekrar deneme; 1–2 dk bekleyip bir kez daha dene.
3. **Ses işleme:**
   ```
   ffmpeg -i audio/<slug>.mp3 -af atempo=1.3 -ar 44100 -ac 1 work/voice.wav
   ffmpeg -i work/voice.wav -af silencedetect=noise=-35dB:d=0.1 -f null -   # cümle parçaları
   ```
   Parçaları metindeki cümlelere eşle (virgül/iki nokta da bölebilir; gerekirse birleştir).
   `kit/cues.js`: `window.CUES=[{s,e},...]` (her parça +0.3 sn kaydırılmış), `window.OUTRO = son e + 0.55`, `window.END = OUTRO + 4`.
4. **Animasyon:** `kit/head.html` (tema, ızgara/grain, başlık, chip, glass, izometrik motor) + `kit/<slug>_timeline.part`
   (örnekler: `examples/anim15..18_timeline.part`; anim18 = perde, en güncel kalıp). Sahne başına: başlık (headline),
   ana çizim, ✕ yanlış / ✓ doğru chip'leri, ölçü çizgileri (dim), karaoke alt yazı (captions), CTA (cta), outro.
   `cat kit/head.html kit/<slug>_timeline.part > kit/<slug>.html`
   Kontrol kareleri: `cd kit && NODE_PATH=/opt/npm-tools/node_modules node render.js stills 2,8,14,20,26 <slug>.html`
   → `kit/stills/*.png` dosyalarına BAK; taşma/üst üste binme varsa düzelt.
5. **Ses miksi:** `kit/audio_template.py` içindeki `add(...)` SFX bloğunu yeni sahne zamanlarına göre düzenle:
   `python3 kit/audio_template.py work/voice.wav kit/cues.js work/mix_raw.wav`
   `ffmpeg -i work/mix_raw.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 44100 work/mix.wav`
6. **Render:** `cd kit && NODE_PATH=/opt/npm-tools/node_modules node render.js video ../work/video.mp4 <slug>.html <END>`
   `ffmpeg -i work/video.mp4 -i work/mix.wav -map 0:v -map 1:a -c:v libx264 -crf 21 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart videos/<slug>.mp4`
   `work/` commit edilmez.
7. **Yayınla:** `videos/<slug>.mp4` commit+push → GitHub Pages ~1 dk içinde yayınlar:
   `https://erkankose978-cyber.github.io/eyla-reels/videos/<slug>.mp4`
   (Bulut ortamı github.io'ya curl atamayabilir; 90 sn bekle.)
8. **Paylaş (21:30'da):** Windsor `execute_action` connector=`instagram`, account=`17841461978375970`,
   action=`create_video_post`, params `{video_url, caption, share_to_feed:true, thumb_offset:1500}`.
   Açıklama formatı: kanca + emoji'li madde listesi + formül + "💬 ... Yorumlara yazın" + "📌 ... kaydedin" + etiketler
   (`#SantimiSantimine #EYLAiçmimarlık` + konu etiketleri + `#içmimarlık #evdekorasyonu #dekorasyon #interiordesign`).
9. topics.md'yi güncelle, commit+push. Kullanıcıya kısa bir bildirim gönder (konu + medya id).
