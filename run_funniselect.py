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
from eegnb.experiments.motor_imagery.funni_select_unicorn import VisualFunni_select_unicorn

# Define some variables
board_name = "unicorn"
experiment = "motor_imagery"
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
ssvep = VisualFunni_select_unicorn(record_duration)
ssvep.run()
