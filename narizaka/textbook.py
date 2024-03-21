import os
import tempfile
import regex
import magic
import pathlib

import xml.etree.ElementTree as ET

class TextBook:
    def __init__(self, path, min_text_length=40000) -> None:
        super().__init__()
        self.name = path.stem
        self.min_text_length = min_text_length
        
        if self._is_fb2(path):
            self.path = path
        else:
            fl, fb2_file = tempfile.mkstemp(suffix='.fb2')
            os.close(fl)
            os.system(f'pandoc "{path}" -o {fb2_file}')
            self.path = fb2_file
        self.iter = ET.parse(self.path).getroot().iter()

    
    def _is_fb2(self, filename: pathlib.Path)-> bool:
        mimetype = magic.from_file(filename=filename, mime=True)
        return mimetype == 'text/xml'
    
    def norm(self, text):
        text = regex.sub(r'[᠆‐‑‒–—―⁻₋−⸺⸻]', '-', text)
        text = regex.sub(r'^\s*?\-', '', text)
        text = regex.sub(r'\[.*?\]', '', text)
        text = regex.sub(r'\s+\.', '. ', text)
        return text
    
    def _get_text(self, el):
        tag = el.tag
        if not isinstance(tag, str) and tag is not None:
            return
        text = ''
        if el.text:
            text += el.text
        
        for e in el:
            if not e.tag.endswith('}a'):
                for s in self._get_text(e):
                    text += s
            if e.tail:
               text += e.tail
        return text

    
    def more_text(self):
        text = ''
        for i in self.iter:
            if i.tag.endswith('}p'):
                text += self.norm(self._get_text(i)) + ' '
                if len(text) >= self.min_text_length:
                    break
        return text 
