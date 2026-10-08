// Deck navigation: ←/→ or PageUp/PageDown or space, N = speaker notes, F = fullscreen, T = light/dark.
// Add ?s=5 to the URL to open on slide 5 (1-based).
(function () {
  const slides = [...document.querySelectorAll('.slide')];
  const panel = document.querySelector('.notes-panel');
  const count = document.getElementById('count');
  let i = 0;
  const fromUrl = parseInt(new URLSearchParams(location.search).get('s'), 10);
  if (fromUrl) i = fromUrl - 1;
  else { try { i = +(sessionStorage.getItem('deck-slide') || 0); } catch (e) {} }

  function show(k) {
    i = Math.max(0, Math.min(slides.length - 1, k));
    slides.forEach((s, j) => s.classList.toggle('active', j === i));
    const notes = slides[i].querySelector('aside.notes');
    panel.innerHTML = notes ? notes.innerHTML : '';
    count.textContent = (i + 1) + ' / ' + slides.length;
    try { sessionStorage.setItem('deck-slide', i); } catch (e) {}
  }
  function fit() {
    const st = document.querySelector('.stage');
    const reserve = document.body.classList.contains('show-notes') ? 0.72 : 0.95;
    const s = Math.min(window.innerWidth * 0.96 / 1280, window.innerHeight * reserve / 720);
    st.style.transform = 'scale(' + s + ')';
    st.style.margin = ((720 * s - 720) / 2) + 'px ' + ((1280 * s - 1280) / 2) + 'px';
  }
  function toggleNotes() { document.body.classList.toggle('show-notes'); fit(); }
  function toggleTheme() {
    const r = document.documentElement;
    const dark = r.dataset.theme ? r.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    r.dataset.theme = dark ? 'light' : 'dark';
  }
  document.addEventListener('keydown', e => {
    if (['ArrowRight', 'PageDown', ' '].includes(e.key)) show(i + 1);
    if (['ArrowLeft', 'PageUp'].includes(e.key)) show(i - 1);
    if (e.key === 'n' || e.key === 'N') toggleNotes();
    if (e.key === 't' || e.key === 'T') toggleTheme();
    if (e.key === 'f' || e.key === 'F') document.documentElement.requestFullscreen?.();
  });
  document.getElementById('prev').onclick = () => show(i - 1);
  document.getElementById('next').onclick = () => show(i + 1);
  document.getElementById('toggleNotes').onclick = toggleNotes;
  document.getElementById('toggleTheme').onclick = toggleTheme;
  window.addEventListener('resize', fit);
  show(i); fit();
})();
