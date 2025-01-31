from app.views.v1.translate import *
from bs4 import BeautifulSoup, NavigableString
import random
import os

translate_html = APIRouter(prefix='/api/v1/translate_html')

@translate_html.post('/translate_page', status_code=status.HTTP_200_OK)
async def modify_html_content(request: TranslationRequest):
    
    model_id, src, tgt = fetch_model_data_from_request(request)
    # Parse the HTML content
    soup = BeautifulSoup(request.text, 'html.parser')
          

    def edit_text(element,model_id,src,tgt):
        """
        Recursively edits the text of the given BeautifulSoup element and its children.
        """
        if isinstance(element, NavigableString):
            return
        if element.name in ['script', 'style']:
            return

        for child in element.children:
            if isinstance(child, NavigableString):
                edited_text = translate_text(model_id,child,src,tgt)
                child.replace_with(edited_text)
            else:
                edit_text(element=child,model_id=model_id,src=src,tgt=tgt)
    
    edit_text(element=soup,model_id=model_id,src=src,tgt=tgt)

    return TranslationResponse(translation=soup)
