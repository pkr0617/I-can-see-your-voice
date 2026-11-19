from hangul import *

첨가모음 = ['ㅣ', 'ㅑ', 'ㅕ', 'ㅛ', 'ㅠ']

def 니은첨가대상(앞, 뒤):
    """제29항: 합성어·파생어에서 앞 단어가 자음으로 끝나고 뒤 실질형태소가 이/야/여/요/유로 시작할 때"""
    if 앞['한글아님'] is not None or 뒤['한글아님'] is not None:
        return False
    if 앞['종'] == '':                  # 앞이 모음으로 끝나면 ㄴ이 붙지 않음 (아이, 여기)
        return False
    if 뒤['초'] != 'ㅇ' or 뒤['중'] not in 첨가모음:
        return False
    if 뒤['중'] == 'ㅣ' and 뒤['종'] == 'ㅆ':   # 맛있다·멋있다 (제15항 다만)
        return False
    if 뒤['첨가없음']:                  # 첫인상[처딘상]
        return False
    if 앞['어절끝']:
        return 어절사이_첨가(앞, 뒤)
    if not 앞['형태소끝'] or 앞['다음형식']:  # 뒤가 조사·어미·접미사(이 등)이면 적용하지 않음
        return False
    return True


def 어절사이_첨가(앞, 뒤):
    """제29항 붙임 2: 두 단어를 이어서 한 마디로 발음할 때 (먹는 약[멍는냑], 옷 입다[온닙따], 국민 윤리[궁민뉼리])"""
    앞품사 = 앞['현재품사']     # 앞 어절의 마지막 형태소
    뒤품사 = 뒤['시작품사']     # 뒤 어절의 첫 형태소
    명사 = ('NNG', 'NNP')
    #관형사형 + 한 글자 명사 (먹는 약, 어려운 일, 할 일 / 줄 이유는 X)
    if 앞품사.startswith('ETM') and 뒤품사 in 명사 and 뒤['시작길이'] == 1:
        return True
    #명사 + 명사 (국민 윤리, 직행 열차)
    if 앞품사 in 명사 and 뒤품사 in 명사:
        return True
    #한 글자 명사 + 동사 (옷 입다[온닙따] / 부엌문 열어, 못 이겨서는 X)
    if 앞품사 in 명사 and 뒤품사.startswith('VV') and 앞['어절음절수'] == 1:
        return True
    return False


def 니은첨가(음절들):
    for i in range(len(음절들) - 1):
        if 니은첨가대상(음절들[i], 음절들[i + 1]):
            음절들[i + 1]['초'] = 'ㄴ'
            음절들[i + 1]['첨가'] = True

    return 음절들
