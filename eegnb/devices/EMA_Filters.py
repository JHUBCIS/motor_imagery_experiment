import math

class EMA_Filters:
    
    def __init__ (self):
        self.prev_ema_lp = 0
        self.prev_ema_hp = 0
        self.prev_ema_bplow = 0
        self.prev_ema_bphigh = 0
        self.prev_ema_nlow = 0 
        self.prev_ema_nhigh = 0 

    # for all following function, f_s is sampling frequency, and f_c is cut-off frequency

    def alpha(self, f_s, f_c):
        return (2 * math.pi * (1 / f_s) * f_c)/(2 * math.pi * (1 / f_s) * f_c + 1)

    def LPF(self, input, f_c, f_s):
        alphaValue = self.alpha(f_s, f_c)
        ema_lp = (1 - alphaValue) * self.prev_ema_lp + alphaValue * input
        self.prev_ema_lp = ema_lp  #Update the previous EMA value for the next call
        return ema_lp
    
    def HPF(self, input, f_c, f_s):
        alphaValue = self.alpha(f_s, f_c)
        ema_hp = (1 - alphaValue) * self.prev_ema_hp + alphaValue * input
        self.prev_ema_hp = ema_hp  # Update the previous EMA value for the next call
        return input - ema_hp  # high-pass filter output
    
    def BPF(self, input, f_c_low, f_c_high, f_s):
        alphaValueLow = self.alpha(f_s, f_c_low)
        alphaValueHigh = self.alpha(f_s, f_c_high)

        ema_bplow = (1 - alphaValueLow) * self.prev_ema_bplow + alphaValueLow * input
        self.prev_ema_bplow = ema_bplow;  # Update the previous EMA value for the next call

        # highpassOutput = input - ema_bplow;  # High-pass filter
        
        ema_bphigh = (1 - alphaValueHigh) * self.prev_ema_bphigh + alphaValueHigh * input
        self.prev_ema_bphigh = ema_bphigh # Update the previous EMA value for the next call
        
        return ema_bphigh - ema_bplow;  # bandpass filter output

    def Notch(self, input, f_c, f_s):
        alphaValueLow = self.alpha(f_s, f_c - 5)
        alphaValueHigh = self.alpha(f_s, f_c + 5)

        ema_nlow = (1 - alphaValueLow) * self.prev_ema_nlow + alphaValueLow * input
        self.prev_ema_nlow = ema_nlow;  # Update the previous EMA value for the next call
        
        ema_nhigh = (1 - alphaValueHigh) * self.prev_ema_nhigh + alphaValueHigh * input
        self.prev_ema_nhigh = ema_nhigh # Update the previous EMA value for the next call
        
        return input - (ema_nhigh - ema_nlow);  # notch filter output