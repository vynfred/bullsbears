'use client';

import React, { useState, useRef } from 'react';
import { 
  Share2, Download, Copy, Twitter, Facebook, 
  Linkedin, Instagram, Zap, TrendingUp, TrendingDown,
  Sparkles, Target, DollarSign
} from 'lucide-react';
import { AIOptionPlay } from '@/lib/api';

interface ShareableContentProps {
  play?: AIOptionPlay;
  tradeResult?: {
    symbol: string;
    option_type: string;
    entry_price: number;
    exit_price: number;
    profit_loss: number;
    profit_percentage: number;
    outcome: 'WIN' | 'LOSS';
  };
  type: 'prediction' | 'result';
}

export default function ShareableContent({ play, tradeResult, type }: ShareableContentProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const generateShareableImage = async () => {
    setIsGenerating(true);
    
    try {
      const canvas = canvasRef.current;
      if (!canvas) return;
      
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Set canvas size
      canvas.width = 800;
      canvas.height = 600;

      // Create gradient background
      const gradient = ctx.createLinearGradient(0, 0, 800, 600);
      if (type === 'prediction') {
        gradient.addColorStop(0, '#0f172a'); // Dark blue
        gradient.addColorStop(1, '#1e293b'); // Darker blue
      } else {
        const isWin = tradeResult?.outcome === 'WIN';
        if (isWin) {
          gradient.addColorStop(0, '#064e3b'); // Dark green
          gradient.addColorStop(1, '#0f172a'); // Dark blue
        } else {
          gradient.addColorStop(0, '#7f1d1d'); // Dark red
          gradient.addColorStop(1, '#0f172a'); // Dark blue
        }
      }
      
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 800, 600);

      // Add cyberpunk grid pattern
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.1)'; // Cyan with low opacity
      ctx.lineWidth = 1;
      for (let i = 0; i < 800; i += 40) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, 600);
        ctx.stroke();
      }
      for (let i = 0; i < 600; i += 40) {
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(800, i);
        ctx.stroke();
      }

      // Add BULLSBEARS branding
      ctx.fillStyle = '#06b6d4'; // Cyan
      ctx.font = 'bold 48px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('BULLSBEARS.XYZ', 400, 80);

      // Add AI-powered subtitle
      ctx.fillStyle = '#fbbf24'; // Yellow
      ctx.font = '20px monospace';
      ctx.fillText('AI-POWERED OPTIONS ANALYSIS', 400, 110);

      if (type === 'prediction' && play) {
        // Prediction content
        const isBullish = play.option_type === 'CALL';
        
        // Add bull/bear emoji
        ctx.font = '80px monospace';
        ctx.fillText(isBullish ? '🐂' : '🐻', 400, 200);
        
        // Add symbol and type
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 60px monospace';
        ctx.fillText(play.symbol, 400, 280);
        
        ctx.fillStyle = isBullish ? '#10b981' : '#ef4444';
        ctx.font = 'bold 36px monospace';
        ctx.fillText(`${play.option_type} $${play.strike}`, 400, 320);
        
        // Add confidence score
        ctx.fillStyle = '#06b6d4';
        ctx.font = 'bold 32px monospace';
        ctx.fillText(`${play.confidence_score.toFixed(1)}% CONFIDENCE`, 400, 380);
        
        // Add entry price
        ctx.fillStyle = '#ffffff';
        ctx.font = '28px monospace';
        ctx.fillText(`ENTRY: $${play.entry_price.toFixed(2)}`, 400, 420);
        ctx.fillText(`TARGET: $${play.target_price.toFixed(2)}`, 400, 460);
        
        // Add AI recommendation
        ctx.fillStyle = '#fbbf24';
        ctx.font = 'bold 24px monospace';
        ctx.fillText('AI RECOMMENDATION: ' + play.ai_recommendation, 400, 520);
        
      } else if (type === 'result' && tradeResult) {
        // Result content
        const isWin = tradeResult.outcome === 'WIN';
        
        // Add result emoji and text
        ctx.font = '80px monospace';
        ctx.fillText(isWin ? '🎉' : '💀', 400, 200);
        
        ctx.fillStyle = isWin ? '#10b981' : '#ef4444';
        ctx.font = 'bold 48px monospace';
        ctx.fillText(isWin ? 'WINNER!' : 'STOPPED OUT', 400, 260);
        
        // Add symbol
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 40px monospace';
        ctx.fillText(tradeResult.symbol, 400, 320);
        
        // Add P/L
        ctx.fillStyle = isWin ? '#10b981' : '#ef4444';
        ctx.font = 'bold 36px monospace';
        ctx.fillText(
          `${isWin ? '+' : ''}$${tradeResult.profit_loss.toFixed(2)}`, 
          400, 380
        );
        
        // Add percentage
        ctx.font = '28px monospace';
        ctx.fillText(
          `${isWin ? '+' : ''}${tradeResult.profit_percentage.toFixed(1)}%`, 
          400, 420
        );
        
        // Add entry/exit prices
        ctx.fillStyle = '#ffffff';
        ctx.font = '24px monospace';
        ctx.fillText(`ENTRY: $${tradeResult.entry_price.toFixed(2)}`, 300, 480);
        ctx.fillText(`EXIT: $${tradeResult.exit_price.toFixed(2)}`, 500, 480);
      }

      // Add disclaimer
      ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
      ctx.font = '16px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('NOT FINANCIAL ADVICE • FOR EDUCATIONAL PURPOSES ONLY', 400, 560);

      // Convert to image
      const imageData = canvas.toDataURL('image/png');
      setGeneratedImage(imageData);
      
    } catch (error) {
      console.error('Error generating image:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadImage = () => {
    if (!generatedImage) return;
    
    const link = document.createElement('a');
    link.download = `bullsbears-${type}-${Date.now()}.png`;
    link.href = generatedImage;
    link.click();
  };

  const copyImageToClipboard = async () => {
    if (!generatedImage) return;
    
    try {
      const response = await fetch(generatedImage);
      const blob = await response.blob();
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob })
      ]);
      alert('Image copied to clipboard!');
    } catch (error) {
      console.error('Failed to copy image:', error);
      alert('Failed to copy image to clipboard');
    }
  };

  const shareToSocial = (platform: string) => {
    const text = type === 'prediction' && play
      ? `🤖 AI picked ${play.symbol} ${play.option_type} with ${play.confidence_score.toFixed(1)}% confidence! Check out BULLSBEARS.XYZ for AI-powered options analysis 📈`
      : tradeResult
      ? `${tradeResult.outcome === 'WIN' ? '🎉' : '💀'} ${tradeResult.symbol} trade ${tradeResult.outcome === 'WIN' ? 'WON' : 'LOST'} ${tradeResult.profit_percentage.toFixed(1)}%! AI-powered analysis from BULLSBEARS.XYZ 🤖`
      : 'Check out BULLSBEARS.XYZ for AI-powered options analysis!';
    
    const url = 'https://bullsbears.xyz';
    
    const shareUrls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}&quote=${encodeURIComponent(text)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}&summary=${encodeURIComponent(text)}`,
    };
    
    const shareUrl = shareUrls[platform as keyof typeof shareUrls];
    if (shareUrl) {
      window.open(shareUrl, '_blank', 'width=600,height=400');
    }
  };

  return (
    <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700/50 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-[var(--accent-yellow)]" />
        <h3 className="font-mono text-[var(--accent-yellow)] uppercase tracking-wider">
          Shareable Content Generator
        </h3>
      </div>

      {/* Canvas for image generation */}
      <canvas
        ref={canvasRef}
        className="hidden"
        width={800}
        height={600}
      />

      {/* Generate Button */}
      {!generatedImage && (
        <div className="text-center mb-6">
          <button
            onClick={generateShareableImage}
            disabled={isGenerating}
            className="neon-button px-6 py-3 flex items-center gap-2 mx-auto"
          >
            {isGenerating ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--text-primary)] border-t-transparent"></div>
                Generating...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Generate {type === 'prediction' ? 'Prediction' : 'Result'} Image
              </>
            )}
          </button>
        </div>
      )}

      {/* Generated Image Preview */}
      {generatedImage && (
        <div className="space-y-4">
          <div className="border border-gray-700/50 rounded-lg overflow-hidden">
            <img
              src={generatedImage}
              alt="Generated shareable content"
              className="w-full h-auto"
            />
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <button
              onClick={downloadImage}
              className="flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
            
            <button
              onClick={copyImageToClipboard}
              className="flex items-center justify-center gap-2 px-3 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
            >
              <Copy className="w-4 h-4" />
              Copy
            </button>
            
            <button
              onClick={() => shareToSocial('twitter')}
              className="flex items-center justify-center gap-2 px-3 py-2 bg-blue-400 hover:bg-blue-300 text-white rounded-lg transition-colors"
            >
              <Twitter className="w-4 h-4" />
              Twitter
            </button>
            
            <button
              onClick={() => shareToSocial('linkedin')}
              className="flex items-center justify-center gap-2 px-3 py-2 bg-blue-700 hover:bg-blue-600 text-white rounded-lg transition-colors"
            >
              <Linkedin className="w-4 h-4" />
              LinkedIn
            </button>
          </div>

          {/* Generate New Button */}
          <div className="text-center">
            <button
              onClick={() => setGeneratedImage(null)}
              className="text-sm text-[var(--accent-cyan)] hover:text-[var(--text-primary)] transition-colors"
            >
              Generate New Image
            </button>
          </div>
        </div>
      )}

      {/* Feature Description */}
      <div className="mt-6 p-4 bg-gray-800/30 rounded-lg border border-gray-700/50">
        <h4 className="font-mono text-sm text-[var(--accent-cyan)] mb-2 uppercase">
          Share Your {type === 'prediction' ? 'AI Predictions' : 'Trade Results'}
        </h4>
        <p className="text-sm text-gray-400 leading-relaxed">
          {type === 'prediction' 
            ? 'Generate eye-catching images of your AI-powered option predictions to share on social media. Show off the confidence scores and analysis!'
            : 'Create viral-worthy content from your trade outcomes. Whether you won or lost, share your journey with the trading community!'
          }
        </p>
      </div>
    </div>
  );
}
