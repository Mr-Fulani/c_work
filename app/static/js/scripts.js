// app/static/js/scripts.js

document.addEventListener('DOMContentLoaded', function() {
    const toggleButtons = document.querySelectorAll('.toggle-details');
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const targetDiv = document.querySelector(targetId);
            if(targetDiv.classList.contains('d-none')) {
                targetDiv.classList.remove('d-none');
                this.textContent = 'Скрыть';
            } else {
                targetDiv.classList.add('d-none');
                this.textContent = 'Подробнее';
            }
        });
    });
});