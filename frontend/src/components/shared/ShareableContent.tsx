// src/components/shared/ShareableContent.tsx
'use client';

import React from 'react';
import { Share2, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import html2canvas from 'html2canvas';

interface ShareableContentProps {
  children: React.ReactNode;
  title: string;
  filename?: string;
}

export default function ShareableContent({ children, title, filename = 'share' }: ShareableContentProps) {
  const ref = React.useRef<HTMLDivElement>(null);

  const download = async () => {
    if (!ref.current) return;
    const canvas = await html2canvas(ref.current);
    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = canvas.toDataURL();
    link.click();
  };

  const share = async () => {
    if (navigator.share && ref.current) {
      const canvas = await html2canvas(ref.current);
      canvas.toBlob(async (blob) => {
        if (!blob) return;
        const file = new File([blob], `${filename}.png`, { type: 'image/png' });
        await navigator.share({ files: [file], title });
      });
    } else {
      download();
    }
  };

  return (
    <div>
      <div ref={ref}>{children}</div>
      <div className="flex justify-center gap-2 mt-4">
        <Button size="sm" variant="secondary" onClick={share}>
          <Share2 className="w-4 h-4 mr-1" />
          Share
        </Button>
        <Button size="sm" variant="secondary" onClick={download}>
          <Download className="w-4 h-4 mr-1" />
          Save
        </Button>
      </div>
    </div>
  );
}