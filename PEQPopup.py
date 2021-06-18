# Kivy imports
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.floatlayout import FloatLayout
from kivy.garden.graph import Graph, SmoothLinePlot, MeshStemPlot
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, InstructionGroup

# Project files
from GlobalAudioVariables import *

# General Python imports
import math
from scipy import signal
import numpy as np

# Global variables
# Define some pixel which is most likely never reaced. Used used when moving GainAndFreqButton
impossible_pixel = (-999,-999)

# How many factors less points are in the plots
denominator = 10 # There are 1/decimation_factor amount of points in the end
# Hox many points are in the original frequency response
points_in_full_frequency_response = int(sampling_rate/2)
# Calculate how many points are in the final responses
amount_of_points = math.floor(points_in_full_frequency_response/denominator)
# TODO 'amount_of_points-1' seems to be more common than, 'amount_of_points' it self due mostly to logarithmic
# jumps in loops. Should this be changed so that 'amount_of_points' would be more common and the few exceptions
# would have +/- 1 when/if needed?

# Graph limits
graph_xmin = 10
graph_xmax = 22000
graph_ymin = -50
graph_ymax = 50

# Input fft decay factor
decay_factor = 0.96


class CurveAreaPlot(MeshStemPlot):

    ########################################### Brief description ###########################################
    # CurveAreaPlot is the plot function for areas between graph minimum and points. Ideally the entire area 
    # would be the same color, but since there are fewer points at low frequecies, they appear lighter or the
    # individual stems are visible. Tried multiple ways of adding more points to low frequencies for a more
    # even color.
    #########################################################################################################

    def plot_mesh(self):
        # This is almost identical to 'MeshStemPlot' plot mesh, only difference is 'y0'
        points = [p for p in self.iterate_points()]
        mesh, vert, _ = self.set_mesh_size(len(points) * 2)
        y0 = self.y_px()(graph_ymin) # Normally lines are drawn from value 0, not graph_ymin, meaning center axis not bottom of the graph
        for k, (x, y) in enumerate(self.iterate_points()):
            vert[k * 8] = x
            vert[k * 8 + 1] = y0
            vert[k * 8 + 4] = x
            vert[k * 8 + 5] = y
        mesh.vertices = vert


class FrequencyResponseGraph(Graph):

    ########################################### Brief description ###########################################
    # FrequencyResponseGraph is the Graph object containing all filter curves and FFTs
    #########################################################################################################

    def __init__(self,*args,**kwargs):
        super(FrequencyResponseGraph, self).__init__(**kwargs)

        # Set size in relation to parent
        self.size_hint = (1,1)

        # Set positon in relation to parent
        self.pos_hint = {'top':1}

        # Control axes color
        self.border_color = [1,1,1, 1]

        # Add padding
        self.padding = 8

        # Add axes labels
        self.xlabel='Frequency (Hz)'
        self.ylabel='Magnitude (dB)'

        # Control major and minor ticks
        self.x_ticks_major=0.25 # from documentation: "ticks_major is 0.1, it means there will be a tick at every 10th of the decade, i.e. 0.1 ... 0.9, 1, 2..."
        self.x_ticks_minor=5
        self.y_ticks_major=10
        self.y_ticks_minor=5

        # Set minimum and maximum values
        self.xmin=graph_xmin
        self.xmax= graph_xmax
        self.ymin=graph_ymin
        self.ymax=graph_ymax

        # Turn on x and y grids
        self.x_grid=True
        self.y_grid=True 
        self.x_grid_label=True
        self.y_grid_label=True

        # Set x axis logarithmic
        self.xlog=True


class GainAndFreqButton(Button):

    ########################################### Brief description ###########################################
    # GainAndFreqButton is a movable button controling specific filter's gain and frequency according to its
    # location on top of FrequencyResponseGraph.
    #########################################################################################################

    def __init__(self, **kwargs):
        super(GainAndFreqButton, self).__init__(**kwargs)

        # Almost like MoveableButton in SoundClip.py, but on_touch_move is doesn't have steps

        # Set size
        self.size_hint = (None,None)
        self.size = (25,25)

        # Set the button's color to transparent so it is never visible
        self.background_color = (0,0,0, 0)

        # A pixel which is never reached
        self.prev_mouse_pos = impossible_pixel

        # Bool used to allow only one MoveableButton to be moved at a time
        self.pressed = False

        # Init instructionGroup for round button
        self.canvas_instructions = InstructionGroup()

    def on_touch_move(self, touch):

        # Naming parent for clarity
        PEQLayout = self.parent

        # Align coordinates to match the popup's position. Better explanation from ref: https://kivy-garden.github.io/graph/flower.html#kivy_garden.graph.Graph.collide_plot
        x, y = PEQLayout.to_widget(touch.pos[0], touch.pos[1], relative=True)

        # If the user is grabbing self or if self is under mouse AND pressed bool is true AND mouse is in the graph area
        if (touch.grab_current == self or self.collide_point(*touch.pos)) and self.pressed and PEQLayout.FrequencyResponseGraph.collide_plot(x, y):

            # On first press, prev_mouse_pos is set to previous position. Impemented this way the user can grab and drag self from any point.
            if self.prev_mouse_pos != impossible_pixel:

                self.pos[0] = self.pos[0]+touch.pos[0]-self.prev_mouse_pos[0]
                self.pos[1] = self.pos[1]+touch.pos[1]-self.prev_mouse_pos[1]

            self.prev_mouse_pos = touch.pos

            # Update canvas by removing and clearing the old, creating and adding new
            self.canvas_instructions.clear()
            self.canvas_instructions.add(Color(rgba=(0.63,0.77,1, 0.9)))
            self.canvas_instructions.add(RoundedRectangle(size=(self.width,self.height),pos=(self.pos[0],self.pos[1]),radius=[100]))

    def on_release(self, *args, **kwargs):
        # Return to the initial state
        self.prev_mouse_pos = impossible_pixel
        self.pressed = False

    def on_press(self, *args, **kwargs):
        # Used to prevent the user from dragging more than one self at a time. Since only one pressed bool can be true at a time.
        self.pressed = True


class AudioFilter:

    ########################################### Brief description ###########################################
    # AudioFilter is a class which contains filter parameters, handles filter coefficient calculations, 
    # does frequency response calculations and contains a plot object for the frequency response curve.
    #########################################################################################################

    def __init__(self, filter_type='Notch', *args, **kwargs):
        super(AudioFilter, self).__init__(*args, **kwargs)

        # Add button which controls gain and center frequency
        self.GainAndFreqButton = GainAndFreqButton()
        self.GainAndFreqButton.bind(pos=self.change_gain_and_freq)

        # Initialize filter parameters
        self.center_freq = 1000
        self.Gain = 0
        self.q = 1 # TODO have some way of changing q in the layout
        self.filter_type = str(filter_type)

        # Initialize flat filter coefficients
        self.b = [1, 0, 0]
        self.a = [1, 0, 0]

        # Create line for filter plot
        self.filter_plot = SmoothLinePlot(color=[1,1,1, 0.6])

        # Initiate magnitudes as zeros, so when they are initually deducted from the complete response there is no bias left in the complete response
        self.magnitudes_in_dB = np.zeros((amount_of_points-1, 1), dtype=np.float32)

        # Filter response used for overlap add filtering
        self.ola_filtering_complex_response = np.ones((1, samples_per_playback_buffer), dtype='complex_').real

    def change_gain_and_freq(self, GainAndFreqButton, pos, **kwargs):
        # Align coordinates to match the popup's position. Better explanation from ref: https://kivy-garden.github.io/graph/flower.html#kivy_garden.graph.Graph.collide_plot
        PEQLayout = self.GainAndFreqButton.parent
        x, y = PEQLayout.to_widget(pos[0], pos[1], relative=True)

        # Align GainAndFreqButton center to be the point which is tracker. If this is omitted the filter peaks will track the bottom left corner of GainAndFreqButton
        x += self.GainAndFreqButton.width # Aligning this was trial and error
        y += self.GainAndFreqButton.height * 0.48

        # Convert mouse position to value from graph (x,y) => (frequency, magnitude)
        self.center_freq, self.Gain = PEQLayout.FrequencyResponseGraph.to_data(x, y)

        # Calculate and add new plot
        self.calculate_coefficients()

    def calculate_coefficients(self, *args, **kwargs):
        # Could add more filter types from ref: https://docs.scipy.org/doc/scipy/reference/signal.html#matlab-style-iir-filter-design

        # Choose function according to filter type
        if self.filter_type == "Notch":
            self.calculate_notch_coefficients()

    def calculate_notch_coefficients(self):
        # ref: All About Audio Equalization: Solutions and Frontiers Vesa Valimaki 1,* and Joshua D. Reiss https://acris.aalto.fi/ws/portalfiles/portal/9936551/applsci_06_00129.pdf
        # Page 9, Equations 29 and 30. Equation 30 has been solved for 'B' and 'B=w_c/Q' has been plugged to Equation 29.
        # For non audio people, the equations are in form (b[0]+b[1]+...)/(a[0]+a[1]+...) and so z^(-N) corresponsd to b[N] in the numerator and a[N] in the denominator

        # Calculate intermediate step local parameters to clean up the final calculations
        G = 10.0**(self.Gain/20)                          # Gain as a linear coefficient
        sqrt_G = math.sqrt(G)                             # Squareroot of gain
        w_c = 2*math.pi*self.center_freq/sampling_rate    # Normalized center frequency
        cos_wc = math.cos(w_c)
        tan_B2 = math.tan(w_c/(2*self.q))

        # Calculate coefficients
        # Numerator
        self.b[0] = sqrt_G + G * tan_B2
        self.b[1] = - ( 2 * sqrt_G * cos_wc )
        self.b[2] = sqrt_G - G * tan_B2

        # Denominator
        self.a[0] = sqrt_G + tan_B2
        self.a[1] = - ( 2 * sqrt_G * cos_wc )
        self.a[2] = sqrt_G - tan_B2

        # Calculate the frequency response
        self.calculate_frequency_response()

    def calculate_frequency_response(self):
        # Calculate complex frequency response of self's filter.
        frequencies, complex_response = signal.freqz(self.b, self.a, worN=points_in_full_frequency_response, fs=sampling_rate) 

        # Logaritmic x axis stacks more points to right side. This gliches the graph figure if points aren't decreased.
        # Since there are more points in the right side (at higher frequencies) more points can be skipped there.
        # The only issue with this is that high q value filters look weird at some low frequencies because their center
        # frequencies (i.e. where their peaks values are) may not exist in the plot.
        #    This is the original idea of how to decimate points. A newer decimation algorithm was implemented in
        # 'PEQLayout.realtime_input_fft()' when I was trying to have more points at lower frequencies.

        # TODO have decimated frequency response curve as a global function not under any class

        # List for frequencies
        decimated_frequencies = np.zeros((amount_of_points-1, 1), dtype=np.float32) # -1 was added to prevent 0 Hz which would lead to log10(0) because of logarithmic x axis

        # List for magnitudes
        decimated_complex_response = np.empty((amount_of_points-1, 1), dtype='complex_') # Data type has to be specified as complex, so that imaginary values wouldn't be omitted


        # Do not decimate points under this frequency
        start_freq = 1000 

        # Divide points at equal distances on a logarithmic scale, starting from start_freq
        jump_of_factor = ((points_in_full_frequency_response)/start_freq)**(1/(amount_of_points-start_freq))
        current_factor = jump_of_factor 

        # Add undecimated points to output arrays. Omit 0 Hz by starting reading from index 1
        decimated_frequencies[0:start_freq] = frequencies[1:start_freq+1].reshape(start_freq,1)
        decimated_complex_response[0:start_freq] = complex_response[1:start_freq+1].reshape(start_freq,1)

        # Starting jumping frequencies after last undecimated frequency
        selected_frequency = start_freq

        # Pick frequencies at logaritmically equal increments. Loop can start minimum from 1 index because floor(0) would lead to 0 Hz and so log10(0) error when logx=True
        for ind in np.arange(start_freq,amount_of_points,1):

            # Calculate next frequency
            selected_frequency *= jump_of_factor
            freq_ind = math.floor(selected_frequency)

            # Store the frequency for plots to know the correct x coordinate for plots
            decimated_frequencies[ind-1] = frequencies[freq_ind]

            # Store the complex amplitude at selected frequency
            decimated_complex_response[ind-1] = complex_response[freq_ind]


        # Naming parent for clarity
        PEQLayout = self.GainAndFreqButton.parent

        # Remove old response total system response. All responses are initiated as zeros
        PEQLayout.system_response_magnitudes_in_dB = np.subtract(PEQLayout.system_response_magnitudes_in_dB, self.magnitudes_in_dB)


        # Calculate self's new magnitudes
        self.magnitudes_in_dB = 20*np.log10(abs(decimated_complex_response))

        # Concatenate new list of magnitudes and frequencies and add it as the new points for plot
        self.filter_plot.points = list(zip(decimated_frequencies, self.magnitudes_in_dB))
        # self.filter_plot.points = np.concatenate((decimated_frequencies.reshape(amount_of_points-1,1), self.magnitudes_in_dB.reshape(amount_of_points-1,1)),axis=1) # numpy version is most likely more efficient but I couldn't solve the 'kivy force_dispatch' related warning it was giving

        # Add new response to total system response
        PEQLayout.system_response_magnitudes_in_dB = np.add(PEQLayout.system_response_magnitudes_in_dB, self.magnitudes_in_dB)
        PEQLayout.system_response_plot.points = list(zip(decimated_frequencies, PEQLayout.system_response_magnitudes_in_dB))
        # PEQLayout.system_response_plot.points = np.concatenate((decimated_frequencies.reshape(amount_of_points-1,1), PEQLayout.system_response_magnitudes_in_dB.reshape(amount_of_points-1,1)),axis=1) # numpy version is most likely more efficient but I couldn't solve the 'kivy force_dispatch' related warning it was giving

        # Calculate overlap add variables. The fft mirror image is included in these complex responses and these
        # responses are equal length to 'samples_per_playback_buffer', which is why they require second fft.
        # Remove effects of old filter from complete response
        PEQLayout.ola_complete_complex_response = np.divide(PEQLayout.ola_complete_complex_response,self.ola_filtering_complex_response)

        # Calculate new response
        _, self.ola_filtering_complex_response = signal.freqz(self.b, self.a, worN=samples_per_playback_buffer, whole=True, fs=sampling_rate) # 'whole=True' includes fft mirror

        # Add new response to complete response
        PEQLayout.ola_complete_complex_response = np.multiply(PEQLayout.ola_complete_complex_response,self.ola_filtering_complex_response)


class PEQLayout(FloatLayout):

    ########################################### Brief description ###########################################
    # PEQLayout is the main layout inside of PEQPopup. It is also responsible for realtime audio filtering
    # and FFT plotting. 
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(PEQLayout, self).__init__(**kwargs)

        # Add the frequency response
        self.FrequencyResponseGraph = FrequencyResponseGraph()
        self.add_widget(self.FrequencyResponseGraph)

        # Initiate curve for the total system response of all filters
        self.system_response_plot = SmoothLinePlot(color=[1,1,1, 1])

        # Initialize the system magnitude values as zeros
        self.system_response_magnitudes_in_dB = np.zeros((amount_of_points-1, 1), dtype=np.float32)
        self.FrequencyResponseGraph.add_plot(self.system_response_plot)

        # Add filters
        self.AudioFilters = [None] * number_of_audio_filters
        for ind in range(0,number_of_audio_filters):

            # Create new AudioFilter instance
            self.AudioFilters[ind] = AudioFilter()
            self.add_widget(self.AudioFilters[ind].GainAndFreqButton)

            # Add filter's plot to graph
            self.FrequencyResponseGraph.add_plot(self.AudioFilters[ind].filter_plot)

        # Create a 0 dB line and add it to plot
        self.zero_dB_line = SmoothLinePlot(color=[1,1,1, 0.9])
        self.zero_dB_line.points = [[self.FrequencyResponseGraph.xmin,0], [self.FrequencyResponseGraph.xmax,0]] # Draws line between these two points. Both have value of 0 dB and the first is at the start and the second at the end of FrequencyResponseGraph
        self.FrequencyResponseGraph.add_plot(self.zero_dB_line)

        # Create plots for input signal's fft curve and add it to graph. Would be cleaner to have these combined under one class
        self.input_fft_area_plot = CurveAreaPlot(color=[0.8,0.8,0.95, 0.6])   # For the area
        self.FrequencyResponseGraph.add_plot(self.input_fft_area_plot)
        self.input_fft_curve_plot = SmoothLinePlot(color=[0.8,0.8,0.95, 0.6]) # For highlighting the curve
        self.FrequencyResponseGraph.add_plot(self.input_fft_curve_plot)

        # Buffer for storing input signal data for fft
        self.fft_buffer_size = math.floor( (((sampling_rate)/2)/samples_per_playback_buffer) ) * samples_per_playback_buffer # This is how many full buffers of samples can fit to 0.5 seconds.
        self.circular_fft_buffer = np.zeros((self.fft_buffer_size), dtype=np.float32)
        self.circular_buffer_ind = 0
        self.hann = np.hanning(self.fft_buffer_size) # Hanning window used for windowing fft

        # Array for storing input fft's magnitudes
        self.input_fft_magnitude_in_dB = np.ones((amount_of_points-1, 1), dtype=np.float32) * -80
        self.decimated_frequencies = np.ones((amount_of_points-1, 1), dtype=np.float32)
        self.input_fft_decay_level = np.ones(self.input_fft_magnitude_in_dB.shape,dtype=np.float32) * (graph_ymin-1) * (1-decay_factor) # Array of some dB values
        self.epsilon_noise = np.ones((amount_of_points-1, 1), dtype='complex_')*10**((graph_ymin-1)/20) # Add noise to prevent log10(0) when plotting graph

        # Overlap add (OLA) variables
        self.ola_complete_complex_response = np.ones((1,samples_per_playback_buffer), dtype='complex_').real
        self.ola_prev_buffers = np.zeros((2,samples_per_playback_buffer), dtype=np.float32)
        self.ola_window = np.hanning(samples_per_playback_buffer) # Have seen both hanning and hamming used

    def filter_audio(self, audio_buffer, channel, *args, **kwargs):
        # channel==0 -> left channel, channel==1 -> right channel

        # Using 50% overlap-add to implement filtering because it was unsure how signal.filtfilt and such functions handle previous input and output samples.
        # Tried writing own time domain filtering function but it was too slow. Down falls of overlap-add is that frequency resolution is dependent on fft
        # length and sampling frequency ratio, 44100/2048≈21.5 Hz per fft bin for example. Increasing fft length increases calculations, delay and frequency
        # accuracy.

        # Calculate half buffer index
        half_buf_ind = int(samples_per_playback_buffer/2)

        # Calculate different sections of overlap and add. Sections are first windowed, then transformed to the frequency domain where they are
        # filtered (multiplied with the complex response). Finally ifft is taken, dimension on (N,1) is squeezed to (N,) and imaginary part is omitted
        # ('.real') eventhough the imaginary part would be 0.

        # Previous buffer's end half. Only end half is used
        buf0 = np.squeeze(np.fft.ifft(np.multiply(self.ola_complete_complex_response,np.fft.fft(np.multiply(self.ola_window,self.ola_prev_buffers[channel]))))).real
        
        # Intersection between previous and current buffer. Used fully
        buf1 = np.squeeze(np.fft.ifft(np.multiply(self.ola_complete_complex_response,np.fft.fft(np.multiply(self.ola_window,np.concatenate((self.ola_prev_buffers[channel][half_buf_ind:samples_per_playback_buffer],audio_buffer[0:half_buf_ind]))))))).real
        
        # End half of current buffer. Only first half is used
        buf2 = np.squeeze(np.fft.ifft(np.multiply(self.ola_complete_complex_response,np.fft.fft(np.multiply(self.ola_window,audio_buffer))))).real


        # Store current buffer for next iteration
        self.ola_prev_buffers[channel] = audio_buffer

        # Initialize output buffer
        output_buffer = np.zeros(audio_buffer.shape, dtype=np.float32)

        # Stack calculated buffers to output
        output_buffer[0:half_buf_ind] = buf0[half_buf_ind:samples_per_playback_buffer] # End half of buf0 stacked to first half of output buffer
        output_buffer[half_buf_ind:samples_per_playback_buffer] = buf2[0:half_buf_ind] # First half of buf2 stacked to the end half of output buffer
        output_buffer = np.add(output_buffer,buf1)                                     # buf1 summed in complete to output buffer

        return output_buffer

    def realtime_input_fft(self, audio_buffer, *args, **kwargs):
        # Put new audio_buffer to circular_fft_buffer
        self.circular_fft_buffer[self.circular_buffer_ind : self.circular_buffer_ind+samples_per_playback_buffer] = audio_buffer

        # Name parent for clarity
        PEQPopup = self.parent.parent.parent # First parent is some boxlayout, second a gridlayout. Popup's source would probably explain this

        # Calculate new fft only some times and when PEQPopup is open
        if (self.circular_buffer_ind == 0 or self.circular_buffer_ind == int(self.fft_buffer_size/2)) and PEQPopup.is_open:

            # Put circular buffer in order
            buffer_in_order = np.concatenate((self.circular_fft_buffer[0:self.circular_buffer_ind], self.circular_fft_buffer[self.circular_buffer_ind:self.fft_buffer_size])) #, axis=1) # buffer may have to be '.reshape()'d.
            buffer_in_order = np.multiply(buffer_in_order,self.hann) # Apply hanning window to buffer

            # Calculate fft
            frequencies, complex_response = signal.freqz(buffer_in_order, 1, worN=points_in_full_frequency_response, fs=sampling_rate) # When denominator 'a' is 1, freqz works as a fft function

            # List for frequencies
            self.decimated_frequencies = np.zeros((amount_of_points-1, 1), dtype=np.float32) # -1 was added to prevent 0 Hz which would lead to log10(0) because of logarithmic x axis

            # List for magnitudes
            decimated_complex_response = np.empty((amount_of_points-1, 1), dtype='complex_') # Data type has to be specified as complex, so that imaginary values wouldn't be omitted


            # Do not decimate points under this frequency
            start_freq = 1000 

            # Divide points at equal distances on a logarithmic scale, starting from start_freq
            jump_of_factor = ((points_in_full_frequency_response)/start_freq)**(1/(amount_of_points-start_freq))
            current_factor = jump_of_factor 

            # Add undecimated points to output arrays. Omit 0 Hz by starting reading from index 1
            self.decimated_frequencies[0:start_freq] = frequencies[1:start_freq+1].reshape(start_freq,1)
            decimated_complex_response[0:start_freq] = complex_response[1:start_freq+1].reshape(start_freq,1)

            # Starting jumping frequencies after last undecimated frequency
            selected_frequency = start_freq

            # Pick frequencies at logaritmically equal increments. Loop can start minimum from 1 index because floor(0) would lead to 0 Hz and so log10(0) error when logx=True
            for ind in np.arange(start_freq,amount_of_points,1):

                # Calculate next frequency
                selected_frequency *= jump_of_factor
                freq_ind = math.floor(selected_frequency)

                # Store the frequency for plots to know the correct x coordinate for plots
                self.decimated_frequencies[ind-1] = frequencies[freq_ind]

                # Store the complex amplitude at selected frequency
                decimated_complex_response[ind-1] = complex_response[freq_ind]


            # New fft's magnitudes
            new_input_fft_magnitude_in_dB = 20*np.log10( np.add( np.absolute(decimated_complex_response), self.epsilon_noise.reshape(amount_of_points-1, 1) ) )

            # Use peak dB value to scale the signal. dB values from 'freqz' aren't calculated in reference to any value. For this reason a sine wave with peak value of 1 
            # results in different peak dB than a broadband noise with the same peak. 
            peak_dB_value = 20*np.log10( np.max( np.absolute( self.circular_fft_buffer ) ) + 0.00001 ) # Adding 0.00001 (-100 dB) of noise to prevent log10(0) warning

            # Calculate the fft's peak value
            peak_fft_dB = np.max( new_input_fft_magnitude_in_dB )

            # Calculate a correction term. peak_dB_value = peak_fft_dB + dB_correction -> dB_correction = peak_dB_value - peak_fft_dB
            dB_correction = peak_dB_value - peak_fft_dB

            # Scale the fft so that 0 dB digital signal will be at graph_ymax. I would have liked to add a secondary y axis on the right side which would have displayed 
            # dB values from 0 dB down similarly to 'Logic pro eq'.
            new_input_fft_magnitude_in_dB += dB_correction+graph_ymax

            # Pick the largest values from the old and the new. First stack them to matrix and pick the larger value from the two to form a new array.
            self.input_fft_magnitude_in_dB = np.amax( np.concatenate((new_input_fft_magnitude_in_dB.reshape(amount_of_points-1, 1), self.input_fft_magnitude_in_dB.reshape(amount_of_points-1, 1)),axis=1),axis=1 ).real # There was a harmless Complex number warning from the initial array so '.real' was added 

            # Update points to plot
            self.input_fft_area_plot.points = list(zip(self.decimated_frequencies, self.input_fft_magnitude_in_dB))
            self.input_fft_curve_plot.points = self.input_fft_area_plot.points

        else:
            # TODO decay is dependent on 'samples_per_playback_buffer'. It would make more sense to have this decay on a separate clock

            # Decay the seen response below the seen y values. The reshape is vital. This runs smoothly for few dozen
            # iterations but transposes at some point which causes the output to be (N,N) matrix instead of a (N,1) array.
            self.input_fft_magnitude_in_dB = self.input_fft_magnitude_in_dB*decay_factor + self.input_fft_decay_level.reshape(self.input_fft_magnitude_in_dB.shape).real

            # Input the new points
            self.input_fft_area_plot.points = list(zip(self.decimated_frequencies, self.input_fft_magnitude_in_dB))
            self.input_fft_curve_plot.points = self.input_fft_area_plot.points

        # Increase index
        self.circular_buffer_ind += samples_per_playback_buffer

        # Loop index to beginning if over limits
        if self.circular_buffer_ind >= self.fft_buffer_size:
            self.circular_buffer_ind = 0


class PEQPopup(Popup):

    ########################################### Brief description ###########################################
    # PEQPopup is the Popup object which opens when the used presses the 'Parametric Equalizer' button. In
    # this popup window the user can equalize the output audio signal and see how the frequency response
    # changes as a result. dB scale in the y axis corresponds to the filter values and output signal 0 dB
    # (-1 to 1 peak to peak float) is scaled to be at the maximum of the graph (graph_ymax). PEQPopup can be
    # closed by pressing outside the popup just like all popups.
    #########################################################################################################

    def __init__(self, *args, **kwargs):
        super(PEQPopup, self).__init__(**kwargs)

        # Define size in relation to entire window
        self.size_hint = (0.7,0.7)

        # Define position in relation to entire window
        self.pos_hint = {"center_x":0.5,"top":0.9}

        # Omit title text
        self.title = ""

        # Set title underline where it is not visible
        self.separator_height = 0

        # Add content to self
        self.PEQLayout = PEQLayout()
        self.add_widget(self.PEQLayout)

        # Remove old background color
        self.background_color = (0,0,0, 0)

        # Add background to Popup
        self.popup_background_instructions = InstructionGroup()
        self.popup_background_instructions.add(Color(0.9,0.9,0.95, 0.8))
        self.popup_background_instructions.add(RoundedRectangle(size=self.size,pos=self.pos,radius=[10]))
        self.canvas.before.add(self.popup_background_instructions)

        # Since Popup pos is (0,0) until it is opened, the graph inside will remain at (0,0) if it isn't moved
        self.bind(pos=self.align_layout)

        # Bind methods for setting bool for wheather self is closed or open
        self.is_open = False
        self.bind(on_open=self.set_bool_to_self_is_open)
        self.bind(on_dismiss=self.set_bool_to_self_is_closed)

    def set_bool_to_self_is_open(self, *args, **kwargs):
        self.is_open = True

    def set_bool_to_self_is_closed(self, *args, **kwargs):
        self.is_open = False

    def align_layout(self, *args, **kwargs):

        # Add background to Popup
        self.popup_background_instructions.clear()
        self.popup_background_instructions.add(Color(0.9,0.9,0.95, 0.8))
        self.popup_background_instructions.add(RoundedRectangle(size=self.size,pos=self.pos,radius=[10]))

        # Move FrequencyResponseGraph on top of Popup. Was at pos=(0,0) on init
        self.PEQLayout.FrequencyResponseGraph.pos = self.pos # Tested also moving 'self.PEQLayout' but FrequencyResponseGraph remained at (0,0)


        # Align GainAndFreqButtons to start from 0 dB
        for ind in range(0,number_of_audio_filters):
            # This shortens the code significantly
            btn = self.PEQLayout.AudioFilters[ind].GainAndFreqButton

            # Unbind btn while it is positioned
            btn.unbind(pos=self.PEQLayout.AudioFilters[ind].change_gain_and_freq)

            # Set position. X coordinate logic is based on the popup's width and trying to leave space for the margin (+2). Y coordinate was almost middle
            # way of the window, but it needed to be raised a bit. I tried also looping through the screen pixels and to look for the desired values with
            # 'PEQLayout.FrequencyResponseGraph.to_data' but couldn't get it to work. Tried also using Plot (class which all plots inherit at some point)
            # methods x_px() and y_px() which return lambda functions which should calculate the pixels where inputted x and y values occure respectively.
            btn.pos = ((ind+1)*self.width/(number_of_audio_filters+2)+self.x+50, Window.height/2 + 42) # y coordinate wont work on a different size screen most likely

            # Make button round
            btn.canvas_instructions.clear()
            btn.canvas_instructions.add(Color(rgba=(0.63,0.77,1, 0.9)))
            btn.canvas_instructions.add(RoundedRectangle(size=btn.size,pos=btn.pos,radius=[100]))
            btn.canvas.after.add(btn.canvas_instructions)

            # Re-bind btn to change filter coefficients on position changes
            btn.bind(pos=self.PEQLayout.AudioFilters[ind].change_gain_and_freq)