# exe 만드는 설정 (PyInstaller)
# 빌드: python -m PyInstaller SEETHESING.spec --noconfirm
#   (PyInstaller 6.22 이상 필요. 옛날 버전은 numpy 2.x / scipy를 제대로 못 묶음)
# 결과: dist/SEETHESING/ 폴더  (안의 SEETHESING.exe 더블클릭하면 프로그램 창이 뜸)
#       dist/SEETHESING.zip       (위 폴더 압축한 것, 친구들한테는 이거 보내면 됨)
#
# exe 하나로 묶으면(onefile) 켤 때마다 140MB를 임시 폴더에 풀어서 6~7초 걸림
# 폴더째로 두면 풀 필요가 없어서 금방 뜸

import shutil

from PyInstaller.utils.hooks import collect_all

datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    # 합성할 때 파일에서 직접 읽는 것들 (원래 폴더 구조 그대로 넣어야 경로가 맞음)
    ('c1/AppendCV/assets-c/*.wav', 'c1/AppendCV/assets-c'),
    ('c1/AppendCV/stops_v3/stops_v3.py', 'c1/AppendCV/stops_v3'),   # appendstop.py가 소스를 읽어서 씀
    ('c2/CodaSynthesizer/*.wav', 'c2/CodaSynthesizer'),
]
binaries = []
hiddenimports = []

# 형태소 분석기 모델 (100MB 정도)
for pkg in ('kiwipiepy', 'kiwipiepy_model'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h


a = Analysis(
    ['tts_web.py'],
    pathex=['음운 변동'],   # tts.py가 실행 중에 sys.path에 넣는 폴더라 미리 알려줘야 함
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['tkinter', 'matplotlib', 'pandas', 'IPython', 'PyQt5', 'PySide6'],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,   # 나머지 파일은 exe 안에 안 넣고 옆 폴더(_internal)에 둠
    name='SEETHESING',
    console=False,   # 검은 콘솔 창 안 띄움 (창 X 누르면 꺼짐)
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name='SEETHESING', upx=False)

# build/ 폴더에도 SEETHESING.exe가 생기는데, 옆에 _internal이 없어서 실행하면
# "Failed to load Python DLL" 에러가 남. 헷갈리지 않게 빌드 끝나면 지움
from PyInstaller import config
shutil.rmtree(config.CONF['workpath'], ignore_errors=True)

with open(f'{DISTPATH}/SEETHESING/README.txt', 'w', encoding='utf-8-sig') as f:
    f.write('너의 목소리가 사인파로 들려\n'
            '\n'
            '1. zip 압축을 먼저 풀어 주세요. (zip 안에서 바로 실행하면 안 돼요)\n'
            '2. 이 폴더 안의 SEETHESING.exe를 더블클릭하면 실행돼요.\n'
            '3. exe만 따로 꺼내지 말고 _internal 폴더와 같이 두세요.\n'
            '   바탕화면에서 켜고 싶으면 exe를 오른쪽 클릭 > 바로 가기 만들기로 바로가기를 옮기세요.\n'
            '\n'
            '처음 실행할 때 "Windows의 PC 보호" 창이 뜨면 추가 정보 > 실행을 누르세요.\n')

shutil.make_archive(f'{DISTPATH}/SEETHESING', 'zip', DISTPATH, 'SEETHESING')
