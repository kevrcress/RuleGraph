interface DiffPanelProps {
  before: string | null;
  after: string | null;
  title?: string;
}

function highlight(text: string, color: "red" | "green") {
  const cls = color === "red" ? "bg-red-900/30 text-red-200" : "bg-green-900/30 text-green-200";
  return (
    <pre className={`whitespace-pre-wrap text-sm p-3 rounded font-mono ${cls} min-h-[80px]`}>
      {text}
    </pre>
  );
}

export default function RuleDiff({ before, after, title }: DiffPanelProps) {
  return (
    <div data-testid="diff-panel" className="w-full">
      {title && <h3 className="text-bone-1 text-sm font-semibold mb-2">{title}</h3>}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-bone-3 mb-1 uppercase tracking-wide">Before</div>
          <div data-testid="diff-before">
            {before ? highlight(before, "red") : (
              <div className="text-bone-4 text-sm italic p-3">No previous version</div>
            )}
          </div>
        </div>
        <div>
          <div className="text-xs text-bone-3 mb-1 uppercase tracking-wide">After</div>
          <div data-testid="diff-after">
            {after ? highlight(after, "green") : (
              <div className="text-bone-4 text-sm italic p-3">No current version</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
