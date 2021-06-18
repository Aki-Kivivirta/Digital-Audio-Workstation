# Kivy imports
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Line
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

# Project files
from GlobalAudioVariables import *
from VolumeSliderBox import VolumeSliderBox
from PEQPopup import PEQPopup

# General Python imports
import string


class TimeTable(TextInput):

    ########################################### Brief description ###########################################
    # TimeTable is a TextInput linked to the value of TimeSlider. The user can alter TimeSlider position by
    # typing values to TimeTable or by dragging TimeSlider
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TimeTable, self).__init__(**kwargs)

        # Default value
        self.text = '  0.0'

        # Define text and background colors
        self.foreground_color = (0.3,0.3,0.3, 1)
        self.background_color = (0.8,0.8,0.8, 1)
        
        # Font style
        self.font_name = 'Arial'

        # Font size
        self.font_size = 70

        # Disable multiple lines
        self.multiline = False

        # Define size
        self.size_hint = (None,None)
        self.size = (150,90)

        # Set maximum value, minimum is not needed since '-' sign is never allowed and '0.0' seconds is always the first 
        self.max = 0

        # Bind focusing in and out of TimeTable to an event
        self.bind(focus=self.remove_decimal)

    def insert_text(self, inputted_text, from_undo=False):
        # Allow only two digits to be inputted
        if len(self.text) >= 2:
            return

        # Allow only digits
        filtered_text = ''
        for c in inputted_text:
            if c.isnumeric():
                filtered_text += c

        # Execute the original method as well
        super(TimeTable, self).insert_text(filtered_text, from_undo=from_undo)

    def remove_decimal(self, instance, focused_bool, *args, **kwargs):
        # Remove the decimal place if focused to TimeTable and add it if clicking out
        if focused_bool:
            # Remove spaces
            self.text = self.text.replace(" ","")
            # Store old value
            self.old_value = self.text
            # Remove decimal place
            self.text = self.text.split('.')[0]
        else:
            # TODO This logic could be cleaner, maybe combine to a single if elif chain?

            # Limit the input values to the maximum value
            if float(self.text.replace(" ","")) > self.max:
                self.text = str(self.max)

            # If the value is changed, start from the first decimal, if not or if there was no text left return the old value. Last condition was added after a rare error where '2.7.0' couldn't be converted to a float.
            if self.text.replace(" ","") != self.old_value.split('.')[0].replace(" ","") and self.text != '' and '.' not in self.text:
                self.text += '.0'
            else:
                self.text = self.old_value

            # If the text is still empty, add the old value. This could be cleaner.
            if self.text == '':
                self.text = self.old_value

            # Move TimeSlider once value has been changed
            TimeSlider = self.parent.parent.MiddleBar.TrackAxis.TimeSlider
            TimeSlider.value = float(self.text)*sampling_rate


class TopBar(FloatLayout):

    ########################################### Brief description ###########################################
    # TopBar is the gradinent grey color bar at the top of the main view. It holds the main objects related
    # to recording, playing/pausing, scrolling time and controling the output signal with volume and 
    # equalization.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(TopBar, self).__init__(*args, **kwargs)

        # pos_hint and size_hint, have to be used in order for user with different size displays, and therefore windows, to have the same ratios in the GUI.
        # Initializing the width to be 100%, i.e. 1, of the entire window and height to be 20%, 0.20, of the entire window
        self.size_hint = (1,0.2)

        # Initialize PEQPopup
        self.PEQPopup = PEQPopup()

    def init_gradient(self, top, start_color, end_color, *args, **kwargs):
        # Cast pixel coordinates to int, just in case
        width = int(self.width)
        height = int(self.height)
        top = int(top)
        top_bar_bottom = top - height

        # Since scale from white to black through grey has equal r,g,b values the same gradient value can be used
        gradient_rate = (start_color-end_color)/height
        current_color = start_color

        # Starting from lighter grey at the top blend to a darker tone. Point (0,0) in kivy is the bottom left corner
        for y1 in range(top, top_bar_bottom, -1):
            self.canvas.add(Color(rgba=(current_color,current_color,current_color, 1)))
            self.canvas.add(Line(points=[0, y1, self.width, y1], width=1))
            current_color -= gradient_rate

        # By accessing Line coordinates through self.canvas.children[2].points, the gradient could maybe be dynamic

    def init_buttons(self, *args, **kwargs):
        # Can't be done in init since colors would be draw on top of the button

        button_width = 80
        button_height = button_width
        button_size = (80,80)

        x = self.x + self.width/2 - button_width*7 # Make space for 5 buttons and have one button gap between middle (where TimeTable is) and the last button (RecButton)
        y = self.y + self.height/2 - button_height/2

        # Scroll backward button
        self.ScrollBackwardButton = Button(size_hint=(None,None), size=button_size, pos=(x,y), background_color=(1,1,1, 0.5), background_normal='.\\Icons\\scroll_backward.png')
        self.add_widget(self.ScrollBackwardButton)

        # Scroll forward button, backwards
        self.ScrollForwardButton = Button(size_hint=(None,None), size=button_size, pos=(x+button_width,y), background_color=(1,1,1, 0.5), background_normal='.\\Icons\\scroll_forward.png')
        self.add_widget(self.ScrollForwardButton)

        # Pause to beginning
        self.PauseToBeginningButton = Button(size_hint=(None,None), size=button_size, pos=(x+2*button_width,y), background_color=(1,1,1, 0.5), background_normal='.\\Icons\\pause_to_beginning.png')
        self.add_widget(self.PauseToBeginningButton)

        # Add PlayButton
        self.PlayButton = Button(size_hint=(None,None), size=button_size, pos=(x+3*button_width,y), background_color=(1,1,1, 0.5), background_normal='.\\Icons\\play.png')
        self.add_widget(self.PlayButton)

        # Add RecordButton
        self.RecordButton = Button(size_hint=(None,None), size=button_size, pos=(x+4*button_width,y), background_color=(1,1,1, 0.5), background_normal='.\\Icons\\record.png') # The background_color behaves weird when the layout is colored
        self.add_widget(self.RecordButton)

        # Add TimeTable
        self.TimeTable = TimeTable(pos_hint={"center_y":0.5,"center_x":0.5})
        self.add_widget(self.TimeTable)

        # Add PEQPopup
        self.PEQButton = Button(text="Parametric EQ", size_hint=(None,None), size=(button_width*1.5,button_width/2), pos_hint={"center_y":0.6,"right":0.93}, background_color=(1,1,1, 0.5)) # The background_color behaves weird when the layout is colored
        self.add_widget(self.PEQButton)
        self.PEQButton.bind(on_release=self.open_PEQPopup)

        # Add MasterVolume
        self.MasterVolume = VolumeSliderBox(size_hint=(0.2,1),pos_hint={"center_y":0.05,"right":0.95})
        self.add_widget(self.MasterVolume)

    def open_PEQPopup(self, *args, **kwargs):
        self.PEQPopup.open()
