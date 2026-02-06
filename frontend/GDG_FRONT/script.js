document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('bg-video');

    // Ensure video plays (some browsers block autoplay without interaction if not muted, but we are muted)
    if (video) {
        // Explicitly set muted to true to satisfy autoplay policies
        video.muted = true;

        const playPromise = video.play();

        if (playPromise !== undefined) {
            playPromise.then(_ => {
                console.log("Video started playing automatically");
            }).catch(error => {
                console.error("Video autoplay failed:", error);

                // Fallback: Show a play button or simple message if autoplay is blocked
                const message = document.createElement('div');
                message.style.position = 'fixed';
                message.style.bottom = '10px';
                message.style.left = '10px';
                message.style.color = 'white';
                message.style.zIndex = '1000';
                message.style.background = 'rgba(0,0,0,0.5)';
                message.style.padding = '5px';
                message.innerText = "Video Autoplay blocked. Click anywhere to play.";
                document.body.appendChild(message);

                document.addEventListener('click', () => {
                    video.play();
                    message.remove();
                }, { once: true });
            });
        }
    }

    // Add 3D tilt effect to the glass card
    const heroCard = document.querySelector('.hero');

    if (heroCard) {
        heroCard.addEventListener('mousemove', (e) => {
            const rect = heroCard.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = ((y - centerY) / centerY) * -10; // Max rotation deg
            const rotateY = ((x - centerX) / centerX) * 10;

            heroCard.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });

        heroCard.addEventListener('mouseleave', () => {
            heroCard.style.transform = 'perspective(1000px) rotateX(0) rotateY(0)';
            heroCard.style.transition = 'transform 0.5s ease';
        });

        heroCard.addEventListener('mouseenter', () => {
            heroCard.style.transition = 'none';
        });
    }
});

function exploreClick() {
    console.log("Explore button clicked");
    // Add navigation or smooth scroll logic here
    // For now, let's just do a cool scale effect on the button
    const btn = document.querySelector('.explore-btn');
    btn.style.transform = 'scale(0.95)';
    setTimeout(() => {
        btn.style.transform = 'scale(1)';
        window.location.href = "../index.html";
        // alert("Welcome to Peak Performers!");
    }, 150);
}
