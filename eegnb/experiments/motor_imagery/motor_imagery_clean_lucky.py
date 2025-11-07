import os
from time import time, sleep
import threading
import random

import numpy as np
from pandas import DataFrame
import pygame
import cv2 # For video handling

from eegnb.experiments import Experiment
from eegnb.devices.EMA_Filters import EMA_Filters
from eegnb.devices.eeg import EEG
from eegnb import generate_save_fn

from typing import Optional


class MotorImageryExperiment(Experiment.BaseExperiment):
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
        self.window = None # Will hold the pygame display surface
        self.window_size = (1536, 864) # Use a fixed resolution for text centering
        self.fps = 60 # Set a consistent target frame rate
        self.clock = pygame.time.Clock() # Pygame Clock for frame rate control

    def load_stimulus(self):
        # Pygame does not require a separate load function for text/simple elements
        pass

    def _create_pygame_text(self, text, font_size=30, color=(255, 255, 255)):
        '''Helper to create a centered Pygame text surface and its rectangular position.'''
        # Use system font, e.g., Arial, or specify a path to a .ttf file
        try:
            font = pygame.font.SysFont('Arial', font_size, bold=True)
        except:
            # Fallback if 'Arial' is not found
            font = pygame.font.Font(None, font_size)
            
        text_surface = font.render(text, True, color)
        # Center the text on the screen
        text_rect = text_surface.get_rect(center=(self.window_size[0] / 2, self.window_size[1] / 2))
        return {"surface": text_surface, "rect": text_rect}

    def _handle_input(self):
        '''
        Helper to check for critical user input (interruption/quit).
        Must be called frequently within all display loops.
        '''
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.running = False
                print("Experiment manually interrupted.")
                return True # Signal interruption
            elif event.type == pygame.QUIT:
                self.running = False
                print("Window close requested, interrupting experiment.")
                return True
            # NOTE: Logic for Left/Right Arrow keys would be added here
        return False # No critical input detected


    def present_stimulus(self):
        self.running = True
        
        # --- CRITICAL CHANGE: Removed input_thread and check_interruption function ---
        # Input handling is now managed by _handle_input() in the main thread loops.


        VIDEO_DURATION = 5
        INSTRUCTION_DURATION = 1
        TRIAL_DURATION = 2
        REST_DURATION = 1

        NUM_SETS = 1
        NUM_MI_SETS = 0

        # Preserving original hardcoded paths
        video_paths = [
            r"C:\Users\kthbl\Documents\motor_imagery_experiment\eegnb\experiments\motor_imagery\movements\wrist_flexing_left.mp4",
            r"C:\Users\kthbl\Documents\motor_imagery_experiment\eegnb\experiments\motor_imagery\movements\wrist_flexing_right-1.mp4"
        ]

        trial_count = 1
        for i in range(NUM_SETS):
            for movement in [1, 2]:
                if not self.running: break
                self.run_set(video_paths[movement - 1], VIDEO_DURATION, INSTRUCTION_DURATION, TRIAL_DURATION, REST_DURATION, trial_count, movement)
                trial_count += 1
            if not self.running: break

        for i in range(NUM_MI_SETS):
            for movement in [1, 2]:
                if not self.running: break
                self.trial_cycle(False, True, video_paths[movement - 1], VIDEO_DURATION, INSTRUCTION_DURATION, TRIAL_DURATION, REST_DURATION, trial_count, movement)
                trial_count += 1
            if not self.running: break
        
        # --- CRITICAL CHANGE: Removed input_thread.join() ---

    def run_set(self, video_path, vid_dur, inst_dur, trial_dur, rest_dur, trial_count, movement):
        for with_video, is_imagery in [(True, False), (True, True), (False, False), (False, True)]:
            if not self.running: break
            self.trial_cycle(with_video, is_imagery, video_path, vid_dur, inst_dur, trial_dur, rest_dur, trial_count, movement)

    def trial_cycle(self, with_video, is_imagery, video_path, vid_dur, inst_dur, trial_dur, rest_dur, trial_count, movement):
        
        # Pre-render all text stimuli using the new Pygame helper
        prompts = {
            "action": self._create_pygame_text(f"Prepare to do\nthe movement {movement}."),
            "imagery": self._create_pygame_text(f"Prepare to imagine\nmovement {movement}."),
            "perform_action": self._create_pygame_text(f"Perform movement {movement}"),
            "perform_imagery": self._create_pygame_text(f"Imagine movement {movement}"),
            "rest": self._create_pygame_text("Rest for 1 second.\nPrepare for next trial.")
        }
        
        if self.running:
            self._run_phase("video", with_video, video_path, vid_dur, trial_count, movement)
        if self.running:
            content = prompts["imagery"] if is_imagery else prompts["action"]
            self._run_phase("instruction", False, content, inst_dur, trial_count, movement, "2")
        if self.running:
            content = prompts["perform_imagery"] if is_imagery else prompts["perform_action"]
            self._run_phase("perform", False, content, trial_dur, trial_count, movement, "3" if is_imagery else "4")
        if self.running:
            self._run_phase("rest", False, prompts["rest"], rest_dur, trial_count, movement, "5")

    def _run_phase(self, phase_name, with_video, content, duration, trial_count, movement, marker_suffix=""):
        sent_marker = False
        start_time = time()
        
        if phase_name == "video" and with_video:
            # --- Video Phase using OpenCV ---
            video_path = content
            cap = cv2.VideoCapture(video_path)
            
            # Check if video opened successfully
            if not cap.isOpened():
                print(f"Error: Could not open video file at {video_path}")
                return
            
            # Use clock for frame-rate control
            # Using self.clock is better than creating a new local clock
            fps = cap.get(cv2.CAP_PROP_FPS)
            # Ensure we use a positive FPS, or fallback to 60
            if fps <= 0: fps = self.fps 

            while cap.isOpened() and self.running and (time() - start_time < duration):
                # --- CRITICAL CHANGE: Handle input at the start of the loop ---
                if self._handle_input():
                    cap.release()
                    return # Exit phase if interrupted
                
                ret, frame = cap.read()
                
                if not ret:
                    # Video finished or error
                    break 

                # Draw, flip, THEN send the marker
                self._draw_video_frame(frame, movement)
                
                # --- CRITICAL CHANGE: Marker sent AFTER the frame flip in _draw_video_frame ---
                self._send_marker(trial_count, 1, movement, sent_marker)
                sent_marker = True # Marker is only sent on the first frame
                
                # Use the calculated video FPS
                self.clock.tick(fps) 

            cap.release()
            # -----------------------------------
        
        elif phase_name != "video":
            # --- Text/Instruction/Rest Phase using Pygame Text Surfaces ---
            
            while self.running and time() < (start_time + duration):
                # --- CRITICAL CHANGE: Handle input at the start of the loop ---
                if self._handle_input():
                    return # Exit phase if interrupted
                
                # Clear the screen
                self.window.fill((0, 0, 0)) 
                
                # Draw the text content
                self.window.blit(content["surface"], content["rect"])
                
                # Update the display
                pygame.display.flip() 

                # --- CRITICAL CHANGE: Marker sent AFTER the flip for minimal visual-marker jitter ---
                self._send_marker(trial_count, marker_suffix, movement, sent_marker)
                sent_marker = True
                
                # --- CRITICAL CHANGE: Use clock.tick for precise timing instead of sleep(0.01) ---
                self.clock.tick(self.fps) 
            # -----------------------------------

    def _send_marker(self, trial_count, vid, movement, sent_marker):
        if not sent_marker and self.eeg:
            # Preserving the original float marker format
            marker = float(f"{trial_count}{vid}{movement}")
            timestamp = time()
            self.eeg.push_sample(marker=marker, timestamp=timestamp)

    def _draw_video_frame(self, cv_frame, movement):
        '''Draws the current video frame and the movement description text.'''
        
        # 1. Convert OpenCV frame (BGR NumPy array) to Pygame Surface
        # Convert BGR to RGB (OpenCV default is BGR)
        frame_rgb = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        
        # Rotate and flip to match standard Pygame surface orientation
        frame_rotated = np.rot90(frame_rgb)
        frame_flipped = np.flipud(frame_rotated)
        pygame_surface = pygame.surfarray.make_surface(frame_flipped)

        # Scale the video surface to fit the window while maintaining aspect ratio 
        # (Preserving original logic, which includes per-frame scaling/optimization)
        surface_rect = pygame_surface.get_rect()
        scale_x = self.window_size[0] / surface_rect.width
        scale_y = self.window_size[1] / surface_rect.height
        scale = min(scale_x, scale_y)
        new_width = int(surface_rect.width * scale)
        new_height = int(surface_rect.height * scale)
        pygame_surface = pygame.transform.scale(pygame_surface, (new_width, new_height))
        
        # Recenter the surface
        surface_rect = pygame_surface.get_rect(center=(self.window_size[0] / 2, self.window_size[1] / 2))

        # Clear screen
        self.window.fill((0, 0, 0)) 
        
        # Draw the video frame
        self.window.blit(pygame_surface, surface_rect) 

        # 2. Draw the movement description text
        movement_description = self._create_pygame_text(f"Movement {movement}", font_size=24)
        
        # Draw the description text (e.g., in the top left corner)
        text_rect = movement_description["rect"]
        text_rect.topleft = (10, 10) 
        self.window.blit(movement_description["surface"], text_rect)
        
        # 3. Update the display
        pygame.display.flip() 
        # NOTE: Marker is sent in _run_phase immediately after this flip.


    def show_instructions(self):
        # Using a higher font size for instruction screen
        instruction_content = self._create_pygame_text(
            self.instruction_text % self.record_duration, 
            font_size=28
        )
        
        # Show instructions until spacebar is pressed
        waiting = True
        while waiting and self.running:
            if self._handle_input():
                if not self.running: # If _handle_input() set self.running=False (QUIT/SPACE)
                    return
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    waiting = False
                elif event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
            
            self.window.fill((0, 0, 0))
            self.window.blit(instruction_content["surface"], instruction_content["rect"])
            pygame.display.flip()
            
            # --- CRITICAL CHANGE: Use clock.tick for precise timing instead of sleep(0.01) ---
            self.clock.tick(self.fps) 


    def setup(self, instructions=True):
        # --- Pygame Initialization (Replaces psychopy.visual.Window) ---
        pygame.init()
        pygame.font.init() # Ensure font module is initialized
        self.record_duration = np.float32(self.duration)
        self.markernames = [1, 2]

        # Create the full-screen display
        self.window = pygame.display.set_mode(self.window_size, pygame.FULLSCREEN | pygame.DOUBLEBUF)
        pygame.display.set_caption(self.exp_name)
        self.window.fill((0, 0, 0)) # Set background color to black
        pygame.display.flip()
        
        self.stim = self.load_stimulus()

        if instructions:
            self.show_instructions()
        # -----------------------------------------------------------------

        if self.eeg:
            if self.save_fn is None:
                random_id = random.randint(1000, 10000)
                experiment_directory = self.name.replace(' ', '_')
                self.save_fn = generate_save_fn(self.eeg.device_name, experiment_directory, random_id, random_id, "unnamed")
                print(f"No path for a save file was passed to the experiment. Saving data to {self.save_fn}")

    def run(self, instructions=True):
        self.running = True
        self.setup(instructions)

        eeg_filt_thread = None
        emaFilt = EMA_Filters()
        self._stop_event = threading.Event()
        
        # Define the thread function
        def eeg_stream_thread():
            eeg = self.eeg
            sfreq = eeg.sfreq
            bp_fc_low = 8
            bp_fc_high = 30
            n_fc = 60

            # ... (eeg_stream_thread body remains the same) ...
            while eeg.stream_started and not self._stop_event.is_set():
                data = eeg.board.get_current_board_data(1)
                _, eeg_data, timestamps = eeg._brainflow_extract(data)
                eeg_data_filt = emaFilt.BPF(eeg_data, bp_fc_low, bp_fc_high, sfreq)  # bandpass filter
                eeg_data_filt = emaFilt.Notch(eeg_data_filt, n_fc, sfreq)  # notch filter
                if len(eeg_data) > 0 and len(timestamps) > 0:
                    last_timestamp = data[eeg.timestamp_channel][0]
                    eeg.filt_data.append([eeg_data_filt[0].tolist(), last_timestamp])


        # Start EEG stream and thread
        if self.eeg:
            print("Wait for the EEG-stream to start...")
            self.eeg.start(self.save_fn, duration=self.record_duration + 10)
            print("eeg stream started")
            
            eeg_filt_thread = threading.Thread(target=eeg_stream_thread)
            eeg_filt_thread.daemon = True
            eeg_filt_thread.start()
            print("eeg_filt_thread initiated")
        else:
            print("No EEG headset connected")
            
        
        try:
            print("Experiment started")
            self.present_stimulus()
            print("Experiment ended")
        
        finally:
            # --- GUARANTEED CLEANUP (Runs even on Ctrl-C or Exception) ---

            if self.eeg:
                self._stop_event.set()
                if eeg_filt_thread:
                    eeg_filt_thread.join()
                    print("eeg_filt_thread terminated")
                
                # --- ROBUST BRAINFLOW CLEANUP (Your existing code) ---
                # Step 1: Attempt to stop the stream gracefully
                try:
                    self.eeg.board.stop_stream() 
                    print("Stop EEG stream successful.")
                except Exception as e:
                    print(f"Warning: Failed to stop stream gracefully (Headset probably disconnected: {e}).")
                
                # Step 2: Force release the session
                try:
                    self.eeg.board.release_session()
                    print("BrainFlow session released.")
                except Exception as e:
                    print(f"Warning: Could not release session cleanly: {e}")
                
                print("Recording saved at", self.save_fn)
            
            # --- Pygame cleanup ---
            pygame.quit()
            print("Pygame display closed.")
            # ----------------------------------------------------