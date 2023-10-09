import magic
from datetime import timedelta
import os
import ffmpeg
import tempfile
import pathlib

import jinja2


class AudioBook():
    def __init__(self, filename: pathlib.Path) -> None:  
        self.audio_files = []      
        if not filename.exists():
            raise Exception('Audio path doesn\'t exists')
        
        if filename.is_dir():
            files = os.listdir(filename)
            files.sort()
            for f in files:
                if self._is_media(filename.joinpath(f)):
                    self.audio_files.append(pathlib.Path(filename.joinpath(f)))
            if not self.audio_files:
                raise Exception('Directory doesn\'t contain any audio files')
        else:
            if not self._is_media(filename):
                raise Exception('Audio book is not audio file')    
            self.audio_files.append(filename)
        self.duration = 0.0
        for fl in self.audio_files:
            probe = ffmpeg.probe(fl)
            self.duration += float(probe["format"]["duration"])

        print(f'Audio duration is {timedelta(seconds=self.duration)}')

    
    def _is_media(self, filename: pathlib.Path)-> bool:
        mimetype = magic.from_file(filename=filename, mime=True)
        return mimetype.split('/')[0] == 'audio'

    


    #     dfp.close()
        
    #     print(f'Done,\nMatched:  {aligner.getStat()}%')
        
    #     if debug_report:

    #         templateLoader = jinja2.FileSystemLoader(searchpath="./")
    #         templateEnv = jinja2.Environment(loader=templateLoader)
    #         template = templateEnv.get_template('debug_report.html')

    #         report = template.render(name=textbook.name, segments=not_matched_list)
    #         f = open(output.joinpath(textbook.name+'.html'), 'w+')
    #         f.write(report)
    #         f.close()
