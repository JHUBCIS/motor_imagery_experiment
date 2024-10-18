# streamplot_test.py
import numpy as np
import time
from threading import Thread
from rolling_buffer import RollingBuffer
from eeg_rt_plot_mpl import EEGRealTimePlotMPL

def simulate_eeg_data(rolling_buffer, update_interval=1/250, num_channels=8):
    while True:
        current_time = time.time()
        eeg_data = np.random.randn(num_channels) * 1000 + np.random.randn(num_channels) * -1000
        rolling_buffer.update([eeg_data.tolist()],[current_time])
        time.sleep(update_interval)

if __name__ == "__main__":
    buffer_time = 1  # seconds
    sfreq = 250  # sampling frequency
    rolling_buffer = RollingBuffer(buffer_time, sfreq)
    
    channel_names = ['Fz', 'C3', 'Cz', 'C4', 'Pz', 'PO7', 'Oz', 'PO8']
    plotter = EEGRealTimePlotMPL(rolling_buffer, channel_names)
    # plotter = EEGRealTimePlotMPL(rolling_buffer)

    eeg_data_thread = Thread(target=simulate_eeg_data, args=(rolling_buffer,))
    eeg_data_thread.daemon = True
    eeg_data_thread.start()
    
    plotter.animate(win_len=20) # adjust win_len to set moving window size
