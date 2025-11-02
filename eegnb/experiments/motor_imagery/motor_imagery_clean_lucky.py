import time
import threading
import random
from typing import Optional, List

import numpy as np
import tkinter as tk
from tkVideoPlayer import TkinterVideo  # pip install tkVideoPlayer

from eegnb.experiments import Experiment
from eegnb.devices.EMA_Filters import EMA_Filters
from eegnb.devices.eeg import EEG
from eegnb import generate_save_fn


########################################
# TIMER POPUP (same pattern as your first file)
########################################
def run_timer_popup(duration_minutes=10):
    """
    A standalone countdown window.
    Runs in its own thread so it doesn't block the experiment.
    """
    root = tk.Tk()
    root.title("Timer")
    root.geometry("1600x800")
    root.attributes("-topmost", True)

    TOTAL_DURATION = duration_minutes * 60
    start_time = time.time()

    lbl = tk.Label(root, font=("Arial", 80, "bold"))
    lbl.pack(expand=True, fill="both")

    def tick():
        elapsed = time.time() - start_time
        remaining = int(TOTAL_DURATION - elapsed)

        if remaining <= 0:
            lbl.config(text="DONE", fg="red")
            return

        mins, secs = divmod(remaining, 60)
        lbl.config(text=f"{mins:02d}:{secs:02d}")
        root.after(1000, tick)

    tick()
    root.mainloop()


########################################
# STIMULUS WINDOW
########################################
class StimulusWindow:
    """
    This manages the on-screen stimulus:
    - full black background
    - either plays a video (wrist flexion, etc.) via TkinterVideo
    - or shows large text instructions ("Imagine movement 1")
    """

    def __init__(self, width=1280, height=720):
        self.root = tk.Tk()
        self.root.title("Stimulus")
        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg="black")
        self.root.attributes("-topmost", True)

        # container frame
        self.frame = tk.Frame(self.root, bg="black")
        self.frame.pack(expand=True, fill="both")

        # label for text prompts OR movement caption overlay
        self.text_label = tk.Label(
            self.frame,
            text="",
            font=("Arial", 48, "bold"),
            fg="white",
            bg="black",
            justify="center",
        )
        self.text_label.pack(expand=True)

        # video widget (created lazily when needed)
        self.video_player = None

        # we track whether we're currently showing video or text
        self.mode = "text"

    def show_text(self, text: str):
        """
        Switch the window into "text mode" and display a big white message
        against a black background.
        """
        # stop any existing video playback
        if self.video_player is not None:
            try:
                self.video_player.stop()
            except Exception:
                pass
            self.video_player.pack_forget()

        self.video_player = None
        self.mode = "text"

        self.text_label.config(text=text, font=("Arial", 48, "bold"), fg="white", bg="black")
        self.text_label.pack(expand=True, fill="both")
        # update once so it renders immediately
        self.root.update()

    def play_video(self, video_path: str, overlay_text: str = ""):
        """
        Switch to "video mode":
        - create TkinterVideo if we haven't
        - load the file, start playback
        - also show a caption label for which movement it is
        """
        # clear text label while playing video, but keep a caption label
        self.text_label.config(text="")
        self.text_label.pack_forget()

        # frame for video + caption
        video_frame = tk.Frame(self.frame, bg="black")
        video_frame.pack(expand=True, fill="both")

        # caption at the top (Movement 1 / Movement 2, etc.)
        if overlay_text:
            caption = tk.Label(
                video_frame,
                text=overlay_text,
                font=("Arial", 32, "bold"),
                fg="white",
                bg="black",
                anchor="center",
            )
            caption.pack(side="top", pady=10)

        # the video widget itself
        self.video_player = TkinterVideo(
            master=video_frame,
            scaled=True,
            bg="black"
        )
        self.video_player.load(video_path)
        self.video_player.pack(expand=True, fill="both")
        self.video_player.play()

        self.mode = "video"
        self.root.update()

    def update_loop_step(self):
        """
        Call frequently in a tight loop so Tk stays responsive and
        the video can advance frames. tkVideoPlayer relies on .update()
        being called.
        """
        self.root.update()

    def close(self):
        try:
            if self.video_player is not None:
                self.video_player.stop()
        except Exception:
            pass
        self.root.destroy()


########################################
# MAIN EXPERIMENT
########################################
class MotorImageryExperimentTk(Experiment.BaseExperiment):
    """
    PsychoPy is gone.
    This experiment:
    - Uses Tk + tkVideoPlayer for stimuli
    - Uses your EEG streaming thread with EMA_Filters
    - Runs timed trial cycles (video / instruction / perform-or-imagine / rest)
    - Sends markers like before
    - Launches a separate timer popup like your first file
    """

    def __init__(self, duration, eeg: Optional[EEG] = None, save_fn=None):
        exp_name = "motor_imagery"
        super().__init__(
            exp_name,
            duration,
            eeg,
            save_fn,
            n_trials=None,
            iti=None,
            soa=None,
            jitter=None
        )

        self.instruction_text = (
            f"\nWelcome to the {self.exp_name} experiment!\n\n"
            "You'll see/imitate hand movements or imagine them.\n"
            "Please pause briefly between selections.\n\n"
            "This experiment will run for %s seconds.\n"
            "Press spacebar to start, press again to interrupt.\n"
        )

        # === EDIT THESE TIMINGS (seconds) ===
        self.VIDEO_DURATION = 5
        self.INSTRUCTION_DURATION = 1
        self.TRIAL_DURATION = 2
        self.REST_DURATION = 1

        # === HOW MANY BLOCKS ===
        self.NUM_SETS = 0        # full set cycles (video+action, video+imagery, etc.)
        self.NUM_MI_SETS = 1     # imagery-only block

        # === YOUR VIDEO FILES ===
        # index 0 -> movement 1 (e.g. left wrist flex)
        # index 1 -> movement 2 (e.g. right wrist flex)
        self.video_paths: List[str] = [
            r"C:\Users\kthbl\Documents\motor_imagery_experiment\eegnb\experiments\motor_imagery\movements\wrist_flexing_left.mp4",
            r"C:\Users\kthbl\Documents\motor_imagery_experiment\eegnb\experiments\motor_imagery\movements\wrist_flexing_right-1.mp4",
        ]

        self.running = False
        self._stop_event = threading.Event()
        self.stimwin: Optional[StimulusWindow] = None

    ############################
    # Internal helpers
    ############################
    def _send_marker_once(self, trial_count, code_fragment, movement, already_sent):
        """
        Push LSL/marker-like float code ONCE at the start of each phase.
        Format matches your design: trialCount + phaseCode + movement
        e.g. trial 12, code '3', movement 2 -> 1232 -> float(1232.0)
        """
        if already_sent:
            return True

        if self.eeg:
            marker_val = float(f"{trial_count}{code_fragment}{movement}")
            ts = time.time()
            # assumes eeg.push_sample(marker=..., timestamp=...)
            self.eeg.push_sample(marker=marker_val, timestamp=ts)

        return True

    def _phase_video(self, trial_count, movement, duration_s):
        """
        Show + play the movement video for 'movement' index for up to duration_s.
        Marker code '1'.
        """
        video_path = self.video_paths[movement - 1]

        overlay_label = f"Movement {movement}"
        self.stimwin.play_video(video_path, overlay_text=overlay_label)

        sent_marker = False
        start_t = time.time()
        while (
            self.running
            and not self._stop_event.is_set()
            and (time.time() - start_t) < duration_s
        ):
            sent_marker = self._send_marker_once(trial_count, "1", movement, sent_marker)
            # keep Tk alive and video advancing
            self.stimwin.update_loop_step()

    def _phase_text(self, trial_count, movement, duration_s, text_str, code_fragment):
        """
        Show a big text instruction for duration_s seconds.
        Marker code depends on stage:
            '2' = prep instruction ("Prepare to imagine...")
            '3' = imagery perform ("Imagine movement X")
            '4' = physical perform ("Perform movement X")
            '5' = rest
        """
        self.stimwin.show_text(text_str)

        sent_marker = False
        start_t = time.time()
        while (
            self.running
            and not self._stop_event.is_set()
            and (time.time() - start_t) < duration_s
        ):
            sent_marker = self._send_marker_once(trial_count, code_fragment, movement, sent_marker)
            self.stimwin.update_loop_step()

    def _trial_cycle(self, trial_count, movement, with_video, is_imagery):
        """
        Run one full trial:
        1. (optional) video demo:       code "1"
        2. prepare screen:              code "2"
        3. perform/imagery instruction: code "3" if imagery else "4"
        4. rest screen:                 code "5"
        """
        # 1. video demo
        if with_video:
            self._phase_video(
                trial_count=trial_count,
                movement=movement,
                duration_s=self.VIDEO_DURATION,
            )

        # 2. prepare instruction
        prep_txt = (
            f"Prepare to imagine\nmovement {movement}."
            if is_imagery
            else f"Prepare to do\nthe movement {movement}."
        )
        self._phase_text(
            trial_count=trial_count,
            movement=movement,
            duration_s=self.INSTRUCTION_DURATION,
            text_str=prep_txt,
            code_fragment="2"
        )

        # 3. perform or imagine
        perform_txt = (
            f"IMAGINE movement {movement}\n(keep body still)"
            if is_imagery
            else f"PERFORM movement {movement}\nNow"
        )
        perform_code = "3" if is_imagery else "4"
        self._phase_text(
            trial_count=trial_count,
            movement=movement,
            duration_s=self.TRIAL_DURATION,
            text_str=perform_txt,
            code_fragment=perform_code
        )

        # 4. rest
        rest_txt = "Rest for 1 second.\nPrepare for next trial."
        self._phase_text(
            trial_count=trial_count,
            movement=movement,
            duration_s=self.REST_DURATION,
            text_str=rest_txt,
            code_fragment="5"
        )

    def _run_full_set_block(self, starting_trial_count):
        """
        Matches your 'run_set' idea:
        For movement in [1,2], run:
            video+physical
            video+imagery
            novideo+physical
            novideo+imagery
        """
        tc = starting_trial_count
        for movement in [1, 2]:
            # video + physical
            self._trial_cycle(tc, movement, with_video=True, is_imagery=False)
            tc += 1

            # video + imagery
            self._trial_cycle(tc, movement, with_video=True, is_imagery=True)
            tc += 1

            # no video + physical
            self._trial_cycle(tc, movement, with_video=False, is_imagery=False)
            tc += 1

            # no video + imagery
            self._trial_cycle(tc, movement, with_video=False, is_imagery=True)
            tc += 1

        return tc

    def _run_imagery_only_block(self, starting_trial_count):
        """
        Matches your NUM_MI_SETS loop:
        For movement in [1,2], run imagery-only (no video).
        """
        tc = starting_trial_count
        for movement in [1, 2]:
            self._trial_cycle(tc, movement, with_video=False, is_imagery=True)
            tc += 1
        return tc

    ############################
    # Experiment lifecycle
    ############################
    def load_stimulus(self):
        # for API compatibility with BaseExperiment
        return self.video_paths

    def setup(self, instructions=True):
        """
        - Set durations, markernames, etc.
        - Build save_fn if needed
        - Create the stimulus window (Tk)
        """
        self.record_duration = np.float32(self.duration)
        self.markernames = [1, 2]

        # main stimulus display window
        self.stimwin = StimulusWindow(width=1280, height=720)

        self.stim = self.load_stimulus()

        # optional instructions phase
        if instructions:
            # You can customize this intro screen however you want.
            intro_msg = (
                "Welcome.\n\n"
                "You will either WATCH and/or PERFORM a wrist movement,\n"
                "or IMAGINE it without moving.\n\n"
                "Press Ctrl+C in console to abort."
            )
            self.stimwin.show_text(intro_msg)
            # brief pause so participant can read instructions before trials start
            start_intro = time.time()
            while time.time() - start_intro < 3.0:
                self.stimwin.update_loop_step()

        if self.eeg:
            if self.save_fn is None:
                random_id = random.randint(1000, 10000)
                experiment_directory = self.name.replace(" ", "_")
                self.save_fn = generate_save_fn(
                    self.eeg.device_name,
                    experiment_directory,
                    random_id,
                    random_id,
                    "unnamed"
                )
                print(
                    "No path for a save file was passed to the experiment. "
                    f"Saving data to {self.save_fn}"
                )

    def present_stimulus(self):
        """
        Run all blocks while self.running is True.
        """
        self.running = True
        trial_count = 1

        # full multi-condition sets
        for _ in range(self.NUM_SETS):
            if (not self.running) or self._stop_event.is_set():
                break
            trial_count = self._run_full_set_block(trial_count)

        # imagery-only sets
        for _ in range(self.NUM_MI_SETS):
            if (not self.running) or self._stop_event.is_set():
                break
            trial_count = self._run_imagery_only_block(trial_count)

        self.running = False

    def run(self, instructions=True):
        """
        Master controller:
        - setup()
        - start EEG thread
        - start timer popup thread
        - call present_stimulus()
        - always cleanup
        """
        self.setup(instructions)

        print("Wait for the EEG-stream to start...")

        emaFilt = EMA_Filters()
        self._stop_event.clear()

        # EEG thread
        def eeg_stream_thread():
            eeg = self.eeg
            sfreq = eeg.sfreq
            bp_fc_low = 8
            bp_fc_high = 30
            n_fc = 60

            while eeg.stream_started and not self._stop_event.is_set():
                data = eeg.board.get_current_board_data(1)
                _, eeg_data, timestamps = eeg._brainflow_extract(data)

                eeg_data_filt = emaFilt.BPF(eeg_data, bp_fc_low, bp_fc_high, sfreq)
                eeg_data_filt = emaFilt.Notch(eeg_data_filt, n_fc, sfreq)

                if len(eeg_data) > 0 and len(timestamps) > 0:
                    last_timestamp = data[eeg.timestamp_channel][0]
                    eeg.filt_data.append([eeg_data_filt[0].tolist(), last_timestamp])

        # start EEG stream
        if self.eeg:
            self.eeg.start(self.save_fn, duration=self.record_duration + 10)
            print("EEG stream started")
            eeg_thread = threading.Thread(target=eeg_stream_thread, daemon=True)
            eeg_thread.start()
            print("eeg_filt_thread initiated")
        else:
            eeg_thread = None
            print("No EEG headset connected")

        # launch timer popup in parallel
        TIMER_DURATION_MINUTES = 10  # EDIT THIS IF NEEDED
        timer_thread = threading.Thread(
            target=run_timer_popup,
            args=(TIMER_DURATION_MINUTES,),
            daemon=True
        )
        timer_thread.start()
        print(f"Timer pop-up launched for {TIMER_DURATION_MINUTES} minutes.")

        print("Experiment started")

        try:
            self.present_stimulus()

        except KeyboardInterrupt:
            print("\n\n>>> Keyboard Interrupt Detected. Shutting down cleanly... <<<")
            self.running = False
            self._stop_event.set()

        finally:
            print("Experiment ending / cleanup...")

            # stop flags
            self.running = False
            self._stop_event.set()

            # stop EEG
            if self.eeg:
                if eeg_thread is not None:
                    eeg_thread.join()
                    print("eeg_filt_thread terminated")

                self.eeg._stop_brainflow()
                print("Stop EEG stream")
                print("Recording saved at", self.save_fn)

            # close stimulus window
            if self.stimwin is not None:
                try:
                    self.stimwin.close()
                except Exception as e:
                    print(f"[WARN] could not close stim window cleanly: {e}")

            print("Experiment ended.")
