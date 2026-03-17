import { useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { getMessages, type MessageKey } from './messages';

function getDocumentLocale(): string | undefined {
  if (typeof document === 'undefined') return undefined;
  return document.documentElement.lang || undefined;
}

export function useT() {
  const { user } = useAppStore();
  const lang = user?.language_preference || getDocumentLocale() || 'en-US';

  const messages = useMemo(() => getMessages(lang), [lang]);

  return useMemo(() => {
    return (key: MessageKey) => messages[key] ?? key;
  }, [messages]);
}

