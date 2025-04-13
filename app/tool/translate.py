from deep_translator import GoogleTranslator

def translate_text(text: str, target_lang: str = "zh-CN") -> str:
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return translated
    except Exception as e:
        return f"翻译失败: {e}"
