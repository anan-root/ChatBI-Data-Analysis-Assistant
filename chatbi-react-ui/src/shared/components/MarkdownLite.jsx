import { useMemo } from 'react';

export function MarkdownLite({ text }) {
  const html = useMemo(() => {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br />');
  }, [text]);

  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
