window.FieldStation = {
  copies: new WeakMap(),
  show(control, targetId) {
    let copy = this.copies.get(control);
    if (!copy) {
      const target = document.getElementById(targetId);
      if (!target) throw new Error('Declared station sheet is absent');
      copy = target.cloneNode(true);
      copy.removeAttribute('id');
      control.parentElement.appendChild(copy);
      this.copies.set(control, copy);
    }
    copy.style.display = 'block';
  },
  flip(control) {
    const group = control.nextElementSibling;
    const before = group.style.display;
    if (before !== 'none' && before !== 'block') return;
    const show = before === 'none';
    group.style.display = show ? 'block' : 'none';
    control.textContent = control.textContent.replace(show ? /^Open / : /^Close /, show ? 'Close ' : 'Open ');
  },
  close(control) {
    control.closest('.specimen-sheet').style.display = 'none';
  }
};
