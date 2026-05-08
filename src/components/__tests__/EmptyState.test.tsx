import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EmptyState } from '../EmptyState';

describe('EmptyState', () => {
  it('should render emoji and title', () => {
    render(
      <EmptyState
        emoji="📭"
        title="No documents"
        description="Upload a file to get started"
      />
    );

    expect(screen.getByText('📭')).toBeInTheDocument();
    expect(screen.getByText('No documents')).toBeInTheDocument();
    expect(screen.getByText('Upload a file to get started')).toBeInTheDocument();
  });

  it('should render action button when provided', () => {
    const onAction = vi.fn();
    render(
      <EmptyState
        emoji="📤"
        title="Empty"
        description="No items"
        actionLabel="Upload"
        onAction={onAction}
      />
    );

    const button = screen.getByText('Upload');
    expect(button).toBeInTheDocument();

    fireEvent.click(button);
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it('should render secondary action when provided', () => {
    const onSecondary = vi.fn();
    render(
      <EmptyState
        emoji="🏠"
        title="Home"
        description="Go back"
        secondaryActionLabel="Back"
        onSecondaryAction={onSecondary}
      />
    );

    const button = screen.getByText('Back');
    expect(button).toBeInTheDocument();

    fireEvent.click(button);
    expect(onSecondary).toHaveBeenCalledTimes(1);
  });

  it('should render both actions', () => {
    render(
      <EmptyState
        emoji="⚡"
        title="Quick action"
        description="Do something"
        actionLabel="Primary"
        onAction={() => {}}
        secondaryActionLabel="Secondary"
        onSecondaryAction={() => {}}
      />
    );

    expect(screen.getByText('Primary')).toBeInTheDocument();
    expect(screen.getByText('Secondary')).toBeInTheDocument();
  });

  it('should not render action buttons when not provided', () => {
    render(
      <EmptyState
        emoji="😴"
        title="Sleeping"
        description="Nothing here"
      />
    );

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
