# Kivy imports
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.slider import Slider

# General Python imports
from numpy import log10


class LevelIndicator(Slider):

    ########################################### Brief description ###########################################
    # LevelIndicator is a Slider object used to display signal levels. It is placed under VolumeSlider
    # in VolumeSliderBox and so cannot be accessed by the user. LevelIndicator's color is bounded to its
    # values and hence length.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(LevelIndicator, self).__init__(**kwargs)

        # Set scale of values. This expects value from 0 to 1, basic audio float scale, where 0 is silence and >1 digital distortion
        self.min = -80
        self.max = 0

        # Set cursor invisible
        self.cursor_size = (0,0)

        # Add value track
        self.value_track = True

        # Initialize value track color as invisible
        self.value_track_color = (0,0,0, 0)

        # Set value track width
        self.value_track_width = 5

        # Initiate level
        self.old_level = self.min

        # Decay factor used for smoothing level changes
        self.decay_factor = 0.2

        # Bind value changes to hide value track if values are too small
        self.bind(value=self.hide_value_track)

    def hide_value_track(self, new_value, *args, **kwargs):
        # If the values are below or equal to the minimum, hide the value_track
        if self.value <= self.min:
            self.value_track = False
        else:
            self.value_track = True

    def calculate_level(self, new_value, *args, **kwargs):
        # Convert values to dB, if values are below minimum force them below the minimum
        if new_value <= 0.0001:
            new_value = self.min-1
        else:
            new_value = float(20*log10(new_value))

        # Calculate 2 point moving average of new input and previous output. For more info look into '2 point moving average filter'.
        self.value = ((new_value)*self.decay_factor + self.old_level*(1-self.decay_factor))
        
        # Store old value for later iterations
        self.old_level = self.value

        # Logic for gradient colors:
        # -80 blue, -40 green, 0 red, -60 between blue and green, -20 between green and red
        # (r,g,b), -80 -> (0,0,1), -40 -> (0,0.5,0.5), -40 -> (0,1,0), -20 -> (0.5,0.5,0), 0 -> (1,0,0)

        b = -self.value/40 - 1
        g = -6.2500e-04*self.value**2 -0.0500*self.value # Formula deduced by solving a second order function which has a maximum of 1 at -40 and has value 0 at -80 and 0
        r = self.value/40 + 1

        # The equations don't take into account areas where the values should stay at zero rather than going negative so they are forced to zero.
        if b < 0:
            b = 0
        if r < 0:
            r = 0

        # Set peak detector color
        self.value_track_color = (r,g,b, 1)


class VolumeSlider(Slider):

    ########################################### Brief description ###########################################
    # VolumeSlider is the Slider in VolumeSliderBox which controls signal volume (=gain).
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(VolumeSlider, self).__init__(**kwargs)

        # Initialize volume values in dB 
        self.min = -80
        self.max = 12

        # Set init value
        self.value = 0

        # 0 dB in linear scale is 1
        self.linear_gain_factor = float(1.0)

        # Set the background invisible
        self.background_width = 0

        # Testing level indicator logic
        self.bind(value=self.calculate_linear_gain_factor)

    def calculate_linear_gain_factor(self, *args, **kwargs):
        # Recalculate linear_gain_factor if VolumeSlider's value is changed. If the value is at minimum, force linear_gain_factor to 0.
        if self.value <= -80:
            self.linear_gain_factor = float(0.0)
        else:
            self.linear_gain_factor = float(10**(self.value/20))

class VolumeSliderBox(FloatLayout):

    ########################################### Brief description ###########################################
    # VolumeSliderBox is a layout which holds both VolumeSlider and LevelIndicator on top of one another.
    # Only VolumeSlider can be altered because it is added after LevelIndicator and because VolumeSliderBox
    # is a FloatLayout.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(VolumeSliderBox, self).__init__(**kwargs)

        # Level indicator. LevelIndicator HAS TO BE added first so it is under VolumeSlider. 
        # Also FloatLayout conviniently allows only one grabbable element per FloatLayout, which will now be the latter added VolumeSlider.
        self.LevelIndicator = LevelIndicator(size_hint=(None,None),size=(180,10),pos_hint={'top':0.8,'right':1})
        self.add_widget(self.LevelIndicator)

        # Slider controling volume
        self.VolumeSlider = VolumeSlider(size_hint=(None,None),size=(180,10),pos_hint={'top':0.8,'right':1})
        self.add_widget(self.VolumeSlider)
        