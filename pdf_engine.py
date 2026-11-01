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

# دعم استخراج النصوص والمصطلحات من المخططات والصور عبر OCR
try:
    import cv2
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
    HAS_OCR = True
    _OCR_ENGINE = None
except ImportError:
    HAS_OCR = False
    _OCR_ENGINE = None

def get_ocr_engine():
    global _OCR_ENGINE
    if HAS_OCR and _OCR_ENGINE is None:
        try:
            _OCR_ENGINE = RapidOCR()
        except Exception:
            _OCR_ENGINE = None
    return _OCR_ENGINE

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

# لا نستثني كلمات الربط أو الأفعال المساعدة حتى تظهر الترجمة كاملة فوق كل كلمة
STOP_WORDS = set()

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
        if not w:
            return ''
        
        # 1. فحص الكلمة في المعجم أولاً (حتى لو كانت حرفاً مثل a أو e أو l)
        if w in self.master_dict:
            return self.master_dict[w]

        # 2. فحص جذور الكلمة والتصريفات في الذاكرة
        for stem in get_word_stems(w):
            if stem in self.master_dict:
                return self.master_dict[stem]

        # 3. فحص الكلمات المركبة بالواصلة مثل wall-less أو rod-shaped
        if '-' in w:
            parts = [p.strip() for p in w.split('-') if p.strip()]
            part_trans = [self.translate_word(p) for p in parts]
            if any(part_trans):
                return ' - '.join(pt for pt in part_trans if pt)

        # 4. الذاكرة المؤقتة للكلمات الحديثة
        with self.lock:
            if w in self.cache:
                return self.cache[w]

        return ''

    def prefetch(self, words_set):
        needed = [
            w for w in words_set 
            if len(w) > 1 and not w.isdigit() and w not in self.master_dict and w not in self.cache
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

        # ترجمة سريعة بدفعة واحدة للكلمات النادرة (Batch Translation عبر طلب واحد فقط)
        try:
            import urllib.request
            import urllib.parse
            # تقسيم إلى دفعات بحجم 40 كلمة لتجنب أي تعليق
            for i in range(0, min(len(truly_needed), 80), 40):
                batch = truly_needed[i:i+40]
                text = "\n".join(batch)
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ar&dt=t&q={urllib.parse.quote(text)}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data and data[0]:
                        trans_text = "".join([p[0] for p in data[0] if p[0]])
                        lines = [clean_arabic_gloss(l.strip()) for l in trans_text.split("\n")]
                        with self.lock:
                            for word, trans in zip(batch, lines):
                                if trans:
                                    self.cache[word] = trans
        except Exception:
            pass


def translate_pdf_file(
    input_pdf_path,
    output_pdf_path,
    font_size=6.8,
    color=(0.85, 0.0, 0.0),
    enable_ocr=True,
    progress_hook=None
):
    font_path = get_font_path()
    if not font_path:
        raise RuntimeError("No Arabic font found.")

    doc = pymupdf.open(input_pdf_path)
    total_pages = len(doc)
    font = pymupdf.Font(fontfile=font_path)
    engine = FastTranslationEngine()
    ocr_engine = get_ocr_engine() if enable_ocr else None

    # 1. جمع الكلمات الفريدة من النصوص والمخططات
    unique_words = set()
    pages_words = {}
    for p_idx in range(total_pages):
        page = doc[p_idx]
        words = list(page.get_text("words"))

        # استخراج المصطلحات التوضيحية داخل الصور والمخططات
        if ocr_engine and page.get_images():
            try:
                for img_info in page.get_image_info():
                    bbox = pymupdf.Rect(img_info['bbox'])
                    if bbox.width > 80 and bbox.height > 50:
                        pix = page.get_pixmap(clip=bbox, dpi=150)
                        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
                        if pix.n == 4:
                            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                        else:
                            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                        res, _ = ocr_engine(img)
                        if res:
                            scale_x = bbox.width / pix.w
                            scale_y = bbox.height / pix.h
                            for box, text, score in res:
                                try: s_val = float(score)
                                except: s_val = 1.0
                                if s_val < 0.35 or not text.strip():
                                    continue
                                bx0 = bbox.x0 + min(p[0] for p in box) * scale_x
                                bx1 = bbox.x0 + max(p[0] for p in box) * scale_x
                                by0 = bbox.y0 + min(p[1] for p in box) * scale_y
                                by1 = bbox.y0 + max(p[1] for p in box) * scale_y
                                l_words = text.split()
                                if not l_words: continue
                                total_c = sum(len(w) for w in l_words) + max(0, len(l_words)-1)
                                cur_x = bx0
                                lw = max(10.0, bx1 - bx0)
                                for lw_text in l_words:
                                    w_len = len(lw_text)
                                    ww = lw * (w_len / max(1, total_c))
                                    sw = lw * (1.0 / max(1, total_c))
                                    # منع التكرار إذا كانت الكلمة موجودة مسبقاً في نفس الإحداثيات
                                    is_dup = any(abs(ew[0] - cur_x) < 14 and abs(ew[1] - by0) < 10 for ew in words)
                                    if not is_dup:
                                        words.append((cur_x, by0, cur_x + ww, by1, lw_text))
                                    cur_x += ww + sw
            except Exception:
                pass

        pages_words[p_idx] = words
        for w in words:
            clean = re.sub(r"^[^\w']+|[^\w']+$", '', w[4]).lower()
            if clean and not clean.isdigit():
                if len(clean) > 1 or clean in engine.master_dict:
                    unique_words.add(clean)

    # 2. الترجمة المسبقة لأي كلمات نادرة بدفعة واحدة
    engine.prefetch(unique_words)

    # 3. إعدادات الخط المضبوطة مع المحاذاة الدقيقة ومنع التداخل
    gloss_size = float(font_size)
    vertical_offset = 1.8
    chosen_color = tuple(color) if isinstance(color, (list, tuple)) else (0.85, 0.0, 0.0)

    for p_idx in range(total_pages):
        page = doc[p_idx]
        words = pages_words.get(p_idx, [])

        # تجميع الكلمات حسب الأسطر لمنع التداخل الأفقي
        lines = {}
        for w in words:
            y_bucket = round(w[1] / 3.0) * 3.0
            lines.setdefault(y_bucket, []).append(w)

        for y_bucket in sorted(lines.keys()):
            line_words = sorted(lines[y_bucket], key=lambda x: x[0])
            last_x1 = -1.0

            for w in line_words:
                x0, y0, x1, y1, raw_text = w[0], w[1], w[2], w[3], w[4]
                clean = re.sub(r"^[^\w']+|[^\w']+$", '', raw_text).lower()

                if not clean or clean.isdigit():
                    continue
                if len(clean) == 1 and clean not in engine.master_dict:
                    continue

                ar_trans = engine.translate_word(clean)
                if not ar_trans:
                    continue

                reshaped = arabic_reshaper.reshape(ar_trans)
                bidi_text = get_display(reshaped)

                cur_size = gloss_size
                gloss_w = font.text_length(bidi_text, fontsize=cur_size)

                # ملاءمة الحجم إذا كانت الكلمة أطول من المساحة الإنجليزية
                word_w = x1 - x0
                if gloss_w > word_w * 1.6 and cur_size > 5.6:
                    cur_size = max(5.4, cur_size - 0.8)
                    gloss_w = font.text_length(bidi_text, fontsize=cur_size)

                x_center = (x0 + x1) / 2.0
                x_pos = max(5.0, x_center - (gloss_w / 2.0))

                # منع التداخل الأفقي مع الكلمة السابقة في نفس السطر
                if x_pos < last_x1 + 1.2:
                    x_pos = last_x1 + 1.2

                y_pos = y0 + vertical_offset

                page.insert_text(
                    pymupdf.Point(x_pos, y_pos),
                    bidi_text,
                    fontname="arial_ar_gloss",
                    fontfile=font_path,
                    fontsize=cur_size,
                    color=chosen_color,
                    overlay=True
                )
                last_x1 = x_pos + gloss_w

        if progress_hook:
            progress_hook(p_idx + 1, total_pages)

    doc.save(output_pdf_path)
    doc.close()
    return output_pdf_path
