import { FlaskConical } from "lucide-react";

export function FixtureNotice({ notice }: { notice: string }) {
  return (
    <div className="fixture-notice" role="status">
      <FlaskConical size={18} aria-hidden="true" />
      <div><strong>Development mode</strong><span>{notice}</span></div>
    </div>
  );
}
