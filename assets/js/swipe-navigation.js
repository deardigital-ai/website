document.addEventListener('DOMContentLoaded', function() {
    let slides = document.querySelectorAll('.post-slide');
    let currentIndex = Array.from(slides).findIndex(slide => slide.classList.contains('active'));
    let startY = 0;
    let diffY = 0;
    let progressBar = document.querySelector('.progress-bar');

    function updateProgress() {
        const progress = ((currentIndex + 1) / slides.length) * 100;
        progressBar.style.width = `${progress}%`;
    }

    // Touch events
    document.addEventListener('touchstart', function(e) {
        startY = e.touches[0].clientY;
    });

    document.addEventListener('touchmove', function(e) {
        if (!startY) return;
        
        diffY = startY - e.touches[0].clientY;
        let currentSlide = slides[currentIndex];
        let nextSlide = slides[currentIndex + 1];
        let prevSlide = slides[currentIndex - 1];

        if (diffY > 0 && nextSlide) {
            currentSlide.style.transform = `translateY(${-diffY}px) scale(${1 - Math.abs(diffY) / 2000})`;
            nextSlide.style.transform = `translateY(calc(100% - ${diffY}px)) scale(${0.95 + Math.abs(diffY) / 2000})`;
        } else if (diffY < 0 && prevSlide) {
            currentSlide.style.transform = `translateY(${-diffY}px) scale(${1 - Math.abs(diffY) / 2000})`;
            prevSlide.style.transform = `translateY(calc(-100% - ${diffY}px)) scale(${0.95 + Math.abs(diffY) / 2000})`;
        }
    });

    document.addEventListener('touchend', function() {
        if (Math.abs(diffY) > 100) {
            if (diffY > 0 && currentIndex < slides.length - 1) {
                currentIndex++;
            } else if (diffY < 0 && currentIndex > 0) {
                currentIndex--;
            }
        }

        updateSlides();
        updateProgress();
        startY = 0;
        diffY = 0;
    });

    function updateSlides() {
        slides.forEach((slide, index) => {
            if (index === currentIndex) {
                slide.classList.add('active');
                slide.classList.remove('next', 'prev');
            } else if (index > currentIndex) {
                slide.classList.add('next');
                slide.classList.remove('active', 'prev');
            } else {
                slide.classList.add('prev');
                slide.classList.remove('active', 'next');
            }
            slide.style.transform = '';
        });
    }

    // Initialize progress
    updateProgress();
}); 