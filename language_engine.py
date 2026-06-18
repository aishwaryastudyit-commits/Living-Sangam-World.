"""
language_engine.py - multilingual learning and accuracy helpers.

Tamil stays the source of truth. Other languages are learner-facing bridges:
captions, narration support lines, and UI labels.
"""
from __future__ import annotations

import copy
import json
import os
from functools import lru_cache
from typing import Any

from schemas import (
    MOOD_TAMIL,
    THINAI_MEANING,
    THINAI_TAMIL,
    Mood,
    Poem,
    PoemAnalysis,
    SceneFrame,
    SubtitleEntry,
    Thinai,
)
# Inside language_engine.py
import streamlit as st

@st.cache_data
def language_choices() -> list[tuple[str, str]]:
    return [
        ("en", "English"),
        ("ta", "Tamil (தமிழ்)"),
        ("fr", "French (Français)"),
        ("hi", "Hindi (हिन्दी)"),
        ("or", "Odia (ଓଡ଼ିଆ)") # Matching your localization dictionary!
    ]
LANGUAGE_OPTIONS: dict[str, str] = {
    "ta": "Tamil",
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "si": "Sinhala",
    "ar": "Arabic",
    "zh-CN": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
}

GTTS_LANGUAGE_ALIASES = {
    "zh-CN": "zh-CN",
}

TAMIL_THINAI_NAMES: dict[Thinai, str] = {
    Thinai.KURINJI: "குறிஞ்சி",
    Thinai.MULLAI: "முல்லை",
    Thinai.MARUTHAM: "மருதம்",
    Thinai.NEYTAL: "நெய்தல்",
    Thinai.PALAI: "பாலை",
    Thinai.UNKNOWN: "திணை",
}

TAMIL_TERMS = {
    "thinai": "திணை",
    "akam": "அகம்",
    "puram": "புறம்",
    "pulavar": "புலவர்",
    "sangam": "சங்கம்",
}

THINAI_HINTS: dict[Thinai, tuple[str, ...]] = {
    Thinai.KURINJI: ("mountain", "hill", "kurinji", "waterfall", "union", "secret meeting"),
    Thinai.MULLAI: ("forest", "mullai", "jasmine", "waiting", "return", "monsoon"),
    Thinai.MARUTHAM: ("field", "paddy", "river", "marutham", "quarrel", "infidelity"),
    Thinai.NEYTAL: ("sea", "shore", "wave", "boat", "neytal", "separation"),
    Thinai.PALAI: ("desert", "wilderness", "journey", "palai", "hardship", "bandit"),
}

FALLBACK_TERMS: dict[str, dict[str, str]] = {
    "en": {
        "thinai": "landscape-emotion tradition",
        "akam": "inner life or love poetry",
        "puram": "public life or heroic poetry",
        "pulavar": "poet-scholar",
    },
    "hi": {
        "thinai": "भूमि-दृश्य और भावना की परंपरा",
        "akam": "अंतरंग प्रेम काव्य",
        "puram": "वीरता और सार्वजनिक जीवन का काव्य",
        "pulavar": "कवि-विद्वान",
    },
    "fr": {
        "thinai": "tradition reliant paysage et emotion",
        "akam": "poesie de l'interieur et de l'amour",
        "puram": "poesie de la vie publique et heroique",
        "pulavar": "poete erudit",
    },
    "es": {
        "thinai": "tradicion de paisaje y emocion",
        "akam": "poesia interior o amorosa",
        "puram": "poesia publica o heroica",
        "pulavar": "poeta sabio",
    },
}

LANGUAGE_BRIDGES: dict[str, dict[str, str]] = {
    "en": {
        "learner_prefix": "For learners in English",
        "thinai_intro": "Thinai means a landscape-emotion tradition",
        "remember": "Remember the Tamil word",
        "place_feeling": "it names both place and feeling",
    },
    "hi": {
        "learner_prefix": "हिंदी सीखने वालों के लिए",
        "thinai_intro": "तिणै का अर्थ है भूमि-दृश्य और भाव की संगम परंपरा",
        "remember": "तमिल शब्द याद रखिए",
        "place_feeling": "यह स्थान और भावना दोनों को एक साथ नाम देता है",
    },
    "te": {
        "learner_prefix": "తెలుగు నేర్చుకునేవారికి",
        "thinai_intro": "తిణై అంటే భూభాగం-భావం కలిసే సంగం సంప్రదాయం",
        "remember": "తమిళ పదాన్ని గుర్తుంచుకోండి",
        "place_feeling": "ఇది స్థలాన్నీ భావాన్నీ ఒకే పేరుతో సూచిస్తుంది",
    },
    "fr": {
        "learner_prefix": "Pour les apprenants en francais",
        "thinai_intro": "Thinai relie paysage et emotion dans la tradition Sangam",
        "remember": "Gardez en memoire le mot tamoul",
        "place_feeling": "il nomme a la fois le lieu et le sentiment",
    },
    "es": {
        "learner_prefix": "Para estudiantes en espanol",
        "thinai_intro": "Thinai une paisaje y emocion en la tradicion Sangam",
        "remember": "Recuerda la palabra tamil",
        "place_feeling": "nombra a la vez el lugar y el sentimiento",
    },
}

PULAVAR_OPENINGS: dict[str, str] = {
    "ta": "ஒரு புலவர் கேட்பதுபோல் கேளுங்கள்: மெதுவாக; மனம் பதிலளிக்கும் முன் நிலம் முதலில் பேசுகிறது.",
    "ml": "ഒരു പുലവർ കേൾക്കുന്നതുപോലെ കേൾക്കൂ: പതുക്കെ; ഹൃദയം മറുപടി പറയുന്നതിന് മുമ്പ് ഭൂമി ആദ്യം സംസാരിക്കുന്നു.",
    "kn": "ಒಬ್ಬ ಪುಲವರನಂತೆ ಆಲಿಸಿ: ನಿಧಾನವಾಗಿ; ಆಲಿಸುವ ಹೃದಯ ಉತ್ತರಿಸುವ ಮೊದಲು ಭೂಮಿ ಮೊದಲು ಮಾತನಾಡುತ್ತದೆ.",
    "te": "ఒక పులవరిలా వినండి: నెమ్మదిగా; హృదయం స్పందించే ముందు నేల ముందుగా మాట్లాడుతుంది.",
    "bn": "একজন পুলভারের মতো শুনুন: ধীরে; হৃদয় উত্তর দেওয়ার আগে ভূমি প্রথমে কথা বলে।",
    "mr": "एका पुलवरप्रमाणे ऐका: हळूहळू; मन उत्तर देण्यापूर्वी भूमी आधी बोलते.",
    "gu": "એक पुलवर जेम सांभळो: धीमे धीमे; हृदय जवाब आपे ते पहलां धरती पहले बोले छे.",
    "pa": "ਇੱਕ ਪੁਲਵਰ ਵਾਂਗ ਸੁਣੋ: ਹੌਲੀ ਹੌਲੀ; ਦਿਲ ਜਵਾਬ ਦੇਣ ਤੋਂ ਪਹਿਲਾਂ ਧਰਤੀ ਪਹਿਲਾਂ ਬੋਲਦੀ ਹੈ।",
    "or": "ଜଣେ ପੁଲଭରଙ୍କ ପରି ଶୁଣନ୍ତୁ: ଧୀରେ ଧୀରେ; ହୃଦୟ ଉତ୍ତର ଦେବା ପୂର୍ବରୁ ଭୂମି ପ୍ରଥମେ କଥା କହେ।",
    "en": "Listen as a Pulavar would: slowly, with the land speaking before the heart answers.",
    "hi": "एक पुलवर की तरह सुनिए: धीरे और गंभीर ढंग से; पहले भूमि बोलती है, फिर मन का भाव उत्तर देता है.",
    "fr": "Ecoutez comme un Pulavar: lentement, avec la terre qui parle avant que le coeur reponde.",
    "es": "Escucha como un Pulavar: despacio, dejando que la tierra hable antes de que responda el corazon.",
}

SCENE_PHRASES: dict[str, dict[str, str]] = {
    "ta": {
        "scene": "காட்சி",
        "behold": "பாருங்கள்",
        "meaning": "இந்தக் காட்சியில், பாடலின் உணர்வு அமைதியாக ஒன்றுகூடுகிறது.",
        "setting": "இந்த நிலம்",
        "closing": "நாவிலே தங்கியிருக்கும் ஒரு செய்யுளைப் போல, இந்தக் காட்சி அங்கேயே நிலைக்கிறது.",
    },
    "ml": {
        "scene": "ദൃശ്യം",
        "behold": "നോക്കൂ",
        "meaning": "ഈ ദൃശ്യത്തിൽ, കവിതയുടെ വികാരം നിശ്ശബ്ദമായി ഒത്തുചേരുന്നു.",
        "setting": "ഈ ഭൂമി",
        "closing": "നാവിൽ തങ്ങി നിൽക്കുന്ന ഒരു പദ്യത്തെപ്പോലെ, ഈ ദൃശ്യം അവിടെ വിശ്രമിക്കുന്നു.",
    },
    "kn": {
        "scene": "ದೃಶ್ಯ",
        "behold": "ನೋಡಿ",
        "meaning": "ಈ ದೃಶ್ಯದಲ್ಲಿ, ಕವಿತೆಯ ಭಾವನೆ ಶಾಂತವಾಗಿ ಒಂದಾಗುತ್ತದೆ.",
        "setting": "ಈ ನೆಲ",
        "closing": "ನಾಲಿಗೆಯ ಮೇಲೆ ಉಳಿದಿರುವ ಒಂದು ಪದ್ಯದಂತೆ, ಈ ದೃಶ್ಯ ಅಲ್ಲಿಯೇ ನೆಲೆಸುತ್ತದೆ.",
    },
    "te": {
        "scene": "దృశ్యం",
        "behold": "చూడండి",
        "meaning": "ఈ దృశ్యంలో, కవిత యొక్క భావం నిశ్శబ్దంగా ఒకటవుతుంది.",
        "setting": "ఈ నేల",
        "closing": "నాలుకపై నిలిచిన ఒక పద్యంలా, ఈ దృశ్యం అక్కడే విశ్రాంతి తీసుకుంటుంది.",
    },
    "bn": {
        "scene": "দৃশ্য",
        "behold": "দেখুন",
        "meaning": "এই দৃশ্যে কবিতার অনুভূতি নীরবে একত্রিত হয়।",
        "setting": "এই ভূমি",
        "closing": "জিভে রয়ে যাওয়া একটি পঙ্‌ক্তির মতো, এই দৃশ্য সেখানেই স্থির থাকে।",
    },
    "mr": {
        "scene": "दृश्य",
        "behold": "पाहा",
        "meaning": "या दृश्यात कवितेची भावना शांतपणे एकवटते.",
        "setting": "ही भूमी",
        "closing": "जिभेवर रेंगाळणाऱ्या एका ओळीप्रमाणे हे दृश्य तिथेच विसावते.",
    },
    "gu": {
        "scene": "દૃશ્ય",
        "behold": "જોવો",
        "meaning": "આ દૃશ્યમાં કવિતાની ભાવના શાંતિથી એકત્રિત થાય છે.",
        "setting": "આ ધરતી",
        "closing": "જીભ પર ટકી રહેલી એક પંક્તિ જેવી, આ દૃશ્ય ત્યાં જ વિરમે છે.",
    },
    "pa": {
        "scene": "ਦ੍ਰਿਸ਼",
        "behold": "ਵੇਖੋ",
        "meaning": "ਇਸ ਦ੍ਰਿਸ਼ ਵਿੱਚ ਕਵਿਤਾ ਦੀ ਭਾਵਨਾ ਚੁੱਪਚਾਪ ਇਕੱਠੀ ਹੁੰਦੀ ਹੈ।",
        "setting": "ਇਹ ਧਰਤੀ",
        "closing": "ਜਿਵੇਂ ਜੀਭ ਉੱਤੇ ਟਿਕੀ ਹੋਈ ਇੱਕ ਪੰਕਤੀ, ਇਹ ਦ੍ਰਿਸ਼ ਉੱਥे ਹੀ ਠਹਿਰ ਜਾਂਦਾ ਹੈ।",
    },
    "or": {
        "scene": "ದୃଶ୍ୟ",
        "behold": "ଦେଖନ୍ତୁ",
        "meaning": "ଏହି ଦୃଶ୍ୟରେ କବିତାର ଭାବନା ନିରବରେ ଏକତ୍ରିତ ହୁଏ।",
        "setting": "ଏହି ଭୂମି",
        "closing": "ଜିଭାରେ ରହିଯାଇଥିବା ଗୋଟିଏ ପଦ୍ୟ ପରି, ଏହି ଦୃଶ୍ୟ ସେଠି ଅବସ୍ଥାନ କରେ।",
    },
    "en": {
        "scene": "Scene",
        "behold": "Behold",
        "meaning": "In this image, the poem's feeling gathers quietly.",
        "setting": "The land is",
        "closing": "The scene rests there, like a verse held on the tongue.",
    },
    "hi": {
        "scene": "दृश्य",
        "behold": "देखिए",
        "meaning": "इस चित्र में कविता का भाव शांत रूप से इकट्ठा होता है.",
        "setting": "यह भूमि है",
        "closing": "दृश्य यहीं ठहर जाता है, जैसे जिह्वा पर ठहरा हुआ एक पद.",
    },
    "fr": {
        "scene": "Scene",
        "behold": "Regardez",
        "meaning": "Dans cette image, le sentiment du poeme se rassemble doucement.",
        "setting": "Le paysage est",
        "closing": "La scene demeure la, comme un vers garde sur la langue.",
    },
    "es": {
        "scene": "Escena",
        "behold": "Mira",
        "meaning": "En esta imagen, el sentimiento del poema se reune en silencio.",
        "setting": "La tierra es",
        "closing": "La escena queda alli, como un verso sostenido en la lengua.",
    },
}

HINDI_SCENE_TITLES: dict[str, str] = {
    "Mountain Opening": "पर्वत का आरंभ",
    "Flowered Slope": "फूलों वाली ढलान",
    "First Meeting": "पहली भेंट",
    "Moonlit Visit": "चांदनी में आगमन",
    "Poetic Echo": "काव्य की प्रतिध्वनि",
    "Forest Dusk": "वन की सांझ",
    "Ayar Settlement": "आयर बस्ती",
    "Waiting Path": "प्रतीक्षा का पथ",
    "Twilight Return": "सांझ की वापसी",
    "Jasmine Rest": "मुल्लै की शांति",
    "Paddy Dawn": "धान के खेतों की सुबह",
    "Lotus Pond": "कमल का तालाब",
    "Village Courtyard": "गांव का आंगन",
    "Domestic Quarrel": "घर का मनमुटाव",
    "Return Home": "घर वापसी",
    "Sugarcane Edge": "गन्ने के खेत का किनारा",
    "Reconciliation": "मिलन और शांति",
    "Seashore Wind": "समुद्र तट की हवा",
    "Waiting Tide": "प्रतीक्षा की लहर",
    "Fishing Boats": "मछुआरों की नावें",
    "Pale Horizon": "फीका क्षितिज",
    "Wave Memory": "लहरों की स्मृति",
    "Dry Road": "सूखा मार्ग",
    "Travel Heat": "यात्रा की गर्मी",
    "Lonely Pause": "एकाकी ठहराव",
    "Distant Figure": "दूर जाता यात्री",
    "Heat Haze": "गर्मी की धुंध",
}

UI_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ta": {
        "Literary Analysis": "இலக்கிய ஆய்வு",
        "Analyzed from image": "படத்திலிருந்து ஆய்வு செய்யப்பட்டது",
        "Poet": "புலவர்",
        "Collection": "தொகை",
        "Period": "காலம்",
        "Thinai": "திணை",
        "Emotion": "உணர்வு",
        "Mood": "மனநிலை",
        "Thurai": "துறை",
        "Speaker": "பேசுவோர்",
        "Listener": "கேட்போர்",
        "Summary": "சுருக்கம்",
        "Learner Guide": "கற்றல் வழிகாட்டி",
        "Sangam Poetics": "சங்கப் பொருள் அமைப்பு",
        "Muthal Porul": "முதற்பொருள்",
        "Time and Place": "காலமும் இடமும்",
        "Landscape": "நிலம்",
        "Season": "பருவம்",
        "Time": "பொழுது",
        "Karu Porul": "கருப்பொருள்",
        "Flora, Fauna and Objects": "மலர், விலங்கு, பொருட்கள்",
        "Uri Porul": "உரிப்பொருள்",
        "Central Emotion or Action": "மைய உணர்வு அல்லது செயல்",
        "Cultural Context": "பண்பாட்டு சூழல்",
        "Literary Devices": "இலக்கிய உத்திகள்",
        "Grammar Notes": "இலக்கணக் குறிப்புகள்",
        "In this poem": "இந்தப் பாடலில்",
        "Word Meanings": "சொற்பொருள்",
        "Characters": "கதாபாத்திரங்கள்",
        "Meaning Breakdown": "பொருள் விளக்கம்",
        "Scene Breakdown": "காட்சி பிரிவு",
        "Scene": "காட்சி",
        "Advanced Details": "மேலும் விவரங்கள்",
        "Environment": "சூழல்",
        "Lighting": "ஒளி",
        "Palette": "நிறத் தொகுப்பு",
        "Image unavailable": "படம் கிடைக்கவில்லை.",
        "Illustration unavailable": "விளக்கப்படம் கிடைக்கவில்லை",
        "Sangam Voice": "சங்கக் குரல்",
        "Narration audio is being prepared for this poem.": "இந்தப் பாடலுக்கான குரல் தயாராகிறது.",
        "Narration audio could not be played here, but the analysis remains available.": "குരலை இங்கே இயக்க முடியவில்லை; ஆய்வு கிடைக்கிறது.",
        "Narration is unavailable for this run.": "இந்த ஓட்டத்தில் குரல் கிடைக்கவில்லை.",
        "Enable narration in the sidebar to hear the poem.": "பாடலைக் கேட்க பக்கப்பட்டியில் குரலை இயக்கவும்.",
        "Ask Pulavar": "புலவரைக் கேளுங்கள்",
        "Ask the ancient scholar anything about Sangam poetry, culture, or this poem.": "சங்கக் கவிதை, பண்பாடு, இந்தப் பாடல் பற்றி புலவரிடம் கேளுங்கள்.",
        "Ask Pulavar a question...": "புலவரிடம் கேள்வி கேளுங்கள்...",
        "Pulavar reflects...": "புலவர் சிந்திக்கிறார்...",
        "Poem source": "பாடல் மூலம்",
        "Type / Paste": "தட்டச்சு / ஒட்டு",
        "Library": "நூலகம்",
        "Camera / Image": "கேமரா / படம்",
        "Enter Sangam poem": "சங்கப் பாடலை உள்ளிடுங்கள்",
        "Paste Tamil or English poem here...": "தமிழ் அல்லது வேறு மொழிப் பாடலை இங்கே ஒட்டுங்கள்...",
        "Select a poem": "பாடலைத் தேர்ந்தெடுக்கவும்",
        "Show Tamil version": "தமிழ் வடிவைக் காட்டு",
        "Poetic Structure": "கவிதை அமைப்பு",
        "Options": "விருப்பங்கள்",
        "Demo judging mode": "டெமோ மதிப்பீட்டு முறை",
        "Learning": "கற்றல்",
        "Narration and subtitle language": "குரல் மற்றும் வசன மொழி",
        "Generate scene images": "காட்சி படங்களை உருவாக்கு",
        "Generate voice narration": "குரல் விளக்கத்தை உருவாக்கு",
        "Generate Experience video": "அனுபவ வீடியோவை உருவாக்கு",
        "Analyze Poem": "பாடலை ஆய்வு செய்",
        "Please enter a poem to analyze.": "ஆய்வு செய்ய ஒரு பாடலை உள்ளிடுங்கள்.",
        "Enter a Sangam poem to begin": "தொடங்க ஒரு சங்கப் பாடலை உள்ளிடுங்கள்",
        "Analysis": "ஆய்வு",
        "Scenes": "காட்சிகள்",
        "Voice": "குரல்",
        "Experience": "அனுபவம்",
        "Ask": "கேள்",
    },
    "ml": {
        "Literary Analysis": "സാഹിത്യ വിശകലനം",
        "Summary": "സംക്ഷേപം",
        "Scene Breakdown": "ദൃശ്യ വിഭജനം",
        "Scene": "ദൃശ്യം",
        "Sangam Voice": "സംഗം ശബ്ദം",
        "Ask Pulavar": "പുലവരിനോട് ചോദിക്കൂ",
        "Poem source": "കവിതയുടെ ഉറവിടം",
        "Type / Paste": "ടൈപ്പ് / ഒട്ടിക്കുക",
        "Library": "ലൈബ്രറി",
        "Camera / Image": "ക്യാമറ / ചിത്രം",
        "Options": "ഓപ്ഷനുകൾ",
        "Learning": "പഠനം",
        "Narration and subtitle language": "വിവരണവും ഉപശീർഷക ഭാഷയും",
        "Generate scene images": "ദൃശ്യ ചിത്രങ്ങൾ സൃഷ്ടിക്കുക",
        "Generate voice narration": "ശബ്ദ വിവരണം സൃഷ്ടിക്കുക",
        "Generate Experience video": "അനുഭവ വീഡിയോ സൃഷ്ടിക്കുക",
        "Analyze Poem": "കവിത വിശകലനം ചെയ്യുക",
        "Analysis": "വിശകലനം",
        "Scenes": "ദൃശ്യങ്ങൾ",
        "Voice": "ശബ്ദം",
        "Experience": "അനുഭവം",
        "Ask": "ചോദിക്കുക",
    },
    "kn": {
        "Literary Analysis": "ಸಾಹಿತ್ಯ ವಿಶ್ಲೇಷಣೆ",
        "Summary": "ಸಾರಾಂಶ",
        "Scene Breakdown": "ದೃಶ್ಯ ವಿಭಾಗ",
        "Scene": "ದೃಶ್ಯ",
        "Sangam Voice": "ಸಂಗಂ ಧ್ವನಿ",
        "Ask Pulavar": "ಪುಲವರನ್ನು ಕೇಳಿ",
        "Poem source": "ಕವನ ಮೂಲ",
        "Type / Paste": "ಬರೆಯಿರಿ / ಅಂಟಿಸಿ",
        "Library": "ಗ್ರಂಥಾಲಯ",
        "Camera / Image": "ಕ್ಯಾಮೆರಾ / ಚಿತ್ರ",
        "Options": "ಆಯ್ಕೆಗಳು",
        "Learning": "ಕಲಿಕೆ",
        "Narration and subtitle language": "ನಿರೂಪಣೆ ಮತ್ತು ಉಪಶೀರ್ಷಿಕೆ ಭಾಷೆ",
        "Generate scene images": "ದೃಶ್ಯ ಚಿತ್ರಗಳನ್ನು ರಚಿಸಿ",
        "Generate voice narration": "ಧ್ವನಿ ನಿರೂಪಣೆ ರಚಿಸಿ",
        "Generate Experience video": "ಅನುಭವ ವೀಡಿಯೊ ರಚಿಸಿ",
        "Analyze Poem": "ಕವನವನ್ನು ವಿಶ್ಲೇಷಿಸಿ",
        "Analysis": "ವಿಶ್ಲೇಷಣೆ",
        "Scenes": "ದೃಶ್ಯಗಳು",
        "Voice": "ಧ್ವನಿ",
        "Experience": "ಅನುಭವಿ",
        "Ask": "ಕೇಳಿ",
    },
    "hi": {
        "Literary Analysis": "साहित्यिक विश्लेषण",
        "Summary": "सारांश",
        "Scene Breakdown": " दृश्य विभाजन",
        "Scene": "दृश्य",
        "Sangam Voice": "संगम आवाज़",
        "Ask Pulavar": "पुलवर से पूछें",
        "Poem source": "कविता स्रोत",
        "Type / Paste": "टाइप / पेस्ट",
        "Library": "पुस्तकालय",
        "Camera / Image": "कैमरा / छवि",
        "Options": "विकल्प",
        "Learning": "अध्ययन",
        "Narration and subtitle language": "वाचन और उपशीर्षक भाषा",
        "Generate scene images": "दृश्य चित्र बनाएं",
        "Generate voice narration": "वाचन बनाएं",
        "Generate Experience video": "अनुभव वीडियो बनाएं",
        "Analyze Poem": "कविता का विश्लेषण करें",
        "Analysis": "विश्लेषण",
        "Scenes": "दृश्य",
        "Voice": "आवाज़",
        "Experience": "अनुभव",
        "Ask": "पूछें",
    },
    "te": {
        "Literary Analysis": "సాహిత్య విశ్లేషణ",
        "Summary": "సారాంశం",
        "Scene Breakdown": "దృశ్య విభజన",
        "Scene": "దృశ్యం",
        "Sangam Voice": "సంగం స్వరం",
        "Ask Pulavar": "పులవర్ని అడగండి",
        "Poem source": "కవిత మూలం",
        "Type / Paste": "టైప్ / పేస్ట్",
        "Library": "గ్రంథాలయం",
        "Camera / Image": "కెమెరా / చిత్రం",
        "Options": "ఎంపಿಕలు",
        "Learning": "అభ్యాసం",
        "Narration and subtitle language": "వివరణ మరియు ఉపశీర్షిక భాష",
        "Generate scene images": "దృశ్య చిత్రాలను సృష్టించండి",
        "Generate voice narration": "వాయిస్ వివరణ సృష్టించండి",
        "Generate Experience video": "అనుభవ వీడియో సృష్టించండి",
        "Analyze Poem": "కవితను విశ్లేషించండి",
        "Analysis": "విశ్లేషణ",
        "Scenes": "దృశ్యాలు",
        "Voice": "స్వరం",
        "Experience": "అనుభవం",
        "Ask": "అడగండి",
    },
    "bn": {
        "Literary Analysis": "সাহিত্য বিশ্লেষণ",
        "Summary": "সারাংশ",
        "Scene Breakdown": "দৃশ্য বিভাজন",
        "Scene": "দৃশ্য",
        "Sangam Voice": "সঙ্গম কণ্ঠ",
        "Ask Pulavar": "পুলভারকে জিজ্ঞাসা করুন",
        "Poem source": "কবিতার উৎস",
        "Type / Paste": "টাইপ / পেস্ট",
        "Library": "লাইব্রেরি",
        "Camera / Image": "ক্যামেরা / ছবি",
        "Options": "বিকল্প",
        "Learning": "শিক্ষা",
        "Narration and subtitle language": "বর্ণনা ও সাবটাইটেল ভাষা",
        "Generate scene images": "দৃশ্যের ছবি তৈরি করুন",
        "Generate voice narration": "ভয়েস বর্ণনা তৈরি করুন",
        "Generate Experience video": "অভিজ্ঞতা ভিডিও তৈরি করুন",
        "Analyze Poem": "কবিতা বিশ্লেষণ করুন",
        "Analysis": "বিশ্লেষণ",
        "Scenes": "दृश्यসমূহ",
        "Voice": "কণ্ঠ",
        "Experience": "অভিজ্ঞতা",
        "Ask": "জিজ্ঞাসা করুন",
    },
    "mr": {
        "Literary Analysis": "साहित्यिक विश्लेषण",
        "Summary": "सारांश",
        "Scene Breakdown": "दृश्य विभाजन",
        "Scene": "दृश्य",
        "Sangam Voice": "संगम आवाज",
        "Ask Pulavar": "पुलवरला विचारा",
        "Poem source": "कवितेचा स्रोत",
        "Type / Paste": "टाइप / पेस्ट",
        "Library": "ग्रंथालय",
        "Camera / Image": "कॅमेरा / प्रतिमा",
        "Options": "पर्याय",
        "Learning": "शिकणे",
        "Narration and subtitle language": "निवेदन व उपशीर्षक भाषा",
        "Generate scene images": "दृश्य प्रतिमा तयार करा",
        "Generate voice narration": "आवाज निवेदन तयार करा",
        "Generate Experience video": "अनुभव व्हिडिओ तयार करा",
        "Analyze Poem": "कवितेचे विश्लेषण करा",
        "Analysis": "विश्लेषण",
        "Scenes": "दृश्ये",
        "Voice": "आवाज",
        "Experience": "अनुभव",
        "Ask": "विचारा",
    },
    "fr": {
        "Literary Analysis": "Analyse litteraire",
        "Summary": "Resume",
        "Scene Breakdown": "Decoupage des scenes",
        "Scene": "Scene",
        "Sangam Voice": "Voix Sangam",
        "Ask Pulavar": "Demander au Pulavar",
        "Options": "Options",
        "Learning": "Apprentissage",
        "Narration and subtitle language": "Langue de narration et de sous-titres",
        "Analyze Poem": "Analyser le poeme",
        "Analysis": "Analyse",
        "Scenes": "Scenes",
        "Voice": "Voix",
        "Experience": "Experience",
        "Ask": "Demander",
    },
    "es": {
        "Literary Analysis": "Analisis literario",
        "Summary": "Resumen",
        "Scene Breakdown": "Desglose de escenas",
        "Scene": "Escena",
        "Sangam Voice": "Voz Sangam",
        "Ask Pulavar": "Preguntar al Pulavar",
        "Options": "Opciones",
        "Learning": "Aprendizaje",
        "Narration and subtitle language": "Idioma de narracion y subtitulos",
        "Analyze Poem": "Analizar poema",
        "Analysis": "Analisis",
        "Scenes": "Escenas",
        "Voice": "Voz",
        "Experience": "Experiencia",
        "Ask": "Preguntar",
    },
}

STRICT_LANGUAGE_COPY: dict[str, dict[str, str]] = {
    "en": {
        "opening": "Listen as a புலவர் would: slowly, with the land speaking before the heart answers.",
        "learner": "This poem belongs to the {thinai_ta} திணை. In சங்கம் poetry, திணை is not just scenery; it joins place, time, nature, and feeling.",
        "scene": "Scene",
        "behold": "Behold",
        "setting": "The landscape is",
        "meaning": "The image gathers the poem's feeling without leaving the சங்கம் world.",
        "closing": "Let the verse settle fully; the காட்சி, the voice, and the meaning now rest together.",
    },
    "ta": {
        "opening": "புலவர் உரைப்பது போல மெதுவாகக் கேளுங்கள்; முதலில் நிலம் பேசும், பின்னர் உள்ளம் பதிலளிக்கும்.",
        "learner": "இந்தப் பாடல் {thinai_ta} திணையைச் சார்ந்தது. சங்க இலக்கியத்தில் திணை என்பது நிலம், காலம், இயற்கை, உணர்வு ஆகியவை ஒன்றாக இணையும் வழி.",
        "scene": "காட்சி",
        "behold": "பாருங்கள்",
        "setting": "நிலப்பரப்பு",
        "meaning": "இந்த காட்சி, பாடலின் உணர்வை சங்க மரபிலேயே அமைதியாகத் தாங்குகிறது.",
        "closing": "பாடல் முழுமையாக அமைதியடையட்டும்; காட்சி, குரல், பொருள் மூன்றும் இங்கே ஒன்றாக நிற்கின்றன.",
    },
    "hi": {
        "opening": "एक புலவர் की तरह सुनिए: धीरे, गंभीरता से; पहले भूमि बोलती है, फिर हृदय उत्तर देता है.",
        "learner": "यह कविता {thinai_ta} திணை से जुड़ी है. சங்கம் काव्य में திணை स्थान, समय, प्रकृति और भाव को एक साथ रखता है.",
        "scene": "दृश्य",
        "behold": "देखिए",
        "setting": "भूमि है",
        "meaning": "यह चित्र कविता की भावना को சங்கம் परंपरा के भीतर शांत ढंग से संजोता है.",
        "closing": "पंक्ति को पूरा ठहरने दीजिए; காட்சி, स्वर और अर्थ अब साथ विश्राम करते हैं.",
    },
    "fr": {
        "opening": "Ecoutez comme un புலவர்: lentement, avec la terre qui parle avant que le coeur reponde.",
        "learner": "Ce poeme appartient au திணை {thinai_ta}. Dans la poesie சங்கம், le திணை unit lieu, temps, nature et sentiment.",
        "scene": "Scene",
        "behold": "Regardez",
        "setting": "Le paysage est",
        "meaning": "Cette image rassemble le sentiment du poeme sans quitter le monde சங்கம்.",
        "closing": "Laissez le vers se poser pleinement; la காட்சி, la voix et le sens reposent ensemble.",
    },
    "es": {
        "opening": "Escucha como un புலவர்: despacio, dejando que la tierra hable antes que responda el corazon.",
        "learner": "Este poema pertenece al திணை {thinai_ta}. En la poesia சங்கம், el திணை une lugar, tiempo, naturaleza y emocion.",
        "scene": "Escena",
        "behold": "Mira",
        "setting": "El paisaje es",
        "meaning": "Esta imagen recoge el sentimiento del poema sin salir del mundo சங்கம்.",
        "closing": "Deja que el verso repose por completo; la காட்சி, la voz y el sentido descansan juntos.",
    },
}


def language_choices() -> list[tuple[str, str]]:
    return [(code, name) for code, name in LANGUAGE_OPTIONS.items()]


def language_label(code: str | None) -> str:
    return LANGUAGE_OPTIONS.get(normalize_language(code), LANGUAGE_OPTIONS["en"])


def normalize_language(code: str | None) -> str:
    if not code:
        return "en"
    code = code.strip()
    if code in LANGUAGE_OPTIONS:
        return code
    short = code.split("-")[0].lower()
    return short if short in LANGUAGE_OPTIONS else "en"


def gtts_language(code: str | None) -> str:
    code = normalize_language(code)
    return GTTS_LANGUAGE_ALIASES.get(code, code)


def improve_analysis_accuracy(
    analysis: PoemAnalysis,
    poem_text: str = "",
    library_poem: Poem | None = None,
) -> PoemAnalysis:
    """Conservative cleanup so weak AI output still follows Sangam rules."""
    if library_poem:
        analysis.thinai = library_poem.thinai or analysis.thinai
        analysis.thurai = analysis.thurai or library_poem.thurai
        analysis.speaker = analysis.speaker or library_poem.speaker
        analysis.listener = analysis.listener or library_poem.listener
        analysis.poet = analysis.poet or library_poem.author
        analysis.poet_tamil = analysis.poet_tamil or library_poem.author_ta
        analysis.collection = analysis.collection or library_poem.collection
        analysis.collection_tamil = analysis.collection_tamil or library_poem.collection_ta
        analysis.period = analysis.period or library_poem.period
        analysis.akam_puram = analysis.akam_puram or library_poem.akam_puram
        analysis.uri_porul = analysis.uri_porul or library_poem.uri_porul
        analysis.meyppadu = analysis.meyppadu or library_poem.meyppadu
        if not analysis.karu_porul:
            analysis.karu_porul = library_poem.karu_porul
        if not analysis.word_meanings:
            analysis.word_meanings = library_poem.word_meanings

    if analysis.thinai == Thinai.UNKNOWN:
        analysis.thinai = infer_thinai(poem_text, analysis)

    if analysis.thinai != Thinai.UNKNOWN:
        analysis.summary = analysis.summary or f"This poem belongs to the {analysis.thinai.value} Sangam landscape."
        analysis.summary_tamil = analysis.summary_tamil or f"இந்தப் பாடல் {THINAI_TAMIL.get(analysis.thinai, '')} திணையின் உணர்வை வெளிப்படுத்துகிறது."
        analysis.mood = analysis.mood if analysis.mood != Mood.UNKNOWN else mood_for_thinai(analysis.thinai)
        analysis.emotion_tamil = analysis.emotion_tamil or MOOD_TAMIL.get(analysis.mood, "")

    analysis.cultural_context = analysis.cultural_context or (
        "Sangam poems join landscape, time, nature, and human feeling into one symbolic system."
    )
    analysis.literary_devices = analysis.literary_devices or (
        "Thinai symbolism, karu imagery, uri emotion, and implied inner meaning."
    )
    return analysis


def infer_thinai(poem_text: str, analysis: PoemAnalysis | None = None) -> Thinai:
    haystack = " ".join(
        [
            poem_text or "",
            getattr(analysis, "summary", "") or "",
            getattr(analysis, "cultural_context", "") or "",
            getattr(analysis, "uri_porul", "") or "",
        ]
    ).lower()
    scores: dict[Thinai, int] = {}
    for thinai, hints in THINAI_HINTS.items():
        scores[thinai] = sum(1 for hint in hints if hint in haystack)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else Thinai.UNKNOWN


def mood_for_thinai(thinai: Thinai) -> Mood:
    return {
        Thinai.KURINJI: Mood.JOY,
        Thinai.MULLAI: Mood.LONGING,
        Thinai.MARUTHAM: Mood.ANGER,
        Thinai.NEYTAL: Mood.LONGING,
        Thinai.PALAI: Mood.SORROW,
    }.get(thinai, Mood.UNKNOWN)


def ui_text(text: str, target_language: str | None = None) -> str:
    """Translate stable UI labels. Falls back to live translation when available."""
    try:
        target_language = normalize_language(target_language)
        if target_language == "en" or not text:
            return text
        local = UI_TRANSLATIONS.get(target_language, {})
        if text in local:
            return local[text]
        if target_language == "ta":
            return text
        translated = translate_text(text, target_language)
        return translated if not _translation_failed(text, translated, target_language) else text
    except Exception as e:
        print(f"[language_engine] UI text fallback for {target_language}: {e}")
        return text or ""


def translate_analysis_payload(analysis: PoemAnalysis, target_language: str) -> dict[str, Any]:
    """Build translated display text for analysis panels."""
    target_language = normalize_language(target_language)
    if target_language == "ta":
        return {
            "summary": analysis.summary_tamil or analysis.summary,
            "emotion": analysis.emotion_tamil or analysis.emotion,
            "mood": MOOD_TAMIL.get(analysis.mood, analysis.mood.value),
            "thinai_meaning": THINAI_MEANING.get(analysis.thinai, ""),
            "cultural_context": analysis.cultural_context_tamil or analysis.cultural_context,
            "literary_devices": analysis.literary_devices,
            "uri_porul": analysis.uri_porul_tamil or analysis.uri_porul,
            "meyppadu": analysis.meyppadu_tamil or analysis.meyppadu,
        }
    payload = {
        "summary": analysis.summary,
        "emotion": analysis.emotion,
        "mood": analysis.mood.value,
        "thinai_meaning": THINAI_MEANING.get(analysis.thinai, ""),
        "cultural_context": analysis.cultural_context,
        "literary_devices": analysis.literary_devices,
        "uri_porul": analysis.uri_porul,
        "meyppadu": analysis.meyppadu,
    }
    if target_language == "en":
        return _safe_payload(payload, target_language)
    return translate_json(payload, target_language)


def translate_text(text: str, target_language: str) -> str:
    try:
        if not text or normalize_language(target_language) in ("en", "ta"):
            return text
        translated = translate_json({"text": text}, target_language)
        return _safe_string(translated.get("text"), text)
    except Exception as e:
        print(f"[language_engine] Text translation fallback for {target_language}: {e}")
        return text or ""


@lru_cache(maxsize=128)
def _translate_json_cached(payload_json: str, target_language: str) -> str:
    """
    Cached ONLY on success. If this raises, lru_cache stores nothing for
    this call — the next attempt will retry instead of being stuck replaying
    a stale failure forever.
    """
    from gemini_client import get_model

    prompt = (
        "Translate the JSON string values into "
        f"{language_label(target_language)} for a global learner of Tamil. "
        "Keep Tamil words such as Thinai, Akam, Puram, Kurinji, Mullai, Marutham, Neytal, Palai unchanged, "
        "and explain them briefly when helpful. Translate ordinary English labels and explanations fully; "
        "do not leave English unchanged unless it is a Tamil literary term, a proper noun, or already in the target language. "
        "Return ONLY valid JSON.\n\n"
        f"{payload_json}"
    )
    response = get_model().generate_content(prompt)
    extracted = _extract_json(response.text)
    json.loads(extracted)  # validate it's real JSON before we let it be cached
    print(f"[language_engine] ✅ Translated payload to {target_language}.")
    return extracted


def translate_json(payload: dict[str, Any], target_language: str) -> dict[str, Any]:
    target_language = normalize_language(target_language)
    if not payload:
        return _safe_payload({}, target_language)
        
    # Deep copy payload to ensure downstream modifications don't break application state references
    working_payload = copy.deepcopy(payload)
    
    if target_language in ("en", "ta"):
        return _safe_payload(working_payload, target_language)

    if os.getenv("DTEC_ENABLE_LIVE_TRANSLATION", "1") != "1":
        print("[language_engine] Live translation disabled via DTEC_ENABLE_LIVE_TRANSLATION.")
        return _safe_payload(working_payload, target_language)

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("[language_engine] ⚠️ No GEMINI_API_KEY/GOOGLE_API_KEY found — skipping translation.")
        return working_payload

    payload_json = json.dumps(working_payload, ensure_ascii=False, sort_keys=True)
    try:
        translated_json = _translate_json_cached(payload_json, target_language)
        return _safe_payload(json.loads(translated_json), target_language)
    except Exception as e:
        print(f"[language_engine] ⚠️ Translation to {target_language} failed: {e}")
        return _safe_payload(working_payload, target_language)


def translate_learning_json(payload: dict[str, Any], target_language: str) -> dict[str, Any]:
    """Translate learner-facing explanations, including Tamil selected-language views."""
    target_language = normalize_language(target_language)
    if not payload:
        return _safe_payload({}, target_language)

    working_payload = copy.deepcopy(payload)
    if target_language == "en":
        return _safe_payload(working_payload, target_language)

    if os.getenv("DTEC_ENABLE_LIVE_TRANSLATION", "1") != "1":
        print("[language_engine] Live translation disabled via DTEC_ENABLE_LIVE_TRANSLATION.")
        return _safe_payload(working_payload, target_language)

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("[language_engine] ⚠️ No GEMINI_API_KEY/GOOGLE_API_KEY found — skipping translation.")
        return working_payload

    payload_json = json.dumps(working_payload, ensure_ascii=False, sort_keys=True)
    try:
        translated_json = _translate_json_cached(payload_json, target_language)
        return _safe_payload(json.loads(translated_json), target_language)
    except Exception as e:
        print(f"[language_engine] ⚠️ Learning translation to {target_language} failed: {e}")
        return _safe_payload(working_payload, target_language)


def _extract_json(text: str) -> str:
    text = (text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        return text[start : end + 1]
    return text


def tamil_thinai_name(thinai: Thinai | None) -> str:
    return TAMIL_THINAI_NAMES.get(thinai or Thinai.UNKNOWN, TAMIL_THINAI_NAMES[Thinai.UNKNOWN])


def _strict_copy(target_language: str) -> dict[str, str]:
    target_language = normalize_language(target_language)
    if target_language in STRICT_LANGUAGE_COPY:
        return STRICT_LANGUAGE_COPY[target_language]

    phrases = SCENE_PHRASES.get(target_language, SCENE_PHRASES["en"])
    bridge = LANGUAGE_BRIDGES.get(target_language, LANGUAGE_BRIDGES["en"])
    opening = PULAVAR_OPENINGS.get(target_language, PULAVAR_OPENINGS["en"])
    return {
        "opening": opening,
        "learner": (
            f"{bridge.get('learner_prefix', language_label(target_language))}: "
            f"{{thinai_ta}} {TAMIL_TERMS['thinai']}. "
            f"{bridge.get('thinai_intro', LANGUAGE_BRIDGES['en']['thinai_intro'])}; "
            f"{bridge.get('place_feeling', LANGUAGE_BRIDGES['en']['place_feeling'])}."
        ),
        "scene": phrases.get("scene", SCENE_PHRASES["en"]["scene"]),
        "behold": phrases.get("behold", SCENE_PHRASES["en"]["behold"]),
        "setting": phrases.get("setting", SCENE_PHRASES["en"]["setting"]),
        "meaning": phrases.get("meaning", SCENE_PHRASES["en"]["meaning"]),
        "closing": phrases.get("closing", SCENE_PHRASES["en"]["closing"]),
    }


def _safe_string(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _offline_learning_bridge(analysis: PoemAnalysis, target_language: str) -> str:
    copy_map = _strict_copy(target_language)
    thinai_ta = tamil_thinai_name(getattr(analysis, "thinai", Thinai.UNKNOWN))
    try:
        return copy_map["learner"].format(thinai_ta=thinai_ta)
    except Exception:
        return f"{language_label(target_language)}: {thinai_ta} {TAMIL_TERMS['thinai']} joins place, nature, and feeling."


def _safe_payload(payload: dict[str, Any], target_language: str) -> dict[str, Any]:
    """Guarantee display payload keys exist even when translation/model work fails."""
    safe = dict(payload or {})
    language = language_label(target_language)
    for key, value in list(safe.items()):
        if value is None:
            safe[key] = ""
    if normalize_language(target_language) not in ("en", "ta"):
        safe.setdefault("learner_language", language)
    return safe


def _translation_failed(source: str, translated: str, target_language: str) -> bool:
    if normalize_language(target_language) == "en":
        return False
    return not translated or translated.strip() == (source or "").strip()


def _fallback_scene_caption(scene: SceneFrame, analysis: PoemAnalysis, target_language: str) -> str:
    copy_map = _strict_copy(target_language)
    thinai_ta = tamil_thinai_name(getattr(analysis, "thinai", Thinai.UNKNOWN))
    if normalize_language(target_language) == "ta":
        return f"{copy_map['scene']} {scene.scene_id}. {scene.title}. {thinai_ta} திணையின் உணர்வு இங்கே விரிகிறது."
    return (
        f"{copy_map['scene']} {scene.scene_id}. {scene.title}. "
        f"{thinai_ta} திணை. {copy_map['meaning']}"
    )


def learning_bridge_text(analysis: PoemAnalysis, target_language: str) -> str:
    target_language = normalize_language(target_language)
    if target_language in STRICT_LANGUAGE_COPY or target_language in SCENE_PHRASES:
        return _offline_learning_bridge(analysis, target_language)
    copy_map = _strict_copy(target_language)
    thinai_ta = tamil_thinai_name(analysis.thinai)
    if target_language in STRICT_LANGUAGE_COPY:
        return copy_map["learner"].format(thinai_ta=thinai_ta)

    source = {
        "text": (
            f"This poem belongs to the Tamil {thinai_ta} திணை. "
            "In Sangam poetry, திணை joins place, time, nature, and feeling."
        )
    }
    translated = translate_json(source, target_language).get("text", source["text"])
    return translated if not _translation_failed(source["text"], translated, target_language) else source["text"]


def scene_caption_text(
    scene: SceneFrame,
    analysis: PoemAnalysis,
    target_language: str = "en",
) -> tuple[str, str]:
    target_language = normalize_language(target_language)
    thinai = getattr(analysis, "thinai", Thinai.UNKNOWN)
    scene_id = getattr(scene, "scene_id", 1)
    title = _safe_string(getattr(scene, "title", ""), f"Scene {scene_id}")
    description = _safe_string(getattr(scene, "description", ""), title)
    uri = _safe_string(getattr(analysis, "uri_porul", ""))
    mood = _safe_string(getattr(getattr(analysis, "mood", None), "value", ""))
    karu = ", ".join(getattr(analysis, "karu_porul", []) or [])
    thinai_ta = tamil_thinai_name(thinai)
    tamil = f"{thinai_ta} திணையின் காட்சி {scene.scene_id}: {scene.title}"

    if target_language == "ta":
        return "", tamil

    analysis_bits = " ".join(
        part
        for part in (
            f"Thinai: {thinai.value}." if thinai and thinai != Thinai.UNKNOWN else "",
            f"Mood: {mood}." if mood and mood != "unknown" else "",
            f"Core feeling: {uri}." if uri else "",
            f"Nature signs: {karu}." if karu else "",
        )
        if part
    )
    englishish = f"Scene {scene_id}. {title}. {description} {analysis_bits}".strip()
    if target_language == "en":
        return englishish.replace(thinai.value, thinai_ta), tamil

    translated = translate_text(englishish, target_language)
    if _translation_failed(englishish, translated, target_language):
        translated = _fallback_scene_caption(scene, analysis, target_language)
    return translated, tamil


def build_learning_script(
    analysis: PoemAnalysis,
    scenes: list[SceneFrame] | None = None,
    target_language: str = "en",
) -> str:
    """Build a scene-first story narration for the video scenes."""
    target_language = normalize_language(target_language)
    copy_map = _strict_copy(target_language)
    parts = []

    selected_scenes = (scenes or [])[:3]
    for index, scene in enumerate(selected_scenes, start=1):
        caption, tamil = scene_caption_text(scene, analysis, target_language)
        spoken_caption = tamil if target_language == "ta" else _story_caption(scene, caption)
        transition = _story_transition(index, len(selected_scenes), target_language)
        line = " ".join(
            part
            for part in (
                transition,
                f"{copy_map['scene']} {scene.scene_id}.",
                spoken_caption,
            )
            if part
        )
        if target_language not in ("en", "ta"):
            translated = translate_text(line, target_language)
            line = translated if not _translation_failed(line, translated, target_language) else line
        parts.append(line)

    closing = _story_closing(target_language)
    if closing:
        parts.append(closing)
    return " ".join(part.strip() for part in parts if part and part.strip())


def _story_caption(scene: SceneFrame, fallback_caption: str) -> str:
    title = _safe_string(getattr(scene, "title", ""), f"Scene {getattr(scene, 'scene_id', 1)}")
    description = _safe_string(getattr(scene, "description", ""), fallback_caption)
    return f"{title}. {description}"


def _story_transition(index: int, total: int, target_language: str) -> str:
    if target_language == "ta":
        prefix = f"{TAMIL_TERMS['pulavar']} voice."
        if index == 1:
            return f"{prefix} The story begins in the first frame."
        if index == total:
            return "In the final frame,"
        return "Then,"
    if index == 1:
        return "Scene one opens the story."
    if index == total:
        return "In the final scene,"
    return "Then the story moves forward."


def _story_closing(target_language: str) -> str:
    if target_language == "ta":
        return f"The {TAMIL_TERMS['thinai']} mood remains after the image fades."
    return "The story settles there, leaving the last image to speak softly."


def build_multilingual_subtitles(
    scenes: list[SceneFrame],
    tracks: list[Any],
    analysis: PoemAnalysis,
    target_language: str = "en",
) -> list[SubtitleEntry]:
    target_language = normalize_language(target_language)
    scene_map = {scene.scene_id: scene for scene in scenes[:3]}
    subtitles: list[SubtitleEntry] = []
    for track in tracks:
        scene = scene_map.get(track.scene_id)
        if not scene:
            continue
        text_target, text_ta = scene_caption_text(scene, analysis, target_language)
        subtitles.append(
            SubtitleEntry(
                index=len(subtitles) + 1,
                start_seconds=track.start_seconds,
                end_seconds=track.end_seconds,
                text_en=text_target,
                text_ta=text_ta,
                speaker=f"Pulavar - {language_label(target_language)}",
                scene_id=track.scene_id,
            )
        )
    return subtitles
