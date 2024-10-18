# rolling_buffer.py
from collections import deque
import numpy as np

class RollingBuffer:
    def __init__(self, buffer_time=1, sfreq=250, num_channels=8):
        self.buffer_length = buffer_time * sfreq
        self.num_channels = num_channels
        self.data_buffer = deque(maxlen=self.buffer_length)
        self.timestamp_buffer = deque(maxlen=self.buffer_length)

    def update(self, new_data, timestamps):
        self.data_buffer.extend(new_data)
        self.timestamp_buffer.extend(timestamps)

        # # Determine the minimum length between new_data and timestamps
        # min_length = min(len(new_data), len(timestamps))
        
        # # Trim new_data and timestamps to have the same length
        # new_data_trimmed = new_data[:min_length]
        # timestamps_trimmed = timestamps[:min_length]

        # # Extend the buffers with the trimmed data and timestamps
        # self.data_buffer.extend(new_data_trimmed)
        # self.timestamp_buffer.extend(timestamps_trimmed)
        
    def get_data(self):
        data_array = np.array(self.data_buffer).T
        timestamp_array = np.array(self.timestamp_buffer).T

        # # Determine the shorter length between data and timestamps
        # min_length = min(len(self.data_buffer), len(self.timestamp_buffer))
        
        # # Ensure data and timestamps are of equal length
        # if min_length < len(self.data_buffer):
        #     data_buffer_sliced = [list(d)[:min_length] for d in self.data_buffer]
        # else:
        #     data_buffer_sliced = self.data_buffer
            
        # if min_length < len(self.timestamp_buffer):
        #     timestamp_buffer_sliced = list(self.timestamp_buffer)[:min_length]
        # else:
        #     timestamp_buffer_sliced = self.timestamp_buffer
        
        # # Convert to numpy arrays and transpose data array to match channels
        # data_array = np.array(data_buffer_sliced).T
        # timestamp_array = np.array(timestamp_buffer_sliced).T

        return data_array, timestamp_array