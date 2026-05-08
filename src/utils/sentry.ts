import * as Sentry from '@sentry/react';
import { Integrations } from '@sentry/tracing';

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  const env = import.meta.env.VITE_SENTRY_ENV || 'development';

  if (!dsn) {
    console.warn('Sentry DSN not configured');
    return;
  }

  Sentry.init({
    dsn,
    environment: env,
    tracesSampleRate: env === 'production' ? 0.1 : 1.0,
    tracePropagationTargets: [/^https:\/\/api\.chathay\.vn/, /^http:\/\/localhost/],
    integrations: [
      new Integrations.BrowserTracing({
        routingInstrumentation: Sentry.reactRouterV6Instrumentation(
          // Use React Router v6 instrumentation
          () => document.querySelector('main') || undefined
        ),
      }),
    ],
    beforeSend(event, hint) {
      // Filter sensitive data
      if (event.request?.data) {
        try {
          const data = JSON.parse(event.request.data);
          // Remove tokens, passwords
          if (data.access_token) data.access_token = '[REDACTED]';
          if (data.password) data.password = '[REDACTED]';
          event.request.data = JSON.stringify(data);
        } catch (e) {
          // Not JSON, skip
        }
      }

      // Remove user email for privacy
      if (event.user?.email) {
        event.user.email = undefined;
      }

      return event;
    },
    beforeBreadcrumb(breadcrumb) {
      // Don't log sensitive data in breadcrumbs
      if (breadcrumb.category === 'console' && breadcrumb.level === 'log') {
        return null; // Skip console.log
      }
      return breadcrumb;
    },
  });
}

// Manual error capture helper
export function captureException(error: Error, context?: Record<string, any>) {
  Sentry.captureException(error, {
    extra: context,
  });
}

// Manual message helper
export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info') {
  Sentry.captureMessage(message, level);
}

// Set user context
export function setUser(user: { id: string; email?: string; username?: string }) {
  Sentry.setUser(user);
}

// Clear user context (on logout)
export function clearUser() {
  Sentry.setUser(null);
}
