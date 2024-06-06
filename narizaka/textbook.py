import os
import tempfile
import regex
import magic
import pathlib

import xml.etree.ElementTree as ET

class TextBook:
    def __init__(self, path, min_text_length=20000) -> None:
        super().__init__()
        self.filename = path
        self.name = path.stem
        self.min_text_length = min_text_length
        self.temp_file = None
        self.can_skip = False
        if magic.from_file(filename=path, mime=True) == 'application/epub+zip':
            self.can_skip = True
        
        if self._is_fb2(path):
            self.path = path
        else:
            fl, self.temp_file = tempfile.mkstemp(suffix='.fb2')
            os.close(fl)
            os.system(f'pandoc "{path}" -o {self.temp_file}')
            self.path = self.temp_file
        self.iter = ET.parse(self.path).getroot().find('{http://www.gribuser.ru/xml/fictionbook/2.0}body').iter()

    
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
        skip = False
        for i in self.iter:
            if i.tag.endswith('}p') and not skip:
                text += self.norm(self._get_text(i)) + ' '
                if len(text) >= self.min_text_length:
                    break
            elif i.tag.endswith('}empty-line') and self.can_skip:
                skip = True
            elif i.tag.endswith('}p') and skip and i.text == None and i.tail == None and not "".join(i.itertext()):
                skip = False
        return text
    
    def __del__(self):
        if self.temp_file:
            os.remove(self.temp_file)
