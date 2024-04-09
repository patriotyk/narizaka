#!/usr/bin/python3

import gi 
import os
import time
from queue import Queue, Empty

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

import logging
logger = logging.getLogger(__name__)
Gst.init(None)


class MediaInfo():
    def __init__(self):
        self.pipeline = Gst.Pipeline()
        self.src = Gst.ElementFactory.make("filesrc")
        self.pipeline.add(self.src)
        self.decbin = Gst.ElementFactory.make("decodebin")
        self.pipeline.add(self.decbin)
        self.conv = Gst.ElementFactory.make("audioconvert")
        self.pipeline.add(self.conv)
        self.res = Gst.ElementFactory.make("audioresample")
        self.pipeline.add(self.res)
        self.rg = Gst.ElementFactory.make("rganalysis")
        self.pipeline.add(self.rg)
        self.sink = Gst.ElementFactory.make("fakesink")
        self.pipeline.add(self.sink)

        self.src.link(self.decbin)
        self.conv.link(self.res)
        self.res.link(self.rg)
        self.rg.link(self.sink)
        self.decbin.connect("pad-added", self._on_pad_added)
        self.decbin.connect("pad-removed", self._on_pad_removed)

        self.rg.set_property("forced", True)
        #self.rg.set_property("reference-level", self.ref_lvl)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

    def _on_pad_added(self, decbin, new_pad):
        sinkpad = self.conv.get_compatible_pad(new_pad, None)
        if sinkpad is not None:
            new_pad.link(sinkpad)

    def _on_pad_removed(self, decbin, old_pad):
        peer = old_pad.get_peer()
        if peer is not None:
            old_pad.unlink(peer)

    def _on_message(self, bus, msg):
        if msg.type == Gst.MessageType.TAG:
            tags = msg.parse_tag()
            self.tl = Gst.TagList.new_empty()
            def handle_tag(taglist, tag, userdata):
                if tag == Gst.TAG_TRACK_GAIN:
                    self.tl.add_value(Gst.TagMergeMode.APPEND, Gst.TAG_TRACK_GAIN,
                                      taglist.get_double(tag)[1])
                elif tag == Gst.TAG_TRACK_PEAK:
                   self.tl.add_value(Gst.TagMergeMode.APPEND, Gst.TAG_TRACK_PEAK,
                                     taglist.get_double(tag)[1])
                elif tag == Gst.TAG_REFERENCE_LEVEL:
                    self.tl.add_value(Gst.TagMergeMode.APPEND, Gst.TAG_REFERENCE_LEVEL,
                                      taglist.get_double(tag)[1])
            tags.foreach(handle_tag, None)
        elif msg.type == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
            self.mainloop.quit()

    def get(self, fname):
        self.src.set_property("location", fname)
        self.pipeline.set_state(Gst.State.PLAYING)
        self.mainloop = GLib.MainLoop()
        self.mainloop.run()
        return self.tl


class Segmenter():
    def __init__(self, sr):

        self.sr = sr
        self.info = MediaInfo()

        self.splits = Queue()
        self.current_segment = None
        self.index = 0
        self.prerolled = False

        
        self.pipeline = Gst.Pipeline()
        self.mainloop = GLib.MainLoop()
        self.bus = self.pipeline.get_bus()
        self.pipeline.bus.add_signal_watch()
        self.bus.connect('message', self.onMessage, self.mainloop)
        
        self.src = Gst.ElementFactory.make("filesrc")
        self.pipeline.add(self.src)
        
        self.decoder = Gst.ElementFactory.make("decodebin")
        self.pipeline.add(self.decoder)
        self.decoder.set_property('caps', Gst.Caps.from_string('audio/x-raw'))
        self.decoder.connect("pad-added", self.on_pad_added)
        
        self.src.link(self.decoder)

        self.aconv = Gst.ElementFactory.make('audioconvert')
        self.pipeline.add(self.aconv)
        self.decoder.link(self.aconv)

        self.dein = Gst.ElementFactory.make('deinterleave')
        self.pipeline.add(self.dein)
        self.deint_conn = self.dein.connect("pad-added", self.on_channel_added)
        self.dein.connect("no-more-pads", self.no_more_pads)
        self.aconv.link(self.dein)

        self.encoder = Gst.ElementFactory.make("wavenc")
        self.pipeline.add(self.encoder)

        self.anorm = Gst.ElementFactory.make("rgvolume")
        self.pipeline.add(self.anorm)
        self.anorm.set_property("album-mode", False)
        #self.anorm.set_property("pre-amp", 12)

        self.capsfilter = Gst.ElementFactory.make('capsfilter')
        self.pipeline.add(self.capsfilter)
      

        self.resample = Gst.ElementFactory.make('audioresample')
        self.pipeline.add(self.resample)
        self.resample.set_property('quality', 10)

        self.capsfilter.set_property('caps', Gst.Caps.from_string(f'audio/x-raw,rate={sr}'))
        self.resample.link(self.capsfilter)
        
        self.resample.link(self.capsfilter)
        self.capsfilter.link(self.anorm)


        self.anorm.link(self.encoder)
        

        
        self.filesink = Gst.ElementFactory.make("filesink")
        self.filesink.set_property('buffer-mode', 2)
        self.pipeline.add(self.filesink)
        self.encoder.link(self.filesink)


        src_filesink_pad = self.filesink.get_static_pad('sink')
        src_filesink_pad.add_probe(Gst.PadProbeType.EVENT_FLUSH, self.pad_filesink_probe)
        

        self.src.set_state(Gst.State.NULL)


    
    def on_pad_added(self, el, pad):
        if self.prerolled:
            return
        sink = self.aconv.get_static_pad('sink')
        pad.link(sink)
    

    def no_more_pads(self, el):
        if self.prerolled:
            return
        self.custom_message('do_seek')

    def custom_message(self, name):
        custom_structure = Gst.Structure.new_empty(name)
        custom_message = Gst.Message.new_application(None, custom_structure)
        self.bus.post(custom_message)

    def on_channel_added(self, el, pad):
        if self.prerolled:
            return
        pad.link(self.resample.get_static_pad('sink'))

    
    def run(self, location, output_folder):
        if not self.splits.empty():
            self.rp_event = Gst.Event.new_tag(self.info.get(location))
            self.pipeline.set_state(Gst.State.NULL)
            self.output_folder = output_folder
            os.makedirs(output_folder, exist_ok=True)
            self.src.set_property("location", location)
            
            self.current_segment = self.splits.get_nowait()
            self.filesink.set_property("location", os.path.join(self.output_folder, self.construct_name(self.current_segment[2])))
            self.prerolled = False
            self.pipeline.set_state(Gst.State.PAUSED)

            self.mainloop.run()
            

    def construct_name(self, index):
        return f'segment_{index:06}.wav'
    
    def save(self, start_time, end_time):
        self.splits.put_nowait((start_time, end_time, self.index))
        file_path = self.construct_name(self.index)
        self.index += 1
        return file_path

    def pad_filesink_probe(self, pad, info):
            event = info.get_event()
            if event.type == Gst.EventType.FLUSH_STOP:
                self.filesink.set_state(Gst.State.NULL)
                self.filesink.set_property("location", os.path.join(self.output_folder, self.construct_name(self.current_segment[2])))
                self.filesink.set_state(Gst.State.PLAYING)
                
            return Gst.PadProbeReturn.OK
    
    def do_seek(self):
        seek_flags = Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE |  Gst.SeekFlags.SEGMENT
        res = self.pipeline.seek(1.0, Gst.Format.TIME, seek_flags, Gst.SeekType.SET, self.current_segment[0] * Gst.SECOND, Gst.SeekType.SET, self.current_segment[1] * Gst.SECOND)
        if not res:
            raise Exception('Can\'t seek')
 
    
    def onMessage(self, bus: Gst.Bus, message: Gst.Message, loop: GLib.MainLoop):
        
        mtype = message.type
        if mtype == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
            self.mainloop.quit()
        elif message.type == Gst.MessageType.APPLICATION:
            if message.get_structure().get_name() == "do_seek":
                self.do_seek()
                self.prerolled = True
                self.pipeline.set_state(Gst.State.PLAYING)

        elif mtype == Gst.MessageType.SEGMENT_DONE:

            try:
                self.current_segment = self.splits.get_nowait()
                self.custom_message('do_seek')
                self.encoder.set_state(Gst.State.NULL)
                self.encoder.set_state(Gst.State.PLAYING)
            except Empty:
                self.bus.post(Gst.Message.new_eos())
        elif mtype == Gst.MessageType.STREAM_START:
            self.resample.get_static_pad('src').push_event(self.rp_event)

        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: %s: %s\n" % (err, debug))
            bus.post(Gst.Message.new_eos())

#Example
# s = Segmenter(sr=24000)
# s.save(0.05, 18.05)
# s.save(18.85, 21.450000000000003)
# s.save(21.8, 28.750000000000004)
# s.run('test_data/ggg.mp3', 'testoutput')
# s.save(23.8, 28.750000000000004)
# s.run('test_data/ggg.mp3', 'testoutput')

