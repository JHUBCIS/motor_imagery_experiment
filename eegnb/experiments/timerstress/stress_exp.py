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




class Stress_exp(Experiment.BaseExperiment):
    '''
    EEG Data streamed and recorded through the Unicorn Recorder
    '''
    def __init__(self, duration, eeg: Optional[EEG] = None, save_fn = None):
      
        exp_name = "motor_imagery"
        super().__init__(exp_name, duration, eeg, save_fn, n_trials = None, iti = None, soa = None, jitter = None)

        self.instruction_text ="""\nWelcome to the {} experiment!\n\nWhen stimuli are presented, use left/right arrow to indicate which stimulus you are looking at.\nPlease pause a bit between selections.\n\nThis experiment will run for %s seconds.\nPress spacebar to start, press again to interrupt. \n""".format(
            self.exp_name)
        

    def load_stimulus(self):
        pass

    def present_stimulus(self):
        self.running = True

        TOTAL_DURATION = 10 * 60
        start_time = time()
      
        
        # Create a countdown timer visual
        timer_text = visual.TextStim(
            self.window,
            text="",
            wrapWidth=30,
            color='white',
            height=5
        )

        while self.running and time() - start_time < TOTAL_DURATION:
          elapsed = time() - start_time
          remaining = int(TOTAL_DURATION - elapsed)
          mins, secs = divmod(remaining, 60)
          timer_text.text = f"{mins:02d}:{secs:02d}"
          timer_text.draw()
          self.window.flip()
  
          # Optional: ESC to quit early
          if 'escape' in event.getKeys():
              self.running = False
              break
            
            

    def setup(self, instructions=True):

            # Initializing the record duration and the marker names
            self.record_duration = np.float32(self.duration)
            self.markernames = [1, 2]
            
            # Setting up the trial and parameter list
            # self.parameter = np.random.binomial(1, 0.5, self.n_trials)
            # self.trials = DataFrame(dict(parameter=self.parameter, timestamp=np.zeros(self.n_trials)))

            # Setting up Graphics 
            self.window = visual.Window([1536, 864], monitor="testMonitor", units="deg", fullscr=True) 
            self.window.color = 'black' # set background color to black
            self.window.flip()
            
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
        self.setup(instructions)

        print("Wait for the EEG-stream to start...")

        emaFilt = EMA_Filters()
        self._stop_event = threading.Event()
        def eeg_stream_thread():
            eeg = self.eeg
            sfreq = eeg.sfreq
            bp_fc_low = 8
            bp_fc_high = 30
            n_fc = 60

            while eeg.stream_started and not self._stop_event.is_set():
                data = eeg.board.get_current_board_data(1)
                _, eeg_data, timestamps = eeg._brainflow_extract(data)
                eeg_data_filt = emaFilt.BPF(eeg_data, bp_fc_low, bp_fc_high, sfreq)  # bandpass filter
                eeg_data_filt = emaFilt.Notch(eeg_data_filt, n_fc, sfreq)  # notch filter
                if len(eeg_data) > 0 and len(timestamps) > 0:
                    last_timestamp = data[eeg.timestamp_channel][0]
                    eeg.filt_data.append([eeg_data_filt[0].tolist(), last_timestamp])

        if self.eeg:
            self.eeg.start(self.save_fn, duration=self.record_duration + 10)
            print("eeg stream started")
            eeg_filt_thread = threading.Thread(target=eeg_stream_thread)
            eeg_filt_thread.daemon = True
            eeg_filt_thread.start()
            print("eeg_filt_thread initiated")
        else:
            print("No EEG headset connected")

        print("Experiment started")
        self.present_stimulus()
        print("Experiment ended")

        if self.eeg:
            self._stop_event.set()
            eeg_filt_thread.join()
            print("eeg_filt_thread terminated")

            self.eeg._stop_brainflow()
            print("Stop EEG stream")
            print("Recording saved at", self.save_fn)

        self.window.close()
        core.quit()


        # Save the DataFrame to a CSV file
        # Directory to save the labels
        # save_dir = "experiment_labels"
        # os.makedirs(save_dir, exist_ok=True)  # Create the directory if it doesn't exist

        # # Find an available filename by incrementing the index
        # i = 1
        # while os.path.exists(f"{save_dir}/experiment_{i}.csv"):
        #     i += 1

        # # Save the DataFrame with the unique filename
        # file_path = f"{save_dir}/experiment_{i}.csv"
        # df = DataFrame(self.stim_labels)  # Assuming `self.stim_labels` is the data to be saved
        # df.to_csv(file_path, index=False)

        # print(f"Labels saved to {file_path}")
