// PushService.ts - Target hit notifications with confetti triggers

interface TargetHitNotification {
  symbol: string;
  targetType: 'LOW' | 'MED' | 'HIGH' | 'STOP';
  currentPrice: number;
  entryPrice: number;
  gainPercent: number;
  direction: 'LONG' | 'SHORT';
}

interface PushServiceConfig {
  enableBrowserNotifications: boolean;
  enableConfetti: boolean;
  watchlistOnly: boolean;
}

class PushNotificationService {
  private config: PushServiceConfig;
  private userWatchlist: Set<string>;
  private notificationPermission: NotificationPermission = 'default';

  constructor() {
    this.config = {
      enableBrowserNotifications: true,
      enableConfetti: true,
      watchlistOnly: true
    };
    this.userWatchlist = new Set();
    this.initializeNotifications();
  }

  // Initialize browser notification permissions
  private async initializeNotifications(): Promise<void> {
    if ('Notification' in window) {
      this.notificationPermission = Notification.permission;
      
      if (this.notificationPermission === 'default') {
        this.notificationPermission = await Notification.requestPermission();
      }
    }
  }

  // Add symbol to user's watchlist
  public addToWatchlist(symbol: string): void {
    this.userWatchlist.add(symbol.toUpperCase());
    console.log(`Added ${symbol} to watchlist`);
  }

  // Remove symbol from user's watchlist
  public removeFromWatchlist(symbol: string): void {
    this.userWatchlist.delete(symbol.toUpperCase());
    console.log(`Removed ${symbol} from watchlist`);
  }

  // Check if symbol is in watchlist
  public isInWatchlist(symbol: string): boolean {
    return this.userWatchlist.has(symbol.toUpperCase());
  }

  // Calculate target hit type based on gain percentage
  private getTargetHitType(gainPercent: number, direction: 'LONG' | 'SHORT'): TargetHitNotification['targetType'] | null {
    const absGain = Math.abs(gainPercent);
    
    if (direction === 'LONG') {
      if (gainPercent >= 31) return 'HIGH';
      if (gainPercent >= 23) return 'MED';
      if (gainPercent >= 18) return 'LOW';
      if (gainPercent <= -5) return 'STOP';
    } else { // SHORT
      if (gainPercent >= 31) return 'HIGH'; // Stock dropped 31%+, we profit
      if (gainPercent >= 23) return 'MED';
      if (gainPercent >= 18) return 'LOW';
      if (gainPercent <= -5) return 'STOP'; // Stock went up 5%+, stop loss
    }
    
    return null;
  }

  // Get notification message based on target type
  private getNotificationMessage(notification: TargetHitNotification): { title: string; body: string; icon: string } {
    const { symbol, targetType, gainPercent, direction } = notification;
    const sign = gainPercent > 0 ? '+' : '';
    
    switch (targetType) {
      case 'HIGH':
        return {
          title: `🧙‍♂️ HIGH HIT! You're a wizard.`,
          body: `${symbol} hit ${sign}${gainPercent.toFixed(1)}% - Your ${direction} pick crushed it!`,
          icon: '🎯'
        };
      case 'MED':
        return {
          title: `🎯 MED HIT!`,
          body: `${symbol} reached ${sign}${gainPercent.toFixed(1)}% - Nice call!`,
          icon: '📈'
        };
      case 'LOW':
        return {
          title: `✅ LOW HIT!`,
          body: `${symbol} hit ${sign}${gainPercent.toFixed(1)}% - Target achieved!`,
          icon: '🎉'
        };
      case 'STOP':
        return {
          title: `🛑 STOP LOSS HIT`,
          body: `${symbol} hit ${sign}${gainPercent.toFixed(1)}% - Consider your exit strategy`,
          icon: '⚠️'
        };
      default:
        return {
          title: `📊 ${symbol} Update`,
          body: `Price movement: ${sign}${gainPercent.toFixed(1)}%`,
          icon: '📊'
        };
    }
  }

  // Trigger confetti animation (to be called by UI components)
  public triggerConfetti(): void {
    if (!this.config.enableConfetti) return;
    
    // Dispatch custom event for confetti component to listen to
    const confettiEvent = new CustomEvent('triggerConfetti', {
      detail: {
        numberOfPieces: 200,
        gravity: 0.2,
        recycle: false,
        duration: 3000
      }
    });
    
    window.dispatchEvent(confettiEvent);
    console.log('🎊 Confetti triggered!');
  }

  // Send browser notification
  private async sendBrowserNotification(notification: TargetHitNotification): Promise<void> {
    if (!this.config.enableBrowserNotifications || this.notificationPermission !== 'granted') {
      return;
    }

    const message = this.getNotificationMessage(notification);
    
    try {
      const browserNotification = new Notification(message.title, {
        body: message.body,
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        tag: `target-hit-${notification.symbol}`,
        requireInteraction: notification.targetType === 'HIGH' || notification.targetType === 'STOP'
      });

      browserNotification.onclick = () => {
        window.focus();
        // Navigate to performance tab
        window.location.hash = '#performance';
        browserNotification.close();
      };

      // Auto-close after 10 seconds for non-critical notifications
      if (notification.targetType !== 'HIGH' && notification.targetType !== 'STOP') {
        setTimeout(() => {
          browserNotification.close();
        }, 10000);
      }

    } catch (error) {
      console.error('Failed to send browser notification:', error);
    }
  }

  // Main method to handle price updates and check for target hits
  public async checkTargetHit(
    symbol: string,
    currentPrice: number,
    entryPrice: number,
    direction: 'LONG' | 'SHORT' = 'LONG'
  ): Promise<void> {
    // Only process watchlist symbols if watchlistOnly is enabled
    if (this.config.watchlistOnly && !this.isInWatchlist(symbol)) {
      return;
    }

    // Calculate gain percentage
    let gainPercent: number;
    if (direction === 'LONG') {
      gainPercent = ((currentPrice - entryPrice) / entryPrice) * 100;
    } else {
      // For SHORT positions, profit when price goes down
      gainPercent = ((entryPrice - currentPrice) / entryPrice) * 100;
    }

    // Check if this is a target hit
    const targetType = this.getTargetHitType(gainPercent, direction);
    if (!targetType) return;

    const notification: TargetHitNotification = {
      symbol,
      targetType,
      currentPrice,
      entryPrice,
      gainPercent,
      direction
    };

    // Send browser notification
    await this.sendBrowserNotification(notification);

    // Trigger confetti for HIGH hits only
    if (targetType === 'HIGH') {
      this.triggerConfetti();
    }

    // Log for debugging
    console.log(`🎯 Target hit detected:`, notification);
  }

  // Update service configuration
  public updateConfig(newConfig: Partial<PushServiceConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  // Get current configuration
  public getConfig(): PushServiceConfig {
    return { ...this.config };
  }

  // Get watchlist as array
  public getWatchlist(): string[] {
    return Array.from(this.userWatchlist);
  }
}

// Export singleton instance
export const pushService = new PushNotificationService();

// Export types for use in other components
export type { TargetHitNotification, PushServiceConfig };

// Utility function to simulate price updates (for demo purposes)
export function simulateTargetHit(symbol: string, targetType: 'LOW' | 'MED' | 'HIGH' | 'STOP'): void {
  const entryPrice = 100;
  let currentPrice: number;
  
  switch (targetType) {
    case 'LOW':
      currentPrice = 118; // +18%
      break;
    case 'MED':
      currentPrice = 123; // +23%
      break;
    case 'HIGH':
      currentPrice = 131; // +31%
      break;
    case 'STOP':
      currentPrice = 95; // -5%
      break;
  }
  
  pushService.addToWatchlist(symbol);
  pushService.checkTargetHit(symbol, currentPrice, entryPrice, 'LONG');
}
