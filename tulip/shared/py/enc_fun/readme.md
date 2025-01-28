


encfun.py, Encoder Fun
by DIYDSP, 1/27/2025

to run on tulipcc:
cd('encfun')
execfile('enc_fun.py')

a basic piano roll/drum sequencer controlled with rotary encoders

to use you will need to plug a m5_8encoder into your I2C port.

For ergonomics, this program requires you to position the m5_8encoder row rotated 180 deg on your table.  That makes the I2C cable flow better.  so "CH8" is upside down and on the left and "CH1" is upside down on on the right.  

Encoder controls are on-screen:
Encoder 1 = horizontal position.  Press for high-resolution.
Encoder 8 = vertical position.  Press to add/remove a note.

Some keyboard controls
Page Up / Page Down = tempo
Spacebar = pause/resume sequencer
Ctrl-C - exit



