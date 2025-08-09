document.addEventListener('DOMContentLoaded', () => {
  const yearSpan = document.getElementById('y');
  if (yearSpan) yearSpan.textContent = new Date().getFullYear();

  const form = document.getElementById('fetchForm');
  const urlInput = document.getElementById('urlInput');
  const hint = document.getElementById('hint');
  const heroState = document.getElementById('heroState');
  const result = document.getElementById('result');
  const thumb = document.getElementById('thumb');
  const title = document.getElementById('title');
  const uploader = document.getElementById('uploader');
  const formatsWrap = document.getElementById('formats');
  const topbar = document.getElementById('topbar');
  const spinner = document.getElementById('spinner');
  const skeleton = document.getElementById('skeleton');

  function setHeroState(text, busy = false) {
    heroState.querySelector('span').textContent = text;
    heroState.querySelector('.pulse').style.background = busy ? '#ffd166' : 'var(--accent)';
    if (spinner) spinner.classList.toggle('hidden', !busy);
  }

  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return '';
    const units = ['B','KB','MB','GB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
    return `${bytes.toFixed(1)} ${units[i]}`;
  }

  function renderFormats(videoUrl, formats) {
    formatsWrap.innerHTML = '';
    formats.forEach((f, idx) => {
      const a = document.createElement('a');
      a.className = 'format';
      a.href = `/download?url=${encodeURIComponent(videoUrl)}&format_id=${encodeURIComponent(f.format_id)}`;
      a.setAttribute('download', '');
      a.style.animation = `fadeIn .3s ease ${idx * 0.03}s both`;
      a.innerHTML = `
        <div class="info">
          <span class="top">${f.quality} • ${f.kind}${f.ext ? ' • ' + f.ext : ''}</span>
          <span class="sub">${f.size_hint ? f.size_hint : (f.filesize ? formatBytes(f.filesize) : '')}</span>
        </div>
        <button class="btn btn--soft">Скачать</button>
      `;
      formatsWrap.appendChild(a);
    });
  }

  const style = document.createElement('style');
  style.textContent = `@keyframes fadeIn{from{opacity:0; transform:translateY(6px)} to{opacity:1; transform:translateY(0)}}`;
  document.head.appendChild(style);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;

    const contentHead = thumb.closest('.video-head');

    // UI busy state on
    setHeroState('Анализируем видео…', true);
    if (topbar) topbar.classList.remove('hidden');
    if (skeleton) skeleton.classList.remove('hidden');
    if (contentHead) contentHead.classList.add('hidden');
    if (formatsWrap) formatsWrap.classList.add('hidden');
    result.classList.remove('hidden');
    hint.textContent = '';
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.setAttribute('disabled', 'true');

    try {
      const res = await fetch('/api/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Ошибка запроса');

      title.textContent = data.title || 'Без названия';
      uploader.textContent = data.uploader || '';
      thumb.src = data.thumbnail || '';
      renderFormats(url, data.formats || []);

      if (skeleton) skeleton.classList.add('hidden');
      if (contentHead) contentHead.classList.remove('hidden');
      if (formatsWrap) formatsWrap.classList.remove('hidden');
      setHeroState('Готово');
    } catch (err) {
      console.error(err);
      setHeroState('Ошибка');
      if (skeleton) skeleton.classList.add('hidden');
      hint.textContent = 'Не удалось получить данные. Проверьте ссылку и попробуйте снова.';
    } finally {
      if (topbar) topbar.classList.add('hidden');
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.removeAttribute('disabled');
    }
  });
}); 