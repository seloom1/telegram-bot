# -*- coding: utf-8 -*-
"""
PDF Translation Engine for Telegram Bot
محرك ترجمة ملفات PDF بين السطور المخصص للبوت السحابي
"""

import os
import re
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor

import pymupdf
import arabic_reshaper
from bidi.algorithm import get_display

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

# 1. تحديد الخط (أولوية للخط المرفق داخل المشروع ليعمل على لينكس ويندوز وسيرفرات ريندر)
def get_font_path():
    bundled_font = os.path.join(FONTS_DIR, "arialbd.ttf")
    if os.path.exists(bundled_font):
        return bundled_font
    
    # خيارات بديلة لويندوز
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

STOP_WORDS = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'it', 'its', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'as', 'by'}

def clean_arabic_gloss(text):
    if not text:
        return ''
    text = re.sub(r'\([^\)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'[a-zA-Z0-9\-_#]', '', text)
    parts = re.split(r'[,،؛;\/\n]', text)
    for p in parts:
        p = p.strip()
        if p and re.search(r'[\u0600-\u06FF]', p):
            words = p.split()
            return ' '.join(words[:2])
    return ''

def get_word_stems(w):
    stems = []
    if w.endswith("'s"):
        stems.append(w[:-2])
    if w.endswith("ies") and len(w) > 4:
        stems.append(w[:-3] + "y")
    elif w.endswith("es") and len(w) > 3:
        stems.append(w[:-2])
    elif w.endswith("s") and len(w) > 2 and not w.endswith("ss"):
        stems.append(w[:-1])
    if w.endswith("ing") and len(w) > 4:
        stems.append(w[:-3])
        stems.append(w[:-3] + "e")
    if w.endswith("ed") and len(w) > 3:
        stems.append(w[:-2])
        stems.append(w[:-1])
    if w.endswith("ly") and len(w) > 3:
        stems.append(w[:-2])
    return stems


class FastTranslationEngine:
    def __init__(self):
        self.master_dict = {}
        self.cache = {}
        self.lock = threading.Lock()
        self.load_dictionaries()

    def load_dictionaries(self):
        # 1. Master Dict
        master_path = os.path.join(BASE_DIR, "master_dictionary.json")
        if os.path.exists(master_path):
            try:
                with open(master_path, 'r', encoding='utf-8') as f:
                    self.master_dict.update(json.load(f))
            except Exception:
                pass

        # 2. Medical Dict
        med_path = os.path.join(BASE_DIR, "medical_dictionary.json")
        if os.path.exists(med_path):
            try:
                with open(med_path, 'r', encoding='utf-8') as f:
                    self.master_dict.update(json.load(f))
            except Exception:
                pass

    def translate_word(self, word):
        w = word.lower().strip()
        if not w or len(w) <= 1:
            return ''
        
        # 1. In-memory dictionary (0ms)
        if w in self.master_dict:
            return self.master_dict[w]

        # 2. In-memory stems (0ms)
        for stem in get_word_stems(w):
            if stem in self.master_dict:
                return self.master_dict[stem]

        # 3. In-memory cache (0ms)
        with self.lock:
            if w in self.cache:
                return self.cache[w]

        return ''

    def prefetch(self, words_set):
        # تصفية الكلمات الحقيقية فقط التي يزيد طولها عن حرفين وغير موجودة في المعجم
        needed = [
            w for w in words_set 
            if len(w) > 2 and not w.isdigit() and w not in self.master_dict and w not in self.cache
        ]
        
        # فحص الجذور أولاً في الذاكرة
        truly_needed = []
        for w in needed:
            found = False
            for stem in get_word_stems(w):
                if stem in self.master_dict:
                    self.cache[w] = self.master_dict[stem]
                    found = True
                    break
            if not found:
                truly_needed.append(w)

        if not truly_needed:
            return

        # محاولة ترجمة الكلمات النادرة أونلاين بدفعة واحدة وسريعة جداً بدون تأخير (Timeout = 2.0s)
        try:
            import urllib.request
            import urllib.parse
            # نترجم فقط أول 30 كلمة غير معروفة كحد أقصى لتجنب أي بطء
            sample_words = truly_needed[:30]
            query = " | ".join(sample_words)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ar&dt=t&q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data and data[0]:
                    full_trans = "".join([part[0] for part in data[0] if part[0]])
                    trans_parts = [clean_arabic_gloss(p.strip()) for p in full_trans.split("|")]
                    with self.lock:
                        for word, trans in zip(sample_words, trans_parts):
                            if trans:
                                self.cache[word] = trans
        except Exception:
            # إذا فشل النت أو حدث حظر، لا يتم تعطيل المعالجة ويستمر المعجم الداخلي فوراً
            pass


def translate_pdf_file(input_pdf_path, output_pdf_path, progress_hook=None):
    font_path = get_font_path()
    if not font_path:
        raise RuntimeError("No Arabic font found.")

    doc = pymupdf.open(input_pdf_path)
    total_pages = len(doc)
    font = pymupdf.Font(fontfile=font_path)
    engine = FastTranslationEngine()

    # 1. جمع الكلمات الفريدة
    unique_words = set()
    pages_words = {}
    for p_idx in range(total_pages):
        page = doc[p_idx]
        words = page.get_text("words")
        pages_words[p_idx] = words
        for w in words:
            clean = re.sub(r"^[^\w']+|[^\w']+$", '', w[4]).lower()
            if clean and not clean.isdigit() and len(clean) >= 1 and clean not in STOP_WORDS:
                unique_words.add(clean)

    # 2. الترجمة المسبقة
    engine.prefetch(unique_words)

    # 3. الرسم على الصفحات مع المحاذاة المضبوطة (5.8pt و Offset = 1.8)
    gloss_size = 5.8
    vertical_offset = 1.8

    for p_idx in range(total_pages):
        page = doc[p_idx]
        words = pages_words.get(p_idx, [])

        for w in words:
            x0, y0, x1, y1, raw_text = w[0], w[1], w[2], w[3], w[4]
            clean = re.sub(r"^[^\w']+|[^\w']+$", '', raw_text).lower()

            if not clean or clean in STOP_WORDS:
                continue

            ar_trans = engine.translate_word(clean)
            if not ar_trans:
                continue

            reshaped = arabic_reshaper.reshape(ar_trans)
            bidi_text = get_display(reshaped)

            gloss_w = font.text_length(bidi_text, fontsize=gloss_size)
            x_center = (x0 + x1) / 2.0
            x_pos = max(5.0, x_center - (gloss_w / 2.0))
            y_pos = y0 + vertical_offset

            page.insert_text(
                pymupdf.Point(x_pos, y_pos),
                bidi_text,
                fontname="arial_ar_gloss",
                fontfile=font_path,
                fontsize=gloss_size,
                color=(0.85, 0.0, 0.0), # أحمر واضح
                overlay=True
            )

        if progress_hook:
            progress_hook(p_idx + 1, total_pages)

    doc.save(output_pdf_path)
    doc.close()
    return output_pdf_path
