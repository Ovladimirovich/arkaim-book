import { describe, it, expect } from 'vitest';
import React from 'react';
import { render } from '@testing-library/react';
import { Markdown } from '@/shared/lib/markdown';

describe('Markdown', () => {
  it('renders plain text', () => {
    const { container } = render(<Markdown content="Hello world" />);
    expect(container.textContent).toContain('Hello world');
  });

  it('renders bold text', () => {
    const { container } = render(<Markdown content="This is **bold** text" />);
    expect(container.textContent).toContain('bold');
  });

  it('renders code', () => {
    const { container } = render(<Markdown content="Use `console.log()` for debugging" />);
    expect(container.textContent).toContain('console.log()');
  });

  it('renders lists', () => {
    const { container } = render(<Markdown content="- Item 1\n- Item 2" />);
    expect(container.textContent).toContain('Item 1');
    expect(container.textContent).toContain('Item 2');
  });

  it('renders headers', () => {
    const { container } = render(<Markdown content="## Header" />);
    expect(container.textContent).toContain('Header');
  });

  it('handles empty content', () => {
    const { container } = render(<Markdown content="" />);
    expect(container.innerHTML).toBe('');
  });

  it('renders multiple lines', () => {
    const { container } = render(<Markdown content="Line 1\nLine 2\nLine 3" />);
    expect(container.textContent).toContain('Line 1');
    expect(container.textContent).toContain('Line 2');
    expect(container.textContent).toContain('Line 3');
  });
});
