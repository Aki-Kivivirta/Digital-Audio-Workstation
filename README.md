# Digital-Audio-Workstation
This is a Digital Audio Workstation (DAW) made in Python utilizing the Kivy framework. With this program the user can record and playback audio, equalize and stereo pan the output and import pre-existing *.wav* files in to the program with drag and drop. All audio files in the program can be moved, splitted or deleted, by selecting one of these modes. 

## Installation

This program has been written on a *Windows 10* device using *Python 3.8.5* and should run on other *Python 3* versions. For other operating systems, *Mac* user will need to find another way of installing *PyAudio*, as *PyAudio* is currently downloaded with a local *.whl* file. *Linux* systems have not been tested. However, Kivy claims to be cross platform and so this program should be relatively easily ran on other operating systems.

The following commands have been tested with *Windows 10* using the standard *Command Prompt*. This project can be downloaded with **git clone https://github.com/Aki-Kivivirta/Digital-Audio-Workstation.git**. After cloning, it is recomended that the user would download the modules to a virtual environment. This can be done on *Windows* by first changing to the project folder **cd Digital-Audio-Workstation** and running **python -m venv env** and then running **env\Scripts\activate.bat**. Now the virtual environment is active and all modules can be installed with **pip install -r requirements.txt**. The program can now be executed by running **python main.py**. Optionally, you can change color of slider tracks and buttons darker by copying **defaulttheme-0.png** from **Extras** folder to **YOUR_DIRECTORY\Digital-Audio-Workstation\env\Lib\site-packages\kivy\data\images** and overwriting the original **defaulttheme-0.png** file.


**TLDR**  
Run these commands in the *Command Prompt* of your *Windows 10* device, in the directory of your choosing  
**git clone https://github.com/Aki-Kivivirta/Digital-Audio-Workstation.git**  
**cd Digital-Audio-Workstation**  
**python -m venv env**  
**env\Scripts\activate.bat**  
**pip install -r requirements.txt**  
**python main.py**  

## How to use the program

Tracks can be added by pressing the **+** button and removed by first selecting a track by pressing the left side box until it is highlighted and then pressing **−** button. Each track has a mute button **M**, solo button **S**, recording button **R**, color button **C**, a volume slider on the top right and a stereo panning slider on the bottom right.

Recording audio can be initiated by first selecting the tracks to record by pressing the **R** button, then pressing the red round symbol in the top left area and stopped by pressing the same button again. Other buttons in the top left area are assumed to be self explanatory.

Split mode can be accessed by pressing *'x'* on your keyboard, delete mode with *'backspace'* and dragging mode, which is the default, by pressing any other key. There is *guitar.wav* in the **Recorded Audio Files** folder, if you want to try how drag and drop works but don't have *.wav* files of your own. 

Where audio is recorded and played back can be controled by grabbing the small down pointing arrow or by typing values to the box on the top center of the screen.

Track height and the amount of audio shown on the screen can be controled by the two smaller sliders located on the right side above the middle of screen. Currently the maximum time in the program has been set as 60 seconds and the closest area to zoom to as 5 seconds, but these limits are arbitrary.

The parametric equalizer can be accessed by pressing the **Parametric equalizer** button on the top right corner. There, each blue dot controls the center frequency and gain of a notch type filter.

## Future development ideas:
- Refactor the program so that all sound processing is done in its own segment. Now sound processing is done under layout objects.
- Add the option to bounce *.wav* files out of the program. This could be implemented with keycommand 'b' which would open a popup where the user could type a filename, select the area to be bounced and have the option to normalize the bounce file. At first bounces could be added to a 'Bounces' subdirectory by default.
- Include the option to have track icon images, such as a picture of a guitar, drums, keyboard etc.
- Add a dropdown menu to each track to control the input device. Currently audio can only be recorded from the default microphone input.
- Change stereo panning slider to a knob, as knobs are more commonly used with panning.
- Add more filter types to parametric equalizer.
- Include the possibility to change filter parameters such as quality (q).
- Create a metronome
- Make looping possible
- Round SoundClip edges and add the possibility to name them
- More robust color SoundClip logic. Currently the colors are selected by random which may result in white base color under a white signal color. It could be nice if new colors were slight deviations from the previous color.
- Add the possibility to drag and drop other audio file formats in addition to *.wav*.
- Compile the program to a single executable file with a module like 'pyinstaller'
- Add the ability to control the maximum amount of time in the program
- Screen size dependent logic for initializing parametric equalizer dots
- Option to reconnect the keyboard if it has failed on initialization

## Bugs

### Hostile

The program may crash after new files have been recorded. This is might be due to all *.wav* files being constantly open, although the program has never crashed when dragging and dropping *.wav* files to the program. In the future I might investigate lighter methods for opening audio while still being in control of every single audio sample.

"Keyboard not available!". This is printed to the console by main.py "MainView._keyboard_closed()", if the user's keyboard is not available. When the keyboard is not available the user cannot change to splitting or deleting modes, but only move sounds in the layout with the normal mode. This occurs on some runs and may be "fixed" by running the program again.

### Non hostile
"Warning:
libpng warning: iCCP: known incorrect sRGB profile
libpng warning: iCCP: cHRM chunk does not match sRGB"
Related to drawing objects like images. Doesn't effect the program.

"main.py:146: DeprecationWarning: Numeric-style type codes are deprecated and will result in an error in the future.
   soundfile.write(track.latest_recorded_audio_file, np.frombuffer(b''.join(samples), "Float32"), sampling_rate)"
Encourages to change the way *.wav* files are written. Doesn't effect the program. 

The down pointing arrow controling where audio is played and recorded (TimeSlider) has frozen on some occasions, but the program still runs. The level trackers have also frozen on some runs.

On one occasion, I managed to get the 'pressed' of 'GainAndFreqButton' bool to stay True even though it wasn't pressed anymore. With this I could push that button while having another button pressed. The glitch went away by pushing that button again.

If the user deletes files in **Recorded Audio Files** folder directory while the program is running, this may result in undefined behavior. There is a possibility this doesn't effect anything since all *.wav*s should be always open.
