const $ = (id) => document.getElementById(id);

const text = $('text');
const makeBtn = $('make');
const statusText = $('status');
const audio = $('audio');
const playBtn = $('play');
const seek = $('seek');
const bar = seek.firstElementChild;

let audioUrl = null;


text.addEventListener('input', () => {
  $('count').textContent = text.value.length;
});

text.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.ctrlKey) {
    e.preventDefault();
    make();
  }
});

makeBtn.addEventListener('click', make);

// 버튼에 밑줄 친 글자: Alt+M 만들기, Alt+S 저장
document.addEventListener('keydown', (e) => {
  if (!e.altKey) return;
  if (e.key === 'm' || e.key === 'M') {
    e.preventDefault();
    make();
  } else if ((e.key === 's' || e.key === 'S') && audioUrl) {
    e.preventDefault();
    $('save').click();
  }
});


function setStatus(msg, isError = false) {
  statusText.textContent = msg;
  statusText.classList.toggle('error', isError);
}

async function make() {
  const sentence = text.value.trim();
  if (!sentence) return text.focus();
  if (makeBtn.disabled) return;

  makeBtn.disabled = true;
  setStatus('발음 파일을 만드는 중...');

  try {
    const res = await fetch('/api/synth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: sentence }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    showResult(data);
    setStatus('');
  } catch (err) {
    if (err.message === 'Failed to fetch') {
      setStatus('서버에 연결할 수 없어요. tts_web.py가 켜져 있는지 확인해 주세요.', true);
    } else {
      setStatus(err.message || '알 수 없는 오류가 났어요.', true);
    }
  }

  makeBtn.disabled = false;
}

function showResult(data) {
  $('result').hidden = false;
  $('pron').textContent = data.pron;

  audio.pause();
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = null;

  $('player').hidden = !data.wav;
  $('empty').hidden = !!data.wav;
  if (!data.wav) return;

  const bytes = Uint8Array.from(atob(data.wav), (c) => c.charCodeAt(0));
  audioUrl = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }));
  audio.src = audioUrl;

  const save = $('save');
  save.href = audioUrl;
  save.download = data.filename + '.wav';

  audio.play().catch(() => {});  // 자동재생 막히면 그냥 둠
}


// ---- 재생 ----

function fmt(sec) {
  sec = Math.floor(sec || 0);
  return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0');
}

function update() {
  const ratio = audio.duration ? audio.currentTime / audio.duration : 0;
  bar.style.width = ratio * 100 + '%';
  $('time').textContent = fmt(audio.currentTime) + ' / ' + fmt(audio.duration);

  if (!audio.paused) requestAnimationFrame(update);
}

playBtn.addEventListener('click', () => {
  if (audio.paused) audio.play();
  else audio.pause();
});

audio.addEventListener('play', () => {
  playBtn.classList.add('playing');
  playBtn.setAttribute('aria-label', '일시정지');
  update();
});

audio.addEventListener('pause', () => {
  playBtn.classList.remove('playing');
  playBtn.setAttribute('aria-label', '재생');
  update();
});

audio.addEventListener('ended', () => {
  audio.currentTime = 0;
  update();
});

audio.addEventListener('loadedmetadata', update);

seek.addEventListener('pointerdown', (e) => {
  if (!audio.duration) return;
  const rect = seek.getBoundingClientRect();
  const ratio = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
  audio.currentTime = ratio * audio.duration;
  update();
});


// ---- 창 버튼 (프로그램 창으로 열었을 때만, 브라우저에서는 그냥 모양) ----

window.addEventListener('pywebviewready', () => {
  const api = window.pywebview.api;
  $('win-min').addEventListener('click', () => api.minimize());
  $('win-max').addEventListener('click', () => api.toggle_maximize());
  $('win-close').addEventListener('click', () => api.close());
  document.querySelector('.titlebar h1').addEventListener('dblclick', () => api.toggle_maximize());
});
