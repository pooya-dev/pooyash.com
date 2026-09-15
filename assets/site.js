(() => {
  const root = document.getElementById('ps-concept');
  root.querySelectorAll('[data-filter]').forEach(button => {
    button.addEventListener('click', () => {
      root.querySelectorAll('[data-filter]').forEach(other => other.setAttribute('aria-pressed', String(other === button)));
      root.querySelectorAll('[data-kind]').forEach(entry => {
        entry.hidden = button.dataset.filter !== 'all' && entry.dataset.kind !== button.dataset.filter;
      });
    });
  });
  const save = document.getElementById('ps-save');
  const size = document.getElementById('ps-size');
  if (!save || !size) return;
  const key = 'saved:' + location.pathname;
  let saved = false;
  try { saved = sessionStorage.getItem(key) === 'true'; } catch (_) {}
  const update = () => {
    save.textContent = saved ? 'Saved for this visit' : 'Save for this visit';
    save.setAttribute('aria-pressed', String(saved));
  };
  update();
  save.addEventListener('click', () => {
    saved = !saved;
    try { sessionStorage.setItem(key, String(saved)); } catch (_) {}
    update();
  });
  size.addEventListener('click', () => {
    const large = root.querySelector('.ps-reader').classList.toggle('ps-reading-large');
    size.setAttribute('aria-pressed', String(large));
  });
})();
