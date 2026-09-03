from __future__ import annotations

import re
import unicodedata


class UrduLishTranscriptNormalizer:
    """Fast deterministic Urdu-script -> Sara-friendly UrduLish normalizer.

    Deepgram's Urdu model correctly returns Urdu script. Sara's deterministic
    NLU is intentionally optimized for Roman Urdu / English schema language,
    so this layer normalizes common conversational + real-estate vocabulary
    without adding another LLM/network call.

    It does NOT invent property facts. It only normalizes language.
    Unknown Urdu words are preserved rather than guessed.
    """

    _PHRASES = (
        # Locations / proper nouns first (longest/specific first).
        ("اسلام آباد", "Islamabad"),
        ("بحریہ ٹاؤن", "Bahria Town"),
        ("ڈی ایچ اے", "DHA"),
        ("ڈی۔ایچ۔اے", "DHA"),
        ("گلبرگ تھری", "Gulberg III"),
        ("گلبرگ", "Gulberg"),
        ("لاہور", "Lahore"),
        ("کراچی", "Karachi"),
        ("گلشنِ اقبال", "Gulshan-e-Iqbal"),
        ("گلشن اقبال", "Gulshan-e-Iqbal"),
        ("گلشن ای اقبال", "Gulshan-e-Iqbal"),

        # Additional location aliases.
        # Language normalization only; Day-2/PostgreSQL validates existence.
        ("ماڈل ٹاؤن", "Model Town"),
        ("کلفٹن", "Clifton"),
        ("ڈیفنس", "DHA"),
        ("دی ایچ اے", "DHA"),
        ("بحریہ", "Bahria Town"),

        # Common conversation phrases.
        ("کے لیے", "ke liye"),
        ("کیلئے", "ke liye"),
        ("دیکھ رہی ہوں", "dekh rahi hoon"),
        ("دیکھ رہا ہوں", "dekh raha hoon"),
        ("دیکھنا چاہتی ہوں", "dekhna chahti hoon"),
        ("دیکھنا چاہتا ہوں", "dekhna chahta hoon"),
        ("مجھے چاہیے", "mujhe chahiye"),
        ("مجھے چاہیئے", "mujhe chahiye"),
        ("کوئی بھی", "koi bhi"),
        ("اور آپشنز", "aur options"),
        ("اور آپشن", "aur option"),
        ("آپشنز", "options"),
        ("آپشن", "option"),
        ("اس سے سستی", "us se sasti"),
        ("اس سے سستا", "us se sasta"),
        ("بجٹ فلیکسبل", "budget flexible"),
        ("بجٹ فلیکسیبل", "budget flexible"),
        ("ایریا فلیکسبل", "area flexible"),
        ("ایریا فلیکسیبل", "area flexible"),

        # Correction / conversational phrases seen in live Urdu STT.
        ("نہیں پوچھنا تھا", "nahi poochna tha"),
        ("نہیں پوچھنا", "nahi poochna"),
        ("پوچھنا تھا", "poochna tha"),
        ("دکھا سکتے ہو", "dikha sakte ho"),
        ("دکھا سکتی ہو", "dikha sakti ho"),

        # Voice/STT aliases for verified property fact questions.
        ("ایجنٹ کا نام", "agent ka naam"),
        ("اے جنٹ کا نام", "agent ka naam"),
        ("اے جنٹ", "agent"),
        ("ایجنٹ", "agent"),
        ("انڈر کنسٹرکشن", "under construction"),
        ("پراپرٹی اسٹیٹس", "property status"),
        ("کنسٹرکشن اسٹیٹس", "construction status"),
        ("ایلیویٹر", "elevator"),
        ("سکیورٹی", "security"),
        ("پرووائڈ کرتے", "provide karte"),
        ("پرووائڈ کرتی", "provide karti"),
        ("پرووائڈ کرتا", "provide karta"),
        ("پرووائڈ", "provide"),
        ("ہاؤس", "house"),
        ("ریڈی", "ready"),
        ("اپشنز", "options"),
        ("اپشن", "option"),
        ("اویلیبل", "available"),
        ("نیڑبائے", "nearby"),
        ("نیڑبائی", "nearby"),
        ("دکھاؤ", "dikhao"),
        ("دکھاو", "dikhao"),

        # Natural fact-follow-up phrases heard in UrduLish voice turns.
        ("کون سی ایمینیٹیز", "konsi amenities"),
        ("کونسی ایمینیٹیز", "konsi amenities"),
        ("کون سی امینیٹیز", "konsi amenities"),
        ("کونسی امینیٹیز", "konsi amenities"),
        ("نیئر بائے اسکولز", "nearby schools"),
        ("نیئر بائے اسکول", "nearby school"),
        ("نیئر بائی اسکولز", "nearby schools"),
        ("نیئر بائی اسکول", "nearby school"),
        ("نیئر بائے ہاسپٹلز", "nearby hospitals"),
        ("نیئر بائے ہاسپٹل", "nearby hospital"),
        ("نیئر بائی ہاسپٹلز", "nearby hospitals"),
        ("نیئر بائی ہاسپٹل", "nearby hospital"),
        ("اس کے نیئر بائے", "is ke nearby"),
        ("اس کے نیئر بائی", "is ke nearby"),
        ("اس میں", "is mein"),

        # Booking / workflow / range phrases.
        ("کرائے پر", "rent par"),
        ("سرمایہ کاری", "investment"),
        ("کرایہ آمدنی", "rental income"),
        ("زیادہ سے زیادہ", "maximum"),
        ("کے اندر", "ke andar"),
        ("سے زیادہ", "se zyada"),
        ("سے کم", "se kam"),
        ("دکھا دیں", "dikha dein"),
        ("دکھا دو", "dikha do"),
        ("بتا دو", "bata do"),
        ("دے دیں", "de dein"),
        ("دے دو", "de do"),
        ("کر دیں", "kar dein"),
        ("کر دو", "kar do"),

        # Common multi-word / spelling variants.
        ("سیکیورٹی", "security"),
        ("فل پیمنٹ", "full payment"),
        ("باتھ روم", "bathroom"),
        ("واش روم", "bathroom"),
        ("شو روم", "showroom"),
        ("مربع فٹ", "sqft"),

        # Real-estate / schema vocabulary.
        ("تین بیڈ روم", "3 bedroom"),
        ("دو بیڈ روم", "2 bedroom"),
        ("چار بیڈ روم", "4 bedroom"),
        ("پانچ بیڈ روم", "5 bedroom"),

        # English number words often returned phonetically in Urdu script.
        ("فیز سکس", "Phase 6"),
        ("فیز فائیو", "Phase 5"),
        ("فیز فور", "Phase 4"),
        ("فیز تھری", "Phase 3"),
        ("فیز ٹو", "Phase 2"),
        ("فیز ون", "Phase 1"),
        ("فیز ایٹ", "Phase 8"),
        ("فیز سیون", "Phase 7"),
        ("فیز نائن", "Phase 9"),
        ("فیز ٹین", "Phase 10"),

        ("بیڈ روم", "bedroom"),
        ("بیڈروم", "bedroom"),
        ("اپارٹمنٹ", "apartment"),
        ("اپارٹمینٹ", "apartment"),
        ("فلیٹ", "flat"),
        ("پراپرٹی", "property"),
        ("پروپرٹی", "property"),
        ("پرچیز", "purchase"),
        ("پرچیس", "purchase"),
        ("پرچیس", "purchase"),
        ("پرچیزز", "purchase"),
        ("خریدنے", "purchase"),
        ("خریدنا", "purchase"),
        ("کرایے", "rent"),
        ("کرایہ", "rent"),
        ("رینٹ", "rent"),
        ("بجٹ", "budget"),
        ("کروڑ", "crore"),
        ("لاکھ", "lakh"),
        ("فیز", "Phase"),
        ("سیکٹر", "Sector"),
        ("بلاک", "Block"),
        ("گھر", "house"),
        ("مکان", "house"),
        ("پلاٹ", "plot"),
        ("آفس", "office"),
        ("دفتر", "office"),
        ("شاپ", "shop"),
        ("دکان", "shop"),
        ("جم", "gym"),
        ("پارکنگ", "parking"),
        ("ایمینیٹیز", "amenities"),
        ("امینیٹیز", "amenities"),
        ("امینٹیز", "amenities"),
        ("ایمینیٹی", "amenity"),
        ("امینیٹی", "amenity"),
        ("اسکولز", "schools"),
        ("اسکول", "school"),
        ("سکولز", "schools"),
        ("سکول", "school"),
        ("ہاسپٹلز", "hospitals"),
        ("ہاسپٹل", "hospital"),
        ("ہسپٹلز", "hospitals"),
        ("ہسپٹل", "hospital"),
        ("ہسپتال", "hospital"),
        ("نیئر بائے", "nearby"),
        ("نیئر بائی", "nearby"),
        ("فلیکسیبل", "flexible"),
        ("ڈیویلپر", "developer"),
        ("انویسٹمنٹ", "investment"),
        ("بلڈر", "builder"),
        ("مینٹیننس", "maintenance"),
        ("ڈویلپر", "developer"),
        ("قیمت", "price"),
        ("مہنگی", "mehngi"),
        ("مہنگا", "mehnga"),
        ("سستی", "sasti"),
        ("سستا", "sasta"),
        ("فلیکسبل", "flexible"),
    )

    _WORDS = {
        "مجھے": "mujhe",
        "میرا": "mera",
        "میری": "meri",
        "میرے": "mere",
        "آپ": "aap",
        "اس": "is",
        "یہ": "ye",
        "کون": "kon",
        "سی": "si",
        "کونسی": "konsi",
        "ایشو": "issue",
        "مسئلہ": "masla",
        "مسلا": "masla",
        "کچھ": "kuch",
        "بھی": "bhi",
        "کوئی": "koi",
        "بجٹ": "budget",
        "چھوڑا": "choro",
        "چھوڑو": "choro",
        "وہ": "woh",
        "ہی": "hi",
        "نہیں": "nahi",
        "نہيں": "nahi",
        "پوچھنا": "poochna",
        "تھا": "tha",
        "تھی": "thi",
        "تم": "tum",
        "دکھا": "dikha",
        "سکتے": "sakte",
        "سکتی": "sakti",
        "ہو": "ho",
        "پرائسز": "prices",
        "پرائس": "price",
        "دوری": "doori",

        # Search / routing / comparison.
        "کتنا": "kitna",
        "کتنی": "kitni",
        "کتنے": "kitne",
        "کب": "kab",
        "کیوں": "kyun",
        "کیسے": "kaise",
        "کیسا": "kaisa",
        "کونسا": "kaunsa",
        "والا": "wala",
        "والی": "wali",
        "دوسرا": "doosra",
        "دوسری": "doosri",
        "دوسرے": "doosre",
        "دستیاب": "available",
        "موجود": "mojood",
        "خالی": "khali",
        "سرچ": "search",
        "تلاش": "talash",
        "ڈھونڈ": "dhoond",

        # Property / purpose.
        "بنگلہ": "bungalow",
        "بنگلا": "bungalow",
        "کوٹھی": "kothi",
        "پورشن": "portion",
        "زمین": "zameen",
        "کمرشل": "commercial",
        "پلازہ": "plaza",
        "خرید": "purchase",
        "لینا": "lena",
        "لینی": "leni",
        "بیچنا": "bechna",
        "فروخت": "sale",
        "سرمایہ": "investment",
        "منافع": "munafa",
        "ریٹرن": "return",

        # Money / size / rooms.
        "ہزار": "thousand",
        "روپے": "rupees",
        "ریٹ": "rate",
        "مرلہ": "marla",
        "مرلے": "marla",
        "کنال": "kanal",
        "گز": "sq yd",
        "کمرہ": "kamra",
        "کمرے": "kamre",
        "باتھ روم": "bathroom",
        "واش روم": "bathroom",
        "منزل": "manzil",

        # Amenities / nearby.
        "پارک": "park",
        "مسجد": "masjid",
        "لفٹ": "lift",
        "جنریٹر": "generator",
        "سولر": "solar",
        "بجلی": "bijli",
        "پانی": "pani",
        "فرنشڈ": "furnished",
        "سوسائٹی": "society",
        "علاقہ": "area",
        "ایریا": "area",

        # Booking / scheduling.
        "اپوائنٹمنٹ": "appointment",
        "اپائنٹمنٹ": "appointment",
        "ملاقات": "mulaqat",
        "وزٹ": "visit",
        "دورہ": "visit",
        "بک": "book",
        "بکنگ": "booking",
        "شیڈول": "schedule",
        "تبدیل": "change",
        "بدل": "badal",
        "بدلنا": "badalna",
        "کینسل": "cancel",
        "منسوخ": "cancel",

        # Time.
        "کل": "kal",
        "آج": "aaj",
        "پرسوں": "parso",
        "بجے": "baje",
        "صبح": "subah",
        "شام": "shaam",
        "دوپہر": "dopahar",
        "رات": "raat",
        "وقت": "waqt",
        "ٹائم": "time",

        # Trust / objections.
        "بھروسہ": "bharosa",
        "اعتبار": "trust",
        "دھوکہ": "dhoka",
        "جعلی": "fake",
        "قانونی": "legal",
        "کاغذات": "kagzat",
        "دستاویز": "documents",
        "رجسٹری": "registry",
        "قبضہ": "possession",
        "قسط": "installment",
        "قسطیں": "installments",
        "بینک": "bank",
        "کمیشن": "commission",
        "ٹیکس": "tax",
        "فیس": "fee",
        "شکایت": "complaint",
        "مینیجر": "manager",
        "نمائندہ": "agent",

        "نام": "naam",
        "کہہ": "keh",
        "کہاں": "kahan",
        "کرتے": "karte",
        "کرتی": "karti",
        "کرتا": "karta",
        "کیا": "kya",
        "ہے": "hai",
        "ہیں": "hain",
        "ہوں": "hoon",
        "ہو": "ho",
        "چاہیے": "chahiye",
        "چاہیئے": "chahiye",
        "چاہتی": "chahti",
        "چاہتا": "chahta",
        "دیکھ": "dekh",
        "رہی": "rahi",
        "رہا": "raha",
        "لیے": "liye",
        "لئے": "liye",
        "کے": "ke",
        "کی": "ki",
        "کا": "ka",
        "کو": "ko",
        "اور": "aur",
        "یا": "ya",
        "نہیں": "nahi",
        "نہی": "nahi",
        "کوئی": "koi",
        "بھی": "bhi",
        "تک": "tak",
        "تقریباً": "around",
        "تقریبا": "around",
        "زیادہ": "zyada",
        "کم": "kam",
        "اچھا": "acha",
        "اچھی": "achi",
        "چلےگا": "chalega",
        "چلےگی": "chalegi",
        "تین": "3",
        "دو": "2",
        "چار": "4",
        "پانچ": "5",
        "ایک": "1",
        "چھ": "6",
        "چھے": "6",
        "سات": "7",
        "آٹھ": "8",
        "نو": "9",
        "دس": "10",
        "گیارہ": "11",
        "بارہ": "12",
        "تیرہ": "13",
        "چودہ": "14",
        "پندرہ": "15",
        "بیس": "20",
        "پچیس": "25",
        "تیس": "30",
        "چالیس": "40",
        "پچاس": "50",
        "ساٹھ": "60",
        "ستر": "70",
        "اسی": "80",
        "نوے": "90",
        "سو": "100",
        "ڈیڑھ": "1.5",
        "ڈھائی": "2.5",

        # Phonetic English numerals commonly produced by Urdu STT.
        "ون": "1",
        "ٹو": "2",
        "تھری": "3",
        "فور": "4",
        "فائیو": "5",
        "فایو": "5",
        "سکس": "6",
        "سیون": "7",
        "ایٹ": "8",
        "نائن": "9",
        "ٹین": "10",
    }

    _URDU_RE = re.compile(r"[\u0600-\u06FF]")
    _DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
    _SPACES_RE = re.compile(r"\s+")

    _DEVANAGARI_PHRASES = (
        ("डी एच ए", "DHA"),
        ("डीएचए", "DHA"),
        ("अस्सलाम ओ अलैकुम", "Assalam-o-Alaikum"),
        ("अस्सलाम वालेकुम", "Assalam-o-Alaikum"),
        ("प्रॉपर्टी", "property"),
        ("प्रोपर्टी", "property"),
        ("अपार्टमेंट", "apartment"),
        ("खरीदना", "purchase"),
        ("खरीदनी", "purchase"),
        ("किराये", "rent"),
        ("किराए", "rent"),
        ("चाहिए", "chahiye"),
        ("करोड़", "crore"),
        ("करोड", "crore"),
        ("बजट", "budget"),
        ("लाख", "lakh"),
        ("फ्लैट", "flat"),
        ("प्लॉट", "plot"),
        ("फेज़", "Phase"),
        ("फेज", "Phase"),
        ("सिक्स", "six"),
        ("टेन", "ten"),
        ("मुझे", "mujhe"),
        ("यार", "yaar"),
        ("में", "mein"),
        ("तीन", "teen"),
        ("चार", "char"),
        ("पाँच", "paanch"),
        ("पांच", "paanch"),
        ("छह", "six"),
        ("दो", "do"),
        ("एक", "ek"),
        ("घर", "house"),
        ("हैं", "hain"),
        ("है", "hai"),
    )

    def normalize(self, text: str) -> str:
        if not isinstance(text, str):
            return ""

        value = unicodedata.normalize("NFKC", text)
        value = (
            value.replace("\u200c", " ")
            .replace("\u200d", " ")
            .replace("\ufeff", "")
            .replace("۔", ".")
            .replace("،", ",")
            .replace("؟", "?")
            .replace("؛", ";")
        )
        value = self._SPACES_RE.sub(" ", value).strip()
        value = self._normalize_devanagari(value)
        value = self._normalize_roman_urdulish(value)
        if not value or not self._URDU_RE.search(value):
            return value

        # Urdu fractional number construction:
        #   ساڑھے تین کروڑ -> 3.5 crore
        #   ساڑھے چار لاکھ -> 4.5 lakh
        # This must run before token-level replacement.
        half_number_words = {
            "ایک": 1,
            "دو": 2,
            "تین": 3,
            "چار": 4,
            "پانچ": 5,
            "چھ": 6,
            "چھے": 6,
            "سات": 7,
            "آٹھ": 8,
            "نو": 9,
            "دس": 10,
            "گیارہ": 11,
            "بارہ": 12,
            "تیرہ": 13,
            "چودہ": 14,
            "پندرہ": 15,
            "بیس": 20,
            "پچیس": 25,
            "تیس": 30,
            "چالیس": 40,
            "پچاس": 50,
            "ساٹھ": 60,
            "ستر": 70,
            "اسی": 80,
            "نوے": 90,
            "سو": 100,
        }

        def _replace_saarhay(match: re.Match[str]) -> str:
            number_word = match.group(1)
            number = half_number_words.get(number_word)
            if number is None:
                return match.group(0)
            return f"{number + 0.5:g}"

        value = re.sub(
            r"ساڑھے\s+("
            + "|".join(
                sorted(
                    (
                        re.escape(word)
                        for word in half_number_words
                    ),
                    key=len,
                    reverse=True,
                )
            )
            + r")(?=\s|$)",
            _replace_saarhay,
            value,
        )

        # Urdu "میں" is ambiguous: at sentence start it normally means "I";
        # elsewhere in property/location phrases it normally means "in".
        value = re.sub(r"^\s*میں(?=\s|$)", "main", value)

        # Replace longer phrases before shorter overlapping aliases.
        for source, target in sorted(
            self._PHRASES,
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            value = value.replace(source, target)

        # Remaining "میں" is overwhelmingly the location relation "mein"
        # in Sara's property-search domain.
        value = value.replace("میں", "mein")

        tokens = value.split()
        normalized_tokens: list[str] = []

        for token in tokens:
            prefix, core, suffix = self._split_punctuation(token)
            replacement = self._WORDS.get(core, core)
            normalized_tokens.append(prefix + replacement + suffix)

        value = " ".join(normalized_tokens)
        value = self._SPACES_RE.sub(" ", value).strip()

        # Small mixed-script cleanup rules.
        value = re.sub(
            r"\bproperty\s+chahiye\b",
            "property chahiye",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\bpurchase\s+ke\s+liye\b",
            "purchase ke liye",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\bkon\s+si\b",
            "konsi",
            value,
            flags=re.IGNORECASE,
        )
        # Normalize common number contexts without inventing values.
        value = re.sub(
            r"\b(\d+(?:\.\d+)?)\s+bed\s*room\b",
            r"\1 bedroom",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\bphase\s+(\d+(?:\.\d+)?)\b",
            r"Phase \1",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"\b(\d+)\.5\s+baje\b",
            r"\1:30 baje",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"\bkaun\s+si\b",
            "kaunsi",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\bkon\s+sa\b",
            "kaunsa",
            value,
            flags=re.IGNORECASE,
        )

        value = self._normalize_roman_urdulish(value)

        return value

    @classmethod
    def _normalize_roman_urdulish(cls, value: str) -> str:
        """Repair conservative Roman-Urdu forms emitted by multilingual STT."""

        # Deepgram commonly renders the location relation "mein" as English
        # "main". Limit the repair to known location-shaped phrases so the
        # first-person Urdu word "main" is not changed globally.
        value = re.sub(
            r"\b(Lahore|Karachi|Islamabad|Bahria\s+Town|Gulberg|"
            r"DHA(?:\s+Phase\s+\d+)?)\s+main\b",
            r"\1 mein",
            value,
            flags=re.IGNORECASE,
        )

        # In Roman UrduLish results, sentence-final "hai" is sometimes decoded
        # as the English homophone "high". Do not rewrite genuine phrases such
        # as "high ROI" or "high-rise".
        value = re.sub(
            r"\bhigh\b(?=\s*[.!?,;:]|\s*$)",
            "hai",
            value,
            flags=re.IGNORECASE,
        )

        # Observed Nova-3 multilingual confusion for "DHA Phase 6". Keep the
        # repair anchored to DHA so genuine uses of "ten six" are untouched.
        value = re.sub(
            r"\bDHA\s+(?:ten|10)\s+(?:six|6)\b",
            "DHA Phase 6",
            value,
            flags=re.IGNORECASE,
        )

        phase_numbers = {
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9",
            "ten": "10",
        }

        def replace_phase(match: re.Match[str]) -> str:
            raw_number = match.group(1).casefold()
            return f"DHA Phase {phase_numbers.get(raw_number, raw_number)}"

        value = re.sub(
            r"\bDHA\s+(?:phase|face|faze)\s+"
            r"(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b",
            replace_phase,
            value,
            flags=re.IGNORECASE,
        )

        number_words = {
            "aik": "1",
            "ek": "1",
            "do": "2",
            "teen": "3",
            "char": "4",
            "chaar": "4",
            "panch": "5",
            "paanch": "5",
            "chay": "6",
            "che": "6",
            "saat": "7",
            "aath": "8",
            "nau": "9",
            "das": "10",
            "bees": "20",
            "pachees": "25",
            "tees": "30",
        }
        pattern = (
            r"\b("
            + "|".join(
                sorted(number_words, key=len, reverse=True)
            )
            + r")\s+(crore|lakh|lac|marla|kanal|bedrooms?)\b"
        )

        def replace_number(match: re.Match[str]) -> str:
            return (
                f"{number_words[match.group(1).casefold()]} "
                f"{match.group(2)}"
            )

        value = re.sub(
            pattern,
            replace_number,
            value,
            flags=re.IGNORECASE,
        )
        return cls._SPACES_RE.sub(" ", value).strip()

    @classmethod
    def _normalize_devanagari(cls, value: str) -> str:
        """Convert Deepgram Hindi-script output to display-safe Roman text."""

        if not cls._DEVANAGARI_RE.search(value):
            return value

        for source, target in sorted(
            cls._DEVANAGARI_PHRASES,
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            value = value.replace(source, target)

        if not cls._DEVANAGARI_RE.search(value):
            return value

        independent_vowels = {
            "अ": "a", "आ": "aa", "इ": "i", "ई": "ee",
            "उ": "u", "ऊ": "oo", "ऋ": "ri", "ए": "e",
            "ऐ": "ai", "ओ": "o", "औ": "au",
        }
        consonants = {
            "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
            "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
            "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
            "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
            "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
            "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
            "ष": "sh", "स": "s", "ह": "h", "क़": "q", "ख़": "kh",
            "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f",
        }
        matras = {
            "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo",
            "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
            "ॉ": "o", "ॅ": "e",
        }
        digits = str.maketrans("०१२३४५६७८९", "0123456789")
        result: list[str] = []

        for character in value.translate(digits):
            if character in consonants:
                result.append(consonants[character] + "a")
            elif character in matras:
                if result and result[-1].endswith("a"):
                    result[-1] = result[-1][:-1]
                result.append(matras[character])
            elif character == "्":
                if result and result[-1].endswith("a"):
                    result[-1] = result[-1][:-1]
            elif character in independent_vowels:
                result.append(independent_vowels[character])
            elif character in {"ं", "ँ"}:
                result.append("n")
            elif character == "ः":
                result.append("h")
            elif character == "़":
                continue
            elif character in {"।", "॥"}:
                result.append(".")
            elif not cls._DEVANAGARI_RE.match(character):
                result.append(character)

        return cls._SPACES_RE.sub(" ", "".join(result)).strip()

    @staticmethod
    def _split_punctuation(token: str) -> tuple[str, str, str]:
        match = re.match(
            r"^([^\w\u0600-\u06FF]*)(.*?)([^\w\u0600-\u06FF]*)$",
            token,
            flags=re.UNICODE,
        )
        if not match:
            return "", token, ""
        return match.group(1), match.group(2), match.group(3)


_default_normalizer = UrduLishTranscriptNormalizer()


def normalize_transcript(text: str) -> str:
    return _default_normalizer.normalize(text)
