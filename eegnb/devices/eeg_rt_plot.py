import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class EEGRealTimePlot(QMainWindow):
    def __init__(self, sfreq, num_channels=8, channel_names=None):
        super().__init__()
        if channel_names:
            self.channel_names = channel_names
        else:
            self.channel_names = [f'Ch{i}' for i in range(1, num_channels + 1)]
        self.sfreq = sfreq
        self.num_channels = num_channels
        print(num_channels, channel_names)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Real-time EEG Data Stream")
        self.setGeometry(100, 100, 1200, 1000)
        self.plotWidget = PlotCanvas(self, sfreq=self.sfreq, num_channels=self.num_channels, channel_names=self.channel_names)  # Pass sfreq here
        self.show()

    def update_plot(self, data):
        self.plotWidget.plot(data)

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, sfreq=256, num_channels=8, channel_names=None):
        self.sfreq = sfreq
        self.fig = Figure(figsize=(12, 10))
        self.fig.subplots_adjust(left=0.15, hspace=0, right=0.75)
        self.ax_array = self.fig.subplots(num_channels, 1, sharex=True)
        self.lines = []
        self.channel_names = channel_names if channel_names else [f'Ch{i}' for i in range(1, num_channels + 1)]
                
        if not isinstance(self.ax_array, np.ndarray):
            self.ax_array = [self.ax_array]

        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def plot(self, data):
        # Clear previous lines from each axes
        for ax in self.ax_array:
            ax.clear()

        # Plot the data
        for i, channel_data in enumerate(data):
            times = np.arange(len(channel_data)) / self.sfreq
            (line,) = self.ax_array[i].plot(times, channel_data, lw=0.5, label="raw")
            self.lines.append(line)
            margin = (np.max(channel_data) - np.min(channel_data)) * 0.05  # 5% margin
            self.ax_array[i].set_ylim(np.min(channel_data) - margin, np.max(channel_data) + margin)

        # y labels
        for i, ax in enumerate(self.ax_array):
            # ax.set_ylim([-50, 50])
            ax.set_ylabel(self.channel_names[i], fontsize="small", labelpad=3)
            ax.tick_params(axis='y', labelsize=6, direction='in')
            # ax.set_yticks([])

        self.ax_array[-1].set_xlabel("Time (s)")
        self.fig.subplots_adjust(hspace=0, right=0.75)
        self.fig.suptitle("Real Time EEG Data Stream")

        self.ax_array[0].legend(fontsize="small", bbox_to_anchor=(1.1, 1), borderaxespad=0)
        
        self.draw()

def main():
    app = QApplication(sys.argv)
    sfreq = 250  # Sampling frequency
    num_channels = 8  # Number of channels
    channel_names = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4']  # Example channel names
    ex = EEGRealTimePlot(sfreq, num_channels, channel_names)
    
    # Simulation of incoming data
    for _ in range(100):  # Simulate updates
        if not ex.isVisible():  # Check if the window is still open
            break  # Exit the loop if the window is closed
        data = [np.random.randn(sfreq) * 10 for _ in range(num_channels)]  # Simulated EEG data for each channel
        print(data)
        ex.update_plot(data)
        QApplication.processEvents()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
