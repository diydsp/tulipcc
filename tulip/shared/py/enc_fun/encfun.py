import random, time, math, os
import tulip, amy, music
from tulip import ticks_ms, seq_add_callback, seq_remove_callback, seq_ticks
import m5_8encoder as enc
import gridfun as gfun

"""
Encoder Fun by DIYDSP
the critters are placing easter eggs and little piles of clover.  another
critter is hopping around the screen.  each time he hops past what the
other has set up the syntehtic critter plays a note.  
"""

def clip(val, min_val, max_val):
    return max(min(val, max_val), min_val)

def round_half_up(n):
    if n > 0:
        return math.floor(n + 0.5)
    else:
        return math.ceil(n - 0.5)
        
# initialize
tulip.tfb_stop()
pix_dir = "pix"
(WIDTH, HEIGHT) = tulip.screen_size()

grass_colors = [80, 157, 180, 249]

# clear the screen
bg = { "grass_color": random.choice(grass_colors) }
bg['grass_color'] = random.choice( grass_colors )
tulip.bg_clear( bg['grass_color'] )


# display UI hints
hints = [
    "[ H. Pos. ]",
    "    [  ] ",  # H. Sel.
    "    [  ] ",  # Duration
    "    [  ] ",  # Timing

    "    [  ] ",   # Row
    "    [  ] ",   # Velocity
    "    [  ] ",   # V. Sel.
    "[ V. Pos. / Add ]",
]

hint_x = 25
hint_y = 580
hint_color = 0
#hint_h_spacing = 960 / (len(hints)-1)
hint_h_spacing = 120 #120
for hint_num, hint in enumerate(hints):
    hx = math.floor( clip( hint_x + hint_num * hint_h_spacing, 0, WIDTH-1) )
    hy = math.floor( clip( hint_y, 0, HEIGHT-1) ) 
    #print(f'x: {hx} y: {hy}, hint: {hint}')
    tulip.bg_str(hint, hx, hy, hint_color, 2)
    
# Load the rabbit sprite frames into sprite RAM
(rabbit_w, rabbit_h) = (48, 32)
tulip.sprite_png(pix_dir + "/rabbit_r_%d.png" % (0), rabbit_w*rabbit_h*0 )


# For the rest of the lines 
for y in range(1,HEIGHT):
    x_start = random.randrange(WIDTH)
    tulip.bg_blit(x_start,0,0,1,0,y)   


seq_edit = {   "x":0.0, "y":0,
        "time_disp_start":0.0,
        "run":1,
        "transport":"playing",
        "tempo":108,
        "grass_color": bg["grass_color"],
        }

# Draw a line of pixels up top with random colors
for x in range(WIDTH):
    tulip.bg_pixel(x,0,seq_edit["grass_color"   ])

class Note():
    def __init__(self, pos, note, vel, dur, note_index):
        self.pos = pos
        self.note = note
        self.vel = vel
        self.dur = dur
        self.note_index = note_index
    def __repr__(self):
        return f"Note: {self.note} at {self.pos} with vel {self.vel} for {self.dur} ticks\n"


class NoteManager():
    def __init__(self):
        self.notes = []
        self.note_index = 1
        
    def add(self, grid, pos, note, vel, dur):
        
        # check if note already exists
        for n in self.notes:
            if n.pos == pos and n.note == note:
                print("note already exists")
                self.notes.remove(n)     # remove note from data struct
                amy.send(sequence= ",,%d" % (n.note_index) )    # remove note-on from sequencer
                amy.send(sequence= ",,%d" % (n.note_index+1) )    # remove note-off from sequencer
                return "removed"

        # store in data struct
        self.note_index += 1
        new_note = Note(pos, note, vel, dur, self.note_index)
        self.notes.append(new_note)
        
        # write into sequencer
        amy.send(voices=1, note=note, vel=vel, sequence= "%d,%d,%d" % (pos, grid.pulses_seen_in_grid, self.note_index) )
        self.note_index += 1
        note_off_pos = ( pos + dur ) % grid.pulses_seen_in_grid
        amy.send(voices=1, note=note, vel=0, sequence= "%d,%d,%d" % (note_off_pos, grid.pulses_seen_in_grid, self.note_index) )  
        return "new"


    def display_notes(self):
        print(self.notes)

class EncVal():
    def __init__(self):
        self.prev = [0] * 8
        enc.read_all_increments()  # clear out values

    def set(self, idx, val):
        self.prev[idx] = val

    def get(self):
        return self.prv_pos
    


class KeebMgr():
    def __init__(self):
        self.note_add_down=False

    def note_add_down_get(self):
        return self.note_add_down

    def note_add_down_set(self, val):
        self.note_add_down = val    


class Cursor():
    def __init__(self):
        self.x = 0
        self.y = 0
        self.out_x = 0
        self.out_y = 0

    def delta_x(self, dx):

        if dx != 0:
            self.x += dx

            val = round_half_up( self.x / 2 )
            if val != self.out_x:            
                delta = val - self.out_x
                self.out_x = val 
                return delta
            else:
                return 0
        else:
            return 0
        
    def delta_y(self, dy):
            if dy != 0:
                self.y += dy
                val = round_half_up( self.y / 2 )
                if val != self.out_y:            
                    delta = val - self.out_y
                    self.out_y = val 
                    return delta
                else:
                    return 0
            else:
                return 0


half_rabbit_w = math.floor(rabbit_w / 2)
half_rabbit_h = math.floor(rabbit_h / 2)

# Register the first frame, we'll swap out frames during animation
# sprite_register(self.sprite_id,self.mem_pos, self.width, self.height)
tulip.sprite_register(0,0, rabbit_w, rabbit_h)
tulip.sprite_move(0, 
                  math.floor(WIDTH/2) - half_rabbit_w, 
                  math.floor(HEIGHT/2) - half_rabbit_h)
tulip.sprite_on(0)

tulip.sprite_register(1,0, rabbit_w, rabbit_h)
tulip.sprite_move(1, math.floor(WIDTH/2) - half_rabbit_w, 0)
tulip.sprite_on(1)


note_manager = NoteManager()
keeb_mgr = KeebMgr()    
grid = gfun.Grid(start_x=200, start_y=50, width=700, height=500, palette_index=3,
                 cols=32,  rows=25, visible_quarter_notes=4,seq_ppq=amy.SEQUENCER_PPQ) 
grid.draw()
cursor_xy_pos = Cursor()
cursor_xy_sel = Cursor()

def beat_callback(t):
    global app

    discrete_steps = 4 
    current_beat = int((seq_ticks() / 48) % discrete_steps )   # 48 PPQ, e.g. 108 BPM = 48*108 ticks/minute = 86 ticks/second

    # plot the running rabbit
    ratio = current_beat / discrete_steps
    sprite_x = grid.start_x + grid.width * ratio - half_rabbit_w
    sprite_y = grid.start_y - grid.VerticalSpacing / 2  # start_y - some vertical spacing upwards, ticker is above the grid :)
    sprite_x = clip(sprite_x, 0, WIDTH-rabbit_w)
    sprite_y = clip(sprite_y, 0, HEIGHT-rabbit_h)

    tulip.sprite_move(1, math.floor(sprite_x), math.floor(sprite_y)) # later add bg scroll, how cool would that be
    print(f'seq_ticks: {seq_ticks()}, current_beat: {current_beat}')   

tempo_x = 25
tempo_y = 200
tempo_color=0
def seq_tempo_delta( tempo_delta ):
    
    temp = seq_edit["tempo"] + tempo_delta
    temp = clip(temp, 0, 9999)
    seq_edit["tempo"] = temp
    amy.send(tempo=temp)
    # rectangle draws downwards, text draws upwards, so offset it
    #tulip.bg_rect(tempo_x,tempo_y, 10*7,28, seq_edit['grass_color'], 1 )
    tulip.bg_rect(                tempo_x, tempo_y   , 7*12,28, 117, 1 )
    tulip.bg_str( f'BPM: {temp}', tempo_x+3, tempo_y+16,          tempo_color, 2)


def seq_transport_cmd( cmd ):    

    if cmd == "toggle":
        if seq_edit["transport"] == "playing":
            seq_edit["transport"] = "paused"
            amy.send(tempo=0) # literally pause seq
            #amy.send(tempo=1) 

        elif seq_edit["transport"] == "paused":
            seq_edit["transport"] = "playing"

            # running in this order causes delays in playback resuming
            # tulip.seq_ticks() doesn't reset to 0
            #amy.send(reset=amy.RESET_TIMEBASE)  # reset seq
            #amy.send(tempo=seq_edit["tempo"])   # unpause seq   

            # running in this order also causes delays in playback resuming
            # tulip.seq_ticks() doesn't reset to 0
            amy.send(tempo=seq_edit["tempo"])   # unpause seq   
            #amy.send(reset=amy.RESET_TIMEBASE)  # reset seq

            # running in this order causes 
            #amy.send(tempo=seq_edit["tempo"])   # unpause seq   

        else:
            seq_edit["transport"] == "paused"
            #amy.send(tempo=1) 
            amy.send(tempo=0) # literally pause seq
    print(f'transport: {seq_edit["transport"]}')

def seq_cursor( dir ):

    if dir == "up": cursor_xy_pos.delta_y(-1)
    elif dir == "down": cursor_xy_pos.delta_y(1)
    elif dir == "left": cursor_xy_pos.delta_x(-1)
    elif dir == "right": cursor_xy_pos.delta_x(1)
    else: print("unhandled cursor dir: %s" % (dir))


def process_key( key ):
    global seq_edit

    # space
    if key == 32: seq_transport_cmd( "toggle")        
        
    # cursor keys
    elif key == 259: seq_cursor("up")
    elif key == 258: seq_cursor("down")  
    elif key == 260: seq_cursor("left")  
    elif key == 261: seq_cursor("right") 

    # esc
    #if key == 0x29: 

    # page up/down
    elif key== 25:seq_tempo_delta(1)
    elif key == 22:seq_tempo_delta(-1)

    else:   
        print("unhandled key: %d" % (key))
        print(f'{tulip.keys()}')

    
def h_note_select( d, delta ):
    
    # first find closest note in this row

    # find distance between this note and all notes
    min_dist = 1000000000
    for note in note_manager.notes:
        x_comp = note.pos - d["x"]   
        x_comp = x_comp % grid.pulses_seen_in_grid 
        y_comp = abs(note.note - (48 + grid.rows - d["y"])) 
        note_dist = x_comp**2 + y_comp**2

        # find closet one, but not including this one.  
        if note_dist != 0:
            print(f'note: {note.note}, dist: {note_dist}')  
            if note_dist < min_dist:
                min_dist = note_dist
                closest_note = note

    
    return closest_note

KNOB_XPOS = 7
KNOB_YPOS = 0
ENC_H_NOTE_SEL = 6
XPOS_PUSH_SCALE = 8
YPOS_PUSH_SCALE = 8
NEW_NOTE_BUTTON1 = 6
NEW_NOTE_BUTTON2 = 0
KNOB_TIME_JOG = 5

# This is called every frame by the GPU.
def game_loop(d):

    global rabbit_h,rabbit_w,WIDTH,HEIGHT,ringing_pan
    
    enc_butts = enc.read_all_buttons()
    enc_butts = [1-x for x in enc_butts]  # rev polarity

    # reset
    if enc_butts[NEW_NOTE_BUTTON1] == 1 and enc_butts[NEW_NOTE_BUTTON2] == 1:
        tulip.bg_clear(random.choice(grass_colors))

    # place musical note
    elif keeb_mgr.note_add_down_get() == False and \
            ( enc_butts[NEW_NOTE_BUTTON1] == 1 or enc_butts[NEW_NOTE_BUTTON2] == 1):

            f_x, f_y = grid.get_coords(d["x"], d["y"])
            f_x = math.floor( clip( float(f_x + grid.HorizontalSpacing/2 ) , 0, WIDTH-1) )
            f_y = math.floor( clip( float(f_y + grid.VerticalSpacing/2   ) , 0, HEIGHT-1) ) 
            keeb_mgr.note_add_down_set(True)
            result = note_manager.add( grid, 
                             pos = d["x"], 
                             note = 48 + grid.rows - d["y"], 
                             vel = 0.5, 
                             dur = 6 ) 
            if result == "new":
                tulip.bg_circle(f_x, f_y, math.floor(grid.HorizontalSpacing/3), 1, 1)  
            elif result == "removed":
                tulip.bg_circle(f_x, f_y, math.floor(grid.HorizontalSpacing/3), d["grass_color"], 1)

            note_manager.display_notes()    
        
    else:

        # move rabbit fwd/back in time in X.  
        # note horizontal is in pulses, e.g. out of 48*4
        redraw_cursor_plox = 0
        dx_pre = enc.read_increment(KNOB_XPOS)
        dx = cursor_xy_pos.delta_x(dx_pre)
        if dx != 0:
            bx = 1 - enc_butts[KNOB_XPOS]  # default bx==1, no button, move one column
                
            if bx == 1: # button unpressed, move one column at a time
                cur_col = grid.cols * ( d["x"] / grid.pulses_seen_in_grid ) 
                cur_col += dx 
                cur_col = cur_col % grid.cols
                ppq_in_grid = ( cur_col / grid.cols ) * grid.pulses_seen_in_grid 

            else:    # button pressed, move one PPQ at a time
                ppq_in_grid = d["x"] + dx

            d["x"] = ppq_in_grid
            d["x"] = d["x"] % grid.pulses_seen_in_grid  
            #print(f'x: {d["x"]}, col: {d["x"]*grid.cols/grid.pulses_seen_in_grid}')
            redraw_cursor_plox = 1

        # move rabbit up/down in notespace / Y-axis
        dy_pre = enc.read_increment(KNOB_YPOS)
        dy = cursor_xy_pos.delta_y(dy_pre)
        if dy != 0:
            #by = 1 - enc_butts[KNOB_YPOS]  # dont invert button press 
            d["y"] -= dy
            d["y"] = d["y"] % grid.rows
            redraw_cursor_plox=1

        # time jog
        jog_amount = enc.read_increment(KNOB_TIME_JOG)
        if jog_amount != 0:
            d["time_disp_start"] += jog_amount
            print(f"jog_amount: {jog_amount} time_disp_start: {d['time_disp_start']}")              
            for row in range(grid.start_y, grid.start_y + grid.height):
                tulip.bg_scroll_x_offset(math.floor( row), math.floor( d["time_disp_start"]) )

        # select note
        note_sel_pre = enc.read_increment(ENC_H_NOTE_SEL)
        note_sel_dx = cursor_xy_sel.delta_x(note_sel_pre)
        if note_sel_dx != 0:
            print(f'h_note_sel_delta: {note_sel_dx}')
            nearest_note = h_note_select( d, note_sel_dx )   
            print(f'nearest_note: {nearest_note}, pos={nearest_note.pos}, note={nearest_note.note}, vel={nearest_note.vel}')    
            d["x"] = nearest_note.pos   
            redraw_cursor_plox = 1

        if redraw_cursor_plox:
            f_x, f_y = grid.get_coords(d["x"], d["y"])
            f_x = math.floor( clip( float(f_x) + grid.HorizontalSpacing/2, 0, WIDTH-1) )
            f_y = math.floor( clip( float(f_y) - grid.VerticalSpacing/2, 0, HEIGHT-1) ) 
            tulip.sprite_move(0, f_x, f_y)


    # obsolete
    if keeb_mgr.note_add_down_get() == True and \
        enc_butts[NEW_NOTE_BUTTON1] == 0 and enc_butts[NEW_NOTE_BUTTON2] == 0:
            keeb_mgr.note_add_down_set(False)

    # fill background with noise pattern
    for i in range(10):
        g_x = int(random.random() * WIDTH)
        g_y = int(random.random() * HEIGHT)    
        tulip.bg_pixel(g_x,g_y,random.choice(grass_colors))


# initialize
amy.reset( amy.RESET_SEQUENCER )
start_time = tulip.ticks_ms()  # do this right before takeoff...
tulip.frame_callback(game_loop, seq_edit)   # Register the frame callback and data
amy.send(voices='0,1,2,3', load_patch=1)
#amy.send(voices=0, note=48, vel=.5)
#amy.send(voices=1, note=55, vel=.5, sequence= "%d,%d,%d" % (0, amy.SEQUENCER_PPQ*4, 999) )
#amy.send(wave=amy.PCM, patch=35,feedback=.5) 
#amy.send(osc=0, note=50, vel= 1)

current_beat = int((seq_ticks() / 48) % 4)
tulip.seq_add_callback(beat_callback, int(amy.SEQUENCER_PPQ))
tulip.keyboard_callback( process_key )
tulip.key_scan(1)

# Run in a loop forever. Catch ctrl-c
try:
    while seq_edit["run"]:
        # In an infinite loop , it's better to sleep than to say "pass", give the Tulip some time to breathe
        time.sleep_ms(100)
        #pass
except KeyboardInterrupt:
    seq_edit["run"] = 0


# Clean up a bit
tulip.keyboard_callback()
tulip.seq_remove_callbacks()
amy.reset()
tulip.key_scan(0)
tulip.frame_callback()
tulip.bg_clear()
tulip.sprite_clear()
tulip.tfb_start()

