import { render } from '@testing-library/react';
import { GlowingOrb } from '@/components/ui/GlowingOrb';

describe('GlowingOrb', () => {
  it('renders with default props', () => {
    const { container } = render(<GlowingOrb />);
    const orb = container.firstChild as HTMLElement;
    expect(orb).toBeInTheDocument();
    expect(orb).toHaveClass('w-24', 'h-24', 'rounded-full');
  });

  it('renders with different sizes', () => {
    const { container, rerender } = render(<GlowingOrb size="sm" />);
    let orb = container.firstChild as HTMLElement;
    expect(orb).toHaveClass('w-16', 'h-16');

    rerender(<GlowingOrb size="large" />);
    orb = container.firstChild as HTMLElement;
    expect(orb).toHaveClass('w-36', 'h-36');
  });

  it('applies active animation when isActive is true', () => {
    const { container } = render(<GlowingOrb isActive={true} />);
    const orb = container.firstChild as HTMLElement;
    expect(orb).toHaveClass('animate-pulse-glow');
  });

  it('does not apply active animation when isActive is false', () => {
    const { container } = render(<GlowingOrb isActive={false} />);
    const orb = container.firstChild as HTMLElement;
    expect(orb).not.toHaveClass('animate-pulse-glow');
  });

  it('applies custom className', () => {
    const { container } = render(<GlowingOrb className="custom-class" />);
    const orb = container.firstChild as HTMLElement;
    expect(orb).toHaveClass('custom-class');
  });
});