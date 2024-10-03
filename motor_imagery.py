from psychopy import visual, core
from psychopy.hardware import keyboard

mywin = visual.Window([800,600], monitor="testMonitor", units="deg")

grating = visual.GratingStim(win=mywin, mask="circle", size=3, pos=[-4,0], sf=3)
fixation = visual.GratingStim(win=mywin, size=0.5, pos=[0,0], sf=0, rgb=-1)
kb = keyboard.Keyboard()

grating.draw()
fixation.draw()
mywin.update()