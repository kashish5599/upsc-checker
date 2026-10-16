interface MarkedTextProps {
  text: string;
}

export default function MarkedText({ text }: MarkedTextProps) {
  const parts = text.split(/(\[\{[\s\S]*?\}\])/g);
  return (
    <>
      {parts.map((part, index) => {
        if (!part.startsWith("[{") || !part.endsWith("}]") || part.length < 4) {
          return part;
        }
        return <strong className="marked-inline" key={`marked-${index}`}>{part.slice(2, -2)}</strong>;
      })}
    </>
  );
}
