import { useViewStore } from "../../store/viewStore";
import { useAuthStore } from "../../store/authStore";

const ROLES_WITH_TOGGLE = ["tech_lead", "admin"];

export default function ViewToggle() {
  const { mode, toggle } = useViewStore();
  const { user } = useAuthStore();

  if (!user || !ROLES_WITH_TOGGLE.includes(user.role)) return null;

  return (
    <div className="flex items-center gap-2">
      <button
        data-testid="view-toggle"
        onClick={toggle}
        className="px-3 py-1 rounded text-sm border border-bone-3 text-bone-1 hover:border-brass-0 hover:text-brass-0 transition-colors"
      >
        Toggle View
      </button>
      <span
        data-testid="view-indicator"
        className="text-sm text-bone-2 capitalize"
      >
        {mode === "business" ? "Business" : "Technical"} View
      </span>
    </div>
  );
}
