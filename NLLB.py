from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline


def translate(text, src_lang, tgt_lang):
    tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
    model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")

    translator = pipeline(
        "translation",
        model=model,
        tokenizer=tokenizer,
        src_lang=src_lang,
        tgt_lang=tgt_lang,
    )
    return translator(text, max_length=512)[0]["translation_text"]


if __name__ == "__main__":
    src_text = "Hello, how are you?"
    print(translate(src_text, src_lang="eng_Latn", tgt_lang="zho_Hans"))
