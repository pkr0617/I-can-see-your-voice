#tts를 창 하나짜리 프로그램으로 쓰기
#실행: python tts_web.py            (프로그램 창으로 열림)
#      python tts_web.py --server   (창 없이 서버만, 브라우저에서 http://127.0.0.1:5000 으로 확인)
#화면은 templates/index.html, static/style.css, static/app.js
#창은 pywebview, 안쪽 서버는 Flask

import base64
import io
import os
import re
import sys
import threading
import wave

#exe(콘솔 없음)로 실행하면 print할 곳이 없어서 에러 나는 거 방지
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True   #html 고치면 새로고침만 해도 반영

제목 = '너의 목소리가 사인파로 들려'
최대글자 = 200
잠금 = threading.Lock()   #합성은 한 번에 하나씩

tts = None   #불러오는 데 몇 초 걸려서 불러오기()에서 채움


def 불러오기():
    global tts, First, Second, Third
    import tts as 모듈   #Kiwi 로딩 때문에 몇 초 걸림
    from hangul import First, Second, Third
    tts = 모듈


def 글자로(음절):
    if 음절['한글아님'] is not None:
        return 음절['한글아님']
    return chr(0xAC00 + (First.index(음절['초']) * 21 + Second.index(음절['중'])) * 28 + Third.index(음절['종']))


def wav로(소리):
    #tts.저장이랑 같은 형식인데 파일 대신 메모리에 씀
    버퍼 = io.BytesIO()
    with wave.open(버퍼, 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(tts.샘플레이트)
        f.writeframes(소리.tobytes())
    return 버퍼.getvalue()


@app.route('/')
def index():
    #창으로 열 때는 ?app=1 이 붙음 -> 바깥 파란 배경 없이 창에 꽉 차게
    return render_template('index.html', max_len=최대글자, title=제목, app_mode=request.args.get('app') == '1')


@app.route('/api/synth', methods=['POST'])
def synth():
    data = request.get_json(silent=True) or {}
    문장 = ' '.join(str(data.get('text', '')).split())   #줄바꿈, 여러 칸 띄어쓰기는 한 칸으로

    if not 문장:
        return jsonify(error='문장을 입력해 주세요.'), 400
    if len(문장) > 최대글자:
        return jsonify(error=f'{최대글자}자까지만 넣을 수 있어요.'), 400

    try:
        with 잠금:
            음절들 = tts.음운변동(문장)
            소리 = tts.합성(문장)
    except Exception as e:
        return jsonify(error=f'합성하다가 오류가 났어요: {e}'), 500

    발음 = ''
    for 음절 in 음절들:
        발음 += 글자로(음절)
        if 음절['어절끝']:
            발음 += ' '

    #윈도우 파일이름에 못 쓰는 글자 빼기 (끝에 오는 . 도 안 됨)
    파일이름 = re.sub(r'[\\/:*?"<>|]', '', tts.파일이름만들기(문장)).strip(' .') or 'output'

    return jsonify(
        pron=발음.strip(),
        filename=파일이름,
        wav=base64.b64encode(wav로(소리)).decode() if len(소리) else None,
    )


#----- 창 -----

로딩화면 = '''<!doctype html><meta charset="utf-8">
<body style="margin:0;height:100vh;display:grid;place-items:center;
  font:14px 'Segoe UI','Malgun Gothic',sans-serif;color:#fff;
  background:linear-gradient(160deg,#0b4fa0,#1d7fd1 45%,#0d5db5 70%,#08386f)">
<div style="text-align:center;text-shadow:0 1px 3px rgba(0,0,0,.5)">불러오는 중...</div>'''


class 창버튼:
    #index.html의 최소화/최대화/닫기 버튼이 JS에서 부르는 함수들
    #(pywebview가 _로 시작하는 건 JS에 안 넘김. 창 객체를 그냥 넣으면 그것까지 넘기려다 꼬임)
    def __init__(self):
        self._창 = None
        self._최대화됨 = False

    def minimize(self):
        self._창.minimize()

    def toggle_maximize(self):
        if self._최대화됨:
            self._창.restore()
        else:
            self._창.maximize()
        self._최대화됨 = not self._최대화됨

    def close(self):
        self._창.destroy()


def 창으로실행():
    import webview
    from werkzeug.serving import make_server

    버튼 = 창버튼()
    창 = webview.create_window(
        제목, html=로딩화면, js_api=버튼,
        width=620, height=440, min_size=(380, 360),
        frameless=True, easy_drag=False,   #테두리는 html에서 직접 그림, 끌기는 제목줄만
        background_color='#0d5db5',
    )
    버튼._창 = 창

    def 시작():
        불러오기()
        서버 = make_server('127.0.0.1', 0, app, threaded=True)   #포트 0 = 비어 있는 아무 포트 (두 번 켜도 안 겹침)
        threading.Thread(target=서버.serve_forever, daemon=True).start()
        창.load_url(f'http://127.0.0.1:{서버.server_port}/?app=1')

    webview.start(시작)   #창 닫으면 여기서 끝남
    os._exit(0)           #그냥 두면 뒷정리하느라 몇 초 동안 프로세스가 남아 있어서 바로 끔


if __name__ == '__main__':
    if '--server' in sys.argv:
        print('불러오는 중...')
        불러오기()
        print('http://127.0.0.1:5000 에서 실행 중 (끄려면 Ctrl+C)')
        app.run(port=5000)
    else:
        창으로실행()
