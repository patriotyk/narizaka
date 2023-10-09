import os
import tempfile
import regex
import magic
import pathlib

import xml.etree.ElementTree as ET

class TextBook:
    def __init__(self, path, min_text_length=3000) -> None:
        super().__init__()
        self.name = path.stem
        self.min_text_length = min_text_length
        
        if self._is_fb2(path):
            self.path = path
        else:
            fl, fb2_file = tempfile.mkstemp(suffix='.fb2')
            os.close(fl)
            os.system(f'pandoc {path} -o {fb2_file}')
            self.path = fb2_file
        self.iter = ET.parse(self.path).getroot().iter()

    
    def _is_fb2(self, filename: pathlib.Path)-> bool:
        mimetype = magic.from_file(filename=filename, mime=True)
        return mimetype == 'text/xml'
    
    def remove_beginning_dashes(self, text):
        text = regex.sub(r'[᠆‐‑‒–—―⁻₋−⸺⸻]', '-', text)
        text = regex.sub(r'^\s*?\-', '', text)
        return text
    
    def more_text(self):
        text = ''
        for i in self.iter:
            if i.tag.endswith('}p'):
                text += self.remove_beginning_dashes(' '.join(i.itertext())) + ' '
                if len(text) >= self.min_text_length:
                    break
        return text 
