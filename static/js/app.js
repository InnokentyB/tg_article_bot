// Базовый JavaScript для веб-админки
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация Bootstrap компонентов
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Обработка модальных окон
    var modals = document.querySelectorAll('.modal');
    modals.forEach(function(modal) {
        modal.addEventListener('show.bs.modal', function (event) {
            console.log('Modal opening:', modal.id);
        });
    });

    // Обработка форм
    var forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Обновление времени
    function updateTime() {
        var now = new Date();
        var timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = now.toLocaleString('ru-RU');
        }
    }
    
    updateTime();
    setInterval(updateTime, 1000);
});
