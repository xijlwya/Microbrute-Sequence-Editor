from tkinter import filedialog
from tkinter import messagebox
import tkinter as tk

import os.path #for saving and loading files, checking file paths
import pygame.mixer #for playing back the sequence
import io #for binary buffer to play midi from
import MidiFile3 #to create midi binary


class PianoRoll(tk.Canvas):
	'''Piano Roll widget'''
	
	def __init__(self, master):
		#layout constants
		self.key_width = 16
		self.key_length = 50
		self.step_length = 20
		
		self.note_range = 125 #microbrute allows for 125 note values
		
		#proportions
		self.width = self.key_length + 64*self.step_length + 16 #+16 for scrollbar default width
		self.height = self.note_range*self.key_width
		
		tk.Canvas.__init__(
			self,
			master,
			width=self.width/2,
			height=400 + 16, #+16 for scrollbar default width
			scrollregion=(0,0,self.width,self.height)
		)
		
		#scrollbars
		vertical_scrollbar = tk.Scrollbar(self, command=self.yview)
		vertical_scrollbar.pack(side=tk.RIGHT,fill=tk.Y)
		horizontal_scrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.xview)
		horizontal_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
		
		#setting up scrollbars
		self.config(xscrollcommand=horizontal_scrollbar.set, yscrollcommand=vertical_scrollbar.set)
		
		self._draw_piano()
		self._draw_lines()
		self._draw_stipple()
	
	def _draw_piano(self):
		'''draw the piano bars on the left'''
		
		count = 7 #highest possible note is f
		octave = 8
		for a in range(0,self.height, self.key_width):
			
			if count > 12:
				count = 1
			if count in [2,4,6,9,11]:
				color = "#000000"
			else:
				color = "#ffffff"
			
			self.create_rectangle(0,a,self.key_length, a + self.key_width, fill = color)
			if count == 12:
				self.create_text(2*self.key_length/3,a+8,text="C"+str(octave))
				octave -= 1
				
			count += 1
		
	def _draw_lines(self):
		'''draw the grid in whcih the notes are placed'''
		self.delete("line")
	
		count = 0
		for a in range(self.key_length+self.step_length,self.width,self.step_length): #vertical lines
			count += 1
			if count == 4:
				self.create_line(a,0,a,self.height,width=4, tag="line")
				count = 0
			else:
				self.create_line(a,0,a,self.height, tag="line")
		
		for a in range(0,self.height,self.key_width): #horizontal lines
			self.create_line(self.key_length, a, self.width, a, tag="line")
			
	def _draw_stipple(self, sequence_length=0):
		'''draw the greyed-out area which indicates that the sequence is shorter than 64 steps'''
		
		self.delete("stipple")
		left = self.key_length + self.step_length*sequence_length
		self.create_rectangle(left,0,self.width, self.height, stipple="gray50", fill="black", width=0, tag="stipple")
		
	def scroll(self, event):
		'''process mousewheel events to scroll'''
		
		#Windows will send <MouseWheel> event, Linux will send <Button-4> and <Button-5> events
		if event.delta:
			self.yview_scroll(-event.delta//40,"units")
		elif event.num == 4:
			self.yview_scroll(-3,"units")
		elif event.num == 5:
			self.yview_scroll(3,"units")
	
	def jump_scroll(self, first_note):
		'''jump the view,so that the first note of the sequence can be seen'''
	
		if first_note is not None:
			self.yview_moveto(1-(first_note+(self.winfo_height()/self.key_width)/2)/self.note_range)
	
	def update(self, stipple=None):
		'''draw the lines and the stipple after notes have changed'''
		
		self._draw_lines()
		if stipple is not None:
			self._draw_stipple(stipple)
	
	def set_note(self, step, value):
		'''put a note/break into the piano roll'''
		
		if step < 0 or step > 63:
			print("Invalid step: ", step)
	
		topx=step*self.step_length+self.key_length
		lowx=topx+self.step_length
		
		#self.delete("step"+str(step))
		
		if value == 'x': #break in the sequencer
			self.create_rectangle(topx,0,lowx,self.height, fill="skyblue", tag="step")
		elif value < 1 or value > self.note_range:
			print("Found invalid value: ", value, "@step ", step)
		else:
			topy=self.height-self.key_width*value
			lowy=topy+self.key_width
			self.create_rectangle(topx, topy, lowx, lowy, fill="limegreen", tag="step")
	
	def get_clicked_note(self, event):
		'''converts between window coordinates and the respective note'''
	
		x = self.canvasx(event.x)
		y = self.canvasy(event.y)
		step = int((x-self.key_length)//self.step_length)
		note = self.note_range-int(y//self.key_width)
		return (step, note)

		
class GUI:
	"""The whole GUI for the Application. Contains the Piano Roll and everything."""
	def __init__(self, master, bank):
		self.bank = bank
		
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
		
		master.title("MicroBrute Sequence Editor - New File")
		master.minsize(500,400)
		
		self.piano_roll = PianoRoll(master)
		self.piano_roll.bind("<Button-1>", self.process_lmb)
		self.piano_roll.bind("<Button-3>", self.process_rmb)
		self.piano_roll.bind("<MouseWheel>", self.piano_roll.scroll) #Windows only!
		self.piano_roll.bind("<Button-4>", self.piano_roll.scroll) #Linux Mouse Wheel
		self.piano_roll.bind("<Button-5>", self.piano_roll.scroll) #Linux Mouse Wheel
		self.piano_roll.yview_moveto(0.4)
		
		self.list = tk.Listbox(master, selectmode=tk.SINGLE, height=8, width=10, activestyle="none")
		self.list.bind("<<ListboxSelect>>", self.list_callback)
		for a in range(1,9):
			self.list.insert(tk.END, "Sequence "+str(a))
		self.list.selection_set(0)
		
		self.play_button = tk.Button(master, text="Play", width=4, command=bank.play_sequence)
		self.save_button = tk.Button(master, text="Save", width=4,command=self.save_bank)		
		self.load_button = tk.Button(master, text="Load", width=4,command=self.load_bank)
		
		
		self.master.columnconfigure(1, weight=3)
		self.master.rowconfigure(5, weight=3)
		self.piano_roll.grid(row=0, column=1, rowspan=6, columnspan=3, sticky=tk.N+tk.E+tk.S+tk.W)
		self.list.grid(row=0, column=0, rowspan=2, padx=5, pady=5)
		self.save_button.grid(row=3, column=0, pady=5)
		self.load_button.grid(row=4, column=0, pady=5)
		self.play_button.grid(row=5, pady=5, padx=(5,5), sticky=tk.N)
		
		
	def process_lmb(self, event): #add note to the sequence
		step, note = self.piano_roll.get_clicked_note(event)
		self.bank.change_sequence(step, note)
		self.sequence_to_display()
	
	def process_rmb(self, event):#setting the sequence length
		step = self.piano_roll.get_clicked_note(event)[0]
		self.bank.shorten_sequence(step)
		self.sequence_to_display()
	
	def save_bank(self):
		filename = filedialog.asksaveasfilename(defaultextension=".mbseq", filetypes=[("MicroBrute sequences",".mbseq")])
		self.master.title("MicroBrute Sequence Editor - "+ os.path.split(filename)[1])
		self.bank.save_bank(filename)
		
	def load_bank(self):
		if self.bank.save_pending:
			if not messagebox.askokcancel("Discard Changes", "Do you want to load without saving changes?"):
				return
		
		filename = filedialog.askopenfilename(defaultextension=".mbseq", filetypes=[("MicroBrute sequences",".mbseq")])
		
		if os.path.isfile(filename):
			self.master.title("MicroBrute Sequence Editor - "+ os.path.split(filename)[1])
			self.bank.load_bank(filename)
			self.piano_roll.jump_scroll(self.bank.get_first_note())
			self.sequence_to_display()

	def list_callback(self, event):
		self.bank.selected_sequence = event.widget.curselection()[0]
		self.piano_roll.jump_scroll(self.bank.get_first_note())
		self.sequence_to_display()
		
	def sequence_to_display(self):
		self.piano_roll.delete("step")
		for step, note in enumerate(self.bank.sequences[self.bank.selected_sequence]):
			self.piano_roll.set_note(step, note)
		self.piano_roll.update(len(self.bank.sequences[self.bank.selected_sequence]))
	
	def on_closing(self):
		if self.bank.save_pending:
			if messagebox.askokcancel("Quit", "Do you want to quit without saving?"):
				self.master.destroy()
		else: self.master.destroy()
		
	def play(self):
		self.bank.play_sequence()
		
		
class Manager:
	#manages single sequences & banks in one big file
	
	def __init__(self, filename='editor_data.dat'):
		if not os.path.isfile(filename):
			open(filename, 'w').close() #just create the file for later usage
		self.file = filename
		
		
class SingleSequence:
	#individual sequence for storing in the database
	def __init__(self, list=[], name="", desc="", tag=""):
		self.list = list
		self.name = name
		self.description = desc
		self.tags = []
		if tag:
			self.tags.append(tag)

		
class Bank:
	#Bank for making and loading mbseq files
	
	def __init__(self):
		self.sequences = [[] for _ in range(8)]
		self.selected_sequence = 0
		self.save_pending = False
	
	def change_sequence(self, step, note):
		#sanity check
		if step < 0 or step > 63:
			raise ValueError('Step of illegal value: '+str(step))
		if (note < 1 or note > 125) and note is not 'x':
			raise ValueError('Note of illegal value: '+str(step))
	
		current = self.sequences[self.selected_sequence]
		length = len(current)
		if step >= length: #step has been added which lies beyond sequence end
			for pos in range(length, step):
				current.append('x')# fill with breaks until you reach step
			current.append(note)
		elif current[step] == note: #clicked on already existing note
			current[step] = 'x'
		else:
			current[step] = note #overwrite existing note
		self.save_pending = True

	def shorten_sequence(self, step):
		#sanity check
		if step < 0 or step > 63:
			raise ValueError('Step of illegal value: '+str(step))
		
		self.sequences[self.selected_sequence] = self.sequences[self.selected_sequence][0:step]
		
		self.save_pending = True
	
	def save_bank(self, filename):
		with open(filename,'w') as f:
			for num, seq in enumerate(self.sequences, 1):
				f.write(str(num) + ':')
				
				if seq:
					for entry in seq[0:-1]:
						f.write(str(entry) + ' ')
					f.write(str(seq[-1]) + '\r\n')
		
		self.save_pending = False
	
	def load_bank(self, filename):
		self.sequences = []
    
		with open(filename, 'r') as f:
			for line in f: #read the 8 lists of numbers and x's 
				value_list = line.split(' ')
				value_list[0] = value_list[0][2:] #strip the colon and sequence number
				value_list[-1] = value_list[-1].strip('\r\n') #strip the final line feed
				
				temp_list = []
				for val in value_list:
					try:
						temp_list.append(int(val))
					except(ValueError):
						temp_list.append('x')
				self.sequences.append(temp_list)
				
		self.save_pending = False
	
	def get_first_note(self):
		for note in self.sequences[self.selected_sequence]:
			if note is not 'x':
				return note
		return None
	
	def make_midi(self, tempo=120):
		midi = MidiFile3.MIDIFile(1)
		
		midi.addTempo(0,0,tempo)
		
		#add a note: midi.addNote(track,channel,pitch,time,duration,volume)
		time_cursor=0.0
		for note in self.sequences[self.selected_sequence]:
			if note is not 'x':
				midi.addNote(0,0,note,time_cursor,1,100)
			time_cursor += 0.25
		
		return midi
	
	def play_sequence(self):
		midifile = io.BytesIO()
		self.make_midi().writeFile(midifile)
		temp = io.BytesIO(midifile.getvalue())
		pygame.mixer.music.load(temp)
		pygame.mixer.music.play()
		
		
def main():
	pygame.mixer.init()
	root = tk.Tk()
	bank = Bank()
	gui = GUI(root, bank)
	
	root.mainloop()
	
if __name__ == '__main__':
	main()