import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <section>
      <h1 className="text-2xl font-bold">Page not found</h1>
      <p className="mt-2 text-gray-700">There's nothing at this address.</p>
      <Link to="/" className="mt-4 inline-block text-brand-700 underline">
        Go to the dashboard
      </Link>
    </section>
  );
}
