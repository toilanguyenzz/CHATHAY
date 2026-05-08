import { Box, Text } from "zmp-ui";

interface EmptyStateProps {
  emoji?: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
}

export function EmptyState({
  emoji = "📭",
  title,
  description,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
}: EmptyStateProps) {
  return (
    <Box style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "60vh",
      gap: 16,
      padding: "0 24px",
      textAlign: "center",
    }}>
      {/* Illustration */}
      <Box style={{
        width: 120,
        height: 120,
        borderRadius: "var(--radius-xl)",
        background: "var(--color-bg-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 56,
        lineHeight: 1,
        border: "2px dashed var(--color-border)",
        marginBottom: 8,
      }}>
        {emoji}
      </Box>

      {/* Title */}
      <Text className="ch-heading-lg" style={{ textAlign: "center" }}>{title}</Text>

      {/* Description */}
      <Text className="ch-caption" style={{
        textAlign: "center",
        maxWidth: 280,
        lineHeight: 1.6,
      }}>{description}</Text>

      {/* Primary Action */}
      {actionLabel && onAction && (
        <Box
          className="ch-btn-primary"
          onClick={onAction}
          style={{
            marginTop: 8,
            width: "100%",
            maxWidth: 280,
            justifyContent: "center",
          }}
        >
          <span>{actionLabel}</span>
        </Box>
      )}

      {/* Secondary Action */}
      {secondaryActionLabel && onSecondaryAction && (
        <Box
          onClick={onSecondaryAction}
          style={{
            marginTop: 4,
            padding: "12px 28px",
            borderRadius: "var(--radius-md)",
            background: "var(--color-bg-subtle)",
            border: "1px solid var(--color-border)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            justifyContent: "center",
            width: "100%",
            maxWidth: 280,
          }}
        >
          <Text style={{
            fontSize: "var(--font-size-sm)",
            fontWeight: 700,
            color: "var(--color-text-secondary)",
          }}>{secondaryActionLabel}</Text>
        </Box>
      )}
    </Box>
  );
}
