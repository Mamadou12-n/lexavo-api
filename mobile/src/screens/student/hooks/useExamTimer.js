import { useState, useRef, useEffect, useCallback } from 'react';

export function useExamTimer({ onTimeUp } = {}) {
  const [examTimer, setExamTimer] = useState(0);
  const timerRef = useRef(null);
  const onTimeUpRef = useRef(onTimeUp);

  useEffect(() => { onTimeUpRef.current = onTimeUp; }, [onTimeUp]);

  const startTimer = useCallback((seconds) => {
    clearInterval(timerRef.current);
    setExamTimer(seconds);
    timerRef.current = setInterval(() => {
      setExamTimer(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          onTimeUpRef.current?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    clearInterval(timerRef.current);
  }, []);

  useEffect(() => () => clearInterval(timerRef.current), []);

  const fmtTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  return { examTimer, timerRef, startTimer, stopTimer, fmtTime };
}
