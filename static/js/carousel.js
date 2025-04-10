document.addEventListener('DOMContentLoaded', function() {
    const track = document.querySelector('.carousel-track');
    const slides = Array.from(document.querySelectorAll('.carousel-slide'));
    
    // Клонируем слайды для бесшовности
    const cloneSlides = slides.map(slide => slide.cloneNode(true));
    cloneSlides.forEach(clone => track.appendChild(clone));
    
    let currentPosition = 0;
    const slideWidth = slides[0].offsetWidth + 60; // width + gap
    const animationSpeed = 0.5; // px/ms
    
    function animate() {
        currentPosition -= animationSpeed;
        
        // Возвращаем в начало при достижении конца
        if (currentPosition <= -slideWidth * slides.length) {
            currentPosition = 0;
            track.style.transition = 'none';
            track.style.transform = `translateX(${currentPosition}px)`;
            // Принудительный reflow
            void track.offsetWidth;
        }
        
        track.style.transition = 'transform 0.1s linear';
        track.style.transform = `translateX(${currentPosition}px)`;
        
        requestAnimationFrame(animate);
    }
    
    // Запускаем анимацию
    animate();
    
    // Пауза при наведении
    track.addEventListener('mouseenter', () => {
        animationSpeed = 0;
    });
    
    track.addEventListener('mouseleave', () => {
        animationSpeed = 0.5;
    });
});