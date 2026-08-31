interface RangeControlProps {
  id: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  helper: string;
  onChange: (value: number) => void;
}

export function RangeControl({ id, label, value, min, max, step, suffix, helper, onChange }: RangeControlProps) {
  const percentage = ((value - min) / (max - min)) * 100;
  const displayValue = (number: number) => `${number > 0 ? "+" : ""}${number}${suffix}`;
  return (
    <div className="range-control">
      <div className="range-label-row">
        <label htmlFor={id}>{label}</label>
        <output htmlFor={id}>{displayValue(value)}</output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        style={{ "--range-progress": `${percentage}%` } as React.CSSProperties}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <div className="range-scale"><span>{displayValue(min)}</span><span>{helper}</span><span>{displayValue(max)}</span></div>
    </div>
  );
}
