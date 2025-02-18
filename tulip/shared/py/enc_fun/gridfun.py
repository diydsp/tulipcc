import math
import tulip

"""
Grid Fun by DIYDSP
simple grid class that draws a basic parameterizable grid
like a piano roll or drum grid

Presently, its the *visible* grid that is parameterizable
Eventually this will be a view or "facade" into a larger grid which is
more like the NoteManager

"""
               
class Grid():
    def __init__(self, start_x, start_y, width, height, palette_index,
                 cols=32, rows=25, visible_quarter_notes=4,seq_ppq=48):
        self.start_x = start_x
        self.start_y = start_y
        self.width = width
        self.height = height
        self.palette_index = palette_index
        self.cols = cols
        self.rows = rows
        self.visible_quarter_notes = visible_quarter_notes
        self.ppq = seq_ppq
        self.pulses_seen_in_grid = self.ppq * self.visible_quarter_notes
        self.note_start = 48
        self.note_num_color_no_highlight = palette_index + 45
        self.note_num_color_highlighted = palette_index + 93
        
        # compute grid spacing
        self.VerticalSpacing = self.height/self.rows
        self.HorizontalSpacing = self.width/self.cols

        self.note_names = ("C-","C#","D-","Eb", 
                      "E-","F-","F#","G-",
                      "G#","A-","Bb","B-")      

    # row numbering is weird, so read up:
    # left-side, vertical column of note names like "C-4"
    # remember: text gets printed "upwards" from the starting point
    # note: idx counts up 0-24, row counts down 25-1
    # drawing note names: note_num counts up e.g. 48-72
    #    plotting starts from bottom row 25, idx 0
    # row 0 is the top row ?
    # row 25 is the bottom row ?
    # cursor up moves the cursor up, lowering the row number, raising idx, increasing note_num
    # cursor down moves the cursor down, raising the row number, lowering idx, decreasing note_num
    def draw_note_name(self, row, idx, highlightedness ):
        #print(f'row: {row}, idx: {idx}')
        x0 = math.floor(self.start_x - 2*self.HorizontalSpacing - 1)
        y0 = math.floor( (1 + row ) * self.VerticalSpacing + self.start_y - 2 ) # 1 + row bc text is printed upwards
        note_num = self.note_start + idx
        note_name = self.note_names[note_num % 12]    
        note_octave = note_num // 12 
        note_str = note_name + str(note_octave) 
        if highlightedness == 0:
            pal_idx = self.note_num_color_no_highlight   
        else:
            pal_idx = self.note_num_color_highlighted  
        tulip.bg_str(note_str,x0,y0,pal_idx,1)

    def draw_note_names(self):
        
        for row, idx in zip(range(self.rows-1, -1, -1), range(0, self.rows )):
            self.draw_note_name(row, idx, 0 )   #  0 = not selected
            #self.draw_note_name(row, idx, self.note_num_color)   


    def draw(self):
    
        # draw vertical lines
        for col in range(self.cols):
            x0 = math.floor(col*self.HorizontalSpacing + self.start_x)
            x1 = x0
            y0 = math.floor(0             + self.start_y)
            y1 = math.floor(self.height-1 + self.start_y)
            tulip.bg_line(x0,y0,x1,y1,self.palette_index)

        # draw horizontal lines
        for row in range(self.rows):
            x0 = math.floor(0 + self.start_x)
            x1 = math.floor(self.width-1 + self.start_x)
            y0 = math.floor(row*self.VerticalSpacing + self.start_y)
            y1 = y0
            tulip.bg_line(x0,y0,x1,y1,self.palette_index)

        self.draw_note_names()

        # # draw note names
        # # array of note names to display
        # note_names = ("C-","C#","D-","Eb", 
        #               "E-","F-","F#","G-",
        #               "G#","A-","Bb","B-")        
        # for row, idx in zip(range(self.rows, 0, -1), range(1, self.rows + 1)):
        #     #print(f'row: {row}, idx: {idx}')
        #     x0 = math.floor(self.start_x - 2*self.HorizontalSpacing - 1)
        #     y0 = math.floor(row*self.VerticalSpacing + self.start_y - 2 )
        #     note_num = self.note_start + idx
        #     note_name = note_names[note_num % 12]    
        #     note_octave = note_num // 12 
        #     note_str = note_name + str(note_octave) 
        #     tulip.bg_str(note_str,x0,y0,self.palette_index+45,1)

    def specs_get(self):
        return self.start_x, self.start_y, self.HorizontalSpacing, self.VerticalSpacing
    
    def get_coords(self, pulse, row):
        x = self.start_x + ( pulse / self.pulses_seen_in_grid ) * self.width
        y = self.start_y + row * self.VerticalSpacing
        return x,y
    