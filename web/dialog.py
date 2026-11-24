"""Native dialog reused from Highlights 1.0, isolated from the server thread."""
import sys
import tkinter as tk
from tkinter import filedialog

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    if sys.argv[-1]=='folder':value=filedialog.askdirectory(title='Selecione a pasta local')
    else:value=filedialog.askopenfilename(title='Selecione sua gameplay',filetypes=[('Vídeos','*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts')])
    root.destroy();print(value)
