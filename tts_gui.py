#tts.py를 창(GUI)으로 쓰는 프로그램  [새 파일]
#실행: python tts_gui.py
#  1. 문장을 입력하고 [합성] (또는 Ctrl+Enter)
#  2. 발음(음운 변동 결과)이 보이고, [재생]으로 듣기, [저장]으로 wav 파일 저장
#tts.py의 합성(), 저장(), 파일이름만들기()와 main.py의 음운변동()을 불러다 쓰기만 함

import os
import queue
import re
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

폴더 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 폴더)

#tts를 import하면 Kiwi(형태소 분석기) 로딩 때문에 몇 초 걸려서, 창을 먼저 띄우고 뒤에서 불러옴
tts = None
임시파일 = os.path.join(tempfile.gettempdir(), 'seethesing_미리듣기.wav')


def 발음글자(음절들):
    #음절들(초/중/종) -> '안녀하세요' 같은 글자로 (tests/run_tests.py의 발음()과 같은 방식)
    from hangul import First, Second, Third
    결과 = ''
    for 음절 in 음절들:
        if 음절['한글아님'] is not None:
            결과 += 음절['한글아님']
        else:
            결과 += chr(0xAC00 + (First.index(음절['초']) * 21 + Second.index(음절['중'])) * 28 + Third.index(음절['종']))
        if 음절['어절끝']:
            결과 += ' '
    return 결과.strip()


class 창:
    def __init__(self, root):
        self.root = root
        self.소리 = None
        self.문장 = ''
        root.title('SEETHESING TTS')
        root.geometry('560x320')

        tk.Label(root, text='문장').pack(anchor='w', padx=10, pady=(10, 0))
        self.입력 = tk.Text(root, height=4, font=('맑은 고딕', 12))
        self.입력.pack(fill='x', padx=10)
        self.입력.bind('<Control-Return>', lambda e: (self.합성(), 'break')[1])

        버튼줄 = tk.Frame(root)
        버튼줄.pack(fill='x', padx=10, pady=8)
        self.합성버튼 = tk.Button(버튼줄, text='합성 (Ctrl+Enter)', width=16, command=self.합성, state='disabled')
        self.합성버튼.pack(side='left')
        self.재생버튼 = tk.Button(버튼줄, text='재생', width=8, command=self.재생, state='disabled')
        self.재생버튼.pack(side='left', padx=6)
        self.저장버튼 = tk.Button(버튼줄, text='저장', width=8, command=self.저장, state='disabled')
        self.저장버튼.pack(side='left')

        tk.Label(root, text='발음').pack(anchor='w', padx=10)
        self.발음 = tk.Label(root, text='', font=('맑은 고딕', 12), anchor='w', justify='left',
                           wraplength=530, relief='groove', padx=6, pady=6)
        self.발음.pack(fill='x', padx=10)

        self.상태 = tk.Label(root, text='불러오는 중... (형태소 분석기 로딩)', fg='gray', anchor='w')
        self.상태.pack(fill='x', padx=10, pady=8, side='bottom')

        #작업 스레드는 화면을 직접 못 건드려서(tkinter 제한), 할 일을 큐에 넣고 메인 스레드가 0.1초마다 꺼내 실행
        self.할일 = queue.Queue()
        self.큐확인()
        threading.Thread(target=self.불러오기, daemon=True).start()

    def 큐확인(self):
        while not self.할일.empty():
            self.할일.get()()
        self.root.after(100, self.큐확인)

    #----- 오래 걸리는 일은 다른 스레드에서 돌리고, 화면 바꾸기는 self.할일 큐로 메인 스레드에 넘김 -----
    def 불러오기(self):
        global tts
        try:
            import tts as 모듈
            tts = 모듈
            self.할일.put(self.준비됨)
        except Exception as e:
            self.할일.put(lambda e=e: self.오류(f'불러오기 실패: {e}'))

    def 준비됨(self):
        self.합성버튼.config(state='normal')
        self.상태.config(text='준비됨')
        self.입력.focus_set()

    def 오류(self, 내용):
        self.상태.config(text=내용, fg='red')
        self.합성버튼.config(state='normal' if tts else 'disabled')
        messagebox.showerror('오류', 내용)

    def 합성(self):
        문장 = self.입력.get('1.0', 'end').strip().replace('\n', ' ')
        if not 문장 or tts is None:
            return
        self.합성버튼.config(state='disabled')
        self.재생버튼.config(state='disabled')
        self.저장버튼.config(state='disabled')
        self.상태.config(text='합성하는 중...', fg='gray')
        threading.Thread(target=self.합성작업, args=(문장,), daemon=True).start()

    def 합성작업(self, 문장):
        try:
            발음 = 발음글자(tts.음운변동(문장))
            소리 = tts.합성(문장)
            self.할일.put(lambda: self.합성끝(문장, 발음, 소리))
        except Exception as e:
            self.할일.put(lambda e=e: self.오류(f'합성 실패: {e}'))

    def 합성끝(self, 문장, 발음, 소리):
        self.문장, self.소리 = 문장, 소리
        self.발음.config(text=발음)
        self.합성버튼.config(state='normal')
        if len(소리) == 0:
            self.상태.config(text='한글이 없어서 만들 소리가 없어요', fg='gray')
            return
        초 = len(소리) / 2 / tts.샘플레이트   #스테레오라 /2
        self.상태.config(text=f'합성 완료 ({초:.2f}초)', fg='black')
        self.재생버튼.config(state='normal')
        self.저장버튼.config(state='normal')
        self.재생()

    def 재생(self):
        if self.소리 is None:
            return
        tts.저장(self.소리, 임시파일)
        try:
            import winsound
            winsound.PlaySound(임시파일, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except ImportError:   #윈도우가 아니면 기본 프로그램으로 열기
            import subprocess
            subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', 임시파일])

    def 저장(self):
        if self.소리 is None:
            return
        #윈도우 파일 이름에 못 쓰는 글자(? : " 등)는 뺌
        기본이름 = re.sub(r'[\\/:*?"<>|]', '', tts.파일이름만들기(self.문장)).strip() or 'output'
        경로 = filedialog.asksaveasfilename(defaultextension='.wav', initialfile=기본이름 + '.wav',
                                          filetypes=[('WAV 파일', '*.wav')])
        if 경로:
            경로 = tts.저장(self.소리, 경로)
            self.상태.config(text=f'저장함: {경로}', fg='black')


if __name__ == '__main__':
    root = tk.Tk()
    창(root)
    root.mainloop()
