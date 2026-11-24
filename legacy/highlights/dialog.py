import sys
import tkinter as tk
from tkinter import filedialog

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    if sys.argv[-1] == 'folder':
        value = filedialog.askdirectory(title='Pasta para os episódios')
    else:
        value = filedialog.askopenfilename(title='Selecione a gameplay', filetypes=[('Vídeos', '*.mp4 *.mkv *.mov *.webm *.avi *.m4v *.ts')])
    root.destroy()
    print(value)
