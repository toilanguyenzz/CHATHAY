import { defineHandler } from 'zmp-sdk';

// Simple analytics wrapper supporting multiple providers
type AnalyticsEvent = {
  event: string;
  properties?: Record<string, any>;
  userId?: string;
  timestamp?: number;
};

class AnalyticsService {
  private providers: Array<{ name: string; track: (event: AnalyticsEvent) => void }> = [];

  constructor() {
    // Initialize providers based on environment
    this.initMixpanel();
    this.initGA4();
  }

  private initMixpanel() {
    const token = import.meta.env.VITE_MIXPANEL_TOKEN;
    if (!token) return;

    // Dynamic import to avoid loading in dev if not needed
    import('mixpanel-browser').then(({ default: mixpanel }) => {
      mixpanel.init(token, {
        api_host: 'https://api.mixpanel.com',
        track_pageview: true,
        pageview: {
          trigger: true, // Auto-track page views
        },
      });
      this.providers.push({
        name: 'mixpanel',
        track: (event) => mixpanel.track(event.event, event.properties),
      });
    });
  }

  private initGA4() {
    // GA4 via gtag would be loaded in index.html
    // This is a placeholder for gtag function
    if (typeof window !== 'undefined' && (window as any).gtag) {
      this.providers.push({
        name: 'ga4',
        track: (event) => {
          (window as any).gtag('event', event.event, event.properties);
        },
      });
    }
  }

  identify(userId: string, traits?: Record<string, any>) {
    this.providers.forEach((provider) => {
      if (provider.name === 'mixpanel') {
        import('mixpanel-browser').then(({ default: mixpanel }) => {
          mixpanel.identify(userId);
          if (traits) mixpanel.people.set(traits);
        });
      }
    });
  }

  track(event: string, properties?: Record<string, any>) {
    const enrichedEvent: AnalyticsEvent = {
      event,
      properties: {
        ...properties,
        timestamp: Date.now(),
        platform: 'zalo-mini-app',
        app_version: '1.0.0',
        ...properties,
      },
    };

    // Log in development
    if (import.meta.env.DEV) {
      console.log('[Analytics]', enrichedEvent);
    }

    this.providers.forEach((provider) => {
      try {
        provider.track(enrichedEvent);
      } catch (error) {
        console.error(`Analytics error (${provider.name}):`, error);
      }
    });
  }

  // Pre-defined events
  trackScreenView(screenName: string) {
    this.track('screen_view', { screen_name: screenName });
  }

  trackFileUpload(file: File, success: boolean, duration: number) {
    this.track('file_upload', {
      file_name: file.name,
      file_type: file.type,
      file_size: file.size,
      success,
      duration_ms: duration,
    });
  }

  trackSummaryViewed(docId: string, summaryLength: number) {
    this.track('summary_viewed', {
      doc_id: docId,
      summary_length_chars: summaryLength,
    });
  }

  trackQuizStarted(docId: string, questionCount: number) {
    this.track('quiz_started', {
      doc_id: docId,
      question_count: questionCount,
    });
  }

  trackQuizCompleted(docId: string, score: number, total: number, duration: number) {
    this.track('quiz_completed', {
      doc_id: docId,
      score,
      total,
      percentage: Math.round((score / total) * 100),
      duration_ms: duration,
    });
  }

  trackQuizShared(docId: string, channel: 'zalo' | 'copy' = 'zalo') {
    this.track('quiz_shared', {
      doc_id: docId,
      channel,
    });
  }

  trackFlashcardReviewed(rating: 'again' | 'hard' | 'good' | 'easy') {
    this.track('flashcard_reviewed', { rating });
  }

  trackFlashcardSessionCompleted(docId: string, cardsReviewed: number) {
    this.track('flashcard_completed', {
      doc_id: docId,
      cards_reviewed: cardsReviewed,
    });
  }

  trackCoinPurchase(packageName: string, amount: number, coins: number) {
    this.track('coin_purchase', {
      package: packageName,
      amount_vnd: amount,
      coins,
      bonus_percent: Math.round(((coins - amount / 100) / (amount / 100)) * 100),
    });
  }

  trackStreakMaintained(streak: number) {
    this.track('streak_maintained', { streak });
  }

  trackStreakBroken(lastStreak: number) {
    this.track('streak_broken', { last_streak: lastStreak });
  }

  trackInviteSent(inviteCode: string) {
    this.track('invite_sent', { invite_code_length: inviteCode.length });
  }

  trackInviteAccepted(inviteCode: string) {
    this.track('invite_accepted', { invite_code: inviteCode });
  }
}

// Singleton instance
export const analytics = new AnalyticsService();

// Export helper for direct usage
export const trackEvent = analytics.track.bind(analytics);
