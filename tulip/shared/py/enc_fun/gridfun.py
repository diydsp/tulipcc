import math
import tulip

"""
methods having to do with a grid
e.g. drum grid, piano roll

"""
               
class Grid():
    def __init__(self, start_x, start_y, width, height, palette_index,
                 cols=32, rows=25, visible_quarter_notes=4,seq_ppq=48):
        self.width = width
        self.height = height
        self.cols = cols
        self.rows = rows
        self.start_x = start_x
        self.start_y = start_y
        self.palette_index = palette_index
        self.visible_quarter_notes = visible_quarter_notes
        self.pulses_seen_in_grid = seq_ppq * self.visible_quarter_notes
        self.note_start = 48

        # compute grid spacing
        self.VerticalSpacing = self.height/self.rows
        self.HorizontalSpacing = self.width/self.cols


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

        # draw note anesm
        # array of note names to display
        note_names = ("C-","C#","D-","Eb", 
                      "E-","F-","F#","G-",
                      "G#","A-","Bb","B-")        
        for row, idx in zip(range(self.rows, 0, -1), range(1, self.rows + 1)):
            print(f'row: {row}, idx: {idx}')
exec
x0 = math.floor(self.start_x - 2*self.HorizontalSpacing - 1)
            y0 = math.floor(row*self.VerticalSpacing + self.start_y - 2 )
            note_num = self.note_start + idx
            note_name = note_names[note_num % 12]    
            note_octave = note_num // 12 
            note_str = note_name + str(note_octave) 
            tulip.bg_str(note_str,x0,y0,self.palette_index+45,1)

    def specs_get(self):
        return self.start_x, self.start_y, self.HorizontalSpacing, self.VerticalSpacing
    
    def get_coords(self, pulse, row):
        x = self.start_x + ( pulse / self.pulses_seen_in_grid ) * self.width
        y = self.start_y + row * self.VerticalSpacing
        return x,y
    