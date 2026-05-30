type StampProps = {
  label: string;
  rotation?: number;
  variant?: "red" | "blue";
};

export function ClassifiedStamp({ label, rotation = -3, variant = "red" }: StampProps) {
  const color = variant === "red" ? "var(--color-stamp-red)" : "var(--color-stamp-blue)";
  return (
    <span
      className="stamp"
      style={{
        transform: `rotate(${rotation}deg)`,
        color,
        borderColor: color,
      }}
    >
      {label}
    </span>
  );
}
