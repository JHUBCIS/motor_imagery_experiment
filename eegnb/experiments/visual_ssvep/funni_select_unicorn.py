import os
from time import time
from glob import glob
from random import choice
import threading 

import numpy as np
import random
from pandas import DataFrame
from psychopy import visual, core, event, constants

from eegnb.experiments import Experiment
# from eegnb.devices.EMA_Filters import EMA_Filters
from eegnb.devices.eeg import EEG
from eegnb import generate_save_fn

from typing import Optional

# import keyboard
import socket


class VisualFunni_select_unicorn(Experiment.BaseExperiment):
    '''
    Welcome to the experiment
    EEG Data streamed and recorded through the Unicorn Recorder
    '''
    def __init__(self, duration, IP = "127.0.0.1", Port = 800):
      
        exp_name = "Motor Imagery "
        super().__init__(exp_name, duration, eeg = None, save_fn = None, n_trials = None, iti = None, soa = None, jitter = None)
        # self.instruction_text = """\n
        # Welcome to the {} experiment!\n\n
        # When stimuli are presented, use left/right arrow to indicate which stimulus you are looking at.\n
        # Please pause a bit between selections.\n\n
        # This experiment will run for %s seconds.\n
        # Press spacebar to start, press again to interrupt. \n""".format(self.exp_name)
        self.instruction_text = (
            "\n"
            "Welcome to the {} experiment!\n\n"
            "Please follow the instructions on screen, thank you.\n"
            "This experiment will run for %s seconds.\n"
            "Press spacebar to interrupt.\n"
        ).format(self.exp_name)
        # self.freq1 = freq1
        # self.freq2 = freq2
        # self.bp_fc_high = bp_fc_high
        # self.bp_fc_low = bp_fc_low
        # self.n_fc = n_fc
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.endPoint = (IP, Port)
        

    def load_stimulus(self): 

        # video_path = ""
        # self.video = visual.MovieStim3(win=self.window, filename=video_path, size=(640, 480))
        # self.fixation = visual.GratingStim(win=self.window, size=0.2, pos=[0, 8], sf=0.2, color=[1, 0, 0], autoDraw=True)

        
        # pattern = np.ones((4, 4))
        # # pattern[::2, ::2] *= -1
        # # pattern[1::2, 1::2] *= -1
        # pos1 = [-14, -4]
        # pos2 = [14, -4]
        # size = 8
        # self._stim1 = visual.RadialStim(win=self.window, tex=pattern, pos=pos1,
        #                                 size=size, radialCycles=2, texRes=256, opacity=1)  
        # self._stim1_neg = visual.RadialStim(win=self.window, tex=pattern*(-1), pos=pos1,
        #                                 size=size, radialCycles=2, texRes=256, opacity=1)
        # self._stim2 = visual.RadialStim(win=self.window, tex=pattern, pos=pos2,
        #                                 size=size, radialCycles=1, texRes=256, opacity=1)
        # self._stim2_neg = visual.RadialStim(win=self.window, tex=pattern*(-1), pos=pos2,
        #                                 size=size, radialCycles=1, texRes=256, opacity=1)
                                        
        # fixation = visual.GratingStim(win=self.window, size=0.2, pos=[0, 8], sf=0.2, color=[1, 0, 0], autoDraw=True)
        pass

    def present_stimulus(self):
        
        self.running = True
    
        def log_key_input():
            def on_key_event(event):
                # if event.name == 'a' or event.name == 's':
                    # marker = b"1" if event.name == 'a' else b"2" 
                    # print("Marker logged:", marker)
                    # timestamp = time()
                    # self.socket.sendto(marker, self.endPoint)
                    # if self.eeg: 
                    #     self.eeg.push_sample(marker=marker, timestamp=timestamp)
                    if event.name == 'space':
                        print("Experiment interrupted by user")
                        self.running = False
            # keyboard.on_press(on_key_event)
            # return on_key_event

        log_key_input()

        start_time = time()   
        self.socket.sendto(b"1", self.endPoint)
        

        VIDEO_DURATION = 5
        INSTRUCTION_DURATION = 2
        ACTION_DURATION = 5
        REST_DURATION = 5

        NUM_SETS = int(self.record_duration // (VIDEO_DURATION + INSTRUCTION_DURATION + ACTION_DURATION + REST_DURATION))

        
        for i in range(NUM_SETS):
            # Run a set of trials with and without visual stimulus
            self.run_set(True, VIDEO_DURATION, INSTRUCTION_DURATION, ACTION_DURATION, REST_DURATION)  # With video
            self.run_set(False, VIDEO_DURATION, INSTRUCTION_DURATION, ACTION_DURATION, REST_DURATION)  # Without video  
        
        # keyboard.unhook_all()

    def run_set(self, with_video, vid_dur, inst_dur, action_dur, rest_dur):
        """Runs a set of trials based on whether there's a visual stimulus."""
        set_start_time = time()
        
        # Cycle between trials with and without video
        if with_video:
            self.trial_cycle(True, True, vid_dur, inst_dur, action_dur, rest_dur)  # Video + Action
        else:
            self.trial_cycle(False, True, vid_dur, inst_dur, action_dur, rest_dur)  # No Video, only Action


    def trial_cycle(self, with_video, is_imagery, video_path, vid_dur, inst_dur, action_dur, rest_dur):
        action_prompt = visual.TextStim(self.window, text="Prepare to do\nthe action shown.", wrapWidth=30, alignText='center', color='white')
        imagery_prompt = visual.TextStim(self.window, text="Prepare to imagine\nthe action shown.", wrapWidth=30, alignText='center', color='white')
        perform_prompt = visual.TextStim(self.window, text="DO\nIT!", wrapWidth=30, alignText='center', color='white')
        rest_prompt = visual.TextStim(self.window, text="Rest for 5 seconds.\nPrepare for next trial.", wrapWidth=30, alignText='center', color='white')

        # 1. Show video (if applicable)
        if with_video:
            video_start_time = time()
            while self.running and time() < (video_start_time + vid_dur):
                # Play video here
                self.window.flip()

        # 2. Show instructions (2 seconds)
        instruction_start_time = time()
        while self.running and time() < (instruction_start_time + inst_dur):
            if is_imagery:
                imagery_prompt.draw()
            else:
                action_prompt.draw()
            self.window.flip()

        # 3. Perform/imagine movement (5 seconds)
        perform_start_time = time()
        while self.running and time() < (perform_start_time + action_dur):
            perform_prompt.draw()
            self.window.flip()

        # 4. Rest (5 seconds)
        rest_start_time = time()
        while self.running and time() < (rest_start_time + rest_dur):
            rest_prompt.draw()
            self.window.flip()


        video_start_time = time()
        while self.running and time() < (video_start_time + vid_dur): 
            current_time = time()
            #video imagine, video 
            if (with_video):
                pass # PLAY VIDEO HERE :)
            

            self.window.flip()
        
        instruction_start_time = time()
        while self.running and time() < (instruction_start_time + inst_dur): # play instructions 
            
            if (is_imagery):
                imagery_prompt.draw()
            else:
                action_prompt.draw()
            
            self.window.flip()
        
        perform_start_time = time()
        while self.running and time() < (perform_start_time + action_dur): # show perform prompt
            perform_prompt.draw()
            self.window.flip()
        
        rest_start_time = time()
        while self.running and time() < (rest_start_time + rest_dur): # rest for 5 seconds
            rest_prompt.draw()
            self.window.flip()
        
        pass


    def setup(self, instructions=True):

            # Initializing the record duration and the marker names
            self.record_duration = np.float32(self.duration)
            self.markernames = [1, 2]
            
            # Setting up the trial and parameter list
            # self.parameter = np.random.binomial(1, 0.5, self.n_trials)
            # self.trials = DataFrame(dict(parameter=self.parameter, timestamp=np.zeros(self.n_trials)))

            # Setting up Graphics 
            self.window = visual.Window([1536, 864], winType='glfw', monitor="testMonitor", units="deg", fullscr=True) 
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

        #Setup the experiment, alternatively could get rid of this line, something to think about
        self.setup(instructions)

        win = visual.Window(size=(800, 600), winType='glfw')
        mov = visual.MovieStim3(win, 'eegnb/experiments/visual_ssvep/wrist_flexing_right-1.mp4', size=(320, 240),
        flipVert=False, flipHoriz=False, loop=False)
        print('orig movie size=%s' % mov.size)
        print('duration=%.2fs' % mov.duration)
        globalClock = core.Clock()

        while mov.status != constants.FINISHED:
            mov.draw()
            win.flip()
            if event.getKeys():
                break

        win.close()
        core.quit()

        print("Wait for the EEG-stream to start...")

        #emaFilt = EMA_Filters()
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
                #eeg_data_filt = emaFilt.BPF(eeg_data, bp_fc_low, bp_fc_high, sfreq) #bandpass filter
                #eeg_data_filt = emaFilt.Notch(eeg_data_filt, n_fc, sfreq) #notch filter
                if len(eeg_data) > 0 and len(timestamps) > 0: # only update if neither is empty
                    last_timestamp = data[eeg.timestamp_channel][0]
                    #eeg.filt_data.append([eeg_data_filt[0].tolist(), last_timestamp])
                else:
                    time.sleep(1)
                    continue

        #Start EEG Stream, wait for signal to settle, and then pull timestamp for start point
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