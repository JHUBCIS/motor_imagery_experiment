import os
from time import time
import threading
import random

import numpy as np
from pandas import DataFrame
from psychopy import visual

from eegnb.experiments import Experiment
from eegnb.devices.EMA_Filters import EMA_Filters
from eegnb.devices.eeg import EEG
from eegnb import generate_save_fn

from typing import Optional


class VisualFunniSelectUnicorn(Experiment.BaseExperiment):
    '''
    Blah Blah Blah it's cool :)

    EEG Data streamed and recorded through the Unicorn Recorder
    '''
    def __init__(self, duration, eeg: Optional[EEG] = None, save_fn=None):
        exp_name = "motor_imagery"
        super().__init__(exp_name, duration, eeg, save_fn, n_trials=None, iti=None, soa=None, jitter=None)

        self.instruction_text = (
            "\nWelcome to the {} experiment!\n\nWhen stimuli are presented, use left/right arrow to indicate which "
            "stimulus you are looking at.\nPlease pause a bit between selections.\n\nThis experiment will run for %s "
            "seconds.\nPress spacebar to start, press again to interrupt. \n".format(self.exp_name)
        )

    def load_stimulus(self):
        pass

    def present_stimulus(self):
        self.running = True

        VIDEO_DURATION = 5
        INSTRUCTION_DURATION = 2
        TRIAL_DURATION = 5
        REST_DURATION = 5

        NUM_SETS = 10
        NUM_MI_SETS = 30

        video_paths = [
            r"/home/daniel/Documents/motor_imagery_experiment/eegnb/experiments/motor_imagery/movements/movements/wrist_flexing_left.mp4",
            r"/home/daniel/Documents/motor_imagery_experiment/eegnb/experiments/motor_imagery/movements/movements/wrist_flexing_right-1.mp4"
        ]

        trial_count = 1
        for i in range(NUM_SETS):
            for movement in [1, 2]:
                self.run_set(video_paths[movement - 1], VIDEO_DURATION, INSTRUCTION_DURATION, TRIAL_DURATION, REST_DURATION, trial_count, movement)
                trial_count += 1

        for i in range(NUM_MI_SETS):
            for movement in [1, 2]:
                self.trial_cycle(False, True, video_paths[movement - 1], VIDEO_DURATION, INSTRUCTION_DURATION, TRIAL_DURATION, REST_DURATION, trial_count, movement)
                trial_count += 1

    def run_set(self, video_path, vid_dur, inst_dur, trial_dur, rest_dur, trial_count, movement):
        for with_video, is_imagery in [(True, False), (True, True), (False, False), (False, True)]:
            self.trial_cycle(with_video, is_imagery, video_path, vid_dur, inst_dur, trial_dur, rest_dur, trial_count, movement)

    def trial_cycle(self, with_video, is_imagery, video_path, vid_dur, inst_dur, trial_dur, rest_dur, trial_count, movement):
        prompts = {
            "action": visual.TextStim(self.window, text=f"Prepare to do\nthe movement {movement}.", wrapWidth=30, alignText='center', color='white'),
            "imagery": visual.TextStim(self.window, text=f"Prepare to imagine\nmovement {movement}.", wrapWidth=30, alignText='center', color='white'),
            "perform_action": visual.TextStim(self.window, text=f"Perform movement {movement}", wrapWidth=30, alignText='center', color='white'),
            "perform_imagery": visual.TextStim(self.window, text=f"Imagine movement {movement}", wrapWidth=30, alignText='center', color='white'),
            "rest": visual.TextStim(self.window, text="Rest for 5 seconds.\nPrepare for next trial.", wrapWidth=30, alignText='center', color='white')
        }

        self._run_phase("video", with_video, video_path, vid_dur, trial_count, movement)
        self._run_phase("instruction", is_imagery, prompts["imagery"] if is_imagery else prompts["action"], inst_dur, trial_count, movement, "2")
        self._run_phase("perform", is_imagery, prompts["perform_imagery"] if is_imagery else prompts["perform_action"], trial_dur, trial_count, movement, "3" if is_imagery else "4")
        self._run_phase("rest", False, prompts["rest"], rest_dur, trial_count, movement, "5")

    def _run_phase(self, phase_name, with_video, content, duration, trial_count, movement, marker_suffix=""):        
        sent_marker = False
        start_time = time()
        while self.running and time() < (start_time + duration):
            if phase_name == "video" and with_video:
                mov = visual.MovieStim3(self.window, content, size=(800, 600), flipVert=False, flipHoriz=False, loop=False)
                while mov.status != visual.FINISHED and self.running:
                    self._send_marker(trial_count, 1, movement, sent_marker)
                    self._draw_video_frame(mov, movement)
                    sent_marker = True
                self.window.flip()
            elif phase_name != "video":
                self._send_marker(trial_count, marker_suffix, movement, sent_marker)
                content.draw()
                self.window.flip()
                sent_marker = True

    def _send_marker(self, trial_count, vid, movement, sent_marker):
        if not sent_marker:
            marker = float(f"{trial_count}{vid}{movement}")
            timestamp = time()
            self.eeg.push_sample(marker=marker, timestamp=timestamp)

    def _draw_video_frame(self, mov, movement):
        movement_description = visual.TextStim(
            win=self.window,
            text=f"Movement {movement}",
            wrapWidth=30,
            alignText='left',
            color='white',
        )
        mov.draw()
        movement_description.draw()
        self.window.flip()

    def setup(self, instructions=True):
        self.record_duration = np.float32(self.duration)
        self.markernames = [1, 2]

        self.window = visual.Window([1536, 864], monitor="testMonitor", units="deg", fullscr=True)
        self.window.color = 'black'
        self.window.flip()
        self.stim = self.load_stimulus()

        if instructions:
            self.show_instructions()

        if self.eeg:
            if self.save_fn is None:
                random_id = random.randint(1000, 10000)
                experiment_directory = self.name.replace(' ', '_')
                self.save_fn = generate_save_fn(self.eeg.device_name, experiment_directory, random_id, random_id, "unnamed")
                print(f"No path for a save file was passed to the experiment. Saving data to {self.save_fn}")

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
