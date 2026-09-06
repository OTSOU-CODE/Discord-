import React, { useEffect, useState, useRef } from 'react';
import { playRollTick, playRoundStart } from '../utils/soundEffects';

export function CarouselRoll({ targetLetter, pool = [], roundNumber, totalRounds, t }) {
  const [displayLetter, setDisplayLetter] = useState('?');
  const [isLanded, setIsLanded] = useState(false);
  const intervalRef = useRef(null);
  const startTimeRef = useRef(Date.now());

  useEffect(() => {
    const letters = pool.length > 0 ? pool : ['أ', 'ب', 'ت', 'ج', 'د', 'ر', 'س', 'م', 'ن'];
    let delay = 60; // start fast
    startTimeRef.current = Date.now();
    setIsLanded(false);

    const tick = () => {
      const elapsed = Date.now() - startTimeRef.current;

      if (elapsed >= 2800) {
        // Land on final letter
        setDisplayLetter(targetLetter);
        setIsLanded(true);
        playRoundStart();
        return;
      }

      // Random intermediate letter
      const randomChar = letters[Math.floor(Math.random() * letters.length)];
      setDisplayLetter(randomChar);
      playRollTick();

      // Progressive deceleration curve
      if (elapsed > 1800) {
        delay = 180;
      } else if (elapsed > 1000) {
        delay = 110;
      }

      intervalRef.current = setTimeout(tick, delay);
    };

    intervalRef.current = setTimeout(tick, delay);

    return () => {
      if (intervalRef.current) clearTimeout(intervalRef.current);
    };
  }, [targetLetter, pool]);

  return (
    <div className="fixed inset-0 z-50 bg-paper-100/95 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center select-none animate-in fade-in duration-300">
      
      {/* Round Pill */}
      <div className="mb-6 px-4 py-1.5 rounded-full bg-amber-100 border border-amber-300 text-amber-900 text-xs font-bold uppercase tracking-wider shadow-xs">
        {t.round} {roundNumber} {t.of} {totalRounds}
      </div>

      <h2 className="text-xl sm:text-2xl font-black text-ink-800 mb-8">
        {isLanded ? t.currentLetter : t.rollingLetter}
      </h2>

      {/* Rotating / Rolling Letter Card */}
      <div className="relative">
        <div className={`w-44 h-44 sm:w-56 sm:h-56 rounded-3xl bg-paper-50 border-4 ${
          isLanded ? 'border-amber-600 shadow-pop scale-105' : 'border-paper-border shadow-notebook'
        } flex items-center justify-center transition-all duration-300 relative overflow-hidden`}>
          
          {/* Paper lined background effect */}
          <div className="absolute inset-0 bg-notebook-lined opacity-30 pointer-events-none" />

          {/* Large Letter */}
          <span className={`font-black text-7xl sm:text-9xl transition-all ${
            isLanded 
              ? 'text-amber-700 animate-bounce-short scale-110 drop-shadow-md' 
              : 'text-ink-800 scale-95 opacity-80'
          }`}>
            {displayLetter}
          </span>
        </div>

        {/* Ambient Ring on Land */}
        {isLanded && (
          <div className="absolute -inset-3 rounded-[32px] border-2 border-amber-500/40 animate-ping pointer-events-none" />
        )}
      </div>

      <p className="mt-8 text-xs font-semibold text-ink-500 animate-pulse">
        {isLanded ? 'Get ready to write!' : 'Rolling letter carousel...'}
      </p>

    </div>
  );
}
