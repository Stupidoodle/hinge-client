"""Hinge enum ID → display label resolution.

Authoritative source: GET /config/v3.
See src/hinge/docs/ENUMS.md for full documentation.
"""

ETHNICITIES: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Native American",
    2: "Black / African Descent",
    3: "East Asian",
    4: "Hispanic / Latino",
    5: "Middle Eastern",
    6: "Pacific Islander",
    7: "South Asian",
    8: "White / Caucasian",
    9: "Other",
    10: "Southeast Asian",
}

RELIGIONS: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Buddhist",
    2: "Catholic",
    3: "Christian",
    4: "Hindu",
    5: "Jewish",
    6: "Muslim",
    7: "Spiritual",
    8: "Agnostic",
    9: "Atheist",
    10: "Other",
    11: "Sikh",
}

RELATIONSHIP_TYPES: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Monogamy",
    2: "Non-Monogamy",
    3: "Figuring Out",
    4: "Friends First",
}

DATING_INTENTIONS: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Life Partner",
    2: "Long-Term Relationship",
    3: "Long-Term, Open to Short",
    4: "Short-Term, Open to Long",
    5: "Short-Term Fun",
    6: "Figuring Out",
}

CHILDREN: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Don't Have Children",
    2: "Have Children",
}

FAMILY_PLANS: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Doesn't Want Children",
    2: "Wants Children",
    3: "Open to Children",
    4: "Not Sure Yet",
}

# Drinking, Drugs, Smoking, Marijuana all share the same mapping
VICES: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Yes",
    2: "Sometimes",
    3: "No",
}

POLITICS: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Liberal",
    2: "Moderate",
    3: "Conservative",
    4: "Other",
    5: "Not Political",
}

EDUCATION_ATTAINED: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "High School",
    2: "Undergraduate",
    3: "Post-Graduate",
}

ZODIAC: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Aries",
    2: "Taurus",
    3: "Gemini",
    4: "Cancer",
    5: "Leo",
    6: "Virgo",
    7: "Libra",
    8: "Scorpio",
    9: "Sagittarius",
    10: "Capricorn",
    11: "Aquarius",
    12: "Pisces",
}

PETS: dict[int, str] = {
    0: "Prefer Not to Say",
    1: "Dog",
    2: "Cat",
    3: "Bird",
    4: "Fish",
    5: "Reptile",
}

# All 144 Hinge language IDs.  Authoritative source: internal reference
# (constructor: name, ordinal, apiId, stringResId).  Verified against
# Bryan's profile: [36, 26, 126, 32] = German, English, Vietnamese, French.
LANGUAGES: dict[int, str] = {
    1: "Afrikaans",
    2: "Albanian",
    3: "Amharic",
    4: "Arabic",
    5: "Armenian",
    6: "Assamese",
    7: "Aymara",
    8: "Azerbaijani",
    9: "Bambara",
    10: "Basque",
    11: "Belarusian",
    12: "Bengali",
    13: "Bhojpuri",
    14: "Bosnian",
    15: "Bulgarian",
    16: "Catalan",
    17: "Cebuano",
    18: "Chichewa",
    19: "Corsican",
    20: "Croatian",
    21: "Czech",
    22: "Danish",
    23: "Dhivehi",
    24: "Dogri",
    25: "Dutch",
    26: "English",
    27: "Esperanto",
    28: "Estonian",
    29: "Ewe",
    30: "Filipino",
    31: "Finnish",
    32: "French",
    33: "Frisian",
    34: "Galician",
    35: "Georgian",
    36: "German",
    37: "Greek",
    38: "Guarani",
    39: "Gujarati",
    40: "Haitian Creole",
    41: "Hausa",
    42: "Hawaiian",
    43: "Hebrew",
    44: "Hindi",
    45: "Hmong",
    46: "Hungarian",
    47: "Icelandic",
    48: "Igbo",
    49: "Ilocano",
    50: "Indonesian",
    51: "Irish",
    52: "Italian",
    53: "Japanese",
    54: "Javanese",
    55: "Kannada",
    56: "Kazakh",
    57: "Khmer",
    58: "Kinyarwanda",
    59: "Konkani",
    60: "Korean",
    61: "Krio",
    62: "Kurdish",
    63: "Kyrgyz",
    64: "Lao",
    65: "Latin",
    66: "Latvian",
    67: "Lingala",
    68: "Lithuanian",
    69: "Luganda",
    70: "Luxembourgish",
    71: "Macedonian",
    72: "Maithili",
    73: "Malagasy",
    74: "Malay",
    75: "Malayalam",
    76: "Maltese",
    77: "Mandarin Chinese",
    78: "Maori",
    79: "Marathi",
    80: "Meiteilon",
    81: "Mizo",
    82: "Mongolian",
    83: "Myanmar",
    84: "Nepali",
    85: "Norwegian",
    86: "Odia",
    87: "Oromo",
    88: "Pashto",
    89: "Persian",
    90: "Polish",
    91: "Portuguese",
    92: "Punjabi",
    93: "Quechua",
    94: "Romanian",
    95: "Russian",
    96: "Samoan",
    97: "Sanskrit",
    98: "Scots Gaelic",
    99: "Sepedi",
    100: "Serbian",
    101: "Sesotho",
    102: "Shona",
    103: "Sindhi",
    104: "Sinhala",
    105: "Slovak",
    106: "Slovenian",
    107: "Somali",
    108: "Spanish",
    109: "Sudanese",
    110: "Swahili",
    111: "Swedish",
    112: "Tajik",
    113: "Tamil",
    114: "Tatar",
    115: "Telugu",
    116: "Thai",
    117: "Tigrinya",
    118: "Tsonga",
    119: "Turkish",
    120: "Turkmen",
    121: "Twi",
    122: "Ukrainian",
    123: "Urdu",
    124: "Uyghur",
    125: "Uzbek",
    126: "Vietnamese",
    127: "Welsh",
    128: "Xhosa",
    129: "Yiddish",
    130: "Yoruba",
    131: "Yue Chinese",
    132: "Zulu",
    # Sign languages (IDs 133–144)
    133: "American Sign Language",
    134: "Black American Sign Language",
    135: "British Sign Language",
    136: "Auslan",
    137: "Austrian Sign Language",
    138: "German Sign Language",
    139: "Swiss German Sign Language",
    140: "Swedish Sign Language",
    141: "French Sign Language",
    142: "Spanish Sign Language",
    143: "Italian Sign Language",
    144: "Klingon",
}


def resolve(mapping: dict[int, str], value: int | None) -> str | None:
    """Resolve a single enum ID to its label. Returns None if unknown/unset."""
    if value is None:
        return None
    label = mapping.get(value)
    if label is None or label == "Prefer Not to Say":
        return None
    return label


def resolve_list(mapping: dict[int, str], values: list[int]) -> str | None:
    """Resolve a list of enum IDs to a comma-separated label string."""
    if not values:
        return None
    labels = [
        mapping.get(v, f"#{v}")
        for v in values
        if v != 0 and mapping.get(v) != "Prefer Not to Say"
    ]
    return ", ".join(labels) if labels else None
