import os
from time import time
from glob import glob
from random import choice
import threading

import numpy as np
import random
from pandas import DataFrame
from psychopy import visual, core, event

from eegnb.experiments import Experiment
from eegnb.devices.EMA_Filters import EMA_Filters
from eegnb.devices.eeg import EEG
from eegnb import generate_save_fn

from typing import Optional

import keyboard


class VisualSSVEP_select(Experiment.BaseExperiment):
    '''
    SSVEP experiment with 2 visual stimuli, by JHUBCIS
    Subject can choose to focus on one of the two stimuli, and use left/right arrow to indicate which one they were focusing on.
    When not focusing on a stimulus, the subject can focus on the red fixation point in the middle.
    The experiment can be designed to last a defined duration, or can be interrupted by the subject pressing a spacebar.
    Recorded data will be saved to specified file path.
    '''

    def __init__(self, duration, eeg: Optional[EEG] = None, save_fn=None, freq1=7, freq2=23, bp_fc_high=60, bp_fc_low=1,
                 n_fc=60):  # 1 for left, 2 for right

        exp_name = "Visual SSVEP"
        super().__init__(exp_name, duration, eeg, save_fn, n_trials=None, iti=None, soa=None, jitter=None)
        self.instruction_text = """\nWelcome to the {} experiment!\n\nWhen stimuli are presented, use left/right arrow to indicate which stimulus you are looking at.\nPlease pause a bit between selections.\n\nThis experiment will run for %s seconds.\nPress spacebar to start, press again to interrupt. \n""".format(
            self.exp_name)
        self.freq1 = freq1
        self.freq2 = freq2
        self.bp_fc_high = bp_fc_high
        self.bp_fc_low = bp_fc_low
        self.n_fc = n_fc

    def load_stimulus(self):

        pattern = np.ones((4, 4))
        pattern[::2, ::2] *= -1
        pattern[1::2, 1::2] *= -1
        pos1 = [-18, -8]
        pos2 = [18, -8]
        size = 5
        self._stim1 = visual.RadialStim(win=self.window, tex=pattern, pos=pos1,
                                        size=size, radialCycles=2, texRes=256, opacity=1)
        self._stim1_neg = visual.RadialStim(win=self.window, tex=pattern * (-1), pos=pos1,
                                            size=size, radialCycles=2, texRes=256, opacity=1)
        self._stim2 = visual.RadialStim(win=self.window, tex=pattern, pos=pos2,
                                        size=size, radialCycles=1, texRes=256, opacity=1)
        self._stim2_neg = visual.RadialStim(win=self.window, tex=pattern * (-1), pos=pos2,
                                            size=size, radialCycles=1, texRes=256, opacity=1)
        fixation = visual.GratingStim(win=self.window, size=0.2, pos=[0, 8], sf=0.2, color=[1, 0, 0], autoDraw=True)

    def present_stimulus(self):

        self.running = True

        def log_key_input():
            # nonlocal running
            def on_key_event(event):
                if event.name == 'left' or event.name == 'right':
                    marker = 1 if event.name == 'left' else 2
                    # print("Marker logged:", marker)
                    timestamp = time()
                    if self.eeg:
                        self.eeg.push_sample(marker=marker, timestamp=timestamp)
                elif event.name == 'space':
                    print("Experiment interrupted by user")
                    self.running = False

            keyboard.on_press(on_key_event)
            # return on_key_event

        log_key_input()

        # Present flickering stim
        start_time = time()
        cycle_duration_1 = 1.0 / self.freq1  # Duration of one cycle of _stim1
        cycle_duration_2 = 1.0 / self.freq2  # Duration of one cycle of _stim2
        next_flip_time_1 = start_time + cycle_duration_1
        next_flip_time_2 = start_time + cycle_duration_2

        self._stim1.setAutoDraw(True)
        self._stim1_neg.setAutoDraw(False)
        self._stim2.setAutoDraw(True)
        self._stim2_neg.setAutoDraw(False)

        while self.running and (time() - start_time) <= self.record_duration:
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

        self._stim1.setAutoDraw(False)
        self._stim1_neg.setAutoDraw(False)
        self._stim2.setAutoDraw(False)
        self._stim2_neg.setAutoDraw(False)

        keyboard.unhook_all()

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
                random_id = random.randint(1000, 10000)
                # Generating save function
                experiment_directory = self.name.replace(' ', '_')
                self.save_fn = generate_save_fn(self.eeg.device_name, experiment_directory, random_id, random_id,
                                                "unnamed")

                print(
                    f"No path for a save file was passed to the experiment. Saving data to {self.save_fn}"
                )

    def run(self, instructions=True):

        # Setup the experiment, alternatively could get rid of this line, something to think about
        self.setup(instructions)

        print("Wait for the EEG-stream to start...")

        emaFilt = EMA_Filters()
        self._stop_event = threading.Event()

        def eeg_stream_thread():
            eeg = self.eeg
            sfreq = eeg.sfreq
            bp_fc_low = self.bp_fc_low
            bp_fc_high = self.bp_fc_high
            n_fc = self.n_fc

            while eeg.stream_started and not self._stop_event.is_set():
                data = eeg.board.get_current_board_data(1)
                _, eeg_data, timestamps = eeg._brainflow_extract(data)
                eeg_data_filt = emaFilt.BPF(eeg_data, bp_fc_low, bp_fc_high, sfreq)  # bandpass filter
                eeg_data_filt = emaFilt.Notch(eeg_data_filt, n_fc, sfreq)  # notch filter
                if len(eeg_data) > 0 and len(timestamps) > 0:  # only update if neither is empty
                    last_timestamp = data[eeg.timestamp_channel][0]
                    eeg.filt_data.append([eeg_data_filt[0].tolist(), last_timestamp])
                else:
                    time.sleep(1)
                    continue

        # Start EEG Stream, wait for signal to settle, and then pull timestamp for start point
        if self.eeg:
            self.eeg.start(self.save_fn, duration=self.record_duration + 10)
            print("eeg stream started")
            eeg_filt_thread = threading.Thread(target=eeg_stream_thread)
            eeg_filt_thread.daemon = True
            eeg_filt_thread.start()
            # time.sleep(10)
            print("eeg_filt_thread initiated")
        else:
            print("No EEG headset connected")

        print("Experiment started")

        self.present_stimulus()

        print("Experiment ended")

        # Closing the EEG stream
        if self.eeg:
            self._stop_event.set()
            eeg_filt_thread.join()
            print("eeg_filt_thread terminated")

            self.eeg._stop_brainflow_save_filt()
            print("Stop EEG stream")
            print("Recording saved at", self.save_fn)
        # Closing the window
        self.window.close()