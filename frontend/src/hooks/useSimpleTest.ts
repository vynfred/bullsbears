'use client';

import { useState } from 'react';

export function useSimpleTest() {
  console.log('useSimpleTest - hook called');
  
  const [count, setCount] = useState(0);
  const [message, setMessage] = useState('initial');
  
  console.log('useSimpleTest - current state:', { count, message });
  
  const increment = () => {
    console.log('useSimpleTest - increment called, current count:', count);
    setCount(prev => {
      const newCount = prev + 1;
      console.log('useSimpleTest - setting count to:', newCount);
      return newCount;
    });
  };
  
  const updateMessage = (newMessage: string) => {
    console.log('useSimpleTest - updateMessage called with:', newMessage);
    setMessage(newMessage);
  };
  
  return {
    count,
    message,
    increment,
    updateMessage
  };
}
