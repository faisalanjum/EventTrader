window.MuseumCards = {
  last: null,
  reveal(trigger, targetId) {
    if (this.last) this.last.remove();
    const target = document.getElementById(targetId);
    if (!target) throw new Error('Referenced museum note is absent');
    const copy = target.cloneNode(true);
    copy.removeAttribute('id');
    copy.style.display = 'block';
    trigger.closest('section').appendChild(copy);
    this.last = copy;
  }
};
