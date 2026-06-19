document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-copy]').forEach(el => {
        el.addEventListener('click', function() {
            const target = document.getElementById(this.dataset.copy);
            if (target) {
                navigator.clipboard.writeText(target.textContent);
                const orig = this.textContent;
                this.textContent = 'Copied!';
                setTimeout(() => this.textContent = orig, 1500);
            }
        });
    });
});
