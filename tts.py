#문장 넣으면 음운 변동 -> 음성 합성 -> wav 저장까지 한번에 해주는 프로그램
#실행: python tts.py        (문장 입력받음, <문장>.wav로 저장)
#      python tts.py 안녕    (문장 입력받음, 안녕.wav로 저장)
#기존 모듈 코드는 안 고치고 불러다 쓰기만 함
#
#[변경 요약] 다른 프로그램(tts_gui.py 등)에서 불러 쓸 수 있게 함수로 나눔
#  - 합성(문장)          : 문장 -> 소리 배열(np.int16, 스테레오)을 돌려줌  (예전 1~2번 부분)
#  - 저장(소리, 파일이름) : 소리를 wav로 저장                             (예전 3번 부분)
#  - 파일이름만들기(문장) : 문장으로 파일 이름 만들기                       (예전 argv/파일이름 부분)
#  - python tts.py 로 직접 실행하면 예전과 똑같이 동작함 (맨 아래 __main__)
#  - 억양/합성 계산 코드 자체는 그대로, 함수 안으로 들어가면서 들여쓰기만 한 칸 들어감
#  - 고친 버그 1개: 문장이 '.' 같은 문장부호로 끝나면 억양 만들기에서 IndexError 나던 것 (아래 [버그수정])

import os
import sys
import types
import numpy as np

폴더 = os.path.dirname(os.path.abspath(__file__))

#설정 (단위는 초, Hz)
피치 = (260, 250)          #보통 음절 피치
H피치 = (275, 265)          #높을 때
L피치 = (200, 190)          #낮을 때
마지막피치 = (250, 200)    #문장 마지막 음절 피치 (끝을 내려줌)
모음길이 = 0.18             #모음 지속시간 (append의 duration)
띄어쓰기쉼 = 0.12          #띄어쓰기에서 쉬는 시간
막힘시간 = 0.03            #어절 안에서 받침 ㄱ ㄷ ㅂ 뒤에 막혀 있는 시간
무음기준 = -50             #음절 끝에서 이것보다 작은 소리(dB)는 무음으로 보고 잘라냄
샘플레이트 = 44100
음절간전환시간 = 0.03


from v.VowelSynthesizer import generator
from c1.AppendCV import appendcvc, appendstop
appendcvc.path = os.path.join(
    os.path.dirname(appendcvc.__file__), 'assets-c'
) + os.sep




# 1. 음운 변동
sys.path.insert(0, os.path.join(폴더, '음운 변동'))
#[변경] 예전 코드:
#   import main
#   from main import inputed_sentence
#   음절들 = main.음절들
#  -> import하는 순간 input()이 실행되던 구조라서, 이제는 함수만 가져오고 합성() 안에서 부름
from main import 음운변동
from hangul import First, Second, Third


#[변경] 예전에는 여기서 바로 sys.argv / inputed_sentence()로 파일이름을 정했음
#  -> 파일이름만들기()로 옮기고, 실제 사용은 맨 아래 __main__에서
def 파일이름만들기(문장):
    파일이름 = 문장

    #파일이름 너무 길어서 파일 생성이 안되는 경우 방지
    if len(파일이름) >= 50:
        파일이름 = 파일이름[:50] + "..."

    return 파일이름



#2. 음성 합성
#종성 붙은 음절은 뒤에 0.27초짜리 꼬리(거의 무음)가 붙어 나와서, 그대로 이으면 끊겨 들림 (었다 -> 었/다)
#그래서 끝에 있는 무음은 잘라냄
def 끝무음자르기(소리):
    크기 = np.abs(소리[::2].astype(float))
    if 크기.max() == 0:
        return 소리
    마지막 = np.nonzero(크기 > 크기.max() * 10 ** (무음기준 / 20))[0][-1]
    return 소리[:(마지막 + 1) * 2]


#[변경] 예전에는 모듈 최상단에서 바로 실행되던 1~2번 부분 (음절 고르기, 억양, 합성, 이어붙이기)
#  -> 합성(문장) 함수 안으로 옮기고, 마지막에 결과를 돌려줌
def 합성(문장):
    음절들 = 음운변동(문장)   #[변경] 예전: 음절들 = main.음절들

    한글음절 = []
    for 음절 in 음절들:
        if 음절['한글아님'] is None:   #한글 아닌 글자(문장부호 등)는 빼고
            한글음절.append(음절)

    #[변경] 한글이 하나도 없으면(빈 문장, 문장부호만) 아래 pitches.pop(-1)에서 에러 나서 빈 소리를 돌려줌
    if len(한글음절) == 0:
        return np.zeros(0, dtype=np.int16)

    ############ 억양 만들기 ##############
    pointer = 0 # 아이터레이터?

    pitches = [] # 여기다가 튜플 저장할거임

    강자음과마찰음 = ['ㄲ', 'ㄸ', 'ㅃ', 'ㅆ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ', 'ㅅ']

    while pointer < len(한글음절):
        #덩어리 하나 떼낼거임
        l = pointer
        #[버그수정] 예전: while 한글음절[pointer]['어절끝'] is False:
        #  '안녕하세요.'처럼 문장부호로 끝나면 '.'가 어절끝을 가져가서 마지막 한글 음절은 어절끝이 False
        #  -> 리스트 끝을 넘어가서 IndexError. 마지막 음절에서는 멈추게 함
        while pointer < len(한글음절) - 1 and 한글음절[pointer]['어절끝'] is False:
            pointer += 1
        pointer += 1

        chunkSize = pointer - l

        #이제부터 본격적으로 ㄱㄱ
        for i in range(l, l + chunkSize):
            #어우 헷갈려 걍 절댓값으로 ㄱㄱ 그 어절에서 몇번째 인덱스인지
            absi = i - l

            if absi == 0: #일단 다 공통되는건 첫음절이 강자음 or 마찰음이면 H 아니면 L이니 이거부터 해줌
                if 한글음절[i]['초'] in 강자음과마찰음:
                    pitches.append(H피치)
                else:
                    pitches.append(L피치)

                continue

            if chunkSize == 4:
                pitches.append(H피치)
                pitches.append(L피치)
                pitches.append(H피치)

                break

            if chunkSize >= 5:
                pitches.append(H피치)
                for j in range(chunkSize-4):
                    pitches.append(피치)
                pitches.append(L피치)
                pitches.append(마지막피치)

                break

            else:
                for j in range(chunkSize-2):
                    pitches.append(피치)
                pitches.append(피치)

                break

        pointer = l + chunkSize


    pitches.pop(-1)
    pitches.append(마지막피치)

    ####################################

    조각들 = []
    for i in range(len(한글음절)):
        음절 = 한글음절[i]
        초 = 음절['초']
        중 = 음절['중']
        종 = 음절['종']
        마지막음절 = (i == len(한글음절) - 1)

        #아직 소리 파일 없는 초성은 빼고 만듦
        if 초 not in appendcvc.overlapsec and 초 not in appendstop.filename:
            print(f"초성 '{초}'는 아직 없어서 빼고 만듭니다")
            초 = ''

        #모음 사이 평음인지: 같은 어절 안에서 앞 음절이 모음이나 ㄴ ㅁ ㅇ ㄹ 받침으로 끝나면 (해도, 안개)
        모음사이 = False
        if i > 0:
            앞 = 한글음절[i - 1]
            if not 앞['어절끝'] and 앞['종'] in ['', 'ㄴ', 'ㅁ', 'ㅇ', 'ㄹ']:
                모음사이 = True


        # # 피치 적용 부분
        # if 마지막음절:
        #     p = 마지막피치
        # else:
        #     p = 피치

        # 진짜 오디오 생성 부분
        소리 = appendcvc.append(초, 중, 종, pitches[i], 모음길이, medial=모음사이).astype(np.int16)
        조각들.append(끝무음자르기(소리))

        #받침 ㄱ ㄷ ㅂ 뒤에는 막힘 시간만큼 무음
        if 종 in ['ㄱ', 'ㄷ', 'ㅂ'] and not 음절['어절끝'] and not 마지막음절:
            조각들.append(np.zeros(int(샘플레이트 * 막힘시간) * 2, dtype=np.int16))   #스테레오라 *2

        #띄어쓰기에서 쉼
        if 음절['어절끝'] and not 마지막음절:
            조각들.append(np.zeros(int(샘플레이트 * 띄어쓰기쉼) * 2, dtype=np.int16))


    if len(조각들) > 0:
        결과 = 조각들[0]
        for i in range(1, len(조각들)):
            결과 = appendcvc.crossfade(결과, 조각들[i], 음절간전환시간)

    else:
        결과 = np.zeros(0, dtype=np.int16)

    return 결과   #[변경] 예전에는 바로 아래에서 저장까지 했음



#========== 3. 저장 ==========
#[변경] 예전에는 최상단에서 바로 저장하던 부분 -> 저장() 함수로 분리
#  파일이름에 .wav가 붙어 있어도 되고 없어도 됨. 저장한 경로(.wav 포함)를 돌려줌
def 저장(결과, 파일이름):
    if 파일이름.endswith('.wav'):
        파일이름 = 파일이름[:-4]
    generator.write_wav(파일이름, 결과, sample_rate=샘플레이트)
    return 파일이름 + '.wav'


#[변경] 예전 모듈 최상단 코드가 하던 일(입력 -> 합성 -> 저장 -> 파일이름 출력)을 그대로 여기서 함
#  python tts.py 로 직접 실행할 때만 동작하고, import할 때는 실행 안 됨
if __name__ == '__main__':
    문장 = input()

    if len(sys.argv) > 1:
        파일이름 = sys.argv[1]
    else:
        #파일이름 = 'output'
        파일이름 = 파일이름만들기(문장)

    결과 = 합성(문장)
    파일이름 = 저장(결과, 파일이름)
    print(f"{파일이름}")
