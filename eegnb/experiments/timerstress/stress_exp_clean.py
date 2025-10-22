import sys
import time
import threading 

import numpy as np
import random

from eegnb.experiments import Experiment
from eegnb.devices.EMA_Filters import EMA_Filters
from eegnb.devices.eeg import EEG
from eegnb import generate_save_fn

from typing import Optional
import tkinter as tk

def run_timer_popup(duration_minutes=10):
    """Creates and runs a simple, updating timer window."""
    
    root = tk.Tk()
    root.title("Timer")
    root.geometry("1600x800") # Simple size
    root.attributes('-topmost', True) # Keep window on top
    
    TOTAL_DURATION = duration_minutes * 60
    start_time = time.time()
    
    # Label to display the time
    time_label = tk.Label(root, font=("Arial", 80, "bold")) 
    time_label.pack(expand=True, fill='both')

    # Function to update the display recursively
    def update_time():
        elapsed = time.time() - start_time
        remaining = int(TOTAL_DURATION - elapsed)
        
        if remaining <= 0:
            time_label.config(text="DONE", fg="red")
            return
            
        mins, secs = divmod(remaining, 60)
        time_label.config(text=f"{mins:02d}:{secs:02d}")
        
        # Schedule the next update in 1000ms (1 second)
        root.after(1000, update_time)

    # Start the update loop
    update_time()
    root.mainloop()

class Stress_exp(Experiment.BaseExperiment):
    '''
    EEG Data streamed and recorded through the Unicorn Recorder
    '''
    def __init__(self, duration, eeg: Optional[EEG] = None, save_fn = None):
      
        exp_name = "motor_imagery"
        super().__init__(exp_name, duration, eeg, save_fn, n_trials = None, iti = None, soa = None, jitter = None)

        self.instruction_text ="""\nWelcome to the {} experiment!\n\nYou will have 10 minutes to complete the test.\n\nThis experiment will run for %s seconds.\nPress spacebar to start, press again to interrupt. \n""".format(
            self.exp_name)
        

    def load_stimulus(self):
        pass

    def present_stimulus(self):
        self.running = True

        TOTAL_DURATION = 10 * 60  # For reference only
        start_time = time.time()
        
        print("\n[--- Stimulus Presentation/Timer Active ---]")

        # A simple, passive wait loop. This will block until TOTAL_DURATION 
        # is reached or self.running is set to False externally (e.g., via keyboard listener).
        while self.running and time.time() - start_time < TOTAL_DURATION:
            time.sleep(1) # Sleep to minimize CPU usage while waiting

        # --- LOOP ENDS ---
        if time.time() - start_time >= TOTAL_DURATION:
            print("\n[--- Duration Complete ---]")
        else:
            print("\n[--- Test Interrupted ---]")
            

    def setup(self, instructions=True):

            # Initializing the record duration and the marker names
            self.record_duration = np.float32(self.duration)
            self.markernames = [1, 2]
            
            # Loading the stimulus from the specific experiment, throws an error if not overwritten in the specific experiment
            self.stim = self.load_stimulus()
            
            # Show Instruction Screen if not skipped by the user
            # if instructions:
            #     self.show_instructions()

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

        TIMER_DURATION_MINUTES =  10 
        timer_gui_thread = threading.Thread(
            target=run_timer_popup, 
            args=(TIMER_DURATION_MINUTES,), 
            daemon=True
        )
        timer_gui_thread.start()
        print(f"Timer pop-up launched for {TIMER_DURATION_MINUTES} minutes.")

        print("Experiment started")
    
        try:
            self.present_stimulus()
            
        except KeyboardInterrupt:
            print("\n\n>>> Keyboard Interrupt Detected. Shutting down cleanly... <<<")
            # Ensure the main loop flag is set to False if it wasn't already
            self.running = False 
            
        finally:
            # This 'finally' block GUARANTEES that the cleanup code runs, 
            # whether the experiment finished normally OR was interrupted.
            print("Experiment ended")

            if self.eeg:
                self._stop_event.set()
                # It's important to join the threads outside the try block 
                # or in a finally block to ensure they are cleaned up.
                eeg_filt_thread.join()
                print("eeg_filt_thread terminated")

                self.eeg._stop_brainflow()
                print("Stop EEG stream")
                print("Recording saved at", self.save_fn)