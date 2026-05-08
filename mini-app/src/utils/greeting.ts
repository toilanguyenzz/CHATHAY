/**
 * Time-based greeting — shared util for all pages.
 */
export function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return { text: "Chào buổi sáng", emoji: "☀️", period: "sáng" };
  if (h < 18) return { text: "Chào buổi chiều", emoji: "🌤️", period: "chiều" };
  return { text: "Chào buổi tối", emoji: "🌙", period: "tối" };
}
