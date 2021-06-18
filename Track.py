# Kivy imports
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, InstructionGroup

# Project files
from SoundClip import SoundClip
from VolumeSliderBox import VolumeSliderBox
from GlobalAudioVariables import *

# General Python imports
import random 
import pyaudio
import soundfile
import numpy as np
import gc


class ColorWheel(ColorPicker):

    ########################################### Brief description ###########################################
    # ColorWheel is the object inside of ColorPickerPopup which allows the user to change Track's SoundClips'
    # color.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(ColorWheel, self).__init__(**kwargs)

        # There was lots of unnecessary parts in ColorPicker so all except the "wheel" were removed.
        for c in self.wheel.parent.children:
            if c != self.wheel:
                self.wheel.parent.remove_widget(c)

        # Have some other color than white when Track is added
        self.color = (random.random(),random.random(),random.random(), 1)


class ColorPickerPopup(Popup):

    ########################################### Brief description ###########################################
    # ColorPickerPopup allows the user to change a Track's SoundClip's color. ColorPickerPopup can be opened
    # by pressing the 'C' button on each TrackControls. Just like all popups, ColorPickerPopup can be closed
    # by clicking outside the popup.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(ColorPickerPopup, self).__init__(**kwargs)

        # Set popup window size
        self.size_hint = (0.4,0.4)

        # Omit title text
        self.title = ""

        # Set title underline where it is not visible
        self.separator_height = 0

        # Add ColorWheel object
        self.ColorWheel = ColorWheel()
        self.add_widget(self.ColorWheel)


class TrackNameField(TextInput):

    ########################################### Brief description ###########################################
    # TrackNameField is a TextInput field located at each Track's TrackControls layout upper left corner
    # which holds the Track's name. Track's name can be altered by clicking TrackNameField. Track name is 
    # used at the moment only to name Track's wav files.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TrackNameField, self).__init__(**kwargs)

        # Disallow multiline text
        self.multiline = False

        # Set colors
        self.foreground_color = (1,1,1, 0.9) # White text
        self.background_color = (0,0,0, 0)   # Transparent background

        # Define size
        self.size_hint=(0.4,None)
        self.height = 30

        # Define position
        self.pos_hint={'top':0.9,'left':0.9}

        # Bind pressing self to a method
        self.bind(focus=self.alter_name)

    def alter_name(self, instance, value, *args, **kwargs):
        # Change colors when self is selected
        if value:
            self.foreground_color = (0,0,0, 0.9) # Black text
            self.background_color = (1,1,1, 0.9) # White background

        # Return to init colors when pressed out of self
        else:
            self.foreground_color = (1,1,1, 0.9) # White text
            self.background_color = (0,0,0, 0)   # Transparent background


class TrackControls(FloatLayout):

    ########################################### Brief description ###########################################
    # TrackControls is a layout which stores objects controling the Track. TrackControls objects are stacked 
    # to TrackControllerField (TrackContainer.py), located in the left side of the main layout.
    #########################################################################################################

    def __init__(self, Nth_track_created, **kwargs):
        super(TrackControls, self).__init__(**kwargs)

        # Text field for Track's name
        self.TrackNameField = TrackNameField(text="Track "+str(Nth_track_created))
        self.add_widget(self.TrackNameField)

        # Slider controling the Track's volume/gain
        self.VolumeSliderBox = VolumeSliderBox(size_hint=(1,1), pos_hint={'top':0.9, 'right':1})
        self.add_widget(self.VolumeSliderBox)

        # Button for controling if the Track is recording or not
        self.MuteBoolBtn = Button(text="M", size_hint=(None,None), size=(10,10), pos_hint={'center_x':0.05, 'top':0.4})
        self.add_widget(self.MuteBoolBtn)

        # Bool for wheather the channel is muted or not
        self.mute_bool = False

        # Bind MuteBoolBtn to its method
        self.MuteBoolBtn.bind(on_release=self.change_Track_mute_status)

        # Button for controling if the Track is soloed for playback or not
        self.SoloBoolBtn = Button(text="S", size_hint=(None,None), size=(10,10), pos_hint={'center_x':0.15, 'top':0.4})
        self.add_widget(self.SoloBoolBtn)

        # Boolean for representing if the Track is soloed
        self.solo_bool = False

        # Bind MuteBoolBtn to its method
        self.SoloBoolBtn.bind(on_release=self.change_Track_solo_status)

        # Button for controling if the Track is recording or not
        self.RecBoolBtn = Button(text="R", size_hint=(None,None), size=(10,10), pos_hint={'center_x':0.25, 'top':0.4})
        self.add_widget(self.RecBoolBtn)

        # Boolean for representing if the Track is recorded to
        self.recording_bool = False

        # Bind MuteBoolBtn to its method
        self.RecBoolBtn.bind(on_release=self.change_Track_recording_status)

        # Icon image, optional
        self.ColorPickerPopup = ColorPickerPopup()
        self.ColorPickerBtn = Button(text="C", color=self.ColorPickerPopup.ColorWheel.color, size_hint=(None,None), size=(10,10), pos_hint={'center_x':0.35, 'top':0.4})
        self.add_widget(self.ColorPickerBtn)
        self.ColorPickerBtn.bind(on_release=self.ColorPickerPopup.open)

        # Slider for controling the Track's panning between left and right channels
        self.TrackPanSlider = Slider(orientation='horizontal', size_hint=(None,None), size=(180,10), min=0,max=1,value=0.5, pos_hint={'right':1, 'top':0.4})
        self.add_widget(self.TrackPanSlider)

    def change_Track_mute_status(self, *args, **kwargs):
        if self.mute_bool:
            # If the channel was muted, turn mute off and set the original color
            self.mute_bool = False
            self.MuteBoolBtn.color = (1,1,1, 1)
            self.MuteBoolBtn.background_color = (1,1,1, 1)
        else:
            # If the channel wasn't muted, turn mute on and set active color
            self.mute_bool = True
            self.MuteBoolBtn.color = (0.6,0.6,1, 1)
            self.MuteBoolBtn.background_color = (0.5,0.5,0.5, 1)

    def change_Track_recording_status(self, *args, **kwargs):
        if self.recording_bool:
            # If the channel had recording active, turn recording off and change color color
            self.recording_bool = False
            self.RecBoolBtn.color = (1,1,1, 1)
            self.RecBoolBtn.background_color = (1,1,1, 1)
        else:
            # If the channel didn't have recording active, turn recording on and change color color
            self.recording_bool = True
            self.RecBoolBtn.color = (0.7,0.1,0.1, 1)
            self.RecBoolBtn.background_color = (0.6,0.6,0.6, 1)

    def change_Track_solo_status(self, *args, **kwargs):
        if self.solo_bool:
            # If the channel had recording active, turn recording off and change color color
            self.solo_bool = False
            self.SoloBoolBtn.color = (1,1,1, 1)
            self.SoloBoolBtn.background_color = (1,1,1, 1)
        else:
            # If the channel didn't have recording active, turn recording on and change color color
            self.solo_bool = True
            self.SoloBoolBtn.color = (0.9,1,0.1, 1)
            self.SoloBoolBtn.background_color = (0.6,0.6,0.6, 1)


class RecordingPlotLayout(BoxLayout):

    ########################################### Brief description ###########################################
    # RecordingPlotLayout is a red box which appears when a Track is recording. RecordingPlotLayout's length
    # indicates how much has been recorded.
    #########################################################################################################

    def __init__(self, **kwargs):
        super(RecordingPlotLayout, self).__init__(**kwargs)

        # Was using a Graph previously, but it had unsolvable Warnings (invalid frustrum...) so switched to a canvas instead

        # Create instructions for canvas and add it
        self.canvas_instructions = InstructionGroup()
        self.canvas_instructions.add(Color(rgba=(0.7,0.1,0.1, 1)))
        self.canvas_instructions.add(Rectangle(size=self.size,pos=self.pos))
        self.canvas.add(self.canvas_instructions)

        # Bind canvas to match size
        self.bind(size=self.resize_canvas)

        # Init size
        self.size_hint = (None,None)
        self.width = 1

    def resize_canvas(self, *args, **kwargs):
        # Remove and clear old canvas
        self.canvas.remove(self.canvas_instructions)
        self.canvas_instructions.clear()

        # Instructions for new canvas
        self.canvas_instructions.add(Color(rgba=(0.7,0.1,0.1, 1)))
        self.canvas_instructions.add(Rectangle(size=self.size,pos=self.pos))

        # Add new canvas
        self.canvas.add(self.canvas_instructions)


class Track:

    ########################################### Brief description ###########################################
    # Track is the class which contains all objects related to a single Track.
    #########################################################################################################

    def __init__(self, Nth_track_created, *args, **kwargs):
        super(Track, self).__init__(*args, **kwargs)

        # Layout displaying how Track's recording is progressing with a red box
        self.RecordingPlotLayout = RecordingPlotLayout()

        # Layout containing Track specific controls. Is added to TrackController in TrackContainer.py.
        self.TrackControls = TrackControls(Nth_track_created)

        # Layout containing Track object's SoundClip objects visually. Is added to TrackSoundClipView's SoundClipField in TrackContainer.py.
        self.TrackSoundClipLayout = FloatLayout()

        # A list which contains SoundClip objects
        self.SoundClips = []

        # Bind y of self.TrackControls and SoundClips to match
        self.TrackControls.bind(y=self.match_Track_attributes_ys)

        # Bind ColorWheel to change the color of SoundClips. Method call is triggered when color attribute is changed.
        self.TrackControls.ColorPickerPopup.ColorWheel.bind(color=self.change_color)

        # Basic object for recording audio
        self.audio = pyaudio.PyAudio()

        # Add variable for latest recorded clip of audio
        self.latest_recorded_audio_file = ''

        # Counter for how many audio clips have been recorded. Used when naming recorded audio files.
        self.audio_clip_counter = 0

        # Bool for if track is receiving audio data
        self.receiving_audio = False

        # Initiate list for holding audio buffers
        self.recorded_buffers = []

        # Unique number used for naming unique audio file names
        self.Nth_track_created = Nth_track_created

    def match_Track_attributes_ys(self, *args, **kwargs):
        # Match RecordingPlotLayout's y with TrackControl box y
        self.RecordingPlotLayout.y = self.TrackControls.y

        # Match all SoundClips y coordinate to the TrackControl box y.
        for clip in self.SoundClips:
            clip.y = self.TrackControls.y

    def recording_process(self, start_or_stop_rec=True, *args, **kwargs):
        # start_or_stop_rec==True->Start recording, False->Stop recording
        if start_or_stop_rec:
            # Initiate audio input stream
            self.stream = self.audio.open(format=pyaudio.paFloat32, channels=number_of_input_channels, rate=sampling_rate, input=True, frames_per_buffer=samples_per_recording_buffer)
            # List containing received audio buffers
            self.recorded_buffers = []
            # Make sure the loop starts
            self.receiving_audio = True

            # Start receiving audio until self.recording_process(False) is called
            while self.receiving_audio:
                data = self.stream.read(samples_per_recording_buffer)
                self.recorded_buffers.append(data)

        else:
            # Stop while loop in the separate thread
            self.receiving_audio = False

            # Stop and close the audio stream
            self.stream.stop_stream()
            self.stream.close()

            # Save the recorded file's name so this file can be added to the GUI
            self.latest_recorded_audio_file = ".\\Recorded Audio Files\\"+str(self.Nth_track_created)+"_"+self.TrackControls.TrackNameField.text+"#"+str(self.audio_clip_counter)+".wav"
            # Increase counter so next audio file has a unique name and doesn't overwrite previous files
            self.audio_clip_counter += 1
            # Write the audio file
            soundfile.write(self.latest_recorded_audio_file, np.frombuffer(b''.join(self.recorded_buffers), "Float32"), sampling_rate)

            # Delete and free memory from the recorded audio
            del self.recorded_buffers
            gc.collect()

            # Create new list for buffers
            self.recorded_buffers = []
        
    def set_height(self, height, *args, **kwargs):
        # Fast changes look glitchy, because height increase of these objects doesn't match the speed at which the layout is increased
        self.TrackControls.height = height
        self.RecordingPlotLayout.height = height

        # Change all SoundClips height
        for clip in self.SoundClips:
            clip.height = height

    def change_color(self, *args, **kwargs):
        # Change the color button's letter color
        self.TrackControls.ColorPickerBtn.color = self.TrackControls.ColorPickerPopup.ColorWheel.color

        # Change plot colors
        for clip in self.SoundClips:
            clip.SoundClipPlot.background_color = self.TrackControls.ColorPickerPopup.ColorWheel.color

    def add_SoundClip(self, recorded_audio_path, samples_in_time_axis, Track_height, SoundClipField_width, start_sample, *args, **kwargs):
        # Append new SoundClip to self's list
        self.SoundClips.append(SoundClip(recorded_audio_path, samples_in_time_axis, Track_height, SoundClipField_width, self.TrackControls.ColorPickerPopup.ColorWheel.color, start_sample))
