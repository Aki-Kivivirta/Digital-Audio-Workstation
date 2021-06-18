# Kivy program configuration
from kivy import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand') # Remove the red dots on right clicks
Config.set('graphics', 'resizable', False) # Fixed size window

# Kivy imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.core.image import Image
from kivy.graphics import Color, Rectangle, Line, InstructionGroup

# Project files
from TopBar import TopBar
from TrackContainer import TrackContainer, MiddleBar
from GlobalAudioVariables import *

# General Python imports
import pyaudio
import numpy as np
import soundfile
import _thread
import librosa
import time
import gc

# Global variables
# Framerate and frames per second
frames_per_second = 40
fps_in_seconds = 1/frames_per_second


class MainView(BoxLayout):

    ########################################### Brief description ###########################################
    # MainView is the 'master' layout object. In addition to parenting the entire layout, it has the main 
    # program functinality such as recording, playback and changing cursor mode.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(MainView, self).__init__(**kwargs)

        # Define in which orientation objects are stacked inside this layout
        self.orientation = 'vertical'

        # Get store maximum window size for drawing the background
        Window.maximize()
        self.maximum_window_size = Window.size

        # Create the top bar
        self.TopBar = TopBar()
        self.add_widget(self.TopBar)

        # Create the middle layer which has controls for TrackContainer
        self.MiddleBar = MiddleBar()
        self.add_widget(self.MiddleBar)

        # Create box containing the recorded tracks
        self.TrackContainer = TrackContainer()
        self.add_widget(self.TrackContainer)

        # Bind touch_up to other areas than Track's objects to remove active_Track
        self.bind(on_touch_up=self.TrackContainer.remove_active_Track)

        # Boolean representing current state for recording. When initializing the program is not recording.
        self.recording_active = False

        # PyAudio object for creating the output sound
        self.PyAudio = pyaudio.PyAudio()

        # Boolean representing current state for playback. When initializing the program is not recording.
        self.playback_active = False

        # Dictionary where wavs of all SoundClips are stored
        self.wav_dict = {}

        # Variable indicating which mode cursor is on
        self.cursor_mode = ''

        # Activate keyboard
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self, 'text')
        if self._keyboard.widget:
            # If keyboard exists, this widget is a VKeyboard object which you can use to change the keyboard layout.
            pass
        self._keyboard.bind(on_key_down=self.change_SoundClip_editing_mode)

        # Look if cursor is on top of SoundClipField
        Window.bind(mouse_pos=self.change_cursor_on_hover)

        # Create SoundClip on file drop if it had been dropped on a SoundClipLayout
        Window.bind(on_dropfile=self.create_SoundClip_from_dropped_file)

        # Colors have to be initialized after the window has been created to get the correct coordinates. 
        Clock.schedule_once(self.init_colors)
        Clock.schedule_once(self.init_controls)
        Clock.schedule_once(self.bind_controls_to_methods)

        # Add one track which has recording on
        Clock.schedule_once(self.add_one_Track_on_init)


    def create_SoundClip_from_dropped_file(self, window_object, dropped_file_path, *args, **kwargs):
        # Convert path from bytes to string
        dropped_file_path = dropped_file_path.decode("utf-8") 

        # Check if dropped file is wav
        if dropped_file_path[-4:].lower() != '.wav':
            return # If not wav return out of method

        # Calculate mouse position in relation to SoundClipField
        dropped_relative_pos = self.TrackContainer.TrackSoundClipView.SoundClipField.to_widget(Window.mouse_pos[0], Window.mouse_pos[1], relative=True)

        # Add file to Track
        for track in self.TrackContainer.Tracks:

            # Check if file was dropped on this Track's TrackSoundClipLayout
            if track.TrackSoundClipLayout.collide_point(*dropped_relative_pos):

                # Switch to loading cursor 
                Window.set_system_cursor('wait')

                # Calculate starting sample based on where wav was dropped
                start_sample = int(self.MiddleBar.TrackScaleController.TimeAxisSlider.max * dropped_relative_pos[0] / self.TrackContainer.TrackSoundClipView.SoundClipField.width)

                # Restrict too long files or cut them to the correct length 
                samples_remaining = self.MiddleBar.TrackScaleController.TimeAxisSlider.max-start_sample        # Calculate maximum amount of samples which can be allowed
                samples, _ = librosa.load(dropped_file_path, sr=sampling_rate, dtype=np.float32)               # Open dropped wav
                samples = samples[0:samples_remaining]                                                         # Restrict amount of samples

                # Create new path name
                track.latest_recorded_audio_file = ".\\Recorded Audio Files\\"+str(track.Nth_track_created)+"_"+track.TrackControls.TrackNameField.text+"#"+str(track.audio_clip_counter)+".wav"
                
                # Increase counter so next audio file has a unique name and doesn't overwrite previous files
                track.audio_clip_counter += 1
                
                # Write new wav to new path
                soundfile.write(track.latest_recorded_audio_file, np.frombuffer(b''.join(samples), "Float32"), sampling_rate) 

                # Add the recorded SoundClip to Track and to layout
                track.add_SoundClip(track.latest_recorded_audio_file,                            # recorded_audio_path
                                    self.MiddleBar.TrackScaleController.TimeAxisSlider.max,      # samples_in_time_axis
                                    self.TrackContainer.Track_height,                            # Track_height
                                    self.TrackContainer.TrackSoundClipView.SoundClipField.width, # SoundClipField_width
                                    start_sample)                                                # start_sample
                track.TrackSoundClipLayout.add_widget(track.SoundClips[-1])

                # Place the SoundClip in the layout
                track.SoundClips[-1].y = track.TrackSoundClipLayout.y
                track.SoundClips[-1].x = track.SoundClips[-1].relative_x * self.TrackContainer.TrackSoundClipView.SoundClipField.width
                track.SoundClips[-1].move_plot()

                # Add the new SoundClip's wav to the dictionary
                self.wav_dict[track.SoundClips[-1].path], _ = librosa.load(track.SoundClips[-1].path, sr=sampling_rate, dtype=np.float32)

                # Switch back to normal cursor 
                Window.set_system_cursor('arrow')

                # Break out since dropped file can be added to only one Track
                break

    def _keyboard_closed(self):
        print('Keyboard not available!')
        self._keyboard.unbind(on_key_down=self.change_SoundClip_editing_mode)
        self._keyboard = None

    def change_SoundClip_editing_mode(self, keyboard, keycode, text, modifiers):
        # This method allows for changing cursor, which indicates for example that SoundClips are deleted/split/moved on press

        # Reference for changing cursor: https://www.reddit.com/r/kivy/comments/bx4h8n/is_there_any_way_to_change_the_mouse_cursor/
        if keycode == (8, 'backspace'):
            self.cursor_mode = 'backspace' # 'backspace' stands for removal of SoundClips
        elif keycode == (120, 'x'):
            self.cursor_mode = 'x' # 'x' stands for cutting SoundClips to separate SoundClips
        else:
            self.cursor_mode = '' # '' stands for normal mode where SoundClips can be moved around
            Window.set_system_cursor('arrow')

    def change_cursor_on_hover(self, *args, **kwargs):
        # collide point wasn't working, so ended up writing 'self.TrackContainer.TrackSoundClipView.collide_point(Window.mouse_pos)' with an if statement 

        # If mouse is on top of TrackSoundClipView and a different mode is accessed, change the cursor. Else keep the regular arrow cursor
        if Window.mouse_pos[0] >= self.TrackContainer.TrackSoundClipView.pos[0] and \
            Window.mouse_pos[0] <= self.TrackContainer.TrackSoundClipView.pos[0] + self.TrackContainer.TrackSoundClipView.size[0] and \
            Window.mouse_pos[1] >= self.TrackContainer.TrackSoundClipView.pos[1] and \
            Window.mouse_pos[1] <= self.TrackContainer.TrackSoundClipView.pos[1] + self.TrackContainer.TrackSoundClipView.size[1]:

            # Cursors:  arrow, ibeam, wait, crosshair, wait_arrow, size_nwse, size_nesw, size_we, size_ns, size_all, no, or hand.
            if self.cursor_mode == 'x':
                Window.set_system_cursor('ibeam')
            elif self.cursor_mode == 'backspace':
                Window.set_system_cursor('crosshair')
        else:
            Window.set_system_cursor('arrow')

    def init_colors(self, *args, **kwargs):
        # Init colors for different areas. Colors have been chosen by own taste.
        self.TopBar.init_gradient(self.size[1], 0.7, 0.5)
        self.TrackContainer.TrackControllerView.init_background_color(0.7,0.7,0.7, 1)
        self.TrackContainer.TrackSoundClipView.init_background_color(0.6,0.6,0.6, 1)
        self.MiddleBar.TrackScaleController.init_background_color(0.55,0.55,0.55, 1)
        self.MiddleBar.TrackAxis.init_background_color(0.45,0.45,0.45, 1)
        self.MiddleBar.TrackAddRemove.init_background_color(0.4,0.4,0.4, 1)

    def init_controls(self, *args, **kwargs):
        self.MiddleBar.init_controls()
        self.TopBar.init_buttons()
        self.TrackContainer.TrackSoundClipView.SoundClipField.width = self.TrackContainer.TrackSoundClipView.width

    def bind_controls_to_methods(self, *args, **kwargs):
        # TopBar binds
        self.TopBar.ScrollForwardButton.bind(on_release=self.MiddleBar.TrackAxis.TimeSlider.scroll_forward)
        self.TopBar.ScrollBackwardButton.bind(on_release=self.MiddleBar.TrackAxis.TimeSlider.scroll_backward)
        self.TopBar.PauseToBeginningButton.bind(on_release=self.pause_to_beginning)
        self.TopBar.PlayButton.bind(on_release=self.init_playback)
        self.TopBar.RecordButton.bind(on_release=self.init_recording)

        # MiddleBar binds
        self.MiddleBar.TrackScaleController.TimeAxisSlider.bind(value=lambda a, b : self.TrackContainer.change_Track_width(self.MiddleBar.TrackScaleController.TimeAxisSlider.value)) # Not sure if I fully understand how this lambda works. Why do the a,b have to be defined? My guess is that they are the self and new_time variables.
        self.MiddleBar.TrackScaleController.TrackHeightSlider.bind(value=self.TrackContainer.change_Track_height)
        self.MiddleBar.TrackAddRemove.AddTrackBtn.bind(on_release=self.TrackContainer.add_Track)
        self.MiddleBar.TrackAddRemove.RemoveTrackBtn.bind(on_release=self.TrackContainer.remove_Track)

        # TrackSoundClipView binds, bind scroll_y to move TrackControllerView
        self.TrackContainer.TrackSoundClipView.bind(scroll_y=self.TrackContainer.TrackControllerView.scroll_layout)

        # TrackControllerView binds, bind scroll_y to move TrackContainer
        self.TrackContainer.TrackControllerView.bind(scroll_y=self.TrackContainer.TrackSoundClipView.scroll_layout)

        # TimeSlider related
        self.TrackContainer.TrackSoundClipView.SoundClipField.bind(width=self.MiddleBar.TrackAxis.TimeSlider.change_width)
        self.MiddleBar.TrackAxis.TimeSlider.width = self.TrackContainer.TrackSoundClipView.SoundClipField.width
        self.TrackContainer.TrackSoundClipView.bind(scroll_x=self.MiddleBar.TrackAxis.scroll_layout)

        # Set TimeTable's maximum to match TimeSlider's maximum
        self.TopBar.TimeTable.max = self.MiddleBar.TrackAxis.TimeSlider.max/sampling_rate

    def add_one_Track_on_init(self, *args, **kwargs):
        # Add one track
        self.TrackContainer.add_Track()

        # Set the Track to record
        self.TrackContainer.Tracks[0].TrackControls.change_Track_recording_status()

    def pause_to_beginning(self, *args, **kwargs):
        # If not recording
        if not self.recording_active:
            # If playing audio, stop playback
            if self.playback_active:
                self.init_playback()

            # Set TimeSlider to the beginning
            self.MiddleBar.TrackAxis.TimeSlider.value = 0

    def init_recording(self, *args, **kwargs):
        # If not currently recording initiate recording
        if not self.recording_active:

            # Store the TimeSlider's starting position
            # value_pos is used instead of value, since value_pos gives the TimeSlider's position in relation to x.
            self.MiddleBar.TrackAxis.TimeSlider.start_x = self.MiddleBar.TrackAxis.TimeSlider.value_pos[0]
            self.MiddleBar.TrackAxis.TimeSlider.start_sample = self.MiddleBar.TrackAxis.TimeSlider.value

            # Bool to determine wheather to start recording process or not
            any_track_recording = False

            # Loop the Tracks which are have recording active
            for track in self.TrackContainer.Tracks:
                # Initiate the Track for recording, if recording_bool is True
                if track.TrackControls.recording_bool:
                    # Recording will start only if this is true
                    any_track_recording = True
                    # Set starting width to 1
                    track.RecordingPlotLayout.width = 1
                    # Start recording audio file in a new thread
                    _thread.start_new_thread(track.recording_process, (True, ))
                    # RecordingPlotLayout is a BoxLayout containing RecordingPlot. RecordingPlot doesn't want to be moved by it self eventhough it has
                    # 'pos' attribute, but it can be moved if it is inside a container.
                    track.RecordingPlotLayout.x = self.MiddleBar.TrackAxis.TimeSlider.start_x
                    # Don't quite understand why this is needed. Could be because RecordingPlotLayout is Track's children and not TrackSoundClipLayout's
                    track.RecordingPlotLayout.y = track.TrackSoundClipLayout.y
                    track.TrackSoundClipLayout.add_widget(track.RecordingPlotLayout)

                    # Unbind the method to be able to change Track's recording status
                    track.TrackControls.RecBoolBtn.unbind(on_release=track.TrackControls.change_Track_recording_status)

            # If any track is recording, start recording process
            if any_track_recording:
                # Start clock
                Clock.schedule_interval(self.recording_process, fps_in_seconds)

                # Reverse the bool so that the next call will stop recording
                self.recording_active = True

                # Forbid the user from scrolling forward/backward, pausing to beginning or initiating playback while recording
                self.TopBar.ScrollForwardButton.unbind(on_release=self.MiddleBar.TrackAxis.TimeSlider.scroll_forward)
                self.TopBar.ScrollBackwardButton.unbind(on_release=self.MiddleBar.TrackAxis.TimeSlider.scroll_backward)
                self.TopBar.PauseToBeginningButton.unbind(on_release=self.pause_to_beginning)
                self.TopBar.PlayButton.unbind(on_release=self.init_playback)

            else:
                # A popup window which tells the user no channel is recording and how to fix it
                no_track_recording_popup = Popup(title='No Track is recording', 
                      content=Label(text="Plese select a track to record by pressing \nthe 'R' button until it changes color.",
                      line_height=1.1), size_hint=(0.3,0.3))
                no_track_recording_popup.open()

        # End recording
        else:
            # Reverse the bool so that the next call will start recording
            self.recording_active = False
            # Clock has to be unschedule not stopped. If stop_clock() is used, all of the schedule_interval calls will
            # build up in use. In the case of this recording animation, the animation was increasing faster after each iteration.
            Clock.unschedule(self.recording_process)

            # Loop the Tracks which are have recording active
            for track in self.TrackContainer.Tracks:
                # If track was recording
                if track.receiving_audio:
                    track.TrackSoundClipLayout.remove_widget(track.RecordingPlotLayout)

                    # Stop recording audio
                    track.recording_process(False)

                    # Add the recorded SoundClip to Track and to layout
                    track.add_SoundClip(track.latest_recorded_audio_file,                             # recorded_audio_path
                                        self.MiddleBar.TrackScaleController.TimeAxisSlider.max,       # samples_in_time_axis
                                        self.TrackContainer.Track_height,                             # Track_height
                                        self.TrackContainer.TrackSoundClipView.SoundClipField.width,  # SoundClipField_width
                                        self.MiddleBar.TrackAxis.TimeSlider.start_sample)             # start_sample
                    track.TrackSoundClipLayout.add_widget(track.SoundClips[-1])

                    # Place the SoundClip in the layout
                    track.SoundClips[-1].y = track.TrackSoundClipLayout.y
                    track.SoundClips[-1].x = track.SoundClips[-1].relative_x * self.TrackContainer.TrackSoundClipView.SoundClipField.width
                    track.SoundClips[-1].move_plot()

                    # Add the new SoundClip's wav to the dictionary
                    self.wav_dict[track.SoundClips[-1].path], _ = librosa.load(track.SoundClips[-1].path, sr=sampling_rate, dtype=np.float32)

                    # Reconnect the bind to the method controling wheather Track is recording or not
                    track.TrackControls.RecBoolBtn.bind(on_release=track.TrackControls.change_Track_recording_status)

            # Allow the user to use the methods which were prohibited during recording
            self.TopBar.ScrollForwardButton.bind(on_release=self.MiddleBar.TrackAxis.TimeSlider.scroll_forward)
            self.TopBar.ScrollBackwardButton.bind(on_release=self.MiddleBar.TrackAxis.TimeSlider.scroll_backward)
            self.TopBar.PauseToBeginningButton.bind(on_release=self.pause_to_beginning)
            self.TopBar.PlayButton.bind(on_release=self.init_playback)

    def recording_process(self, *args, **kwargs):
        # Default is that the recoding wont stop
        end_recording = False

        # Loop through the Tracks and at the first one which is recording, increase the TimeSlider's position and break out of the loop since it needs to be done only once.
        for track in self.TrackContainer.Tracks:
            if track.TrackControls.recording_bool:

                # Increase TimeSlider's position. Done this way to prevent anything from happening if the user grabs TimeSlider when recording
                self.MiddleBar.TrackAxis.TimeSlider.value = self.MiddleBar.TrackAxis.TimeSlider.start_sample + len(track.recorded_buffers)*samples_per_recording_buffer

                # If TimeSlider has reached its end==maximum value, end_recording will be True and recording will end.
                if self.MiddleBar.TrackAxis.TimeSlider.value >= self.MiddleBar.TrackAxis.TimeSlider.max:
                    self.MiddleBar.TrackAxis.TimeSlider.value = self.MiddleBar.TrackAxis.TimeSlider.max
                    end_recording = True

                # Break after the looking how many samples the first recording Track has recorded. All Tracks should record roughly the same amount of samples
                break

        # Go through all tracks. If the track is recording, increase the recoring animation's width to match the TimeSlider's position.
        for track in self.TrackContainer.Tracks:
            if track.TrackControls.recording_bool:
                track.RecordingPlotLayout.width = self.MiddleBar.TrackAxis.TimeSlider.value_pos[0]-self.MiddleBar.TrackAxis.TimeSlider.start_x

        # If TimeSlider has reached its end==maximum value, end_recording will be True and recording will end.
        if end_recording:
            self.init_recording()

    def init_playback(self, *args, **kwargs):
        # This if else is because pushing the same button activates the same event and passing a variable would
        # require partial functions which are more complex than this implementation.
        if self.playback_active:
            self.playback_active = False
            # Change displayed image
            self.TopBar.PlayButton.background_normal='.\\Icons\\play.png'
        else:
            self.playback_active = True
            # Change displayed image
            self.TopBar.PlayButton.background_normal='.\\Icons\\pause.png'

        # Start playback
        if self.playback_active:

            # Forbid the user from recording while playback is on
            self.TopBar.RecordButton.unbind(on_release=self.init_recording)

            # Open a .Stream object to write the WAV file to 'output = True' indicates that the sound will be played rather than recorded
            self.audio_output_stream = self.PyAudio.open(
                                format=pyaudio.paFloat32,
                                channels = number_of_output_channels,
                                rate = sampling_rate,
                                output = True,
                                stream_callback=self.playback_audio_callback,
                                frames_per_buffer=samples_per_playback_buffer)

            # Start streaming audio to output
            self.audio_output_stream.start_stream()

            # Check if TimeSlider has reached its maximum value and playback has to be stopped
            Clock.schedule_interval(self.playback_end_check, 1/10)

        else:
            # Stop output audio stream
            self.audio_output_stream.stop_stream()

            # Close audio output stream
            self.audio_output_stream.close()

            # Stop checking if TimeSlider has reached its maximum value
            Clock.unschedule(self.playback_end_check)

            # If there are Tracks, send zeros to LevelIndicators to decay them to silence
            if len(self.TrackContainer.Tracks) > 0:
                Clock.schedule_interval(self.decay_LevelIndicators_to_silence,playback_buffer_time)

            # Allow user to start recording
            self.TopBar.RecordButton.bind(on_release=self.init_recording)


    def decay_LevelIndicators_to_silence(self, *args, **kwargs):
        # If playback has started again, unschedule this method and return out
        if self.playback_active:
            Clock.unschedule(self.decay_LevelIndicators_to_silence)
            return

        # Initialize LevelIndicator average as 0
        LevelIndicator_average = 0

        # Loop all Tracks and send zero to the LevelIndicator
        for track in self.TrackContainer.Tracks:
            # Send zeros to LevelIndicator
            track.TrackControls.VolumeSliderBox.LevelIndicator.calculate_level(float(0))

            # Add new level to averages
            LevelIndicator_average += track.TrackControls.VolumeSliderBox.LevelIndicator.value

        # Send zeros to MasterVolume LevelIndicator
        self.TopBar.MasterVolume.LevelIndicator.calculate_level(float(0))

        # Add the MasteVolume level to averages
        LevelIndicator_average += self.TopBar.MasterVolume.LevelIndicator.value

        # Calculate average
        LevelIndicator_average /= len(self.TrackContainer.Tracks)+1 # The amount of Tracks + 1 MasterVolume

        # If all LevelIndicators are below min (if they reach min they are set to below min, so the indicator can't be seen), unschedule this method
        if LevelIndicator_average <= track.TrackControls.VolumeSliderBox.LevelIndicator.min:
            # Force all of the LevelIndicators to their minimum to make sure all of them will be hidden
            for track in self.TrackContainer.Tracks:
                track.TrackControls.VolumeSliderBox.LevelIndicator.value = track.TrackControls.VolumeSliderBox.LevelIndicator.min

            # Hide MasterVolume LevelIndicator
            self.TopBar.MasterVolume.LevelIndicator.value = self.TopBar.MasterVolume.LevelIndicator.min

            # Unschedule this method
            Clock.unschedule(self.decay_LevelIndicators_to_silence)

    def playback_audio_callback(self, in_data, frame_count, time_info, status):
        ##########################
        # Inspiration for lighter realtime playback to be implemented in the future. Currently all existing wavs are always open in 'wav_dict'
        # https://stackoverflow.com/questions/28743400/pyaudio-play-multiple-sounds-at-once
        # https://stackoverflow.com/questions/30071822/pyaudio-how-to-get-sound-on-only-one-speaker
        # https://stackoverflow.com/questions/18721780/play-a-part-of-a-wav-file-in-python
        ##########################

        # Initialize output buffer where audio will be summed to
        output_buffer = np.zeros( (samples_per_playback_buffer,2), dtype=np.float32)

        # TimeSlider's position in seconds
        TimeSlider_sample = int(self.MiddleBar.TrackAxis.TimeSlider.value)

        # Move TimeSlider to the next buffer's position. Having this increment here, allows for multiple buffers to be processed simultaneously, since one thread doesn't have to be processed till the end while the next one has TimeSlider in the correct value.
        self.MiddleBar.TrackAxis.TimeSlider.value += samples_per_playback_buffer

        # List of Tracks which will be played
        tracks_to_be_played = []

        # List of Tracks which aren't played. These Tracks' level indicator will receive values below level indicator minimum
        tracks_not_soloed = []

        # Look if there are soloed tracks
        for track in self.TrackContainer.Tracks:
            if track.TrackControls.solo_bool:
                tracks_to_be_played.append(track)
            else:
                tracks_not_soloed.append(track)

        # If there were no soloed Tracks, loop through all tracks
        if len(tracks_to_be_played) == 0:
            tracks_to_be_played = self.TrackContainer.Tracks
            tracks_not_soloed = []


        # Go through tracks. If the track is not muted add (sum together) the audio buffer which corresponds to the TimeSlider's position.
        for track in tracks_to_be_played:

            # If mute is on, move to the next Track and send zeros to LevelIndicator
            if track.TrackControls.mute_bool:
                track.TrackControls.VolumeSliderBox.LevelIndicator.calculate_level(float(0))
                continue

            for clip in track.SoundClips:

                # Once the program crashed inside the first if due to: 'ValueError: operands could not be broadcast together with shapes (1024,) (517,) (1024,)'
                # Couldn't replicate this bug but added try except to prevent crashing. While debugging this found out that the second and third elif were called 
                # more than once which was unexpected. This might be explained by the prints used for debugging inside the if elif chain slowing donwn the program
                # and multiple threads reaching this the same section before TimeSlider was incremented or something similar.

                # Level indicator has to use audio_buffer to get the individual Track levels. If not the latter Tracks get the levels of all Tracks combined.
                audio_buffer = np.zeros( (samples_per_playback_buffer,1), dtype=np.float32)

                try:
                    # If TimeSlider is in between the SoundClip's start and end
                    if TimeSlider_sample > clip.start_sample and TimeSlider_sample+samples_per_playback_buffer < clip.start_sample+clip.length_in_samples:
                        # Read a buffer of audio from wav file which TimeSlider is on
                        audio_buffer = self.wav_dict[clip.path][TimeSlider_sample-clip.start_sample : TimeSlider_sample+samples_per_playback_buffer-clip.start_sample]

                    # If the wav starts in the middle of the buffer
                    elif TimeSlider_sample < clip.start_sample and TimeSlider_sample+samples_per_playback_buffer >= clip.start_sample:
                        # Read the start from wav
                        audio_buffer = self.wav_dict[clip.path][0 : TimeSlider_sample+samples_per_playback_buffer-clip.start_sample]
                        # Add zeros to the beginning
                        audio_buffer = np.concatenate( (np.zeros(samples_per_playback_buffer-audio_buffer.size),audio_buffer), axis=0)

                    # If the wav ends during this buffer 
                    elif TimeSlider_sample < clip.start_sample+clip.length_in_samples and TimeSlider_sample+samples_per_playback_buffer > clip.start_sample+clip.length_in_samples:
                        # Read the end of the buffer
                        audio_buffer = self.wav_dict[clip.path][TimeSlider_sample-clip.start_sample : clip.length_in_samples]
                        # Add zeros to the end
                        audio_buffer = np.concatenate( (audio_buffer,np.zeros(samples_per_playback_buffer-audio_buffer.size)), axis=0)

                except:
                    print("Unmatching buffer sizes with, path: "+str(clip.path)+", TimeSlider_sample: "+str(TimeSlider_sample))

                # Apply Track's volume to output_buffer
                audio_buffer *= track.TrackControls.VolumeSliderBox.VolumeSlider.linear_gain_factor

                # Change level indicator level. Levels are calculated from the current audio_buffer's highest absolute value.
                track.TrackControls.VolumeSliderBox.LevelIndicator.calculate_level(float(np.amax(np.absolute(audio_buffer))))

                # Calculate left and right channel gains according to the panning slider
                right_channel_gain = track.TrackControls.TrackPanSlider.value # The more right the slider is the higher the Slider values are
                left_channel_gain = float(1)-right_channel_gain

                # Sum the read samples to the output buffer and apply channel gains. For some reason 'audio_buffer' has shape '(samples_per_playback_buffer,)' rather than '(samples_per_playback_buffer,1)' on at least the second iteration, which has to be fixed by using '.reshape(samples_per_playback_buffer,1)'.
                output_buffer += np.concatenate((left_channel_gain*audio_buffer.reshape(samples_per_playback_buffer,1), right_channel_gain*audio_buffer.reshape(samples_per_playback_buffer,1)), axis=1)

        # Apply output volume/gain to output_buffer
        output_buffer *= self.TopBar.MasterVolume.VolumeSlider.linear_gain_factor

        # Apply Parametric Equalizer (PEQ) filters
        output_buffer[:,0] = self.TopBar.PEQPopup.PEQLayout.filter_audio(output_buffer[:,0], 0)
        output_buffer[:,1] = self.TopBar.PEQPopup.PEQLayout.filter_audio(output_buffer[:,1], 1)

        # Plot mono output signal fft in PEQPopup
        self.TopBar.PEQPopup.PEQLayout.realtime_input_fft(np.add(output_buffer[:,0],output_buffer[:,1]))

        # Change output level indicator level. Levels are calculated from the current output_buffer's highest absolute value.
        self.TopBar.MasterVolume.LevelIndicator.calculate_level(float(np.amax(np.absolute(output_buffer))))

        # Send value below level indicator minimum to the rest of Tracks which aren't soloed. HOX can't send float(0) to level indicator
        # because it will result in -inf dB which will cause the level indicator to stay at -inf. 
        level_indicator_minimum = self.TrackContainer.Tracks[0].TrackControls.VolumeSliderBox.LevelIndicator.min # All LevelIndicators have the same minimum
        for non_soloed_track in tracks_not_soloed:
            non_soloed_track.TrackControls.VolumeSliderBox.LevelIndicator.calculate_level(level_indicator_minimum-1)

        # Return output_buffer as bytes and continue streaming. End check is done in self.playback_end_check.
        return (output_buffer.tobytes(), pyaudio.paContinue)

    def playback_end_check(self, *args, **kwargs):
        # Don't know if playback callback method 'playback_audio_callback' should be stopped by returning 'pyaudio.paComplete' rather than this function.
        # There were no examples how to 'stop_stream()' or 'close()' after 'paComplete' would have been returned which is problematic since the callback 
        # is called on a separate thread. This seems to work for now, but I don't know if this will scale for larger audio files.

        # Check if TimeSlider has reached/surpassed its maximum value, playback is stopped
        if self.MiddleBar.TrackAxis.TimeSlider.value >= self.MiddleBar.TrackAxis.TimeSlider.max:
            self.MiddleBar.TrackAxis.TimeSlider.value = self.MiddleBar.TrackAxis.TimeSlider.max
            self.init_playback()

    def destructor(self, *args, **kwargs):
        # Terminate the PyAudio instance
        self.PyAudio.terminate()

        # Delete and free memory from wav_dict
        del self.wav_dict
        gc.collect()


class DAWApp(App):

    def build(self):
        # Change the logo of window's top left corner
        self.icon = '.\\Icons\\recording_symbol.png'

        # Change window's top bar's text
        self.title = 'Pygic' # Python + Logic

        # Create an instance of MainView which can be called from '__main__' when closing the program
        self.MainView = MainView()

        # Start main program
        return self.MainView

if __name__=='__main__':
    # Create an instance of the main app
    DAWApp = DAWApp()
    DAWApp.run()

    # On this line app has been closed. Run destructor which closes opened processes
    DAWApp.MainView.destructor()
