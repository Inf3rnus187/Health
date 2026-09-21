const WC_MIN = -1024;
const WC_MAX = 3071;
const WW_MAX = 4096;

interface RangeProps {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}

interface ControlsProps {
  wc: number;
  ww: number;
  onWc: (value: number) => void;
  onWw: (value: number) => void;
  onReset: () => void;
}

function Range({ label, value, min, max, onChange }: RangeProps) {
  return (
    <label>
      {label} {Math.round(value)}
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

export function DicomControls({ wc, ww, onWc, onWw, onReset }: ControlsProps) {
  return (
    <div className="dicom-controls">
      <Range
        label="Centre"
        value={wc}
        min={WC_MIN}
        max={WC_MAX}
        onChange={onWc}
      />
      <Range label="Fenêtre" value={ww} min={1} max={WW_MAX} onChange={onWw} />
      <button className="btn btn-ghost" type="button" onClick={onReset}>
        Auto
      </button>
    </div>
  );
}
