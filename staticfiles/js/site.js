document.querySelectorAll('[data-copy-link]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var url = btn.getAttribute('data-copy-link');
    var label = btn.querySelector('[data-copy-label]');
    navigator.clipboard.writeText(url).catch(function () {});
    if (!label) return;
    var original = label.textContent;
    label.textContent = 'Copied';
    setTimeout(function () { label.textContent = original; }, 1600);
  });
});
