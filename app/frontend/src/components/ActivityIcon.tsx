import Image from "next/image";
import type { SportCategory } from "@/lib/constants";

const CATEGORY_ICON_MAP: Record<SportCategory, string> = {
  run: "runner.png",
  ride: "cycling.png",
  climbing: "climber.png",
  winter: "skiing.png",
  fitness: "gym.png",
  swim: "default.png",
  water: "default.png",
  other: "default.png",
};

const SIZES = {
  xs: 14,
  sm: 16,
  md: 24,
  lg: 32,
} as const;

interface ActivityIconProps {
  /** Sport category to display icon for */
  category: SportCategory;
  /** Icon size */
  size?: keyof typeof SIZES;
  /** Additional CSS classes */
  className?: string;
}

export default function ActivityIcon({
  category,
  size = "md",
  className,
}: ActivityIconProps) {
  const filename = CATEGORY_ICON_MAP[category] ?? "default.png";
  const px = SIZES[size];

  return (
    <Image
      src={`/icons/${filename}`}
      alt={category}
      width={px}
      height={px}
      className={className}
      unoptimized
    />
  );
}

/** Venue icon for crag/gym display */
export function VenueIcon({
  venueType,
  size = "md",
  className,
}: {
  venueType: string;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const filename = venueType === "indoor_gym" ? "gym.png" : "home.png";
  const px = SIZES[size];

  return (
    <Image
      src={`/icons/${filename}`}
      alt={venueType === "indoor_gym" ? "Gym" : "Outdoor"}
      width={px}
      height={px}
      className={className}
      unoptimized
    />
  );
}
