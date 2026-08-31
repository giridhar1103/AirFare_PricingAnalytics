export const formatCurrency = (value: number, digits = 0) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: digits
  }).format(value);

export const formatCompact = (value: number) =>
  new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);

export const formatPercent = (value: number, digits = 1) =>
  new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(value);

export const signedPercent = (value: number, digits = 1) => {
  const formatted = formatPercent(Math.abs(value), digits);
  if (Math.abs(value) < 0.00001) return formatted;
  return `${value > 0 ? "+" : "-"}${formatted}`;
};
