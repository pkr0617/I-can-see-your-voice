#테스트 케이스(cases.json) 전부 돌려서 틀린 것만 출력
#실행: python tests/run_tests.py        (음운 변동 폴더에서)
#      python tests/run_tests.py -a     (맞은 것도 전부 출력)
#main.py는 input()으로 문장을 받는 구조라서, input과 print를 바꿔치기해서 그대로 실행함
import builtins
import contextlib
import io
import json
import os
import re
import sys

import kiwipiepy

폴더 = os.path.dirname(os.path.abspath(__file__))
음운폴더 = os.path.dirname(폴더)
sys.path.insert(0, 음운폴더)
from hangul import First, Second, Third

#Kiwi를 매번 새로 만들면 느려서 하나만 만들어 재사용
_kiwi = kiwipiepy.Kiwi()
kiwipiepy.Kiwi = lambda *a, **k: _kiwi

main코드 = compile(open(os.path.join(음운폴더, 'main.py'), encoding='utf-8').read(), 'main.py', 'exec')


def 발음(문장):
    원래input = builtins.input
    builtins.input = lambda *a: 문장
    try:
        공간 = {'__name__': 'main'}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(main코드, 공간)
    finally:
        builtins.input = 원래input
    결과 = ''
    for 음절 in 공간['음절들']:
        if 음절['한글아님'] is not None:
            결과 += 음절['한글아님']
        else:
            결과 += chr(0xAC00 + (First.index(음절['초']) * 21 + Second.index(음절['중'])) * 28 + Third.index(음절['종']))
        if 음절['어절끝']:
            결과 += ' '
    return 결과.strip()


def 정리(s):
    #띄어쓰기·문장부호·장음표시(:)는 비교에서 뺌
    return re.sub(r'[\s.,!?:~]', '', s)


def main():
    전부출력 = '-a' in sys.argv
    케이스들 = json.load(open(os.path.join(폴더, 'cases.json'), encoding='utf-8'))
    틀림 = 0
    for c in 케이스들:
        결과 = 발음(c['input'])
        맞음 = 정리(결과) in [정리(a) for a in c['answers']]
        if not 맞음:
            틀림 += 1
        if 전부출력 or not 맞음:
            print(('O' if 맞음 else 'X'), f"[{c['sheet']}] {c['input']} -> {결과}   정답: {' / '.join(c['answers'])}")
    print(f'\n{len(케이스들) - 틀림}/{len(케이스들)} 통과')


if __name__ == '__main__':
    main()
