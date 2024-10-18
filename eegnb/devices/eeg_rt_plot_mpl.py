# eeg_rt_plot_mpl.py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import time
import matplotlib.dates as mdates
from datetime import datetime

# import threading

class EEGRealTimePlotMPL:
    def __init__(self, rolling_buffer, channel_names=None):
        self.rolling_buffer = rolling_buffer
        self.channel_names = channel_names if channel_names else [f'Ch{i+1}' for i in range(self.rolling_buffer.num_channels)]
        self.fig, self.axs = plt.subplots(self.rolling_buffer.num_channels, 1, figsize=(10, 8), sharex=True)

        # self.stop_event = threading.Event()
        
        # Initialize lines for updating data
        self.lines = []
        for ax, name in zip(self.axs, self.channel_names):
            ax.set_ylabel(name)
            line, = ax.plot([], [])  # Initialize empty line
            self.lines.append(line)

        # Set the x-axis to handle date and time formatting
        self.axs[-1].xaxis_date()  # Treat the x-axis data as dates
        self.axs[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # Format the dates as hours:minutes:seconds

    def stream_check(self):
        data, timestamps = self.rolling_buffer.get_data()

        # Check if timestamps is not empty and data has elements (is not empty)
        if len(timestamps) > 0 and data.size > 0:
            # print(f"Timestamp Range: {min(timestamps)} to {max(timestamps)}")
            # for i in range(data.shape[0]):  # Assuming data is a 2D array-like structure
            #     print(f"Data Channel {i}: Min={min(data[i])}, Max={max(data[i])}")
            return True
        else:
            # More specific checks for which list(s) are empty
            if len(timestamps) == 0 and data.size > 0:
                print("Timestamps are empty")
            elif data.size == 0 and len(timestamps) > 0:
                print("Data is empty")
            else:  # This covers the case where both are empty
                print("Both timestamps and data are empty")
            return False

        

    def update_plot(self, frame):

        while not self.stream_check():  # Wait for data to be available
            time.sleep(0.1)  # Wait a bit before returning, adjust as needed
            print("waiting for data stream")

        data, timestamps = self.rolling_buffer.get_data()
        # Ensure timestamps and data have the same length
        min_length = min(len(timestamps), data.shape[1])
        timestamps = timestamps[:min_length]
        data = data[:, :min_length]

        timestamps = [datetime.fromtimestamp(ts) for ts in timestamps]  # Convert timestamps to datetime objects

        for i, line in enumerate(self.lines):
            if timestamps:
                line.set_data(timestamps, data[i])  # Update line data
            else:
                line.set_data(np.arange(len(data[i])), data[i])

            ymin, ymax = data[i].min(), data[i].max()
            padding = (ymax - ymin) * 0.1  # Add 10% padding
            if padding == 0:  # In case of flat line (no variation)
                padding = 0.5  # Use a default padding

            self.axs[i].relim()  # Recalculate limits
            self.axs[i].autoscale()  # Rescale x and y axes

            # Hide x and y tick labels and ticks, but leave y-axis label (title) visible
            # self.axs[i].xaxis.set_tick_params(labelbottom=False)  # Hides x tick labels
            # self.axs[i].yaxis.set_tick_params(labelleft=False)  # Hides y tick labels

            # Hide the ticks themselves
            # for tick in self.axs[i].xaxis.get_major_ticks() + self.axs[i].yaxis.get_major_ticks():
            #     tick.tick1line.set_visible(False)
            #     tick.tick2line.set_visible(False)

        self.fig.canvas.draw() # this significanly slows the plot, but allows showing x and y axes updating dynamically
        return self.lines

    def animate(self, win_len=20): # adjust win_len to set moving window size
        self.anim = FuncAnimation(self.fig, self.update_plot, interval=win_len, blit=True, cache_frame_data=False) 
        plt.show()
