
from eegnb.experiments import Experiment
import os
from time import time
from glob import glob
from random import choice

import numpy as np
import random
from pandas import DataFrame
from psychopy import visual, core, event


from eegnb.devices.eeg import EEG
from eegnb import generate_save_fn
from typing import Optional

# import keyboard


class VisualSSVEP_select(Experiment.BaseExperiment):
    '''
    SSVEP experiment with 2 visual stimuli, by JHUBCIS
    Subject can choose to focus on one of the two stimuli, and use left/right arrow to indicate which one they were focusing on.
    When not focusing on a stimulus, the subject can focus on the red fixation point in the middle.
    The experiment can be designed to last a defined duration, or can be interrupted by the subject pressing a spacebar.
    Recorded data will be saved to specified file path.
    '''
    def __init__(self, duration, eeg: Optional[EEG]=None, save_fn=None, freq1 = 15, freq2 = 55): #1 for left, 2 for right
        
        exp_name = "Visual SSVEP"
        super().__init__(exp_name, duration, eeg, save_fn, n_trials = None, iti = None, soa = None, jitter = None)
        self.instruction_text = """\nWelcome to the {} experiment!\n\nWhen stimuli are presented, use left/right arrow to indicate which stimulus you are looking at.\nPlease pause a bit between selections.\n\nThis experiment will run for %s seconds.\nPress spacebar to start, press again to interrupt. \n""".format(self.exp_name)
        self.freq1 = freq1
        self.freq2 = freq2

    def load_stimulus(self):
        
        pattern = np.ones((4, 4))
        pattern[::2, ::2] *= -1
        pattern[1::2, 1::2] *= -1
        pos1 = [-18, -8]
        pos2 = [18, -8]
        size = 5
        self._stim1 = visual.RadialStim(win=self.window, tex=pattern, pos=pos1,
                                        size=size, radialCycles=2, texRes=256, opacity=1)  
        self._stim1_neg = visual.RadialStim(win=self.window, tex=pattern*(-1), pos=pos1,
                                        size=size, radialCycles=2, texRes=256, opacity=1)
        self._stim2 = visual.RadialStim(win=self.window, tex=pattern, pos=pos2,
                                        size=size, radialCycles=1, texRes=256, opacity=1)
        self._stim2_neg = visual.RadialStim(win=self.window, tex=pattern*(-1), pos=pos2,
                                        size=size, radialCycles=1, texRes=256, opacity=1)
        fixation = visual.GratingStim(win=self.window, size=0.2, pos=[0, 8], sf=0.2, color=[1, 0, 0], autoDraw=True)

        # # Generate the possible ssvep frequencies based on monitor refresh rate
        # # def get_possible_ssvep_freqs(frame_rate, stim_type="single"):
            
        # #     max_period_nb = int(frame_rate / 6)
        # #     periods = np.arange(max_period_nb) + 1
            
        # #     if stim_type == "single":
        # #         freqs = dict()
        # #         for p1 in periods:
        # #             for p2 in periods:
        # #                 f = frame_rate / (p1 + p2)
        # #                 try:
        # #                     freqs[f].append((p1, p2))
        # #                 except:
        # #                     freqs[f] = [(p1, p2)]

        # #     elif stim_type == "reversal":
        # #         freqs = {frame_rate / p: [(p, p)] for p in periods[::-1]}

        # #     return freqs

        # def init_flicker_stim(frame_rate, cycle, soa):
            
        #     if isinstance(cycle, tuple):
        #         stim_freq = int (frame_rate / sum(cycle))
        #         # n_cycles = int(soa * stim_freq)
            
        #     else:
        #         stim_freq = int(frame_rate / cycle)
        #         cycle = (int(cycle), int(cycle))
        #         # n_cycles = int((soa * stim_freq) / 2)

        #     # return {"cycle": cycle, "freq": stim_freq, "n_cycles": n_cycles}
        #     return {"cycle": cycle, "freq": stim_freq}

        # # Set up stimuli
        # frame_rate = np.round(self.window.getActualFrameRate())  # Frame rate, in Hz
        # # freqs = get_possible_ssvep_freqs(frame_rate, stim_type="single")
        # cycle1 = int(frame_rate/self.freq1)
        # cycle2 = int(frame_rate/self.freq2)
        # self.stim_patterns = [
        # init_flicker_stim(frame_rate, cycle1, self.soa),
        # init_flicker_stim(frame_rate, cycle2, self.soa),
        # ]
        
        # print(
        #     (
        #         "\nFlickering frequencies (Hz): {}\n".format(
        #             [self.stim_patterns[0]["freq"], self.stim_patterns[1]["freq"]]
        #         )
        #     )
        # )

        # return [
        #     init_flicker_stim(frame_rate, cycle1, self.soa),
        #     init_flicker_stim(frame_rate, cycle2, self.soa),
        # ]


    def present_stimulus(self):
        
        # ind = self.trials["parameter"].iloc[idx]
        self.running = True

        # Push sample
        # replace with pushing dependent on key input
        # if self.eeg:
        #     timestamp = time()
        #     if self.eeg.backend == "muselsl":
        #         marker = [self.markernames[ind]]
        #     else:
        #         marker = self.markernames[ind]
        #     self.eeg.push_sample(marker=marker, timestamp=timestamp)
            
        # def log_key_input():
        #     # nonlocal running
        #     def on_key_event(event):
        #         if event.name == 'left' or event.name == 'right':
        #             marker = 1 if event.name == 'left' else 2 
        #             # print("Marker logged:", marker)
        #             timestamp = time()
        #             if self.eeg: 
        #                 self.eeg.push_sample(marker=marker, timestamp=timestamp)
        #         elif event.name == 'space':
        #             print("Experiment interrupted by user")
        #             # if self.eeg: self.eeg._stop_brainflow(), print(self.save_fn) 
        #             self.running = False
        #     keyboard.on_press(on_key_event)
        #     # return on_key_event

        # # event_handler = log_key_input(self)
        # log_key_input()

        
        # Present flickering stim
        # try:
        start_time = time()
        cycle_duration_1 = 1.0 / self.freq1  # Duration of one cycle of _stim1
        cycle_duration_2 = 1.0 / self.freq2  # Duration of one cycle of _stim2
        next_flip_time_1 = start_time + cycle_duration_1
        next_flip_time_2 = start_time + cycle_duration_2

        self._stim1.setAutoDraw(True)
        self._stim1_neg.setAutoDraw(False)
        self._stim2.setAutoDraw(True)
        self._stim2_neg.setAutoDraw(False)

        while self.running and (time()-start_time) <= self.record_duration:
            current_time = time()
            if current_time >= next_flip_time_1:
                self._stim1.setAutoDraw(not self._stim1.autoDraw)  # Toggle visibility
                self._stim1_neg.setAutoDraw(not self._stim1_neg.autoDraw)  # Toggle visibility
                # self.window.flip()
                next_flip_time_1 += cycle_duration_1

            if current_time >= next_flip_time_2:
                self._stim2.setAutoDraw(not self._stim2.autoDraw)  # Toggle visibility
                self._stim2_neg.setAutoDraw(not self._stim2_neg.autoDraw)  # Toggle visibility
                # self.window.flip()
                next_flip_time_2 += cycle_duration_2
            self.window.flip()
        # finally:
            # keyboard.unhook(event_handler)

        self._stim1.setAutoDraw(False)
        self._stim1_neg.setAutoDraw(False)
        self._stim2.setAutoDraw(False)
        self._stim2_neg.setAutoDraw(False)
        
        # keyboard.unhook_all()

            # Number of frames to run the loop for the longer of the two cycles
        # Example adjustment if self.stim_patterns contains cycle counts for multiple stimuli
        # max_cycles = max([pattern["n_cycles"] for pattern in self.stim_patterns])

        
        # # Separate cycle counts for each stimulus
        # cycle1_frames = self.stim_patterns[ind]["cycle"][0]
        # cycle2_frames = self.stim_patterns[ind]["cycle"][1]

        # # Frame counters for each stimulus
        # frame_counter1 = 0
        # frame_counter2 = 0

        # # Run the loop for the maximum number of cycles
        # for _ in range(max_cycles):
        #     if frame_counter1 < cycle1_frames:
        #         self._stim1.setAutoDraw(True)
        #     else:
        #         self._stim1.setAutoDraw(False)

        #     if frame_counter2 < cycle2_frames:
        #         self._stim2.setAutoDraw(True)
        #     else:
        #         self._stim2.setAutoDraw(False)

        #     # Increment frame counters
        #     frame_counter1 = (frame_counter1 + 1) % (2 * cycle1_frames)
        #     frame_counter2 = (frame_counter2 + 1) % (2 * cycle2_frames)

        #     # Flip the window to update the display
        #     self.window.flip()

        # # Ensure both stimuli are turned off after flashing
        # self._stim1.setAutoDraw(False)
        # self._stim2.setAutoDraw(False)
        # self.window.flip()

    def setup(self, instructions=True):

            # Initializing the record duration and the marker names
            self.record_duration = np.float32(self.duration)
            self.markernames = [1, 2]
            
            # Setting up the trial and parameter list
            # self.parameter = np.random.binomial(1, 0.5, self.n_trials)
            # self.trials = DataFrame(dict(parameter=self.parameter, timestamp=np.zeros(self.n_trials)))

            # Setting up Graphics 
            self.window = visual.Window([1536, 864], monitor="testMonitor", units="deg", fullscr=True) 
            
            # Loading the stimulus from the specific experiment, throws an error if not overwritten in the specific experiment
            self.stim = self.load_stimulus()
            
            # Show Instruction Screen if not skipped by the user
            if instructions:
                self.show_instructions()

            # Checking for EEG to setup the EEG stream
            if self.eeg:
                # If no save_fn passed, generate a new unnamed save file
                if self.save_fn is None:  
                    # Generating a random int for the filename
                    random_id = random.randint(1000,10000)
                    # Generating save function
                    experiment_directory = self.name.replace(' ', '_')
                    self.save_fn = generate_save_fn(self.eeg.device_name, experiment_directory, random_id, random_id, "unnamed")

                    print(
                        f"No path for a save file was passed to the experiment. Saving data to {self.save_fn}"
                    )

    

    def run(self, instructions=True):

        # Setup the experiment, alternatively could get rid of this line, something to think about
        self.setup(instructions)

        print("Wait for the EEG-stream to start...")

        # Start EEG Stream, wait for signal to settle, and then pull timestamp for start point
        if self.eeg:
            self.eeg.start(self.save_fn, duration=self.record_duration + 5)
            print("EEG Stream started")
        else: 
            print("No EEG headset connected")

        print("Experiment started")
        # start = time()
        
        self.present_stimulus()

        # Iterate through the events
        # for ii, trial in self.trials.iterrows():
          
        #     # Intertrial interval
        #     # core.wait(self.iti + np.random.rand() * self.jitter)

        #     # Stimulus presentation overwritten by specific experiment
        #     self.present_stimulus(ii, trial)

        #     # Offset
        #     core.wait(self.soa)
        #     self.window.flip()

        #     # Exiting the loop condition, looks ugly and needs to be fixed
        #     if len(event.getKeys()) > 0 or (time() - start) > self.record_duration:
        #         break

        #     # Clearing the screen for the next trial    
        #     event.clearEvents()
        print("Experiment ended")
        # Closing the EEG stream 
        if self.eeg:
            self.eeg.stop()
            print("Stop EEG stream")
            print("Recording saved at", self.save_fn)
        # Closing the window
        self.window.close()