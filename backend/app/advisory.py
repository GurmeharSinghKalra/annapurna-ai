"""The offline advisory reply, used whenever Gemini is unavailable.

This is a template, not an answer: it restates the current recommendation in the farmer's language
and says plainly that it is not a reply to their question. The previous version read like an
answer, which was misleading when the farmer had asked something specific.

It also attaches the season-finance summary in every language. Previously the finance sentence was
appended only in the English branch, so a Hindi-speaking farmer with a budget on screen silently
got none of it.
"""

from __future__ import annotations

from .schemas import FarmProfile, FinanceContext, Recommendation

# Fully translated templates rather than an English sentence with a translated prefix.
TEMPLATES = {
    "English": {
        "intro": (
            "The AI advisor is offline, so this is not an answer to your question. Here is what your current plan says."
        ),
        "plan": "{crop} is rated {suitability}% for your field ({verdict}).",
        "advice": "{advisory} Rotation: {rotation}",
        "money": "Estimated return at the planning price is about INR {profit:,}.",
        "finance": (
            "Your season budget estimates INR {profit:,} profit with a break-even price of "
            "INR {break_even:,} per quintal. Check the selling price before you commit money."
        ),
        "limit": "Note: {limiter}",
        "close": "Confirm anything costly or health-related with your local agriculture officer.",
    },
    "Hindi": {
        "intro": ("AI सलाहकार अभी उपलब्ध नहीं है, इसलिए यह आपके सवाल का जवाब नहीं है। आपकी मौजूदा योजना यह कहती है।"),
        "plan": "आपके खेत के लिए {crop} को {suitability}% आँका गया है ({verdict}).",
        "advice": "{advisory} फसल चक्र: {rotation}",
        "money": "योजना मूल्य पर अनुमानित वापसी लगभग INR {profit:,} है।",
        "finance": (
            "आपके सीज़न बजट में INR {profit:,} मुनाफ़े का अनुमान है और लागत-वसूली मूल्य "
            "INR {break_even:,} प्रति क्विंटल है। पैसा लगाने से पहले बिक्री मूल्य जाँच लें।"
        ),
        "limit": "ध्यान दें: {limiter}",
        "close": "कोई भी महँगा या स्वास्थ्य से जुड़ा निर्णय अपने कृषि अधिकारी से पुष्टि कर लें।",
    },
    "Punjabi": {
        "intro": ("AI ਸਲਾਹਕਾਰ ਹੁਣ ਉਪਲਬਧ ਨਹੀਂ ਹੈ, ਇਸ ਲਈ ਇਹ ਤੁਹਾਡੇ ਸਵਾਲ ਦਾ ਜਵਾਬ ਨਹੀਂ ਹੈ। ਤੁਹਾਡੀ ਮੌਜੂਦਾ ਯੋਜਨਾ ਇਹ ਕਹਿੰਦੀ ਹੈ।"),
        "plan": "ਤੁਹਾਡੇ ਖੇਤ ਲਈ {crop} ਨੂੰ {suitability}% ਮੰਨਿਆ ਗਿਆ ਹੈ ({verdict}).",
        "advice": "{advisory} ਫਸਲ ਚੱਕਰ: {rotation}",
        "money": "ਯੋਜਨਾ ਕੀਮਤ 'ਤੇ ਅੰਦਾਜ਼ਨ ਵਾਪਸੀ ਲਗਭਗ INR {profit:,} ਹੈ।",
        "finance": (
            "ਤੁਹਾਡੇ ਸੀਜ਼ਨ ਬਜਟ ਵਿੱਚ INR {profit:,} ਮੁਨਾਫ਼ੇ ਦਾ ਅੰਦਾਜ਼ਾ ਹੈ ਅਤੇ ਲਾਗਤ-ਵਸੂਲੀ ਕੀਮਤ "
            "INR {break_even:,} ਪ੍ਰਤੀ ਕੁਇੰਟਲ ਹੈ। ਪੈਸਾ ਲਗਾਉਣ ਤੋਂ ਪਹਿਲਾਂ ਵਿਕਰੀ ਕੀਮਤ ਜਾਂਚ ਲਵੋ।"
        ),
        "limit": "ਧਿਆਨ ਦਿਓ: {limiter}",
        "close": "ਕੋਈ ਵੀ ਮਹਿੰਗਾ ਜਾਂ ਸਿਹਤ ਨਾਲ ਜੁੜਿਆ ਫ਼ੈਸਲਾ ਆਪਣੇ ਖੇਤੀਬਾੜੀ ਅਧਿਕਾਰੀ ਤੋਂ ਪੁਸ਼ਟੀ ਕਰੋ।",
    },
    "Haryanvi": {
        "intro": ("AI salahkar abhi band se, is karan yo tere sawal ka jawab nahi se. Teri maujooda yojna yo kahe se."),
        "plan": "Tere khet ke liye {crop} ko {suitability}% aanka gaya se ({verdict}).",
        "advice": "{advisory} Fasal chakar: {rotation}",
        "money": "Yojna bhaav pe anumanit vapsi karib INR {profit:,} se.",
        "finance": (
            "Tere season budget mein INR {profit:,} munafe ka anuman se aur lagat-vasuli bhaav "
            "INR {break_even:,} per quintal se. Paisa lagane te pehle bikri bhaav jaanch le."
        ),
        "limit": "Dhyan de: {limiter}",
        "close": "Koi bhi mehnga ya sehat se juda faisla apne krishi adhikari te puchh le.",
    },
}


def localized_chat_answer(
    crop: str,
    farm: FarmProfile,
    recommendation: Recommendation,
    finance: FinanceContext | None = None,
) -> str:
    template = TEMPLATES.get(farm.language, TEMPLATES["English"])
    parts = [
        template["intro"],
        template["plan"].format(crop=crop, suitability=recommendation.suitability, verdict=recommendation.verdict),
    ]
    if recommendation.limiters:
        parts.append(template["limit"].format(limiter=recommendation.limiters[0]))
    parts.append(template["advice"].format(advisory=recommendation.advisory, rotation=recommendation.rotation))
    parts.append(template["money"].format(profit=recommendation.expected_profit))
    if finance:
        parts.append(
            template["finance"].format(profit=finance.expected_profit, break_even=finance.break_even_price_per_quintal)
        )
    parts.append(template["close"])
    return " ".join(parts)
