# Kivy imports
from kivy.uix.button import Button
from kivy.graphics import Color
from kivy.garden.graph import Graph, MeshStemPlot
from kivy.core.window import Window

# Project files
from GlobalAudioVariables import *

# General Python imports
import gc
import numpy as np
import librosa
import soundfile

# Global variables
# Define some pixel which is most likely never reaced
impossible_pixel = (-999,-999)


class MoveableButton(Button):

    ########################################### Brief description ###########################################
    # MoveableButton is a Button object which tracks the mouse once pressed. Horizontal (=x) movement is free, 
    # but vertical (=y) changes are bounded to Track height.
    #########################################################################################################

    def __init__(self, **kwargs):
        super(MoveableButton, self).__init__(**kwargs)

        # Few times a dragged SoundClip has jumped few hundred pixels to the left which would suggest 'self.prev_mouse_pos[0]' was 
        # incorrectly initialized. This 'feature' appeared when I had wildly changed SoundClipField's width.

        # A pixel which is never reached
        self.prev_mouse_pos = impossible_pixel

        # Bool used to allow only one MoveableButton to be moved at a time
        self.pressed = False

    def on_touch_move(self, touch):
        # If the user is grabbing self or if self is under mouse and pressed bool is true
        if (touch.grab_current == self or self.collide_point(*touch.pos)) and self.pressed:

            # On first press, prev_mouse_pos is set to previous position. Impemented this way the user can grab and drag self from any point.
            if self.prev_mouse_pos != impossible_pixel:
                self.pos[0] = self.pos[0]+touch.pos[0]-self.prev_mouse_pos[0]

                # Naming parent chains for clarity
                SoundClipField = self.parent.parent

                # If there are more than one tracks SoundClipField's (GridLayout) height is larger than single track's heigh AND if the mouse moves higher AND mouse is not above SoundClipField, the soundclip is moved up.
                if SoundClipField.height > self.height and touch.pos[1] > (self.pos[1]+self.height) and touch.pos[1] < SoundClipField.height:
                    self.pos[1] = self.pos[1]+self.height

                # If there are more than one tracks SoundClipField's (GridLayout) height is larger than single track's heigh AND if the mouse moves lower AND mouse is not below SoundClipField , the soundclip is moved down.
                if SoundClipField.height > self.height and touch.pos[1] < (self.pos[1]) and touch.pos[1] > 0:
                    self.pos[1] = self.pos[1]-self.height

            self.prev_mouse_pos = touch.pos

    def on_release(self, *args, **kwargs):
        # Return to the initial state
        self.prev_mouse_pos = impossible_pixel
        self.pressed = False

    def on_press(self, *args, **kwargs):
        # Used to prevent the user from dragging more than one self at a time. Since only one pressed bool can be true at a time.
        self.pressed = True


class SoundClipPlot(Graph):

    ########################################### Brief description ###########################################
    # SoundClipPlot is the graph containing a SoundClip's wav waveform.
    #########################################################################################################

    def __init__(self,**kwargs):
        super(SoundClipPlot, self).__init__(**kwargs)

        # Which values of the wav file are plotted. Starting from the first sample (xmin=0), plot amplitude values between -1 and 1. To 'add gain'/zoom in to the plots you can use smaller ymin and ymax values.
        self.xmin = 0
        self.ymin = -1
        self.ymax = 1

        # Remove x and y axes from plots and remove the defaul padding to center the wav plot.
        self.border_color = [0,0,0, 0] # the alpha has to be 0, the rgb values don't make a difference when alpha=0.
        self.padding = 0 # Graph.padding is receives only single value, rather than [left,top,right,down] or single value


class SoundClip(MoveableButton):

    ########################################### Brief description ###########################################
    # SoundClip is a MoveableButton which has SoundClipPlot bounded to its position. SoundClip's horizontal
    # position (=x) changes when its wav is played and vertical position (=y), to which Track it belongs to.
    # Different Tracks can have different volume (=gain) and stereo panning settings. 
    #   
    # SoundClips can be split when the user has pressed 'x' and the cursor has changed to an ibeam and
    # deleted when user has pressed 'backspace' and cursor has changed to a crosshair. Splitting splits
    # a single SoundClip in to two SoundClips from the clicked position and deleting deletes the clicked
    # SoundClip. Both of these modes can be exited by pressing any other key which is indicated by the
    # cursor changing to the regular arrow type. SoundClips are dragged in the normal mode. More on
    # changing SoundClip editing modes from change_SoundClip_editing_mode in main.py
    #########################################################################################################

    def __init__(self, recorded_audio_path, samples_in_time_axis, height, SoundClipField_width, color, start_sample, *args, **kwargs):
        super(SoundClip, self).__init__(*args, **kwargs)

        # Set the button's color to transparent so it is never visible
        self.background_color = (0,0,0, 0)

        # Where this SoundClip's audio file is found from
        self.path = recorded_audio_path
        # Read wav file, librosa doesn't have a close
        amplitudes, _ = librosa.load(self.path, sr=sampling_rate, dtype=np.float32)

        # Define SoundClip's size not to depend on layout size
        self.size_hint = (None,None)

        # Calculate the length of this SoundClip in pixels by getting its size percentages of all samples available and multiplying that by the amount of pixels in that same area
        self.length_in_samples = len(amplitudes)
        clip_length_in_pixels = (self.length_in_samples/samples_in_time_axis) * SoundClipField_width
        self.size = (clip_length_in_pixels, height)

        # Init the audio waveform plot
        self.SoundClipPlot = SoundClipPlot(size_hint=(None,None),size=self.size)
        self.SoundClipPlot.background_color = color
        self.add_widget(self.SoundClipPlot)

        # Bind plot size to the SoundClip's size
        self.bind(size=self.scale_plot)

        # Create time amplitude curve containing object
        self.TimeAmplitudeCurve = MeshStemPlot(color=[1,1,1, 0.3])

        # Decrease the amount of sample drawn
        plot_decimation_rate = 200 # Draw every 200th sample
        amplitudes = [amplitudes[ind] for ind in range(0,self.length_in_samples, plot_decimation_rate)] # Pick every 200th sample

        # Create sample index vector which gives the plot the correct x coordinates
        soundclip_length = np.linspace(0,self.length_in_samples-1, num=self.length_in_samples)
        # Combine the two vectors to a list which contains (x,y) coordinate pairs 
        audio_time_curve = list(zip(soundclip_length, amplitudes))

        # Add points to plot
        self.TimeAmplitudeCurve.points = audio_time_curve
        # Change the plot's length to be equal to the amount of points added. +1 prevents zero division. The program crahed once and the error stated "File "C:\Users\Aki\.kivy\garden\garden.graph\__init__.py", line 1036, in x_px 'ratiox = (size[2] - size[0]) / float(xmax - xmin)'  ZeroDivisionError: float division by zero", meaning xmax and xmin were both zero.
        self.SoundClipPlot.xmax = len(self.TimeAmplitudeCurve.points) + 1
        # Add plot
        self.SoundClipPlot.add_plot(self.TimeAmplitudeCurve)

        # When the audio starts playing
        self.start_sample = int(start_sample)
        self.x = (self.start_sample/samples_in_time_axis) * SoundClipField_width

        # Store relative width and x in variables
        # TODO this should be able to be calculated without these variables, just like height is manipulated.
        self.relative_x = self.x/SoundClipField_width
        self.relative_width = clip_length_in_pixels/SoundClipField_width

        # Bind SoundClip's movement to move_plot method
        self.bind(pos=self.move_plot)

    def scale_plot(self, *args, **kwargs):
        self.SoundClipPlot.size = self.size

    def move_plot(self, *args, **kwargs):
        SoundClipField = self.parent.parent

        if SoundClipField:
            # Synchronize SoundClipPlot (the wav plot) with the button
            self.SoundClipPlot.pos = self.pos
            # Calculate the new relative position of SoundClip
            self.relative_x = self.x/SoundClipField.width
            # Calculate at which sample the audio starts
            MainView = self.parent.parent.parent.parent.parent
            self.start_sample = int( MainView.MiddleBar.TrackAxis.TimeSlider.max * self.x/SoundClipField.width )
        else:
            print("Error! SoundClip "+str(self)+" has belongs to no SoundClipField and so has most likely been removed.")

    def remove_self(self, *args, **kwargs):

        # Name parent chains for clarity
        MainView = self.parent.parent.parent.parent.parent
        TrackContainer = self.parent.parent.parent.parent

        # Remove self
        for track in TrackContainer.Tracks:
            if self in track.SoundClips:
                # Remove from parent Track's list of SoundClips
                track.SoundClips.remove(self)

                # Remove from the layout
                track.TrackSoundClipLayout.remove_widget(self)

                # Remove self from wav_dict
                del MainView.wav_dict[self.path]

                # Delete self and free memory
                del self
                gc.collect()

                # Break out of loop. If there are Tracks left to be looped 'if self in track.SoundClips:' will
                # cause the program to crash since self has just been destroyed and no longer exists.
                break

    def split_self(self, *args, **kwargs):
        # Split self in to two SoundClips according to which pixel/sample was clicked

        # Name parent chains for clarity
        MainView = self.parent.parent.parent.parent.parent
        TrackContainer = self.parent.parent.parent.parent

        # Calculate where self is in relation to Window 
        TrackSoundClipView = self.parent.parent.parent
        x_in_relation_to_window = self.x + TrackSoundClipView.x

        # How self is split
        percentage_split = (Window.mouse_pos[0]-x_in_relation_to_window)/self.width

        # Open self's wav to get the samples for the 2 new SoundClips
        samples = MainView.wav_dict[self.path]

        # Get sample at which self is split
        split_sample = int( np.floor( len(samples) * percentage_split ) )

        # Get samples for the new SoundClips
        new_samples_first_half = samples[0:split_sample]
        new_samples_second_half = samples[split_sample+1:-1]

        # Create new wavs
        new_name_first_half = self.path.split(".wav")[0] + '_1.wav' # add '_1' to the end of the first half to create a new unique name
        soundfile.write(new_name_first_half, np.frombuffer(b''.join(new_samples_first_half), "Float32"), sampling_rate)

        new_name_second_half = self.path.split(".wav")[0] + '_2.wav' # add '_2' to the end of the second half to create a new unique name
        soundfile.write(new_name_second_half, np.frombuffer(b''.join(new_samples_second_half), "Float32"), sampling_rate)

        # Loop to find Track which holds self
        for track in TrackContainer.Tracks:
            if self in track.SoundClips:

                # Create new SoundClip, add it to the layout and open it to wav_dict
                track.add_SoundClip(new_name_first_half,                                             # recorded_audio_path
                                    MainView.MiddleBar.TrackScaleController.TimeAxisSlider.max,      # samples_in_time_axis
                                    MainView.TrackContainer.Track_height,                            # Track_height
                                    MainView.TrackContainer.TrackSoundClipView.SoundClipField.width, # SoundClipField_width
                                    self.start_sample)                                               # start_sample

                # Add to layout
                track.TrackSoundClipLayout.add_widget(track.SoundClips[-1])
                # Add to wav_dict
                MainView.wav_dict[track.SoundClips[-1].path] = new_samples_first_half

                # Place the SoundClip in the layout
                track.SoundClips[-1].y = track.TrackSoundClipLayout.y
                track.SoundClips[-1].x = track.SoundClips[-1].relative_x * MainView.TrackContainer.TrackSoundClipView.SoundClipField.width
                track.SoundClips[-1].move_plot()

                # The same but this time for the second half
                track.add_SoundClip(new_name_second_half,                                            # recorded_audio_path
                                    MainView.MiddleBar.TrackScaleController.TimeAxisSlider.max,      # samples_in_time_axis
                                    MainView.TrackContainer.Track_height,                            # Track_height
                                    MainView.TrackContainer.TrackSoundClipView.SoundClipField.width, # SoundClipField_width
                                    self.start_sample+split_sample+1)                                # start_sample

                # Add to layout
                track.TrackSoundClipLayout.add_widget(track.SoundClips[-1])
                # Add to wav_dict
                MainView.wav_dict[track.SoundClips[-1].path] = new_samples_second_half

                # Place the SoundClip in the layout
                track.SoundClips[-1].y = track.TrackSoundClipLayout.y
                track.SoundClips[-1].x = track.SoundClips[-1].relative_x * MainView.TrackContainer.TrackSoundClipView.SoundClipField.width
                track.SoundClips[-1].move_plot()

                # Break out since only one SoundClip can be split at a time
                break

        # Remove self (the old SoundClip which was just split)
        self.remove_self()

    def on_press(self, *args, **kwargs):
        MainView = self.parent.parent.parent.parent.parent

        # Select method based on which mode is active
        if MainView.cursor_mode == 'x':
            self.split_self()

        elif MainView.cursor_mode == 'backspace':
            self.remove_self()

        else:
            # Run the original method, which sets the 'pressed' boolean to True allowing the user to move the SoundClip
            super(SoundClip, self).on_press(*args, **kwargs)

    def on_release(self, *args, **kwargs):
        # If the SoundClip was moved and thus prev_mouse_pos != impossible_pixel
        if self.prev_mouse_pos != impossible_pixel: 

            # Naming this parent.parent... chain for clarity
            TrackContainer = self.parent.parent.parent.parent

            # Loop through the Tracks
            for track in TrackContainer.Tracks:
                # If the mouse is between the track.TrackSoundClipLayout's height
                if self.prev_mouse_pos[1] >= track.TrackSoundClipLayout.y and self.prev_mouse_pos[1] <= track.TrackSoundClipLayout.y+track.TrackSoundClipLayout.height:

                    # Remove self from its previous Track. Since the parent chain of this local 'TrackContainer' goes through 'SoundClipField' rather than being able to access
                    # the 'parent' Track.SoundClips, looping through 'Tracks' again is the simplest way of implementing the removal.
                    for parent_Track in TrackContainer.Tracks:
                        if self in parent_Track.SoundClips:

                            # Remove from parent Track's list of SoundClips
                            parent_Track.SoundClips.remove(self)

                            # Remove from parent Track's layout for SoundClips
                            parent_Track.TrackSoundClipLayout.remove_widget(self)

                            # Useful print for debugging
                            # print(self.path+" removed from "+parent_Track.TrackControls.TrackNameField.text)

                    # Change the moved SoundClip's color to match the Track
                    self.SoundClipPlot.background_color = track.TrackControls.ColorPickerPopup.ColorWheel.color 

                    # Add SoundClip to current track
                    track.SoundClips.append(self)

                    # Add to Track's layout for SoundClips
                    track.TrackSoundClipLayout.add_widget(self)

                    # Useful print for debugging
                    # print(self.path+" added to "+track.TrackControls.TrackNameField.text)

            # Keep SoundClip inside the GUI
            # Prohibit the beginning from clipping behind the first time instance
            if self.x < 0:
                self.x = 0
            # Prohibit the ending from clipping behind the last time instance. This one isn't as robust as the 'if' prior for some reason.
            elif self.x+self.width > TrackContainer.TrackSoundClipView.SoundClipField.width:
                self.x = TrackContainer.TrackSoundClipView.SoundClipField.width - self.width

            # Prohibit from going below the available height
            if self.y < 0:
                self.y = 0
            # Prohibit from going above the available height
            elif self.y+self.height > TrackContainer.TrackSoundClipView.SoundClipField.height:
                self.y = TrackContainer.TrackSoundClipView.SoundClipField.height - self.height

        # Running the original on_release method after the main processes to be able to use 'self.prev_mouse_pos' for moving the SoundClip
        super(SoundClip, self).on_release(*args, **kwargs)
