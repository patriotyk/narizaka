import auditok

class Splitter():
    def split_to_segments(self, audio_file, all_words):
        def _split(region, threshold=46, deep=4):
            if not region.meta:
                region.meta = {'start': 0}
            audio_regions = []
            for r in region.split(
                min_dur=0.2,     # minimum duration of a valid audio event in seconds
                max_dur=80,       # maximum duration of an event
                max_silence=0.11, # maximum duration of tolerated continuous silence within an event
                energy_threshold=threshold # threshold of detection
            ):
                r.meta = {'start': r.meta.start+region.meta.start, 'end': r.meta.end+region.meta.start}
                if r.duration > 8.0 and deep:
                    regions = _split(r, threshold+2, deep-1)
                    if len(regions)> 1:
                        audio_regions = audio_regions + regions
                else:
                    audio_regions.append(r)
            return audio_regions

        
        region = auditok.load(str(audio_file), large_file=True)
        audio_regions = sorted(_split(region), key=lambda x: x.meta.start)
        
        pugaps = []
        text = ''
        for i, word in enumerate(all_words[:-1]):
            text += word['word']
            if word['word'][-1] in [',','.','?','-',':','!', '»', ';'] or \
              ((all_words[i+1]['start'] - word['end']) > 0.2 and (all_words[i+1]['end'] - all_words[i+1]['start']) > 0.4 and
              (word['end'] - word['start']) > 0.4):
                pugaps.append([word['end'], all_words[i+1]['start'], i])
                text = ''
        
        
        temp_reg = None
        start_word = 0
        regions_by_punct = []
        for i, r in enumerate(audio_regions[:-1]):

            if not temp_reg:
                temp_reg = r
            else:
                start = temp_reg.meta.start
                temp_reg += r
                temp_reg.meta = {'end': r.meta.end, 'start': start}

            gap_dur = audio_regions[i+1].meta.start - r.meta.end
            gap_point = r.meta.end + (gap_dur/2)
            found = next((item for item in pugaps if (item[0]-0.1) <= gap_point <= item[1]+0.1), None)
            
            if found:
                if start_word != found[2]+1:
                    text = ''.join([word['word'] for word in all_words[start_word:found[2]+1]])
                    if text.strip():
                        regions_by_punct.append({'start': temp_reg.meta.start,
                                                'end': r.meta.end,
                                                'text': text})
                        temp_reg = None
                        start_word = found[2]+1
                

        ready_segment = {}
        for segment in regions_by_punct:
            if not ready_segment:
                ready_segment = segment
                continue

            if ((segment['start'] - ready_segment['end']) < 0.4 and ready_segment['text'][-1] in [',', ':', '-', '»', '\'', '.', '?', '!'] and (segment['end'] - ready_segment['start']) < 11)\
                or (ready_segment['text'][-1] in [',', ':', '-', '»', '\'']  and (segment['end'] - ready_segment['start']) < 20):
                ready_segment['end'] = segment['end']
                ready_segment['text'] += segment['text']
            else:
                yield ready_segment
                ready_segment = segment
        yield ready_segment

    