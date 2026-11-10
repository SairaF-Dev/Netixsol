"""
Hand-written review benchmark: sentiment, aspects and spam on text the models have never seen.

Why: the synthetic review corpus is 8,000 reviews made from 11 sentence templates (777 distinct texts), so a random
train/test split puts the same sentences on both sides and every model scores 1.000. These reviews were written
separately, in new words, with labels decided by a person.

Label conventions
- sentiment: the reviewer's overall verdict. A review that clearly praises one thing and complains about another
  with no overall verdict ("kapra acha hai magar 2 hafte baad mila") is Neutral, matching the system's design.
- aspects: only aspects the review actually talks about get +1 / -1; everything else is 0.
- spam: promotional links / phone numbers / referral codes / competitor promotion / repetitive bot text.
  Hard negatives (genuine reviews in capitals, mentioning a phone number, the word "fake", "do not buy") are
  included on purpose.

DEV sets may be used while improving the models. HOLDOUT sets were written at the same time, before any change,
and must never be used for tuning.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

ASPECTS = ("quality", "price", "delivery", "size_fit", "packaging", "seller")
SENTIMENTS = ("Positive", "Neutral", "Negative")


def _r(text: str, lang: str, sentiment: str, **aspects: int) -> dict[str, Any]:
    return {"text": text, "lang": lang, "sentiment": sentiment, "aspects": aspects}


SENTIMENT_DEV: list[dict[str, Any]] = [
    # English
    _r("Stitching came apart after the first wash. Really disappointed.", "English", "Negative", quality=-1),
    _r("Great value, I'd buy it again at this price.", "English", "Positive", price=1),
    _r("Arrived a day early and the box was perfectly intact.", "English", "Positive", delivery=1, packaging=1),
    _r("The fabric is lovely but the courier took twelve days.", "English", "Neutral", quality=1, delivery=-1),
    _r("Not worth the money at all.", "English", "Negative", price=-1),
    _r("Size L fits like a medium, had to return it.", "English", "Negative", size_fit=-1),
    _r("Seller answered all my questions on chat within minutes, very helpful.", "English", "Positive", seller=1),
    _r("Phone heats up while charging and the battery drains fast.", "English", "Negative", quality=-1),
    _r("It's okay. Does the job, nothing special.", "English", "Neutral"),
    _r("Colour is exactly as shown and the material feels premium.", "English", "Positive", quality=1),
    _r("Parcel was soaked and the carton was crushed, though the shoes inside were fine.", "English", "Neutral", packaging=-1, quality=1),
    _r("Absolutely love it, my wife wore it on Eid and everyone asked where it's from.", "English", "Positive"),
    _r("Expensive compared to the shop down the road.", "English", "Negative", price=-1),
    _r("Delivery was quick but the kurta is too tight around the shoulders.", "English", "Neutral", delivery=1, size_fit=-1),
    _r("Wrong colour was sent and the seller never replied to my messages.", "English", "Negative", seller=-1),
    _r("Good quality laptop bag, sturdy zips, reasonable price.", "English", "Positive", quality=1, price=1),
    _r("Completely useless, stopped working on day two.", "English", "Negative", quality=-1),
    _r("Packaging was neat and the parcel came on time. Product is decent.", "English", "Positive", packaging=1, delivery=1, quality=1),
    _r("Perfume smell fades within an hour, feels like a cheap copy.", "English", "Negative", quality=-1),
    _r("Fits true to size and the fabric breathes well in summer.", "English", "Positive", size_fit=1, quality=1),
    # Roman Urdu
    _r("Kapra bohot patla hai, pehli dhulai mein rang utar gaya.", "Roman_Urdu", "Negative", quality=-1),
    _r("Itni kam qeemat mein itni achi cheez, maza aa gaya.", "Roman_Urdu", "Positive", price=1, quality=1),
    _r("Parcel 3 din mein aa gaya, packing bhi theek thi.", "Roman_Urdu", "Positive", delivery=1, packaging=1),
    _r("Suit to khoobsurat hai magar 2 hafte baad mila.", "Roman_Urdu", "Neutral", quality=1, delivery=-1),
    _r("Bilkul paise ki barbadi hai, mat lena.", "Roman_Urdu", "Negative", price=-1),
    _r("Medium order kiya tha, bohot khula hai.", "Roman_Urdu", "Negative", size_fit=-1),
    _r("Dukandar bhai ne foran jawab diya aur exchange bhi kar diya.", "Roman_Urdu", "Positive", seller=1),
    _r("Mobile garam ho jata hai aur charging jaldi khatam ho jati hai.", "Roman_Urdu", "Negative", quality=-1),
    _r("Theek thaak hai, itna khas nahi.", "Roman_Urdu", "Neutral"),
    _r("Rang bilkul tasveer wala hai, silai bhi saaf hai.", "Roman_Urdu", "Positive", quality=1),
    _r("Dabba toota hua aaya lekin joote sahi salamat the.", "Roman_Urdu", "Neutral", packaging=-1, quality=1),
    _r("Ammi ko bohot pasand aaya, shukriya.", "Roman_Urdu", "Positive"),
    _r("Market se mehnga mila, dobara nahi lunga.", "Roman_Urdu", "Negative", price=-1),
    _r("Delivery to jaldi hui par kameez tang hai.", "Roman_Urdu", "Neutral", delivery=1, size_fit=-1),
    _r("Ghalat rang bhej diya aur seller phone nahi uthata.", "Roman_Urdu", "Negative", seller=-1),
    _r("Bag mazboot hai, zip achi quality ki hai, qeemat bhi munasib.", "Roman_Urdu", "Positive", quality=1, price=1),
    _r("Do din chala phir band ho gaya, bakwas.", "Roman_Urdu", "Negative", quality=-1),
    _r("Waqt par pohncha aur packing saaf suthri thi.", "Roman_Urdu", "Positive", delivery=1, packaging=1),
    _r("Khushboo ek ghante mein ur jati hai, nakli lagti hai.", "Roman_Urdu", "Negative", quality=-1),
    _r("Size bilkul perfect hai aur garmi mein kapra aaramdeh hai.", "Roman_Urdu", "Positive", size_fit=1, quality=1),
    # Urdu script
    _r("کپڑا بہت پتلا ہے، پہلی دھلائی میں رنگ اتر گیا۔", "Urdu", "Negative", quality=-1),
    _r("اتنی کم قیمت میں اتنی اچھی چیز، مزہ آ گیا۔", "Urdu", "Positive", price=1, quality=1),
    _r("پارسل تین دن میں آ گیا، پیکنگ بھی ٹھیک تھی۔", "Urdu", "Positive", delivery=1, packaging=1),
    _r("سوٹ تو خوبصورت ہے مگر دو ہفتے بعد ملا۔", "Urdu", "Neutral", quality=1, delivery=-1),
    _r("بالکل پیسوں کا ضیاع ہے، مت خریدیں۔", "Urdu", "Negative", price=-1),
    _r("میڈیم منگوایا تھا، بہت کھلا ہے۔", "Urdu", "Negative", size_fit=-1),
    _r("دکاندار نے فوراً جواب دیا اور تبدیل بھی کر دیا۔", "Urdu", "Positive", seller=1),
    _r("موبائل گرم ہو جاتا ہے اور بیٹری جلدی ختم ہوتی ہے۔", "Urdu", "Negative", quality=-1),
    _r("ٹھیک ٹھاک ہے، کوئی خاص بات نہیں۔", "Urdu", "Neutral"),
    _r("رنگ بالکل تصویر جیسا ہے، سلائی بھی صاف ہے۔", "Urdu", "Positive", quality=1),
    _r("ڈبہ ٹوٹا ہوا آیا لیکن جوتے صحیح سلامت تھے۔", "Urdu", "Neutral", packaging=-1, quality=1),
    _r("امی کو بہت پسند آیا، شکریہ۔", "Urdu", "Positive"),
    _r("بازار سے مہنگا ملا، دوبارہ نہیں لوں گا۔", "Urdu", "Negative", price=-1),
    _r("ڈلیوری تو جلدی ہوئی لیکن قمیض تنگ ہے۔", "Urdu", "Neutral", delivery=1, size_fit=-1),
    _r("غلط رنگ بھیج دیا اور دکاندار فون نہیں اٹھاتا۔", "Urdu", "Negative", seller=-1),
    _r("بیگ مضبوط ہے، زپ اچھی ہے، قیمت بھی مناسب ہے۔", "Urdu", "Positive", quality=1, price=1),
    _r("دو دن چلا پھر بند ہو گیا، بیکار۔", "Urdu", "Negative", quality=-1),
    _r("وقت پر پہنچا اور پیکنگ صاف ستھری تھی۔", "Urdu", "Positive", delivery=1, packaging=1),
    _r("خوشبو ایک گھنٹے میں اڑ جاتی ہے، نقلی لگتی ہے۔", "Urdu", "Negative", quality=-1),
    _r("سائز بالکل ٹھیک ہے اور گرمی میں کپڑا آرام دہ ہے۔", "Urdu", "Positive", size_fit=1, quality=1),
]

SENTIMENT_HOLDOUT: list[dict[str, Any]] = [
    _r("Not bad at all, honestly better than I expected.", "English", "Positive"),
    _r("The watch looks cheap and the strap broke within a week.", "English", "Negative", quality=-1),
    _r("Super fast shipping, came in a sealed box.", "English", "Positive", delivery=1, packaging=1),
    _r("Lovely print, shame the trousers are too short.", "English", "Neutral", quality=1, size_fit=-1),
    _r("Overpriced for what you get, but the seller was polite.", "English", "Neutral", price=-1, seller=1),
    _r("Rider was rude and the parcel came 9 days late.", "English", "Negative", delivery=-1),
    _r("worth every rupee, quality is top notch", "English", "Positive", price=1, quality=1),
    _r("Item never matched the description. Asked for a refund, no reply.", "English", "Negative", quality=-1, seller=-1),
    _r("Average product, average packing.", "English", "Neutral"),
    _r("Blender is powerful and easy to clean.", "English", "Positive", quality=1),
    _r("Bura nahi hai, umeed se behtar nikla.", "Roman_Urdu", "Positive"),
    _r("Ghari sasti lagti hai aur strap hafte mein toot gaya.", "Roman_Urdu", "Negative", quality=-1),
    _r("Bohat tez delivery, seal pack dabba aaya.", "Roman_Urdu", "Positive", delivery=1, packaging=1),
    _r("Print pyara hai par shalwar choti hai.", "Roman_Urdu", "Neutral", quality=1, size_fit=-1),
    _r("Qeemat zyada hai lekin seller ka rawaiya acha tha.", "Roman_Urdu", "Neutral", price=-1, seller=1),
    _r("Rider ne batameezi ki aur parcel 9 din late aaya.", "Roman_Urdu", "Negative", delivery=-1),
    _r("Har rupay ke qabil, quality zabardast.", "Roman_Urdu", "Positive", price=1, quality=1),
    _r("Cheez description jaisi bilkul nahi thi, refund manga koi jawab nahi.", "Roman_Urdu", "Negative", quality=-1, seller=-1),
    _r("Aam sa product hai, aam si packing.", "Roman_Urdu", "Neutral"),
    _r("Blender taqatwar hai aur saaf karna asaan.", "Roman_Urdu", "Positive", quality=1),
    _r("برا نہیں ہے، امید سے بہتر نکلا۔", "Urdu", "Positive"),
    _r("گھڑی سستی لگتی ہے اور پٹا ایک ہفتے میں ٹوٹ گیا۔", "Urdu", "Negative", quality=-1),
    _r("بہت تیز ڈلیوری، سیل بند ڈبہ آیا۔", "Urdu", "Positive", delivery=1, packaging=1),
    _r("پرنٹ پیارا ہے پر شلوار چھوٹی ہے۔", "Urdu", "Neutral", quality=1, size_fit=-1),
    _r("قیمت زیادہ ہے لیکن دکاندار کا رویہ اچھا تھا۔", "Urdu", "Neutral", price=-1, seller=1),
    _r("رائیڈر نے بدتمیزی کی اور پارسل نو دن دیر سے آیا۔", "Urdu", "Negative", delivery=-1),
    _r("ہر روپے کے قابل، کوالٹی زبردست۔", "Urdu", "Positive", price=1, quality=1),
    _r("چیز تفصیل جیسی بالکل نہیں تھی، رقم واپسی مانگی کوئی جواب نہیں۔", "Urdu", "Negative", quality=-1, seller=-1),
    _r("عام سی پراڈکٹ، عام سی پیکنگ۔", "Urdu", "Neutral"),
    _r("بلینڈر طاقتور ہے اور صاف کرنا آسان ہے۔", "Urdu", "Positive", quality=1),
]


def _s(text: str, rating: int, spam: bool) -> dict[str, Any]:
    return {"text": text, "rating": rating, "spam": spam}


SPAM_DEV: list[dict[str, Any]] = [
    _s("Get 70% OFF on all brands!! Order at shopdeals.pk or DM on insta @cheapbrands", 5, True),
    _s("Earn Rs 5000 daily from home, WhatsApp 0321-1234567", 5, True),
    _s("Use my referral code SAVE50 for discount on your first order!!!", 5, True),
    _s("Ye wala mat lo, hamari dukaan se asli maal lo, link bio mein", 1, True),
    _s("Nice product nice product nice product nice product", 5, True),
    _s("Wholesale rates available, contact 0333 7654321 for bulk orders", 5, True),
    _s("سستے داموں برانڈڈ کپڑے، واٹس ایپ کریں 03001112233", 5, True),
    _s("Best best best best!!!!! 5 star 5 star", 5, True),
    _s("BOHOT ZABARDAST!!! Ammi ko bohot pasand aaya", 5, False),
    _s("100% original product, checked the serial on Samsung's website.", 5, False),
    _s("Rider called from a 0300 number before arriving, very polite.", 5, False),
    _s("Do not buy if you have wide feet, runs narrow.", 2, False),
    _s("Fake leather, peeling after a month. Very disappointed.", 1, False),
    _s("5 stars, would recommend to friends.", 5, False),
    _s("Worst purchase ever, the zip broke on day one.", 1, False),
    _s("Order kiya tha Eid ke liye, waqt par mil gaya. Shukriya!", 5, False),
]

SPAM_HOLDOUT: list[dict[str, Any]] = [
    _s("Click here www.bestoffers-online.com for a free iPhone giveaway", 5, True),
    _s("Follow our page for daily sale updates and giveaways!!!", 5, True),
    _s("Sab se sasta maal sirf hamare paas, call karein 0345-9988776", 5, True),
    _s("good good good good good good", 5, True),
    _s("ارزاں ترین قیمت پر خریداری کے لیے ہماری ویب سائٹ وزٹ کریں", 5, True),
    _s("AMAZING QUALITY, totally worth it!!", 5, False),
    _s("The courier said to call him on 0312 if late, he was on time though.", 4, False),
    _s("This is a fake copy, not the original brand. Returned it.", 1, False),
    _s("Do not wash in hot water, colour bleeds. Otherwise fine.", 3, False),
    _s("Very bad, never buying again.", 1, False),
]


def evaluate_sentiment(predict, items: list[dict[str, Any]]) -> dict[str, Any]:
    """`predict(text) -> 'Positive' | 'Neutral' | 'Negative'`. Returns overall and per-language accuracy / macro-F1."""
    y = [it["sentiment"] for it in items]
    p = [predict(it["text"]) for it in items]
    out: dict[str, Any] = {
        "n": len(items),
        "accuracy": round(float(accuracy_score(y, p)), 4),
        "macro_f1": round(float(f1_score(y, p, labels=list(SENTIMENTS), average="macro", zero_division=0)), 4),
        "per_language": {},
    }
    for lang in ("English", "Roman_Urdu", "Urdu"):
        idx = [i for i, it in enumerate(items) if it["lang"] == lang]
        yl, pl = [y[i] for i in idx], [p[i] for i in idx]
        out["per_language"][lang] = {
            "n": len(idx),
            "accuracy": round(float(accuracy_score(yl, pl)), 4),
            "macro_f1": round(float(f1_score(yl, pl, labels=list(SENTIMENTS), average="macro", zero_division=0)), 4),
        }
    out["errors"] = [
        {"text": it["text"], "expected": y[i], "predicted": p[i]} for i, it in enumerate(items) if y[i] != p[i]
    ]
    return out


def evaluate_aspects(predict, items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    `predict(text) -> {aspect: -1|0|1}`. Reports, over all review x aspect cells:
    - detection: precision / recall / F1 of "this aspect is mentioned" (non-zero)
    - polarity accuracy on aspects that are mentioned AND detected
    - exact cell accuracy (3-class) and per-aspect macro-F1 averaged
    """
    y_rows, p_rows = [], []
    for it in items:
        pred = predict(it["text"])
        y_rows.append([int(it["aspects"].get(a, 0)) for a in ASPECTS])
        p_rows.append([int(pred.get(a, 0)) for a in ASPECTS])
    y, p = np.array(y_rows), np.array(p_rows)
    y_m, p_m = (y != 0).ravel(), (p != 0).ravel()
    both = (y != 0) & (p != 0)
    per_aspect_f1 = [
        float(f1_score(y[:, j], p[:, j], labels=[-1, 0, 1], average="macro", zero_division=0)) for j in range(len(ASPECTS))
    ]
    return {
        "n_reviews": len(items),
        "mentions": int(y_m.sum()),
        "detection_precision": round(float(precision_score(y_m, p_m, zero_division=0)), 4),
        "detection_recall": round(float(recall_score(y_m, p_m, zero_division=0)), 4),
        "detection_f1": round(float(f1_score(y_m, p_m, zero_division=0)), 4),
        "polarity_accuracy_when_detected": round(float((y[both] == p[both]).mean()) if both.any() else 0.0, 4),
        "cell_accuracy": round(float((y == p).mean()), 4),
        "mean_aspect_macro_f1": round(float(np.mean(per_aspect_f1)), 4),
    }


def evaluate_spam(predict, items: list[dict[str, Any]]) -> dict[str, Any]:
    """`predict(text, rating) -> bool`."""
    y = [it["spam"] for it in items]
    p = [bool(predict(it["text"], it["rating"])) for it in items]
    return {
        "n": len(items),
        "precision": round(float(precision_score(y, p, zero_division=0)), 4),
        "recall": round(float(recall_score(y, p, zero_division=0)), 4),
        "f1": round(float(f1_score(y, p, zero_division=0)), 4),
        "errors": [
            {"text": it["text"], "expected_spam": y[i], "predicted_spam": p[i]}
            for i, it in enumerate(items)
            if y[i] != p[i]
        ],
    }


def benchmark_table(results: dict[str, dict[str, dict[str, Any]]]) -> pd.DataFrame:
    """Flatten {set: {system: metrics}} into rows for CSV."""
    rows = []
    for set_name, systems in results.items():
        for system, m in systems.items():
            rows.append({"set": set_name, "system": system, **{k: v for k, v in m.items() if not isinstance(v, (dict, list))}})
    return pd.DataFrame(rows)
