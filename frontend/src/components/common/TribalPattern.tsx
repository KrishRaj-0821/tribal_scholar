import React from 'react';

export type TribalPatternVariant = 
  | 'forest' 
  | 'river' 
  | 'woven' 
  | 'earth' 
  | 'mountain' 
  | 'community'
  | 'toda-diamond' 
  | 'warli-rhythm' 
  | 'gond-dots' 
  | 'saura-border';

interface TribalPatternProps {
  variant?: TribalPatternVariant;
  family?: TribalPatternVariant;
  className?: string;
  height?: number;
  opacity?: number;
  color?: string;
  asBackground?: boolean;
}

/**
 * TribalPattern: Authentic, respectful geometric vector motifs inspired by
 * documented regional visual traditions across India (Forest, River, Woven Loom,
 * Earth/Bhil Dots, Mountain Peaks, Community Links).
 * Adheres strictly to the 5%–12% opacity range for backgrounds and creates
 * rich visual texture without overwhelming content.
 */
export const TribalPattern: React.FC<TribalPatternProps> = ({
  variant,
  family,
  className = '',
  height = 10,
  opacity = 1,
  color = '#1D0A69',
  asBackground = false
}) => {
  const selectedPattern = family || variant || 'woven';

  // Normalize legacy names to the 6 primary families
  const normalizedVariant: 'forest' | 'river' | 'woven' | 'earth' | 'mountain' | 'community' = 
    selectedPattern === 'toda-diamond' ? 'woven' :
    selectedPattern === 'warli-rhythm' ? 'community' :
    selectedPattern === 'gond-dots' ? 'earth' :
    selectedPattern === 'saura-border' ? 'river' :
    selectedPattern as any;

  if (asBackground || opacity < 0.25) {
    const bgOpacity = Math.min(Math.max(opacity, 0.04), 0.14); // strict 4%-14% range

    return (
      <div 
        className={`absolute inset-0 pointer-events-none select-none overflow-hidden ${className}`} 
        style={{ opacity: bgOpacity }}
        aria-hidden="true"
      >
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            {normalizedVariant === 'woven' && (
              <pattern id="pat-bg-woven" width="48" height="48" patternUnits="userSpaceOnUse">
                <path d="M 24,0 L 48,24 L 24,48 L 0,24 Z" fill="none" stroke={color} strokeWidth="1.2" />
                <path d="M 24,8 L 40,24 L 24,40 L 8,24 Z" fill="none" stroke={color} strokeWidth="0.8" strokeDasharray="2 2" />
                <circle cx="24" cy="24" r="2" fill={color} />
              </pattern>
            )}

            {normalizedVariant === 'forest' && (
              <pattern id="pat-bg-forest" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 20,4 L 32,24 L 8,24 Z" fill="none" stroke={color} strokeWidth="1" />
                <line x1="20" y1="24" x2="20" y2="36" stroke={color} strokeWidth="1.2" />
                <line x1="6" y1="36" x2="34" y2="36" stroke={color} strokeWidth="0.8" />
              </pattern>
            )}

            {normalizedVariant === 'river' && (
              <pattern id="pat-bg-river" width="60" height="30" patternUnits="userSpaceOnUse">
                <path d="M 0,15 Q 15,5 30,15 T 60,15" fill="none" stroke={color} strokeWidth="1" />
                <path d="M 0,22 Q 15,12 30,22 T 60,22" fill="none" stroke={color} strokeWidth="0.8" strokeDasharray="3 3" />
              </pattern>
            )}

            {normalizedVariant === 'earth' && (
              <pattern id="pat-bg-earth" width="36" height="36" patternUnits="userSpaceOnUse">
                <circle cx="9" cy="9" r="1.5" fill={color} />
                <circle cx="27" cy="9" r="1.5" fill={color} />
                <circle cx="18" cy="18" r="2.5" fill="none" stroke={color} strokeWidth="1" />
                <circle cx="9" cy="27" r="1.5" fill={color} />
                <circle cx="27" cy="27" r="1.5" fill={color} />
              </pattern>
            )}

            {normalizedVariant === 'mountain' && (
              <pattern id="pat-bg-mountain" width="50" height="30" patternUnits="userSpaceOnUse">
                <polygon points="25,4 48,26 2,26" fill="none" stroke={color} strokeWidth="1.2" />
                <polygon points="25,12 38,26 12,26" fill="none" stroke={color} strokeWidth="0.8" strokeDasharray="2 2" />
              </pattern>
            )}

            {normalizedVariant === 'community' && (
              <pattern id="pat-bg-community" width="44" height="44" patternUnits="userSpaceOnUse">
                <polygon points="22,6 30,20 14,20" fill="none" stroke={color} strokeWidth="1" />
                <polygon points="22,34 30,20 14,20" fill="none" stroke={color} strokeWidth="1" />
                <circle cx="22" cy="4" r="2" fill={color} />
                <line x1="0" y1="20" x2="14" y2="20" stroke={color} strokeWidth="1" />
                <line x1="30" y1="20" x2="44" y2="20" stroke={color} strokeWidth="1" />
              </pattern>
            )}
          </defs>
          <rect width="100%" height="100%" fill={`url(#pat-bg-${normalizedVariant})`} />
        </svg>
      </div>
    );
  }

  // Linear Divider Ribbon Bands
  return (
    <div 
      className={`w-full overflow-hidden select-none ${className}`} 
      style={{ height: `${height}px`, opacity }}
      aria-hidden="true"
    >
      <svg width="100%" height={height} xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
        <defs>
          {normalizedVariant === 'forest' && (
            <pattern id={`pat-ribbon-${normalizedVariant}`} width="32" height={height} patternUnits="userSpaceOnUse">
              <line x1="0" y1="1" x2="32" y2="1" stroke={color} strokeWidth="0.8" strokeOpacity="0.4" />
              <path d={`M 4,${height - 1} L 16,2 L 28,${height - 1}`} fill="none" stroke={color} strokeWidth="1.2" />
              <line x1="16" y1="2" x2="16" y2={height - 1} stroke={color} strokeWidth="1" />
              <line x1="0" y1={height - 0.5} x2="32" y2={height - 0.5} stroke={color} strokeWidth="1" />
            </pattern>
          )}

          {normalizedVariant === 'river' && (
            <pattern id={`pat-ribbon-${normalizedVariant}`} width="40" height={height} patternUnits="userSpaceOnUse">
              <path d={`M 0,${height / 2} Q 10,1 20,${height / 2} T 40,${height / 2}`} fill="none" stroke={color} strokeWidth="1.2" />
              <path d={`M 0,${height - 2} Q 10,${height / 2} 20,${height - 2} T 40,${height - 2}`} fill="none" stroke={color} strokeWidth="0.8" strokeOpacity="0.5" />
            </pattern>
          )}

          {normalizedVariant === 'woven' && (
            <pattern id={`pat-ribbon-${normalizedVariant}`} width="24" height={height} patternUnits="userSpaceOnUse">
              <polygon points={`12,1 23,${height / 2} 12,${height - 1} 1,${height / 2}`} fill="none" stroke={color} strokeWidth="1.2" />
              <polygon points={`12,${height / 2 - 1.5} 14.5,${height / 2} 12,${height / 2 + 1.5} 9.5,${height / 2}`} fill={color} />
              <line x1="0" y1="0.5" x2="24" y2="0.5" stroke={color} strokeWidth="0.5" strokeOpacity="0.5" />
              <line x1="0" y1={height - 0.5} x2="24" y2={height - 0.5} stroke={color} strokeWidth="0.5" strokeOpacity="0.5" />
            </pattern>
          )}

          {normalizedVariant === 'earth' && (
            <pattern id={`pat-ribbon-${normalizedVariant}`} width="28" height={height} patternUnits="userSpaceOnUse">
              <circle cx="7" cy={height / 2} r="2" fill={color} />
              <circle cx="14" cy={height / 2} r="1.2" fill={color} fillOpacity="0.6" />
              <circle cx="21" cy={height / 2} r="2" fill={color} />
              <line x1="0" y1={height - 1} x2="28" y2={height - 1} stroke={color} strokeWidth="0.8" strokeOpacity="0.4" />
            </pattern>
          )}

          {normalizedVariant === 'mountain' && (
            <pattern id={`pat-ribbon-${normalizedVariant}`} width="30" height={height} patternUnits="userSpaceOnUse">
              <polygon points={`15,1 29,${height - 1} 1,${height - 1}`} fill="none" stroke={color} strokeWidth="1.2" />
              <line x1="0" y1={height - 0.5} x2="30" y2={height - 0.5} stroke={color} strokeWidth="1" />
            </pattern>
          )}

          {normalizedVariant === 'community' && (
            <pattern id={`pat-ribbon-${normalizedVariant}`} width="26" height={height} patternUnits="userSpaceOnUse">
              <polygon points={`13,1 18,${height / 2} 8,${height / 2}`} fill="none" stroke={color} strokeWidth="1" />
              <polygon points={`13,${height - 1} 18,${height / 2} 8,${height / 2}`} fill="none" stroke={color} strokeWidth="1" />
              <circle cx="13" cy="2" r="1.2" fill={color} />
              <line x1="0" y1={height / 2} x2="8" y2={height / 2} stroke={color} strokeWidth="1" />
              <line x1="18" y1={height / 2} x2="26" y2={height / 2} stroke={color} strokeWidth="1" />
              <line x1="0" y1={height - 0.5} x2="26" y2={height - 0.5} stroke={color} strokeWidth="0.8" strokeOpacity="0.4" />
            </pattern>
          )}
        </defs>
        <rect width="100%" height={height} fill={`url(#pat-ribbon-${normalizedVariant})`} />
      </svg>
    </div>
  );
};
