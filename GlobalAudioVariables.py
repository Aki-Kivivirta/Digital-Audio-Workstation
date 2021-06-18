# Global variables for audio recording and playback

sampling_rate = 44100
samples_per_recording_buffer = 1024
samples_per_playback_buffer = 2048 # There were audible clicks at 1024, which is a very common buffer size
number_of_input_channels = 1 	   # No stereo recording available yet
number_of_output_channels = 2 	   # Stereo output
playback_buffer_time = samples_per_playback_buffer/sampling_rate # How much time does one samples_per_playback_buffer take (in seconds)
number_of_audio_filters = 10       # How many audio filters are available from PEQPopup, this can be as many as you like since filtering is done in the frequency domain and so the amount of computations is only dependent on the fft length
