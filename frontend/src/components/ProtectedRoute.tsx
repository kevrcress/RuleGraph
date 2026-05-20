import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

interface Props {
  children: React.ReactNode;
  roles?: string[];
}

export default function ProtectedRoute({ children, roles }: Props) {
  const { token, user } = useAuthStore();

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return (
      <div data-testid="access-denied" className="p-8 text-center">
        <h2 className="text-xl text-ember mb-2">Access Denied</h2>
        <p className="text-bone-2">You do not have permission to view this page.</p>
      </div>
    );
  }

  return <>{children}</>;
}
