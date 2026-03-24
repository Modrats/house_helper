import '@testing-library/jest-dom';
import { vi, beforeEach } from 'vitest';

// Mock fetch globally so components that fetch on mount don't produce
// unhandled async state updates during routing/layout tests.
beforeEach(() => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => [],
  } as unknown as Response);
});
