/**
 * order_button.js
 *
 * Скрипт для анимации кнопки .order.
 * При клике добавляется класс .animate на 10 секунд, запуская CSS-анимацию "доставки".
 */

document.addEventListener('DOMContentLoaded', function() {
    const orderButton = document.querySelector('.order');
    if (orderButton) {
        orderButton.addEventListener('click', function() {
            if (!orderButton.classList.contains('animate')) {
                orderButton.classList.add('animate');
                setTimeout(() => {
                    orderButton.classList.remove('animate');
                }, 10000);
            }
        });
    }
});