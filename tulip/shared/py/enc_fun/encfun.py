import random, time, math, os

import tulip, amy, music, midi
from tulip import ticks_ms, seq_add_callback, seq_remove_callback, seq_ticks
import m5_8encoder as enc
import sequencer as tulpy_seq

import gridfun as gfun
#from operator import attrgetter # not available?

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
    "[ H. Sel. ]",  # H. Sel.
    "    [  ] ",  # Duration
    "    [  ] ",  # Timing

    "    [  ] ",   # Row
    "    [  ] ",   # Velocity
    "[ V. Sel. ]",   # V. Sel.
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
        "patch":114,
        }

# Draw a line of pixels up top with random colors
for x in range(WIDTH):
    tulip.bg_pixel(x,0,seq_edit["grass_color"   ])

class Note():
    def __init__(self, pos, note_num, vel, dur, note_index):
        self.pos = pos
        self.note_num = note_num
        self.vel = vel
        self.dur = dur
        self.note_index = note_index
    def __repr__(self):
        return f"Pos {self.pos}, note_num: {self.note_num}, vel {self.vel}, dur {self.dur} ticks\n"


class NoteManager():
    def __init__(self):
        self.notes = []
        self.note_index = 1
        
    def remove_note_cmds_from_amy_seq(self, note ):
        amy.send(sequence= ",,%d" % (note.note_index) )    # remove note-on from sequencer
        amy.send(sequence= ",,%d" % (note.note_index+1) )    # remove note-off from sequencer
        return "new"

    def add_note_cmds_to_amy_seq( self, note_num, vel, pos, dur, grid, note_index ):
        
        amy.send(voices=1, note=note_num, vel=vel, sequence= "%d,%d,%d" % (pos, grid.pulses_seen_in_grid, note_index) )
        note_off_pos = ( pos + dur ) % grid.pulses_seen_in_grid
        amy.send(voices=1, note=note_num, vel=0, sequence= "%d,%d,%d" % (note_off_pos, grid.pulses_seen_in_grid, note_index+1) )    
        #print(f'on:{note_num} ({note_index})@{pos},, off:({note_index+1})@{note_off_pos}')

    def toggle_in_note_mgr_and_amy_seq(self, grid, pos, note_num, vel, dur):
        
        # check if note already exists
        for note in self.notes:
            if note.pos == pos and note.note_num == note_num:
                print("note already exists")
                self.notes.remove(note)     # remove note from data struct

                self.remove_note_cmds_from_amy_seq( note ) # remove note from sequencer

                #amy.send(sequence= ",,%d" % (note.note_index) )    # remove note-on from sequencer
                #amy.send(sequence= ",,%d" % (note.note_index+1) )    # remove note-off from sequencer
                return "removed"

        # store in Note Manager
        self.note_index += 2 # 0 offset = note on, 1 offset = note off
        new_note = Note(pos, note_num, vel, dur, self.note_index)
        self.notes.append(new_note)
        # sort for easier display.  
        # not efficient but can be upgraded to bisect or sortedcontainers.
        self.notes.sort(key=lambda item: (item.pos, item.note_num))
            #self.notes.sort(key=attrgetter("pos", "note_num"))  # attrgetter not available
 
        # write into sequencer
        self.add_note_cmds_to_amy_seq( note_num, vel, pos, dur, grid, self.note_index) 
        # amy.send(voices=1, note=note_num, vel=vel, sequence= "%d,%d,%d" % (pos, grid.pulses_seen_in_grid, self.note_index) )
        # self.note_index += 1
        # note_off_pos = ( pos + dur ) % grid.pulses_seen_in_grid
        # amy.send(voices=1, note=note_num, vel=0, sequence= "%d,%d,%d" % (note_off_pos, grid.pulses_seen_in_grid, self.note_index) )  
        return "new"


    def display_notes(self):
        print(self.notes)

   

class ButtonManager():
    """Keep track of which encoders' buttons were last measured down.  Good for detecting changes.
    Perhaps encoder driver does this already?"""
    def __init__(self):
        self.note_add_down=False

    def note_add_down_get(self):
        return self.note_add_down

    def note_add_down_set(self, val):
        self.note_add_down = val    


class Reducer():
    """Make up for the fact that encoders move two values for every physical step"""
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


def redraw_cursor( d, grid, color ):
    f_x, f_y = grid.get_coords(d["x"], d["y"])
    f_x = math.floor( clip( float(f_x) + grid.HorizontalSpacing/2 -1, 0, WIDTH-1) )
    f_y = math.floor( clip( float(f_y) - grid.VerticalSpacing/2 + 2, 0, HEIGHT-1) ) 
    tulip.sprite_move(0, f_x, f_y)

def redraw_note_name( d, prev_y, grid, color ):
    # redraw prev position with unselected color
    idx = grid.rows - 1 - prev_y
    grid.draw_note_name( prev_y, idx, 0 )   

    # redraw new position with selected color
    idx = grid.rows - 1 - d["y"]
    grid.draw_note_name( d["y"], idx, 1 )

    # maybe for later
    # tulip.bg_rect( d["x"], d["y"]+10, 200, 20, bg["grass_color"], 1) 
    #     ,0, 200, 20, bg["grass_color"], 1)


half_rabbit_w = math.floor(rabbit_w / 2)
half_rabbit_h = math.floor(rabbit_h / 2)

# cursor
# sprite_register(self.sprite_id,self.mem_pos, self.width, self.height)
tulip.sprite_register(0,0, rabbit_w, rabbit_h)
# not good idea to turn on sprite here, it will be turned on in game loop
tulip.sprite_on(0)

# chaser rabbit
tulip.sprite_register(1,0, rabbit_w, rabbit_h)
tulip.sprite_move(1, math.floor(WIDTH/2) - half_rabbit_w, 0)
tulip.sprite_on(1)


note_manager = NoteManager()
button_mgr = ButtonManager()    
grid = gfun.Grid(start_x=200, start_y=50, width=700, height=500, palette_index=3,
                 cols=32,  rows=25, visible_quarter_notes=4,seq_ppq = amy.AMY_SEQUENCER_PPQ,
#                 seq_ppq=amy.SEQUENCER_PPQ) 
)
grid.draw()

redraw_cursor( seq_edit, grid, color = 1 )


reducer_xy_pos = Reducer()  # for position encoders
reducer_xy_sel = Reducer()  # for selection encoders
reducer_xy_mod = Reducer()  # for moving position, and note number

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
    #print(f'seq_ticks: {seq_ticks()}, current_beat: {current_beat}')   

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
            #amy.send(reset=amy.RESET_TIMEBASE)  # testing reset seq here

        elif seq_edit["transport"] == "paused":
            seq_edit["transport"] = "playing"

            # testing reset-before-restore-tempo
            amy.send(reset=amy.RESET_TIMEBASE)  # reset seq
            amy.send(tempo=seq_edit["tempo"])   # unpause seq   

            # testing restore-tempo_before_reset
            #amy.send(tempo=seq_edit["tempo"])   # unpause seq   
            #amy.send(reset=amy.RESET_TIMEBASE)  # reset seq

        else:
            seq_edit["transport"] = "paused"
            amy.send(tempo=0) # literally pause seq
    print(f'transport: {seq_edit["transport"]}')

def seq_cursor( dir ):

    if dir == "up": reducer_xy_pos.delta_y(-1)
    elif dir == "down": reducer_xy_pos.delta_y(1)
    elif dir == "left": reducer_xy_pos.delta_x(-1)
    elif dir == "right": reducer_xy_pos.delta_x(1)
    else: print("unhandled cursor dir: %s" % (dir))

patch_x = 25
patch_y = 200 + 32 * 1
patch_color=0
    

def patch_delta( patch_delta ):
    temp = seq_edit["patch"] + patch_delta
    temp = clip(temp, 0, 9999)
    seq_edit["patch"] = temp
    print('patch: %d' % (temp))
    amy.send(voices=1,load_patch=temp)
    # rectangle draws downwards, text draws upwards, so offset it
    tulip.bg_rect(patch_x,patch_y, 12*7,28, seq_edit['grass_color'], 1 )
    tulip.bg_str( f'Patch: {temp}', patch_x+3, patch_y+16,          patch_color, 2)


def process_key( key ):
    global seq_edit

    tulip_keys = tulip.keys()

    # space
    if key == 32: seq_transport_cmd( "toggle")        
        
    # cursor keys
    elif key == 259:  # up
        patch_delta(1)
    elif key == 258:  # down
        patch_delta(-1)

    elif key == 260: seq_cursor("left")  
    elif key == 261: seq_cursor("right") 

    # esc
    #if key == 0x29: 

    # page up/down
    elif key== 25:seq_tempo_delta(1)
    elif key == 22:seq_tempo_delta(-1)

    elif key == 43:   # tab -> tap tempo?
        pass


    # see if 
    elif tulip_keys[0] == 1 and tulip_keys[1] == 30:   # ctrl-1
        print
        pass

    else:   
        print("unhandled key: %d" % (key))
        print(f'{tulip_keys}')

def update_closest_note(note_dist,min_dist,note,closest_note):
    # find closet one, but not including one currently at the cursor's position.  
    if note_dist != 0:
        #print(f'note: {note.note_num}, pos: {note.pos}, dist: {note_dist}')  
        if note_dist < min_dist:
            min_dist = note_dist
            closest_note = note
    return min_dist, closest_note


def xaxis_note_select( d, delta ):
    
    min_dist = 1000000000
    closest_note = None

    # 1. seek closet note from curs y pos, but not including any currently at the cursor's column.
    for note in note_manager.notes:
        if note.pos != d["x"]:
            if delta > 0:
                x_comp = note.pos - d["x"]   
            elif delta < 0:
                x_comp = d["x"] - note.pos
            x_comp = x_comp % grid.pulses_seen_in_grid 
            y_comp = abs(note.note_num - (48 + grid.rows - d["y"])) 
            note_dist = x_comp**2 + y_comp**2
            min_dist, closest_note = update_closest_note(note_dist,min_dist,note,closest_note)

    if closest_note != None:
        return closest_note

    # 2. first find closest note in this row
    #print('x_note_sel stage 2')
    for note in note_manager.notes:
        if note.note_num == 48 + grid.rows - d["y"]:
            if delta > 0:
                x_comp = note.pos - d["x"]   
            elif delta < 0:
                x_comp = d["x"] - note.pos
            x_comp = x_comp % grid.pulses_seen_in_grid 
            note_dist = x_comp**2 
            min_dist, closest_note = update_closest_note(note_dist,min_dist,note,closest_note)

    return closest_note

def yaxis_note_select( d, delta ):
    
    min_dist = 1000000000
    closest_note = None

    # 1. seek closest note at curs x position. aka time at the ppq scale/column 
    # look up and down the pitch axis for the closest note
    for note in note_manager.notes: 
        if note.pos == d["x"]:
            if delta > 0:
                y_comp = note.note_num - (48 + grid.rows - d["y"])
            elif delta < 0:
                y_comp = (48 + grid.rows - d["y"]) - note.note_num
            y_comp = y_comp % grid.rows
            note_dist = y_comp**2
            min_dist, closest_note = update_closest_note(note_dist,min_dist,note,closest_note)
    
    if closest_note != None:
        return closest_note

    # 2. seek closest note from curs x position, but not including any currently at the cursor's row.
    #print("y_note_sel stage 2")
    for note in note_manager.notes:
        #if note.pos == d["x"] and note.note_num != 48 + grid.rows - d["y"]:
        current_note_number = 48 + grid.rows - d["y"]
        if note.note_num != current_note_number:
            if delta > 0:
                y_comp = note.note_num - (48 + grid.rows - d["y"])
            elif delta < 0:
                y_comp = (48 + grid.rows - d["y"]) - note.note_num
            x_comp = abs(note.pos - d["x"])
            y_comp = y_comp % grid.rows
            note_dist = x_comp**2 + y_comp**2
            min_dist, closest_note = update_closest_note(note_dist,min_dist,note,closest_note)

    if closest_note != None:
        return closest_note

    # 3. find distance between this note and all notes
    #print("y_note_sel stage 3")
    for note in note_manager.notes:
        if delta > 0:
            y_comp = note.note_num - (48 + grid.rows - d["y"])
        elif delta < 0:
            y_comp = (48 + grid.rows - d["y"]) - note.note_num
        x_comp = abs(note.pos - d["x"]) 
        note_dist = x_comp**2 + y_comp**2
        min_dist, closest_note = update_closest_note(note_dist,min_dist,note,closest_note)
    return closest_note

def draw_note_at_coords( x, y, grid, color ):
    x = math.floor( clip( float(x + grid.HorizontalSpacing / 2 ), 0, WIDTH-1) )
    y = math.floor( clip( float(y + grid.VerticalSpacing / 2 ), 0, HEIGHT-1) ) 
    #x = math.floor( clip( float(x) + grid.HorizontalSpacing/2 -1, 0, WIDTH-1) )
    #y = math.floor( clip( float(y) - grid.VerticalSpacing/2 + 2, 0, HEIGHT-1) ) 
    tulip.bg_circle(x, y, math.floor(grid.HorizontalSpacing/3), color, 1)

def draw_note_at_cursor( d, grid, color ):
    f_x, f_y = grid.get_coords(d["x"], d["y"])
    draw_note_at_coords( f_x, f_y, grid, color )  

    #f_x = math.floor( clip( float(f_x + grid.HorizontalSpacing/2 ) , 0, WIDTH-1) )
    #f_y = math.floor( clip( float(f_y + grid.VerticalSpacing/2   ) , 0, HEIGHT-1) ) 
    #tulip.bg_circle(f_x, f_y, math.floor(grid.HorizontalSpacing/3), color, 1)

def calc_new_ppq_in_grid( start_pos, dx, bx ):
    if bx == 1:
        cur_col = grid.cols * ( start_pos / grid.pulses_seen_in_grid )
        cur_col += dx
        cur_col = cur_col % grid.cols
        ppq_in_grid = ( cur_col / grid.cols ) * grid.pulses_seen_in_grid
    else:
        ppq_in_grid = start_pos + dx
        #ppq_in_grid = d["x"] + dx
    ppq_in_grid = ppq_in_grid % grid.pulses_seen_in_grid
    return ppq_in_grid

def move_cursor_x( d, dx, bx ):
    d["x"] = calc_new_ppq_in_grid( d["x"], dx, bx )
    #print(f'x: {d["x"]}, col: {d["x"]*grid.cols/grid.pulses_seen_in_grid}')

def move_note_in_time( d, grid, move_note_enc_delta, enc_butts ):
    bx = 1 - enc_butts[ENC_MOVE_NOTE_POS]  # default bx==1, no button, move one column
    #print(f'move_note_delta: {move_note_enc_delta}')
    # change notes position
    # find note at cursor's position
    for note in note_manager.notes:
        if note.pos == d["x"] and note.note_num == 48 + grid.rows - d["y"]:
            
            temp_note = note # make a temp copy
            draw_note_at_cursor( d, grid, bg["grass_color"] )  # erase current note

            # re-add to make it go away in note manager and sequencer
            note_manager.toggle_in_note_mgr_and_amy_seq( grid, note.pos, note.note_num, note.vel, note.dur )
            
            # modify note position
            temp_note.pos = calc_new_ppq_in_grid( d["x"], move_note_enc_delta, bx )    

            # re-add note to note manager
            note_manager.toggle_in_note_mgr_and_amy_seq( grid, temp_note.pos, temp_note.note_num, temp_note.vel, temp_note.dur )

            # update cursor pos and redraw at new positoin
            d["x"] = temp_note.pos
            draw_note_at_cursor( d, grid, 1 )  
            return True, True #    redraw_cursor_plox = 1
            #break           

    return False, False # redraw_cursor_plox = 0

def move_note_in_pitch( d, grid, move_note_enc_delta, enc_butts ):
    #print(f'move_note_delta: {move_note_enc_delta}')
    # change notes position
    # find note at cursor's position
    for note in note_manager.notes:
        if note.pos == d["x"] and note.note_num == 48 + grid.rows - d["y"]:
            
            draw_note_at_cursor( d, grid, bg["grass_color"] )  # erase current note

            note_manager.remove_note_cmds_from_amy_seq( note )   # remove note from amy sequencer
            note.note_num += move_note_enc_delta  # modify note number
            note_manager.add_note_cmds_to_amy_seq( note.note_num, note.vel, note.pos, note.dur, grid, note.note_index ) # add note to amy sequencer

            # update cursor pos and redraw at new positoin
            d["y"] = 48 + grid.rows - note.note_num
            draw_note_at_cursor( d, grid, 1 )



            # re-add to make it go away in note manager and sequencer
            #note_manager.add( grid, note.pos, note.note_num, note.vel, note.dur )
            # re-add note to note manager
            #note_manager.add( grid, temp_note.pos, temp_note.note_num, temp_note.vel, temp_note.dur )   

            return True, True # redraw_cursor_plox = 1, redraw_note_name_plox = 1

    return False, False

def select_note_in_time( d, grid, note_sel_dx ):    
    nearest_note = xaxis_note_select( d, note_sel_dx )   
    #print(f'nearest_note: {nearest_note}')    
    if nearest_note != None:
        d["x"] = nearest_note.pos   
        d["y"] = 48 + grid.rows - nearest_note.note_num
        return True, True #
    else:
        #print("no nearest note found")
        return False, False


def rotate_note_in_time( grid, note, note_move_dx ):       

    note_manager.remove_note_cmds_from_amy_seq( note )   # remove note from amy sequencer

    x,y = grid.get_coords( note.pos, 48 + grid.rows - note.note_num ) 
    draw_note_at_coords( x, y, grid, bg["grass_color"] )  # erase note

    note.pos = calc_new_ppq_in_grid( note.pos, note_move_dx, 1 ) # modify note position in grid

    x,y = grid.get_coords( note.pos, 48 + grid.rows - note.note_num ) 
    draw_note_at_coords( x, y, grid, 1 )  # draw note

    note_manager.add_note_cmds_to_amy_seq( note.note_num, note.vel, note.pos, note.dur, grid, note.note_index ) # add note to amy sequencer



def rotate_notes_in_time( d, grid, note_move_dx ):    
    for note in note_manager.notes:
        rotate_note_in_time( grid, note, note_move_dx )
    
  



# map encoders to functions
ENC_MOVE_CURS_XPOS = 7
ENC_NOTE_SEEK_LR   = 6
ENC_MOVE_NOTE_POS = 5
ENC_TIME_JOG      = 4
ENC_MOVE_NOTE_NUM = 2
ENC_NOTE_SEEK_UD   = 1
ENC_MOVE_CURS_YPOS = 0
NEW_NOTE_BUTTON1  = 0

# This is called every frame by the GPU.
def game_loop(d):

    global rabbit_h,rabbit_w,WIDTH,HEIGHT,ringing_pan
    
    enc_butts = enc.read_all_buttons()
    enc_butts = [1-x for x in enc_butts]  # rev polarity

    # place musical note
    if button_mgr.note_add_down_get() == False \
        and enc_butts[NEW_NOTE_BUTTON1] == 1:
            button_mgr.note_add_down_set(True)

            result = note_manager.toggle_in_note_mgr_and_amy_seq( grid, 
                             pos = d["x"], 
                             note_num = 48 + grid.rows - d["y"], 
                             vel = 0.5, 
                             dur = 6 ) 

            if result == "new":
                draw_note_at_cursor( d, grid, 1 )  
            elif result == "removed":
                draw_note_at_cursor( d, grid, bg["grass_color"] )

            note_manager.display_notes()    
        
    else:
        # move cursor around

        prev_y = d["y"]
        redraw_cursor_plox = 0
        redraw_note_name_plox = 0

        # move cursor fwd/back in time in X.  note horizontal is in pulses, e.g. out of 48*4
        dx_pre = enc.read_increment(ENC_MOVE_CURS_XPOS)
        dx = reducer_xy_pos.delta_x(dx_pre)
        if dx != 0:
            bx = 1 - enc_butts[ENC_MOVE_CURS_XPOS]  # default bx==1, no button, move one column
            move_cursor_x( d, dx, bx )
            redraw_cursor_plox = 1

        # move cursor up/down in notespace / Y-axis
        dy_pre = enc.read_increment(ENC_MOVE_CURS_YPOS)
        dy = reducer_xy_pos.delta_y(dy_pre)
        if dy != 0:
            #by = 1 - enc_butts[KNOB_YPOS]  # dont invert button press 
            d["y"] -= dy
            d["y"] = d["y"] % grid.rows
            redraw_cursor_plox=1
            redraw_note_name_plox=1
            

        # move note in time
        move_note_pos_pre = enc.read_increment(ENC_MOVE_NOTE_POS)
        move_note_enc_delta = reducer_xy_mod.delta_x(move_note_pos_pre)
        if move_note_enc_delta != 0:
            redraw_cursor_plox, redraw_note_name_plox = move_note_in_time( d, grid, move_note_enc_delta, enc_butts)
                        
        # move note in pitch
        move_note_num_pre = enc.read_increment(ENC_MOVE_NOTE_NUM)
        move_note_enc_delta = reducer_xy_mod.delta_y(move_note_num_pre)
        if move_note_enc_delta != 0:
            redraw_cursor_plox, redraw_note_name_plox = move_note_in_pitch( d, grid, move_note_enc_delta, enc_butts)

        # time jog
        jog_amount = enc.read_increment(ENC_TIME_JOG)
        if jog_amount != 0:
            d["time_disp_start"] += jog_amount
            print(f"jog_amount: {jog_amount} time_disp_start: {d['time_disp_start']}")              
            for row in range(grid.start_y, grid.start_y + grid.height):
                tulip.bg_scroll_x_offset(math.floor( row), math.floor( d["time_disp_start"]) )


        # select note left/right -or- rotate notes in time
        note_sel_pre = enc.read_increment(ENC_NOTE_SEEK_LR)
        note_sel_dx = reducer_xy_sel.delta_x(note_sel_pre)
        if note_sel_dx != 0:
            if enc_butts[ENC_NOTE_SEEK_LR] == 1:
                rotate_notes_in_time( d, grid, note_sel_dx )
            else:
                redraw_cursor_plox, redraw_note_name_plox = select_note_in_time( d, grid, note_sel_dx )


        # select note up/down
        note_sel_pre = enc.read_increment(ENC_NOTE_SEEK_UD)
        note_sel_dy = reducer_xy_sel.delta_y(note_sel_pre)
        if note_sel_dy != 0:
            #print(f'v_note_sel_delta: {note_sel_dy}')
            nearest_note = yaxis_note_select( d, note_sel_dy )   
            #print(f'nearest_note: {nearest_note}, pos={nearest_note.pos}, note_num={nearest_note.note_num}, vel={nearest_note.vel}')    
            if nearest_note != None:
                d["x"] = nearest_note.pos   
                d["y"] = 48 + grid.rows - nearest_note.note_num
                redraw_cursor_plox = 1
                redraw_note_name_plox = 1
            else:
                print("no nearest note found")
        

        if redraw_cursor_plox:
            redraw_cursor( d, grid, 1 )

        if redraw_note_name_plox:
            #print(f'note name: {note_name}')
            redraw_note_name( d, prev_y, grid, 1 )


            # idx = grid.rows - 1 - prev_y
            # grid.draw_note_name( prev_y, idx, 0 )

            # idx = grid.rows - 1 - d["y"]
            # grid.draw_note_name( d["y"], idx, 1 )


    # New note button released
    if button_mgr.note_add_down_get() == True and \
        enc_butts[NEW_NOTE_BUTTON1] == 0:
            button_mgr.note_add_down_set(False)

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
#amy.send(voices=1, note=55, vel=.5, sequence= "%d,%d,%d" % (0, 48 * 4, 999) )
#amy.send(wave=amy.PCM, patch=35,feedback=.5) 
#amy.send(osc=0, note=50, vel= 1)

# midi.config.add_synth(channel=5, num_voices=1, patch_number=114)
# add_synth(patch_number=..) is deprecated and will be removed.  Use add_synth(PatchSynth(patch_number=..)) instead.
#midi.config.add_synth( midi.PatchSynth( patch_number=114) )
midi.config.add_synth( midi.PatchSynth(patch_number=114), channel=5)

music_seq = tulpy_seq.Sequence( 4 ) # every quarter note
music_seq.add(0, beat_callback )  #  update the running rabbit every quarter note
current_beat = int((seq_ticks() / 48) % 4)
#tulip.seq_add_callback(beat_callback, grid.ppq)
#tulip.seq_add_callback(beat_callback, int(amy.SEQUENCER_PPQ))

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
