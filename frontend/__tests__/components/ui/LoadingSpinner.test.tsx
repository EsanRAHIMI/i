import { render } from '@testing-library/react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders with default props', () => {
    const { container } = render(<LoadingSpinner />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveClass('w-6', 'h-6', 'animate-spin');
  });

  it('renders with different sizes', () => {
    const { container, rerender } = render(<LoadingSpinner size="sm" />);
    let spinner = container.firstChild as HTMLElement;
    expect(spinner).toHaveClass('w-4', 'h-4');

    rerender(<LoadingSpinner size="lg" />);
    spinner = container.firstChild as HTMLElement;
    expect(spinner).toHaveClass('w-8', 'h-8');
  });

  it('applies custom className', () => {
    const { container } = render(<LoadingSpinner className="text-red-500" />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner).toHaveClass('text-red-500');
  });

  it('has proper accessibility attributes', () => {
    const { container } = render(<LoadingSpinner />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner).toHaveClass('border-2', 'border-gray-600', 'border-t-primary-500');
  });
});