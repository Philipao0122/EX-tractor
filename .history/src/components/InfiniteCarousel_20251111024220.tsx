import React, { useState, useEffect, useRef } from 'react';

interface InfiniteCarouselProps {
  images: { src: string; alt?: string }[];
  height?: number;
  gap?: number;
  speed?: number;
  direction?: 'left' | 'right';
  pauseOnHover?: boolean;
  rounded?: boolean;
}

export const InfiniteCarousel: React.FC<InfiniteCarouselProps> = ({
  images,
  height = 160,
  gap = 8,
  speed = 18,
  direction = 'left',
  pauseOnHover = true,
  rounded = true,
}) => {
  const [isPaused, setIsPaused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [trackWidth, setTrackWidth] = useState(0);
  const [isReducedMotion, setIsReducedMotion] = useState(false);

  // Check for reduced motion preference
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setIsReducedMotion(mediaQuery.matches);

    const handleChange = () => setIsReducedMotion(mediaQuery.matches);
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // Calculate track width based on container and items
  useEffect(() => {
    if (!trackRef.current || !containerRef.current) return;

    const updateTrackWidth = () => {
      if (!trackRef.current || !containerRef.current) return;
      
      const containerWidth = containerRef.current.offsetWidth;
      const itemCount = trackRef.current.children.length;
      const itemWidth = (trackRef.current.children[0] as HTMLElement)?.offsetWidth || 0;
      
      // Calculate total track width (original + duplicate for seamless loop)
      const calculatedWidth = (itemWidth + gap) * itemCount * 2 + gap;
      setTrackWidth(calculatedWidth > containerWidth * 2 ? calculatedWidth : containerWidth * 2);
    };

    // Initial calculation
    updateTrackWidth();

    // Recalculate on window resize
    const resizeObserver = new ResizeObserver(updateTrackWidth);
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [images, gap]);

  // Animation effect
  useEffect(() => {
    if (isReducedMotion || isPaused || !trackRef.current) return;

    const track = trackRef.current;
    let animationFrame: number;
    let startTime: number | null = null;
    const pixelsPerSecond = (trackWidth / 26) / speed;
    let position = 0;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      
      const elapsed = (timestamp - startTime) / 1000; // Convert to seconds
      position = (elapsed * pixelsPerSecond) % (trackWidth / 2);
      
      if (direction === 'left') {
        track.style.transform = `translateX(-${position}px)`;
      } else {
        track.style.transform = `translateX(${position}px)`;
      }
      
      animationFrame = requestAnimationFrame(animate);
    };

    animationFrame = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animationFrame);
    };
  }, [isPaused, trackWidth, speed, direction, isReducedMotion]);

  // Duplicate images for seamless loop
  const duplicatedImages = [...images, ...images];

  if (images.length === 0) return null;

  return (
    <div 
      className="relative w-full overflow-hidden"
      style={{
        height: `${height}px`,
        maskImage: 'linear-gradient(90deg, transparent 0%, #000 5%, #000 95%, transparent 100%)',
        WebkitMaskImage: 'linear-gradient(90deg, transparent 0%, #000 5%, #000 95%, transparent 100%)',
      }}
      ref={containerRef}
      onMouseEnter={() => pauseOnHover && setIsPaused(true)}
      onMouseLeave={() => pauseOnHover && setIsPaused(false)}
      onFocus={() => pauseOnHover && setIsPaused(true)}
      onBlur={() => pauseOnHover && setIsPaused(false)}
      role="list"
      aria-label="Carrusel de imágenes"
    >
      <div 
        ref={trackRef}
        className="absolute top-0 left-0 h-full flex items-center will-change-transform"
        style={{
          gap: `${gap}px`,
          width: `${trackWidth}px`,
          padding: `0 ${gap}px`,
        }}
      >
        {duplicatedImages.map((img, index) => (
          <div 
            key={`${index}-${img.src}`}
            className="flex-shrink-0 h-full flex items-center justify-center"
            role="listitem"
            aria-label={`Imagen ${index % images.length + 1} de ${images.length}`}
          >
            <img
              src={img.src}
              alt={img.alt || ''}
              className={`h-full w-auto object-cover ${rounded ? 'rounded' : ''}`}
              style={{
                maxWidth: 'none',
                height: '100%',
                aspectRatio: 'auto',
              }}
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default InfiniteCarousel;
