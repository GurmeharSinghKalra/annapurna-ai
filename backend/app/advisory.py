from .schemas import FarmProfile


LANGUAGE_PREFIX = {
    "English": "Advisory",
    "Hindi": "सलाह",
    "Punjabi": "Salah",
    "Haryanvi": "Salah",
}


def localized_chat_answer(crop: str, farm: FarmProfile, advisory: str, rotation: str, expected_profit: int) -> str:
    language = farm.language or "English"
    if language == "Hindi":
        return (
            f"सलाह: {crop} अभी आपकी मिट्टी, मौसम और बजट के हिसाब से अच्छा विकल्प है. "
            f"{advisory} फसल चक्र: {rotation} अनुमानित रिटर्न INR {expected_profit:,} है."
        )
    if language == "Punjabi":
        return (
            f"Salah: {crop} tuhadi mitti, mausam ate budget de hisaab naal changa vikalp hai. "
            f"{advisory} Crop rotation: {rotation} Expected return INR {expected_profit:,}."
        )
    if language == "Haryanvi":
        return (
            f"Salah: {crop} teri mitti, mausam aur budget ke hisaab te theek fasal se. "
            f"{advisory} Fasal rotation: {rotation} Expected return INR {expected_profit:,}."
        )
    return (
        f"Advisory: {crop} is a strong match for the current soil, weather, and budget. "
        f"{advisory} Crop rotation: {rotation} Expected return INR {expected_profit:,}."
    )
