# Kivy imports
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle, Line, InstructionGroup
from kivy.uix.slider import Slider
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button

# Project files
from Track import Track
from GlobalAudioVariables import *

# General Python imports
import gc

# Global variables
# Minimum and maximum amount of time shown in TrackSoundClipView
minimum_time = 5  * sampling_rate # Seconds * Sampling rate = Samples
maximum_time = 60 * sampling_rate # Seconds * Sampling rate = Samples

# Track size in pixels
minimum_track_height = 100
maximum_track_height = 400
init_track_height = 200


############################### FOLLOWING CLASSES USED FOR MiddleBar ###############################

class BackgroundColorBoxLayout(BoxLayout):

    ########################################### Brief description ###########################################
    # BackgroundColorBoxLayout is a regular BoxLayout which has color initialization as a methdo. This is 
    # one way of implementing color to layouts. Since Kivy programs do not have their full size when the
    # program is initialzed colors have to be added later, for example with a 'Clock.schedule_once' call.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(BackgroundColorBoxLayout, self).__init__(**kwargs)

    def init_background_color(self, r, g, b, alpha, *args, **kwargs):
        # Define the boxes background colors
        self.canvas.before.add(Color(r,g,b,alpha))
        self.canvas.before.add(Rectangle(size=self.size, pos=self.pos))


class TimeSlider(Slider):

    ########################################### Brief description ###########################################
    # TimeSlider controls which SoundClips are played and where Tracks will record. Values correspond to
    # audio sample values, meaning each second of audio has 'sampling_rate' amount of samples.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TimeSlider, self).__init__(**kwargs)

        # Can only be grabbed from the cursor
        self.sensitivity = 'handle'

        # Remove the margin to TrackControllerView. Enables using value_pos for storing where recording was started. 
        self.padding = 0

        # Set limits corresponding to time in seconds
        self.min = 0
        self.max = maximum_time

        # Used to keep track where the recording was started from. This is used to disable the user from moving the TimeSlider during recording process.
        self.start_x = 0 # Reassigned higher in before the recording starts
        self.value_increment = 0

        # Add custom cursor icon and adjust its width
        self.cursor_image = ".\\Icons\\TimeSlider_cursor.png"

        # Set cursor size
        self.cursor_size = (30,30)

        # Set track as invisible
        self.background_width = 0

        # Bind change in value to change TimeTable's value
        self.bind(value=self.update_TimeTable)

    def playback_increase_position(self, fps_in_seconds, *args, **kwargs):
        # Here position can be changed while playback is on
        self.value += fps_in_seconds

        # If maximum has been reached or surpassed, return True
        if self.value >= self.max:
            return True
        else:
            return False

    def change_width(self, SoundClipField, *args, **kwargs):
        self.width = SoundClipField.width

    def update_TimeTable(self, *args, **kwargs):
        TimeTable = self.parent.parent.parent.parent.TopBar.TimeTable

        # Set new value to TimeTable
        value = str(round(self.value/sampling_rate,1))

        # Align TimeTable's value to the right using spaces if needed.
        if len(value) < 4:
            TimeTable.text = "  "+value
        else:
            TimeTable.text = value

    def scroll_forward(self, *args, **kwargs):
        # Scroll forward tenth of TrackAxis, meaning the jump is larger when more audio is showing. Conversely the step is smaller when zoomed closer to a smaller area.
        TrackAxis = self.parent
        self.value_pos = (self.value_pos[0]+TrackAxis.width/10, self.value_pos[1]) # Doesn't require exeptions for clipping out of bounds

    def scroll_backward(self, *args, **kwargs):
        # Scroll backwards tenth of TrackAxis, meaning the jump is larger when more audio is showing. Conversely the step is smaller when zoomed closer to a smaller area.
        TrackAxis = self.parent
        self.value_pos = (self.value_pos[0]-TrackAxis.width/10, self.value_pos[1]) # Doesn't require exeptions for clipping out of bounds


class TrackScaleController(BackgroundColorBoxLayout):

    ########################################### Brief description ###########################################
    # TrackScaleController is the higher thin bar under TopBar which contains two sliders for controling the
    # Track height and how many seconds of audio is shown in TrackSoundClipView.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TrackScaleController, self).__init__(**kwargs)

        # Define size relation to parent
        self.size_hint = (1, 0.5)

    def init_sliders(self, *args, **kwargs):
        # For some reason pos or pos_hint wasn't working, ended up adding padding, which has to be done here, since self.width is 0 in __init__.
        slider_width = 200
        self.padding = [self.width-2*slider_width,0,0,0] # [left_pad, up_pad, right_pad, down_pad]

        # Add TimeAxisSlider and TrackHeightSlider which control Track attribute dimensions
        self.TimeAxisSlider = Slider(orientation='horizontal',min=minimum_time,max=maximum_time,value=maximum_time,sensitivity='handle',size_hint=(None,1),width=slider_width,cursor_size=(23,23))
        self.add_widget(self.TimeAxisSlider)

        self.TrackHeightSlider = Slider(orientation='horizontal',min=minimum_track_height,max=maximum_track_height,value=init_track_height,sensitivity='handle',size_hint=(None,1),width=slider_width,cursor_size=(23,23))
        self.add_widget(self.TrackHeightSlider)


class TrackAxis(ScrollView):

    ########################################### Brief description ###########################################
    # TrackAxis is the layout which holds TimeSlider under TopBar and TrackScaleController, and above
    # TrackSoundClipView. TrackAxis is a ScrollView, which allows its objects like TimeSlider, to be moved
    # inside of it. TrackAxis cannot be moved by it self, but its movement is bounded to TrackSoundClipView's
    # movement.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TrackAxis, self).__init__(**kwargs)

        # Define size relation to parent
        self.size_hint = (1,0.5)

        # Add TimeSlider
        self.TimeSlider = TimeSlider(size_hint=(None,1),width=self.width) # Width could be anything on init
        self.add_widget(self.TimeSlider)

        # "Disable" scrolling from this layout by setting bars as only type of scrolling and bar_width to 0
        self.scroll_type = ['bars']
        self.bar_width = 0

    def init_background_color(self, r, g, b, alpha, *args, **kwargs):
        # Define the boxes background colors
        self.canvas.before.add(Color(r,g,b,alpha))
        self.canvas.before.add(Rectangle(size=self.size, pos=self.pos))

    def scroll_layout(self, TrackSoundClipView, *args, **kwargs):
        # This method has been binded to the hbar scrolling of TrackSoundClipView.
        self.scroll_x = TrackSoundClipView.scroll_x

    def on_scroll_move(self, *args, **kwargs):
        # Moving the scroll bars close to their maximum/minimum values may result in a zero division error in the Kivy code. This override try except attempts to prevent that.
        try:
            super(TrackAxis, self).on_scroll_move(*args, **kwargs)
        except:
            pass
            # print("Prevented zero division:")
            # print("self.vbar: ",self.vbar)
            # print("self.hbar: ",self.hbar)


class TrackAddRemove(BackgroundColorBoxLayout):

    ########################################### Brief description ###########################################
    # TrackAddRemove contains two buttons for adding and removing Tracks. There is currently no limit to the
    # amount of Tracks that can be added. A Track can be removed by first selecting it by clicking the
    # Track's TrackControls layout on the left until it is highlighted and then pressing the '−' in
    # TrackAddRemove.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TrackAddRemove, self).__init__(**kwargs)

        # Define size relation to parent
        self.size_hint = (0.2,1) 
        
    def init_buttons(self, *args, **kwargs):
        self.AddTrackBtn = Button(text="+", size_hint=(0.5,1), background_color=(1,1,1, 0.01)) # Colors acting weird
        self.add_widget(self.AddTrackBtn)
        self.RemoveTrackBtn = Button(text="−", size_hint=(0.5,1), background_color=(1,1,1, 0.01)) # Colors acting weird
        self.add_widget(self.RemoveTrackBtn)


class MiddleBar(BoxLayout):

    ########################################### Brief description ###########################################
    # MiddleBar is a horizontal layout in between TopBar and TrackContainer. 
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(MiddleBar, self).__init__(**kwargs)

        # Define size relation to parent
        self.size_hint = (1,0.05)

        # Define orientation
        self.orientation = 'horizontal'

        # Create and add TrackAddRemove
        self.TrackAddRemove = TrackAddRemove()
        self.add_widget(self.TrackAddRemove)

        # Another layout which contains TrackScaleController and TrackAxis. This couldn't be done in a 
        # single FloatLayout, since a FloatLayout allows only one of its child objects to be grabbed.
        self.SoundClipFieldDimensionsAndTimeAxis = BoxLayout(orientation='vertical', size_hint=(0.8,1))
        self.add_widget(self.SoundClipFieldDimensionsAndTimeAxis)

        # Create and add TrackScaleController
        self.TrackScaleController = TrackScaleController()
        self.SoundClipFieldDimensionsAndTimeAxis.add_widget(self.TrackScaleController)

        # Create and add TrackAxis
        self.TrackAxis = TrackAxis()
        self.SoundClipFieldDimensionsAndTimeAxis.add_widget(self.TrackAxis)

    def init_controls(self, *args, **kwargs):
        self.TrackScaleController.init_sliders()
        self.TrackAddRemove.init_buttons()


############################### FOLLOWING CLASSES USED FOR TrackContainer ###############################


class TrackControllerView(ScrollView):

    ########################################### Brief description ###########################################
    # TrackControllerView is the ScrollView in which all Track's TrackControls layouts are stored. Similarly
    # to TrackAxis, TrackControllerView can only be scrolled from TrackSoundClipView.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TrackControllerView, self).__init__(**kwargs)

        # Define size
        self.size_hint = (0.2,1)

        # Add layout containing TrackControls 
        self.TrackControllerField = GridLayout(cols=1,size_hint=(1,None),height=0)
        self.add_widget(self.TrackControllerField)

        # "Disable" scrolling from this layout by setting bars as only type of scrolling and bar_width to 0
        self.scroll_type = ['bars']
        self.bar_width = 0

    def init_background_color(self, r, g, b, alpha, *args, **kwargs):
        # Define the boxes background colors
        self.canvas.before.add(Color(r,g,b,alpha))
        self.canvas.before.add(Rectangle(size=self.size, pos=self.pos))

    def scroll_layout(self, TrackSoundClipView, *args, **kwargs):
        # This method has been binded to the vbar scrolling of TrackSoundClipView.
        self.scroll_y = TrackSoundClipView.scroll_y # This could be done without this method with a partial function

    def on_scroll_move(self, *args, **kwargs):
        # Moving the scroll bars close to their maximum/minimum values may result in a zero division error in the Kivy code. This override try except attempts to prevent that.
        try:
            super(TrackControllerView, self).on_scroll_move(*args, **kwargs)
        except:
            pass
            # print("Prevented zero division:")
            # print("self.vbar: ",self.vbar)
            # print("self.hbar: ",self.hbar)


class TrackSoundClipView(ScrollView):

    ########################################### Brief description ###########################################
    # TrackSoundClipView is the ScrollView under which all SoundClips are. Changing Track height from
    # TrackHeightSlider or the amount of seconds shown from TimeAxisSlider, alters SoundClipField's size,
    # which is the layout that holds all SoundClips. If SoundClipField is will not fit, the view can be 
    # scrolled with bars appearing in the bottom and right side.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TrackSoundClipView, self).__init__(**kwargs)

        # Define size
        self.size_hint = (0.8, 1)

        # Set scrolling on only when draging the bars. Have experienced cases where the layout was scrolled by draging the layout which would suggest 'self.scroll_type = [‘bars’, ‘content’]'.
        self.scroll_type = ['bars']

        # Modify default bars
        self.bar_width = 15
        self.bar_color = [0.8,0.8,0.8, 0.9]
        self.bar_inactive_color = [0.8,0.8,0.8, 0.2]

        # Add the layout to the ScrollView
        self.SoundClipField = GridLayout(cols=1,size_hint=(None,None),size=(0,0)) # height has to be 0 on init since there are no objects inside the layout, width is 0 because in init self.width is 100 and so the width has to be altered after init anyway
        self.add_widget(self.SoundClipField)

    def init_background_color(self, r, g, b, alpha, *args, **kwargs):
        # Define the boxes background colors
        self.canvas.before.add(Color(r,g,b,alpha))
        self.canvas.before.add(Rectangle(size=self.size, pos=self.pos))

    def scroll_layout(self, TrackControllerView, *args, **kwargs):
        # This method has been binded to the vbar scrolling of TrackControllerView.
        self.scroll_y = TrackControllerView.scroll_y # This could be done without this method with a partial function

    def on_scroll_move(self, *args, **kwargs):
        # Moving the scroll bars close to their maximum/minimum values may result in a zero division error in the Kivy code. This override try except attempts to prevent that.
        try:
            super(TrackSoundClipView, self).on_scroll_move(*args, **kwargs)
        except:
            pass
            # print("Prevented zero division:")
            # print("self.vbar: ",self.vbar)
            # print("self.hbar: ",self.hbar)


class TrackContainer(BoxLayout):

    ########################################### Brief description ###########################################
    # TrackContainer is the layout under TopBar and MiddleBar. It splits in to TrackControllerView and 
    # TrackSoundClipView and holds all Tracks.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TrackContainer, self).__init__(**kwargs)

        # Set size and layout stacking orientation
        self.size_hint = (1, 0.75)
        self.orientation = 'horizontal'

        # Add child layouts
        self.TrackControllerView = TrackControllerView()
        self.add_widget(self.TrackControllerView)

        self.TrackSoundClipView = TrackSoundClipView()
        self.add_widget(self.TrackSoundClipView)

        # Attribute holding MiddleBar.TrackScaleController.TrackHeightSlider.value
        self.Track_height = init_track_height

        # List for Track objects
        self.Tracks = []

        # Which Track object is active. Used for removing 
        self.active_Track = None

        # InstructionGroup containing the Color and Rectangle used for highlighting active_Track. Has to be stored so it can be removed. Using canvas.clear() makes TrackControls invisible.
        self.active_Track_highlight_instructions = InstructionGroup()

        # Counter which gives Tracks unique names
        self.Tracks_created_counter = 1

    def add_Track(self, *args, **kwargs):
        # Create new Track
        track = Track(self.Tracks_created_counter)

        # Increase counter used to give Tracks unique names
        self.Tracks_created_counter += 1

        # Add Track to list of Tracks
        self.Tracks.append(track)

        # Set height
        track.set_height(self.Track_height)

        # Set the TrackControls' width to match the left side box's width
        track.TrackControls.width = self.TrackControllerView.TrackControllerField.width

        # Add the Track's controls to the layout. Located in the left side of the GUI
        self.TrackControllerView.TrackControllerField.add_widget(track.TrackControls)

        # Increase the left side layout's height by the Track's height
        self.TrackControllerView.TrackControllerField.height = self.TrackControllerView.TrackControllerField.height + self.Track_height

        # Add self.Track_height to all SoundClip's y so they stay were they were, since the height was increased
        for track in self.Tracks:
            for clip in track.SoundClips:
                clip.y += self.Track_height

        # Bind on_touch_up events to change the active_Track attribute
        track.TrackControls.bind(on_touch_up=self.change_active_Track)
        track.TrackSoundClipLayout.bind(on_touch_up=self.remove_active_Track)

        # Increase the size SoundClipField
        self.TrackSoundClipView.SoundClipField.height = self.TrackSoundClipView.SoundClipField.height + self.Track_height

        # Add the track's layout containing SoundClip objects
        self.TrackSoundClipView.SoundClipField.add_widget(track.TrackSoundClipLayout)

    def remove_Track(self, *args, **kwargs):
        # If active_Track != None, remove a Track. Just a reminder: self.active_Track isn't a bool but a Track object or None.
        if self.active_Track:

            # Close the object responsible for recording audio
            self.active_Track.audio.terminate()

            # Remove the Tracks all SoundClip objects
            for clip in self.active_Track.SoundClips:

                # Remove individual SoundClip
                self.active_Track.TrackSoundClipLayout.remove_widget(clip)

                # Remove wav from MainView's wav_dict
                MainView = self.parent

                # Delete open wav from dict and free its memory. You don't have to "pop" from list if an object has already been deleted.
                del MainView.wav_dict[clip.path]
                gc.collect()

            # Remove all layouts assosiated with Track
            self.TrackControllerView.TrackControllerField.remove_widget(self.active_Track.TrackControls)
            self.TrackSoundClipView.SoundClipField.remove_widget(self.active_Track.TrackSoundClipLayout)

            # Reduce height of parent layouts
            self.TrackSoundClipView.SoundClipField.height = self.TrackSoundClipView.SoundClipField.height - self.Track_height
            self.TrackControllerView.TrackControllerField.height = self.TrackControllerView.TrackControllerField.height - self.Track_height

            # Remove from self.Tracks
            self.Tracks.remove(self.active_Track)

            # Delete the active Track and free active Tracks memory with garbage collector
            del self.active_Track
            gc.collect()

            # Logically better here. Can be probably moved outside of if.
            self.active_Track = None

    def update_active_Track_highlight(self, track, *args, **kwargs):
        # If there was a previous active_Track, remove its highlight
        if self.active_Track:
            self.active_Track.TrackControls.canvas.remove(self.active_Track_highlight_instructions)

        # Clear instructions and add new ones for canvas
        self.active_Track_highlight_instructions.clear()
        self.active_Track_highlight_instructions.add(Color(rgba=(1,1,1, 0.1)))
        self.active_Track_highlight_instructions.add(Rectangle(size=track.TrackControls.size,pos=track.TrackControls.pos))

        # Add highlight to TrackControls. Adding highlight to TrackSoundClipLayout
        track.TrackControls.canvas.add(self.active_Track_highlight_instructions)

    def change_active_Track(self, clicked_layout, touch, *args, **kwargs):
        if clicked_layout.collide_point(*touch.pos):
            # Since the Track to be removed can't be found by using parent attribute the correct Track has to be found by looping.
            for track in self.Tracks:
                if (track.TrackControls == clicked_layout or track.TrackSoundClipLayout == clicked_layout) and self.active_Track != track:

                    # Update highlight
                    self.update_active_Track_highlight(track)

                    # Change active track
                    self.active_Track = track

    def remove_active_Track(self, clicked_layout, touch, *args, **kwargs):        
        # If TrackControls or RemoveTrackBtn wasn't clicked and there is an active track, remove active_Track
        RemoveTrackBtn = self.parent.MiddleBar.TrackAddRemove.RemoveTrackBtn

        if self.TrackControllerView != clicked_layout and not RemoveTrackBtn.collide_point(*touch.pos) and self.active_Track:
            # Remove highlight
            self.active_Track.TrackControls.canvas.remove(self.active_Track_highlight_instructions)

            # Change active track to None
            self.active_Track = None

    def change_Track_width(self, new_time, *args, **kwargs):
        # Scale the Layout inside of scrollable view
        # When TimeAxisSlider.value == maximum_time -> SoundClipField.width == TrackSoundClipView.width
        # When TimeAxisSlider.value == minimum_time -> SoundClipField.width == TrackSoundClipView.width*(maximum_time/minimum_time)
        self.TrackSoundClipView.SoundClipField.width = self.TrackSoundClipView.width * maximum_time/new_time

        for track in self.Tracks:
            for clip in track.SoundClips:
                clip.x = clip.relative_x * self.TrackSoundClipView.SoundClipField.width
                clip.width = clip.relative_width * self.TrackSoundClipView.SoundClipField.width

    def change_Track_height(self, height_slider, *args, **kwargs):
        # Store for later use in other methods
        self.Track_height = height_slider.value

        # Scale size of layouts
        self.TrackControllerView.TrackControllerField.height = len(self.Tracks) * self.Track_height
        self.TrackSoundClipView.SoundClipField.height = len(self.Tracks) * self.Track_height

        # Set all Tracks to correct height
        for ind in range(0,len(self.Tracks)):
            track = self.Tracks[ind]
            track.set_height(self.Track_height)

            # Update highlight
            if track == self.active_Track:
                self.update_active_Track_highlight(track)
