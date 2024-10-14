"""
SSVEP run experiment
===============================

This example demonstrates the initiation of an EEG stream with eeg-expy, and how to run 
an experiment. 

"""

###################################################################################################  
# Setup
# ---------------------  
#  
# Imports
import os
from eegnb import generate_save_fn
from eegnb.devices.eeg import EEG
from eegnb.experiments.visual_ssvep.ssvep_select import VisualSSVEP_select

# Define some variables
board_name = "muse2"
experiment = "visual_ssvep"
subject_id = 0
session_nb = 0
record_duration = 120

###################################################################################################
# Initiate EEG device
# ---------------------
#
# Start EEG device
# eeg_device = EEG(board_name)

# Create save file name
save_fn = generate_save_fn(board_name, experiment, subject_id, session_nb)
print(save_fn)

###################################################################################################  
# Run experiment
# ---------------------  
#  
ssvep = VisualSSVEP_select(duration=record_duration, eeg=None, save_fn=save_fn)
ssvep.run()
