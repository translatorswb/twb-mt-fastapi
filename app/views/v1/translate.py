from fastapi import APIRouter, HTTPException, status
import logging

from app.helpers.config import Config
from app.utils.utils import get_model_id
from app.models.v1.translate import (
    BatchTranslationRequest,
    BatchTranslationResponse,
    LanguagesResponse,
    TranslationRequest,
    TranslationResponse,
)
from app.utils.translate import translate_text
from app.constants import MULTIMODALCODE
import re
from transformers import pipeline

# Initialize the translation pipeline
translator = pipeline("translation", model="facebook/nllb-200-3.3B", src_lang='eng_Latn', tgt_lang='kin_Latn')
translate_v1 = APIRouter(prefix='/api/v1/translate')

DEVDEBUG = True
logger = logging.getLogger('console_logger')

def fetch_model_data_from_request(request):
    config = Config()

    src = config.map_lang_to_closest(request.src)
    tgt = config.map_lang_to_closest(request.tgt)
    use_multi = True if request.use_multi == 'True' else False

    #Get regular model_id
    model_id = get_model_id(
        src=src,
        tgt=tgt,
        alt_id=request.alt
    )

    compatible_model_ids = config._lookup_pair_in_languages_list(src, tgt, request.alt)

    if not compatible_model_ids:
        raise HTTPException(
                status_code=406,
                detail=f'Language pair {model_id} is not supported.',
            )

    if DEVDEBUG: 
        logger.debug(f'compatible_model_ids {compatible_model_ids}')
        if use_multi:
            logger.debug(f'use_multi {use_multi}')
    
    regular_model_exists = model_id in config.loaded_models
    multilingual_model_exists_for_pair = any([mid.startswith(MULTIMODALCODE) for mid in compatible_model_ids])

    if not regular_model_exists and not use_multi and multilingual_model_exists_for_pair:
        use_multi = True

    if use_multi:
        if multilingual_model_exists_for_pair:
            #fetch multimodal 
            # model_id = get_model_id(src=MULTIMODALCODE,
                                    # tgt=MULTIMODALCODE,
                                    # alt_id=request.alt)
            model_id = config._pair_to_model_id(compatible_model_ids[0])
            if len(compatible_model_ids) > 1:
                logger.warning(f"More than one compatible model. Choosing {compatible_model_ids[0]} among {compatible_model_ids}")

        else:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No multilingual model support for pair {src}-{tgt}. Remove flag `use_multi` from request',
        )

    if DEVDEBUG: logger.debug(f'model_id {model_id}')

    return model_id, src, tgt

@translate_v1.post("", status_code=status.HTTP_200_OK)
@translate_v1.post('/', status_code=status.HTTP_200_OK)
async def translate_sentence(
    request: TranslationRequest,
) -> TranslationResponse:

    model_id, src, tgt = fetch_model_data_from_request(request)

    translation = translate_text(model_id, request.text, src, tgt)

    return TranslationResponse(translation=translation)

@translate_v1.post('/batch', status_code=status.HTTP_200_OK)
async def translate_batch(
    request: BatchTranslationRequest,
) -> BatchTranslationResponse:
    config = Config()

    model_id, src, tgt = fetch_model_data_from_request(request)

    translated_batch = []
    for sentence in request.texts:
        translation = translate_text(model_id, sentence, src, tgt)
        translated_batch.append(translation)
    
    #TODO: translated_batch = translate_text(model_id, request.texts)

    return BatchTranslationResponse(translation=translated_batch)

@translate_v1.get('', status_code=status.HTTP_200_OK)
@translate_v1.get('/', status_code=status.HTTP_200_OK)
async def languages() -> LanguagesResponse:
    config = Config()

    return LanguagesResponse(
        languages=config.language_codes, models=config.languages_list
    )

def remove_markdown(text):
    """Remove markdown formatting from text."""
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)  # Bold
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)  # Italics
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)  # Links
    text = re.sub(r'`(.*?)`', r'\1', text)  # Inline code
    text = re.sub(r'~~(.*?)~~', r'\1', text)  # Strikethrough
    return text

def reapply_markdown(original, modified):
    """Reapply markdown formatting after translation."""
    pattern = r'(\*\*.*?\*\*|\*.*?\*|__.*?__|_.*?_|\[.*?\]\(.*?\)|`.*?`|~~.*?~~)'
    matches = re.finditer(pattern, original)

    result = ""
    cursor = 0

    for match in matches:
        start, end = match.span()
        token = match.group()
        if cursor < start:
            result += modified[cursor:start]
        stripped = remove_markdown(token).strip()
        translated_stripped = translator(stripped)[0]['translation_text']
        result += token.replace(stripped, translated_stripped)
        cursor = end

    if cursor < len(original):
        result += modified[cursor:]
    
    return result

def process_text(text):
    """Remove markdown, translate, and reapply markdown formatting."""
    plain_text = remove_markdown(text)
    translated_text = translator(plain_text)[0]['translation_text']
    return reapply_markdown(text, translated_text)

@translate_v1.post('/markdown', status_code=status.HTTP_200_OK)
async def translate_markdown(request: TranslationRequest) -> TranslationResponse:
    translated_markdown = process_text(request.text)
    return TranslationResponse(translation=translated_markdown)